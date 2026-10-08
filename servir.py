#!/usr/bin/env python3
"""Servidor do blackhole.

Duas coisas em um processo so:

  1. serve o index.html com no-store — sem isso o celular guarda o arquivo
     antigo e as mudancas nao aparecem;
  2. atende /ws, o WebSocket das salas online.

O WebSocket e escrito na mao com a biblioteca padrao (hashlib + struct): a
maquina nao tem `websockets` instalado nem npm, e o jogo inteiro e um arquivo
so — pendurar uma dependencia aqui estragaria isso. Sao ~90 linhas: aperto de
mao do RFC 6455, leitura de quadro mascarado e escrita de quadro de texto.

O servidor NAO simula o jogo. Quem simula e o navegador do anfitriao; aqui so
existe a lista de salas e o repasse de mensagens. Assim toda a fisica continua
morando no game.html, sem uma segunda copia das regras para manter em dia.
"""
import base64, collections, functools, hashlib, http.server, json, os, random
import socket, socketserver, struct, sys, threading, time

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"   # o numero magico do RFC 6455
LETRAS = "ABCDEFGHJKLMNPQRSTUVWXYZ"   # sem I e O: confundem com 1 e 0 na fala
LOTACAO = 4                            # gente de verdade por sala
BONECOS = 8                            # gente + cpus: o jogo tem 7 rivais no maximo
NOME_MAX = 10

# Quanto tempo a sala sobrevive sem ninguem ligado. E o conserto do problema
# mais chato do online: voce cria a sala no celular e troca de app para passar
# o codigo ao seu amigo — o navegador suspende a pagina, o socket cai, e sem
# essa carencia a sala morria antes de alguem chegar a digitar as quatro
# letras. Com ela, quem volta reocupa a MESMA cadeira, com o MESMO codigo.
GRACA = 180                            # 3 minutos

# Retratos "no ar" por convidado: mandados e ainda nao confirmados por ele.
# Fila do servidor nao basta: entre aqui e o celular ha o buffer do sistema,
# o proxy, a operadora — cada um guarda segundos de mundo velho para quem tem
# internet fraca. Com a confirmacao, so sai retrato novo quando os anteriores
# chegaram, e o lento recebe POUCOS retratos, mas sempre frescos.
VOO = 4

salas = {}                             # codigo -> Sala
trava = threading.Lock()


class Sala:
    def __init__(self, codigo, anfitriao, senha, nome):
        self.codigo = codigo
        self.membros = [anfitriao]     # o da posicao 0 e sempre o anfitriao
        self.senhas = [senha]          # a chave da cadeira, para poder voltar
        self.nomes = [nome]            # o nome de cada cadeira, que vai em cima do boneco
        self.cpus = 1
        self.jogando = False
        self.seq = 0                   # numero de cada retrato, para confirmar
        self.expira = None             # quando ninguem esta ligado, o prazo

    def vazia(self):
        return not any(self.membros)

    def cpus_validas(self):
        # sozinho e preciso ao menos uma cpu; e gente + cpus cabe no campo
        return max(1 if len(self.membros) < 2 else 0,
                   min(self.cpus, BONECOS - len(self.membros)))

    def avisar(self, msg, menos=None, retrato=False):
        dados = quadro_de(msg)         # serializa uma vez so, para todos
        for m in list(self.membros):
            if m is not None and m is not menos:
                m.enviar(dados, retrato, msg.get("q", 0))

    def sala_msg(self, para):
        return {"t": "sala", "codigo": self.codigo,
                "slot": self.membros.index(para),
                "anfitriao": self.membros[0] is para,
                "quantos": len(self.membros), "cpus": self.cpus_validas(),
                "vivos": [1 if m else 0 for m in self.membros],
                "nomes": self.nomes,
                "senha": self.senhas[self.membros.index(para)],
                "jogando": self.jogando}

    def espalhar_sala(self):
        for m in list(self.membros):
            if m is not None:
                m.enviar(self.sala_msg(m))


def quadro_de(obj):
    dados = json.dumps(obj, separators=(",", ":")).encode()
    quadro = bytearray([0x81])
    n = len(dados)
    if n < 126:
        quadro.append(n)
    elif n < 65536:
        quadro.append(126)
        quadro += struct.pack(">H", n)
    else:
        quadro.append(127)
        quadro += struct.pack(">Q", n)
    return bytes(quadro + dados)


