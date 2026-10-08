#!/usr/bin/env python3
"""Duas abas jogando a mesma partida online, de ponta a ponta.

Sobe pelo servidor de verdade (http://127.0.0.1:8085): o WebSocket nao existe
em file://, e o jogo recusa de proposito quando abre por arquivo.
"""
import sys, time
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8085/"
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


with sync_playwright() as p:
    nav = p.chromium.launch()
    ctx = nav.new_context(viewport={"width": 420, "height": 820},
                          device_scale_factor=1)
    a = ctx.new_page()          # anfitriao
    b = ctx.new_page()          # convidado
    erros = []
    for pg, nome in ((a, "A"), (b, "B")):
        pg.on("pageerror", lambda e, n=nome: erros.append(n + ": " + str(e)))
        pg.goto(URL)
        pg.wait_for_timeout(400)

    print("\n— sala —")
    a.evaluate("() => { cena = 'online'; }")
    a.wait_for_timeout(200)
    a.screenshot(path="/tmp/bh-online.png")
    a.evaluate("() => ligarRede(() => mandar({t:'criar'}))")
    confere(espera(a, "cena === 'sala'"), "anfitriao entrou na sala")
    codigo = a.evaluate("() => REDE.codigo")
    print("  codigo:", codigo)
    confere(len(codigo or "") == 4, "codigo tem quatro letras")
    a.wait_for_timeout(300)
    a.screenshot(path="/tmp/bh-sala.png")

    b.evaluate("() => { cena = 'codigo'; ligarRede(() => {}); }")
    b.wait_for_timeout(400)
    b.screenshot(path="/tmp/bh-codigo.png")
    for ch in codigo:
        b.evaluate("ch => digitar(ch)", ch)
        b.wait_for_timeout(60)
    confere(espera(b, "cena === 'sala'"), "convidado entrou na sala")
    confere(a.evaluate("() => REDE.quantos") == 2, "anfitriao viu dois na sala")
    confere(b.evaluate("() => REDE.slot") == 1, "convidado ficou na cadeira 1")
    confere(not b.evaluate("() => REDE.anfitriao"), "convidado nao e anfitriao")

    print("\n— partida —")
    a.evaluate("() => mandar({t:'cfg', cpus:1})")
    a.wait_for_timeout(200)
    a.evaluate("() => mandar({t:'ir'})")
    confere(espera(a, "cena === 'jogo'"), "anfitriao comecou")
    confere(espera(b, "cena === 'jogo'"), "convidado comecou junto")
    confere(a.evaluate("() => rivais.length") == 2, "tres bonecos em campo")
    confere(a.evaluate("() => rivais.filter(r => r.humano).length") == 1,
            "um dos rivais do anfitriao e humano")
    confere(b.evaluate("() => buraco.slot") == 1, "o boneco do convidado e a cadeira 1")
    confere(b.evaluate("() => rivais.some(r => r.slot === 0)"),
            "o anfitriao aparece como rival na tela do convidado")

    # deixa a previsao assentar: nos primeiros quadros o boneco do convidado
    # ainda esta vindo do centro do mapa para o lugar que o anfitriao mandou
    a.wait_for_timeout(1200)
    # o convidado anda para a direita por dois segundos
    x0b = b.evaluate("() => buraco.x")
    x0a = a.evaluate("() => rivais.find(r => r.slot === 1).x")
    b.keyboard.down("ArrowRight")
    b.wait_for_timeout(2000)
    b.keyboard.up("ArrowRight")
    b.wait_for_timeout(400)
    dx_b = b.evaluate("() => buraco.x") - x0b
    dx_a = a.evaluate("() => rivais.find(r => r.slot === 1).x") - x0a
    print("  andou: convidado %.1f  |  visto pelo anfitriao %.1f" % (dx_b, dx_a))
    confere(dx_b > 20, "o boneco do convidado andou na tela dele")
    confere(dx_a > 20, "e andou tambem na tela do anfitriao")
    longe = a.evaluate("() => rivais.find(r => r.slot === 1).x") - b.evaluate("() => buraco.x")
    print("  desencontro entre as duas telas: %.1f px de mundo" % abs(longe))
    confere(abs(longe) < 12, "as duas telas concordam sobre onde ele esta")

    # o mundo do convidado veio do anfitriao, nao do proprio sorteio
    confere(b.evaluate("() => limitesRede !== null"), "convidado usa a arena do anfitriao")
    confere(abs(a.evaluate("() => estrelas.length")
                - b.evaluate("() => estrelas.length")) <= 1,
            "as duas telas tem o mesmo campo de estrelas")
    d = a.evaluate("""() => {
      const r = rivais.find(x => x.slot === 1);
      return Math.hypot(r.x, r.y);
    }""")
    a.wait_for_timeout(500)
    a.screenshot(path="/tmp/bh-jogo-a.png")
    b.screenshot(path="/tmp/bh-jogo-b.png")

    print("\n— brawl pela rede —")
    a.evaluate("() => { arcoiris = null; arcoirisPassou = false; esperaArcoIris = 1; }")
    a.wait_for_timeout(300)
    confere(espera(b, "arcoiris !== null", 4), "o cometa arco-iris chegou na tela do convidado")
    a.evaluate("() => { arcoiris.x = buraco.x; arcoiris.y = buraco.y; }")
    a.wait_for_timeout(400)
    confere(a.evaluate("() => brawl > 0"), "o brawl abriu no anfitriao")
    confere(espera(b, "brawl > 0", 4), "e abriu tambem no convidado")
    b.wait_for_timeout(600)
    b.screenshot(path="/tmp/bh-brawl-convidado.png")
    pos = b.evaluate("() => estrelas.map(e => [e.x, e.y])")
    b.wait_for_timeout(1500)
    pos2 = b.evaluate("() => estrelas.map(e => [e.x, e.y])")
    n = min(len(pos), len(pos2))
    andou = max([abs(pos[i][0] - pos2[i][0]) + abs(pos[i][1] - pos2[i][1])
                 for i in range(n)] or [0])
    print("   estrela que mais andou no convidado: %.2f px" % andou)
    confere(andou < 1.0, "o campo do convidado tambem fica suspenso")
    a.evaluate("() => { brawl = 2; }")
    confere(espera(b, "brawl === 0", 4), "e o fim do brawl chegou junto")

    print("\n— fim de partida —")
    a.evaluate("() => terminar(buraco)")
    time.sleep(0.6)
    confere(a.evaluate("() => cena") == "fim", "anfitriao foi para a tela de fim")
    confere(espera(b, "cena === 'fim'"), "convidado foi junto")
    confere(b.evaluate("() => vencedor && vencedor.slot") == 0,
            "os dois concordam sobre quem ganhou")
    b.wait_for_timeout(300)
    b.screenshot(path="/tmp/bh-fim-b.png")
    a.evaluate("() => mandar({t:'ir'})")
    confere(espera(a, "cena === 'jogo'") and espera(b, "cena === 'jogo'"),
            "o anfitriao recomecou para os dois")

    print("\n— quem sai vira cpu —")
    b.evaluate("() => largarSala()")
    time.sleep(1.0)
    confere(a.evaluate("() => rivais.filter(r => r.humano).length") == 0,
            "o boneco de quem saiu passou a ser cpu")
    confere(a.evaluate("() => rivais.length") == 2, "e continua em campo")


    for pg, nome in ((a, "A"), (b, "B")):
        e = pg.evaluate("() => [cena, VL, VA]")
        print("  %s: cena=%s tela=%dx%d" % (nome, e[0], e[1], e[2]))
    confere(not erros, "sem erro de javascript" + ("" if not erros else ": " + str(erros)))
    nav.close()

print()
if falhas:
    print("%d falha(s)" % len(falhas))
    sys.exit(1)
print("tudo certo")
