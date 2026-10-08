#!/usr/bin/env python3
"""Sala de tres com nomes, cpus escolhidas pelo anfitriao e um convidado LENTO.

  venv/bin/python nomes.py [url]      (padrao http://127.0.0.1:8085/)

O terceiro jogador entra por um proxy que estrangula o que DESCE para ele
(~12 KB/s, menos que os retratos pedem). O que se mede e o atraso dos
retratos no SEGUNDO jogador, o de internet boa: com o servidor antigo o lento
travava o repasse de todo mundo; agora cada um tem a sua fila.
"""
import socket, sys, threading, time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8085/"
alvo = urlparse(URL)
falhas = []


def confere(cond, o_que):
    print(("  ok  " if cond else "FALHA ") + o_que)
    if not cond:
        falhas.append(o_que)


def espera(pg, expr, seg=8):
    fim = time.time() + seg
    while time.time() < fim:
        if pg.evaluate("() => " + expr):
            return True
        time.sleep(0.1)
    return False


# ── proxy lento: so a descida (servidor -> jogador) e estrangulada ──
BYTES_POR_SEG = 12000


def proxy_lento():
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)

    def bombear(de, para, lento):
        try:
            while True:
                d = de.recv(1024 if lento else 65536)
                if not d:
                    break
                para.sendall(d)
                if lento:
                    time.sleep(len(d) / BYTES_POR_SEG)
        except OSError:
            pass
        for s in (de, para):
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def aceitar():
        while True:
            c, _ = srv.accept()
            u = socket.create_connection((alvo.hostname, alvo.port or 80))
            threading.Thread(target=bombear, args=(c, u, False), daemon=True).start()
            threading.Thread(target=bombear, args=(u, c, True), daemon=True).start()

    threading.Thread(target=aceitar, daemon=True).start()
    return srv.getsockname()[1]


porta_lenta = proxy_lento()

# o WebSocket do lento vai pelo proxy; a pagina carrega direto
DESVIO = """
(() => {
  const WS = window.WebSocket;
  window.WebSocket = function (u, p) {
    const x = new URL(u); x.host = "127.0.0.1:%d";
    return new WS(x.href, p);
  };
  window.WebSocket.prototype = WS.prototype;
})();
""" % porta_lenta

# carimbo de hora no retrato (anfitriao) e o atraso na chegada (convidados)
CARIMBO = """() => {
  const m0 = mandar;
  mandar = o => { if (o.t === "e") { o.ts = Date.now(); window.__tam = JSON.stringify(o).length; } m0(o); };
}"""
MEDIDOR = """() => {
  window.__atrasos = [];
  const r0 = receber;
  receber = m => { if (m.t === "e" && m.ts) window.__atrasos.push(Date.now() - m.ts); r0(m); };
}"""

