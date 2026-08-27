#!/usr/bin/env python3
"""A sala tem de sobreviver ao celular do anfitriao travando a tela.
Fala WebSocket na unha, para poder derrubar a conexao na hora exata."""
import socket, base64, os, struct, json, time, sys
G = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
falhas = []
def confere(c, o):
    print(("  ok  " if c else "FALHA ") + o)
    if not c: falhas.append(o)

def liga():
    s = socket.create_connection(("127.0.0.1", 8085))
    k = base64.b64encode(os.urandom(16)).decode()
    s.send(("GET /ws HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n" % k).encode())
    s.settimeout(4); s.recv(400); return s

def manda(s, o):
    d = json.dumps(o).encode(); m = os.urandom(4)
    s.send(bytearray([0x81, 0x80 | len(d)]) + m + bytes(b ^ m[i % 4] for i, b in enumerate(d)))

def le(s):
    h = s.recv(2); n = h[1] & 0x7f
    if n == 126: n = struct.unpack(">H", s.recv(2))[0]
    dados = b""
    while len(dados) < n: dados += s.recv(n - len(dados))
    return json.loads(dados.decode())

print("— o anfitriao cria e a tela do celular trava —")
a = liga(); manda(a, {"t": "criar"}); m = le(a)
cod, senha = m["codigo"], m["senha"]
print("  sala", cod)
confere(bool(senha), "a sala veio com senha de cadeira")
a.close()
time.sleep(0.6)

b = liga(); manda(b, {"t": "entrar", "codigo": cod}); r = le(b)
confere(r["t"] == "sala", "o amigo consegue entrar mesmo com o anfitriao fora")
confere(r["slot"] == 1, "e senta na cadeira 1")

print("\n— o anfitriao volta —")
a2 = liga(); manda(a2, {"t": "voltar", "codigo": cod, "senha": senha}); r = le(a2)
confere(r["t"] == "sala", "reocupou a cadeira")
confere(r["slot"] == 0 and r["anfitriao"], "e voltou como anfitriao, na cadeira 0")
confere(r["codigo"] == cod, "com o mesmo codigo")
r2 = le(b)
confere(r2["quantos"] == 2, "o amigo viu a sala completa de novo")

print("\n— senha errada nao rouba cadeira —")
c = liga(); manda(c, {"t": "voltar", "codigo": cod, "senha": "xxxx"}); r = le(c)
confere(r["t"] == "erro", "senha errada e recusada")
c.close()

print("\n— a sala vazia so morre depois da carencia —")
manda(a2, {"t": "tchau"}); time.sleep(0.3)
d = liga(); manda(d, {"t": "entrar", "codigo": cod}); r = le(d)
confere(r["t"] == "erro", "sair de proposito desmonta a sala na hora")
for s in (a2, b, d):
    try: s.close()
    except Exception: pass

print()
if falhas:
    print("%d falha(s)" % len(falhas)); sys.exit(1)
print("tudo certo")