class Cliente:
    """Um WebSocket aberto, com uma FILA e uma thread de escrita proprias.

    Antes o repasse escrevia direto no socket, na thread de quem mandou. O
    retrato do anfitriao saia para os convidados um depois do outro, e bastava
    UM com a internet mais lenta (o terceiro jogador, no celular) para a
    escrita travar esperando ele: os retratos de todo mundo atrasavam, e o
    lento ainda recebia uma fila de mundos velhos, cada vez mais atrasada.

    Agora cada um tem a sua fila. Retrato e descartavel: se ainda ha um na
    fila esperando sair quando chega o seguinte, o velho e jogado fora — o
    lento recebe o mundo mais NOVO que der, nunca um acumulado de passado.
    O resto (sala, ir, menu...) sai sempre, na ordem."""

    def __init__(self, wfile, sock):
        self.wfile = wfile
        self.sock = sock
        self.fila = collections.deque()
        self.tem = threading.Condition()
        self.sala = None
        self.vivo = True
        # controle de fluxo (so para quem confirma: aba velha em cache nao manda)
        self.confirma = False
        self.ack = 0
        self.ack_t = 0.0
        self.voando = collections.deque()
        self.guardado = None
        threading.Thread(target=self._escrever, daemon=True).start()

    def enviar(self, obj, retrato=False, q=0):
        dados = obj if isinstance(obj, bytes) else quadro_de(obj)
        with self.tem:
            if not self.vivo:
                return
            if retrato and self.confirma:
                while self.voando and self.voando[0] <= self.ack:
                    self.voando.popleft()
                # confirmacao parada ha mais de 1 s: nao trava, volta a mandar
                if len(self.voando) >= VOO and time.time() - self.ack_t < 1.0:
                    self.guardado = (dados, q)     # so o mais novo espera
                    return
                self.voando.append(q)
            if retrato:
                for k, (r, _) in enumerate(self.fila):
                    if r:                      # no maximo um: o velho sai
                        del self.fila[k]
                        break
            self.fila.append((retrato, dados))
            if len(self.fila) > 400:           # parado de vez: derruba
                self.fechar_ja()
            self.tem.notify()

    def confirmar(self, q):
        with self.tem:
            self.confirma = True
            self.ack = max(self.ack, q)
            self.ack_t = time.time()
            while self.voando and self.voando[0] <= self.ack:
                self.voando.popleft()
            g = self.guardado
            if not g or len(self.voando) >= VOO:
                return
            self.guardado = None
        self.enviar(g[0], True, g[1])

    def _escrever(self):
        while True:
            with self.tem:
                while self.vivo and not self.fila:
                    self.tem.wait()
                if not self.vivo:
                    return
                _, dados = self.fila.popleft()
            try:
                self.wfile.write(dados)
                self.wfile.flush()
            except Exception:
                self.fechar()
                return

    def fechar_ja(self):                       # chamado com self.tem na mao
        self.vivo = False
        self.tem.notify()
        try:
            self.sock.shutdown(socket.SHUT_RDWR)   # solta o leitor tambem
        except OSError:
            pass

    def fechar(self):
        with self.tem:
            self.fechar_ja()


def ler_quadro(rfile):
    """Devolve o texto de um quadro, ou None se a conexao acabou.
    Junta continuacoes: navegador pode partir mensagem grande em pedacos."""
    partes = []
    while True:
        cab = rfile.read(2)
        if len(cab) < 2:
            return None
        fim = cab[0] & 0x80
        op = cab[0] & 0x0F
        mascarado = cab[1] & 0x80
        n = cab[1] & 0x7F
        if n == 126:
            n = struct.unpack(">H", rfile.read(2))[0]
        elif n == 127:
            n = struct.unpack(">Q", rfile.read(8))[0]
        if n > 1 << 22:                       # 4 MB: nada aqui chega perto
            return None
        chave = rfile.read(4) if mascarado else b"\0\0\0\0"
        corpo = rfile.read(n) if n else b""
        if len(corpo) < n:
            return None
        if mascarado:
            corpo = bytes(b ^ chave[i % 4] for i, b in enumerate(corpo))
        if op == 0x8:                          # tchau
            return None
        if op in (0x9, 0xA):                   # ping/pong: ignora
            continue
        partes.append(corpo)
        if fim:
            try:
                return b"".join(partes).decode()
            except UnicodeDecodeError:
                return None