with sync_playwright() as p:
    nav = p.chromium.launch()
    erros = []
    pags = []
    for nome, lento in (("A", False), ("B", False), ("C", True)):
        ctx = nav.new_context(viewport={"width": 420, "height": 820},
                              device_scale_factor=1)
        if lento:
            ctx.add_init_script(DESVIO)
        pg = ctx.new_page()
        pg.on("pageerror", lambda e, n=nome: erros.append(n + ": " + str(e)))
        pg.goto(URL)
        pg.evaluate("() => { localStorage.clear(); REDE.meuNome = ''; }")
        pg.wait_for_timeout(300)
        pags.append(pg)
    a, b, c = pags

    print("\n— sala e nomes —")
    a.evaluate("() => ligarRede(() => mandar({t:'criar', nome: REDE.meuNome}))")
    confere(espera(a, "cena === 'sala'"), "anfitriao criou a sala")
    codigo = a.evaluate("() => REDE.codigo")
    for pg in (b, c):
        pg.evaluate("() => { cena = 'codigo'; ligarRede(() => {}); }")
        pg.wait_for_timeout(300)
        for ch in codigo:
            pg.evaluate("ch => digitar(ch)", ch)
        confere(espera(pg, "cena === 'sala'"), "convidado entrou")
    a.wait_for_timeout(400)
    a.screenshot(path="/tmp/bh-sala-vazia.png")

    # escreve o nome do jeito que gente escreve: toca na caixa e digita
    for pg, nome in ((a, "Ana"), (b, "João"), (c, "Cris")):
        bx = pg.evaluate("() => { const r = botaoNome(); return [(r.x + r.l/2) * escala, (r.y + r.a/2) * escala]; }")
        pg.mouse.click(bx[0], bx[1])
        pg.wait_for_timeout(100)
        confere(pg.evaluate("() => document.activeElement === campoNome"),
                "tocar na caixa abre o campo do nome (%s)" % nome)
        pg.keyboard.type(nome, delay=30)
        pg.keyboard.press("Enter")          # nao pode comecar a partida
    a.wait_for_timeout(1500)
    confere(a.evaluate("() => cena") == "sala", "enter no nome nao comecou a partida")
    for pg, n in ((a, "A"), (b, "B"), (c, "C")):
        nomes = pg.evaluate("() => REDE.nomes")
        confere(nomes == ["Ana", "Joao", "Cris"], "%s ve os tres nomes: %s" % (n, nomes))
    confere(b.evaluate("() => salvo.nome") == "Joao", "o nome fica guardado no aparelho")
    a.screenshot(path="/tmp/bh-sala-nomes.png")
    b.screenshot(path="/tmp/bh-sala-convidado.png")

    print("\n— cpus —")
    confere(a.evaluate("() => cpusMax()") == 5, "com tres pessoas cabem ate 5 cpus")
    r = a.evaluate("() => { const r = botaoCpu(5); return [(r.x + r.l/2) * escala, (r.y + r.a/2) * escala]; }")
    a.mouse.click(r[0], r[1])
    confere(espera(b, "REDE.cpus === 5", 4), "anfitriao escolheu 5 cpus e o convidado ve")
    r = b.evaluate("() => { const r = botaoCpu(2); return [(r.x + r.l/2) * escala, (r.y + r.a/2) * escala]; }")
    b.mouse.click(r[0], r[1])
    b.wait_for_timeout(600)
    confere(a.evaluate("() => REDE.cpus") == 5, "convidado nao muda as cpus")

    print("\n— partida —")
    a.evaluate("() => { mandar({t:'ir'}); }")
    for pg in pags:
        confere(espera(pg, "cena === 'jogo'"), "comecou")
    confere(a.evaluate("() => rivais.length") == 7, "3 pessoas + 5 cpus = 8 bonecos")
    confere(a.evaluate("() => rivais.filter(r => r.humano).length") == 2,
            "dois rivais humanos no anfitriao")
    confere(b.evaluate("() => rivais.filter(r => r.humano).map(r => nomeDe(r)).sort().join()")
            == "Ana,Cris", "no placar do convidado os nomes sao os da sala")

    a.evaluate(CARIMBO)
    b.evaluate(MEDIDOR)
    c.evaluate(MEDIDOR)
    # o convidado B anda um pouco, para os bonecos se espalharem na tela
    b.keyboard.down("ArrowRight"); b.wait_for_timeout(800); b.keyboard.up("ArrowRight")
    a.wait_for_timeout(9000)
    tam = a.evaluate("() => window.__tam")
    print("   retrato com 8 bonecos: %d bytes (%.0f KB/s por convidado)" % (tam, tam * 20 / 1000))

    def resumo(pg):
        v = sorted(pg.evaluate("() => window.__atrasos.slice(40)"))
        if not v:
            return 0, 0, 0
        return v[len(v) // 2], v[int(len(v) * 0.95)], len(v)
    mb, pb, nb = resumo(b)
    mc, pc, nc = resumo(c)
    print("   B (internet boa):  mediana %4d ms  p95 %5d ms  (%d retratos)" % (mb, pb, nb))
    print("   C (internet lenta): mediana %4d ms  p95 %5d ms  (%d retratos)" % (mc, pc, nc))
    confere(pb < 150, "o lento nao atrasa o jogador de internet boa")
    confere(pc < 3000, "o lento recebe mundo recente, nao uma fila de passado")

    # plaquinhas: tira foto com os tres perto um do outro
    a.evaluate("""() => {
      const hs = rivais.filter(r => r.humano);
      hs[0].x = buraco.x + 45; hs[0].y = buraco.y - 10;
      hs[1].x = buraco.x - 40; hs[1].y = buraco.y + 30;
    }""")
    b.wait_for_timeout(1200)
    a.screenshot(path="/tmp/bh-placas-a.png")
    b.screenshot(path="/tmp/bh-placas-b.png")

    confere(not erros, "sem erro de javascript" + ("" if not erros else ": " + str(erros)))
    nav.close()

print()
if falhas:
    print("%d falha(s)" % len(falhas))
    sys.exit(1)
print("tudo certo")
