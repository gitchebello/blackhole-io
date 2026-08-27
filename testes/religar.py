#!/usr/bin/env python3
"""A queda de conexao no navegador: a pagina tem de voltar sozinha para a
mesma cadeira, com o mesmo codigo, sem jogar ninguem para fora."""
import sys, time
from playwright.sync_api import sync_playwright
falhas = []
def ok(c, o):
    print(("  ok  " if c else "FALHA ") + o)
    if not c: falhas.append(o)
def espera(pg, e, seg=14):
    f = time.time() + seg
    while time.time() < f:
        if pg.evaluate("() => " + e): return True
        time.sleep(0.15)
    return False

with sync_playwright() as p:
    nav = p.chromium.launch()
    ctx = nav.new_context(viewport={"width": 390, "height": 780}, device_scale_factor=1)
    a = ctx.new_page(); b = ctx.new_page(); erros = []
    for pg in (a, b):
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.goto("http://127.0.0.1:8085/"); pg.wait_for_timeout(400)

    print("— o celular do anfitriao trava a tela no saguao —")
    a.evaluate("() => { cena='online'; ligarRede(() => mandar({t:'criar'})); }")
    ok(espera(a, "cena === 'sala'"), "sala criada")
    cod = a.evaluate("() => REDE.codigo")
    a.evaluate("() => REDE.ws.close()")
    a.wait_for_timeout(300)
    ok(a.evaluate("() => REDE.caiu"), "a pagina percebeu a queda")
    a.screenshot(path="/tmp/bh-religando.png")
    ok(espera(a, "!REDE.caiu && cena === 'sala'"), "religou sozinha")
    ok(a.evaluate("() => REDE.codigo") == cod, "com o mesmo codigo")
    ok(a.evaluate("() => REDE.anfitriao"), "e continua anfitria")

    print("\n— o amigo entra —")
    b.evaluate("c => { cena='codigo'; ligarRede(() => setTimeout(() => { for (const ch of c) digitar(ch); }, 300)); }", cod)
    ok(espera(b, "cena === 'sala'"), "o amigo entrou na sala")
    ok(espera(a, "REDE.quantos === 2"), "e o anfitriao viu ele chegar")

    print("\n— queda no meio da partida —")
    a.evaluate("() => mandar({t:'ir'})")
    ok(espera(a, "cena === 'jogo'") and espera(b, "cena === 'jogo'"), "partida comecou")
    a.wait_for_timeout(1200)
    onde = b.evaluate("() => [buraco.x, buraco.y]")
    a.evaluate("() => REDE.ws.close()")
    a.wait_for_timeout(700)
    ok(b.evaluate("() => REDE.pausado"), "o convidado soube que o anfitriao caiu")
    b.screenshot(path="/tmp/bh-pausado.png")
    b.wait_for_timeout(1200)
    parado = b.evaluate("() => [buraco.x, buraco.y]")
    ok(abs(parado[0] - onde[0]) + abs(parado[1] - onde[1]) < 2,
       "e o boneco dele congelou em vez de sair andando sozinho")
    ok(espera(a, "!REDE.caiu"), "o anfitriao religou no meio da partida")
    ok(espera(b, "!REDE.pausado", 10), "e a partida seguiu para o convidado")
    ok(b.evaluate("() => cena") == "jogo", "ninguem foi jogado para fora")

    print("\n— o convidado tambem cai e volta —")
    b.evaluate("() => REDE.ws.close()")
    b.wait_for_timeout(400)
    ok(espera(b, "!REDE.caiu"), "o convidado religou")
    ok(b.evaluate("() => buraco.slot") == 1, "voltou para a mesma cadeira")
    ok(espera(a, "rivais.some(r => r.humano)", 6), "e o anfitriao voltou a obedecer o comando dele")
    ok(not erros, "sem erro de javascript" + ("" if not erros else ": " + str(erros)))
    nav.close()
print()
if falhas: print("%d falha(s)" % len(falhas)); sys.exit(1)
print("tudo certo")