def codigo_novo():
    while True:
        c = "".join(random.choice(LETRAS) for _ in range(4))
        if c not in salas:
            return c


def senha_nova():
    return base64.urlsafe_b64encode(os.urandom(9)).decode()


def varrer():
    """Joga fora as salas cujo prazo de carencia acabou. Roda de carona nas
    mensagens que criam ou procuram sala — nao precisa de thread propria."""
    agora = time.time()
    for c in [c for c, s in salas.items()
              if s.expira is not None and s.expira < agora]:
        salas.pop(c, None)


def sair_da_sala(cli, definitivo=False):
    """definitivo=True quando a pessoa APERTOU sair. Um socket que simplesmente
    cai e outra coisa: pode ser a tela do celular travando, e nesse caso a
    cadeira fica guardada esperando a volta."""
    with trava:
        sala = cli.sala
        cli.sala = None
        if not sala or cli not in sala.membros:
            return
        i = sala.membros.index(cli)
        era_anfitriao = i == 0

        if definitivo and era_anfitriao:
            # o dono desmontou a sala: nao ha o que guardar
            salas.pop(sala.codigo, None)
            sala.avisar({"t": "acabou", "motivo": "anfitriao"}, menos=cli)
            for m in sala.membros:
                if m is not None:
                    m.sala = None
            return

        if definitivo and not sala.jogando:
            # saiu de vez do saguao: a cadeira dele some e as outras se juntam
            sala.membros.pop(i)
            sala.senhas.pop(i)
            sala.nomes.pop(i)
        else:
            # a cadeira fica: ela e a identidade de todo mundo (cor, placar,
            # alvo de tiro), e mexer nos indices no meio da partida embaralha
            # o jogo inteiro. Quem some vira CPU ate voltar.
            sala.membros[i] = None

        if sala.vazia():
            sala.expira = time.time() + GRACA
        else:
            sala.espalhar_sala()
            if era_anfitriao:
                # sem anfitriao ninguem simula: os outros ficam sabendo e
                # esperam. Nao ha por que derrubar a sala junto.
                sala.avisar({"t": "pausa"})


def limpar_nome(v):
    nome = "".join(ch for ch in str(v or "") if ch.isprintable())
    return " ".join(nome.split())[:NOME_MAX]


def tratar(cli, msg):
    t = msg.get("t")

    if t == "criar":
        sair_da_sala(cli, definitivo=True)
        with trava:
            varrer()
            c = codigo_novo()
            sala = Sala(c, cli, senha_nova(), limpar_nome(msg.get("nome")))
            salas[c] = sala
            cli.sala = sala
            cli.enviar(sala.sala_msg(cli))
        return

    if t == "voltar":
        # a mesma pessoa reocupando a cadeira dela depois de uma queda
        cod = str(msg.get("codigo", "")).upper()[:4]
        senha = str(msg.get("senha", ""))
        with trava:
            varrer()
            sala = salas.get(cod)
            if not sala or senha not in sala.senhas:
                cli.enviar({"t": "erro", "msg": "SALA NAO EXISTE"})
                return
            i = sala.senhas.index(senha)
            antigo = sala.membros[i]
            if antigo is not None and antigo is not cli:
                antigo.fechar()            # aba velha ainda pendurada
            sala.membros[i] = cli
            cli.sala = sala
            sala.expira = None
            sala.espalhar_sala()
            if i == 0:
                sala.avisar({"t": "segue"})
        return

    if t == "entrar":
        cod = str(msg.get("codigo", "")).upper()[:4]
        sair_da_sala(cli, definitivo=True)
        with trava:
            varrer()
            sala = salas.get(cod)
            if not sala:
                cli.enviar({"t": "erro", "msg": "SALA NAO EXISTE"})
                return
            if sala.jogando:
                cli.enviar({"t": "erro", "msg": "PARTIDA EM ANDAMENTO"})
                return
            if len([m for m in sala.membros if m]) >= LOTACAO:
                cli.enviar({"t": "erro", "msg": "SALA CHEIA"})
                return
            sala.membros.append(cli)
            sala.senhas.append(senha_nova())
            sala.nomes.append(limpar_nome(msg.get("nome")))
            sala.expira = None
            cli.sala = sala
            sala.espalhar_sala()
        return

    sala = cli.sala
    if not sala:
        return
    sou_anfitriao = sala.membros and sala.membros[0] is cli

    if t == "cfg" and sou_anfitriao:
        with trava:
            sala.cpus = max(0, min(BONECOS - 1, int(msg.get("cpus", 0))))
            sala.espalhar_sala()
        return

    if t == "nome":
        with trava:
            if cli not in sala.membros:
                return
            sala.nomes[sala.membros.index(cli)] = limpar_nome(msg.get("nome"))
            sala.espalhar_sala()
        return

    if t == "ir" and sou_anfitriao:
        with trava:
            sala.jogando = True
            sala.avisar({"t": "ir", "quantos": len(sala.membros),
                         "cpus": sala.cpus_validas(), "semente": msg.get("semente", 1)})
        return

    if t == "menu" and sou_anfitriao:
        with trava:
            sala.jogando = False
            # de volta ao saguao as lapides somem e as cadeiras se juntam
            vivos = [i for i, m in enumerate(sala.membros) if m is not None]
            sala.senhas = [sala.senhas[i] for i in vivos]
            sala.nomes = [sala.nomes[i] for i in vivos]
            sala.membros = [sala.membros[i] for i in vivos]
            sala.avisar({"t": "menu"})
            sala.espalhar_sala()
        return

    if t == "e" and sou_anfitriao:          # retrato do mundo: vai para todos
        with trava:
            sala.seq += 1
            msg["q"] = sala.seq
        sala.avisar(msg, menos=cli, retrato=True)
        return

    if t == "k":                            # convidado confirmou um retrato
        try:
            cli.confirmar(int(msg.get("q", 0)))
        except (TypeError, ValueError):
            pass
        return

    if t == "i" and not sou_anfitriao:      # comando de um convidado: so o dono
        with trava:
            if cli not in sala.membros:
                return
            msg["slot"] = sala.membros.index(cli)
            dono = sala.membros[0]
        # o anfitriao pode estar fora no momento (tela travada, wi-fi caindo):
        # a cadeira dele fica vazia ate voltar, e o comando so se perde. Sem
        # esta guarda o repasse estourava e derrubava a conexao do CONVIDADO,
        # que entao perdia o aviso de que a partida tinha voltado.
        if dono is not None:
            dono.enviar(msg)
        return

    if t == "oi":
        return                              # so para o caminho nao esfriar

    if t == "tchau":
        sair_da_sala(cli, definitivo=True)


class Atendente(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?")[0] == "/ws":
            self.aperto_de_mao()
            return
        super().do_GET()

    def aperto_de_mao(self):
        # Registrado sempre, com quem pediu: e a unica forma de saber se o
        # celular de alguem esta chegando ate aqui ou parando no caminho.
        quem = self.client_address[0]
        chave = self.headers.get("Sec-WebSocket-Key")
        if not chave or "upgrade" not in \
                (self.headers.get("Connection", "") or "").lower():
            print("ws RECUSADO de %s: cabecalhos %r" % (
                quem, dict(self.headers)), flush=True)
            self.send_error(400, "esperava websocket")
            return
        print("ws ABERTO de %s (%s)" % (quem, self.headers.get("User-Agent", "?")),
              flush=True)
        aceite = base64.b64encode(
            hashlib.sha1((chave + GUID).encode()).digest()).decode()
        self.wfile.write(("HTTP/1.1 101 Switching Protocols\r\n"
                          "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                          "Sec-WebSocket-Accept: %s\r\n\r\n" % aceite).encode())
        self.wfile.flush()
        # sem Nagle: retrato pequeno nao fica esperando juntar com o proximo
        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        cli = Cliente(self.wfile, self.connection)
        try:
            while cli.vivo:
                texto = ler_quadro(self.rfile)
                if texto is None:
                    break
                try:
                    msg = json.loads(texto)
                except ValueError:
                    continue
                if isinstance(msg, dict):
                    tratar(cli, msg)
        except (OSError, struct.error):
            pass
        finally:
            print("ws FECHADO de %s" % quem, flush=True)
            cli.fechar()
            sair_da_sala(cli)
        self.close_connection = True


class Servidor(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8085
pasta = sys.argv[2] if len(sys.argv) > 2 else \
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "serve")
with Servidor(("0.0.0.0", porta),
              functools.partial(Atendente, directory=pasta)) as s:
    print("servindo %s na porta %d (ws em /ws)" % (pasta, porta), flush=True)
    s.serve_forever()
