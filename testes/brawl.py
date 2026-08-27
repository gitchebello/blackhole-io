#!/usr/bin/env python3
"""O cometa arco-iris e o modo BRAWL: nasce uma vez so, e quando alguem
encosta nele as estrelas param de valer por 15 segundos."""
import sys, time
from playwright.sync_api import sync_playwright

falhas = []
def confere(c, o):
    print(("  ok  " if c else "FALHA ") + o)
    if not c: falhas.append(o)

with sync_playwright() as p:
    nav = p.chromium.launch()
    ctx = nav.new_context(viewport={"width": 420, "height": 820}, device_scale_factor=1)
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto("http://127.0.0.1:8085/")
    pg.wait_for_timeout(400)
    pg.evaluate("() => { jogar(); }")
    pg.wait_for_timeout(300)

    # o relogio: ele nao nasce antes da hora
    confere(pg.evaluate("() => arcoiris === null"), "no comeco nao ha cometa arco-iris")
    q = pg.evaluate("() => esperaArcoIris")
    confere(abs(q - 3300) < 60, "o relogio comeca em ~55 s (esta em %d quadros)" % q)

    # forca o nascimento
    pg.evaluate("() => { esperaArcoIris = 1; }")
    pg.wait_for_timeout(300)
    confere(pg.evaluate("() => arcoiris !== null"), "nasceu quando o relogio zerou")
    pg.wait_for_timeout(400)
    pg.screenshot(path="/tmp/bh-arcoiris.png")

    est0 = pg.evaluate("() => estrelas.length")
    com0 = pg.evaluate("() => buraco.comidas")
    # empurra o cometa em cima do jogador
    pg.evaluate("() => { arcoiris.x = buraco.x; arcoiris.y = buraco.y; }")
    pg.wait_for_timeout(300)
    confere(pg.evaluate("() => brawl > 0"), "encostou e abriu o brawl")
    confere(pg.evaluate("() => arcoiris === null"), "o cometa se desfez no impacto")
    dur = pg.evaluate("() => brawl")
    confere(dur > 780, "o brawl dura ~15 s (%d quadros no relogio)" % dur)
    pg.wait_for_timeout(700)
    pg.screenshot(path="/tmp/bh-brawl.png")

    # durante o brawl nenhuma estrela e comida nem reposta
    n1 = pg.evaluate("() => estrelas.length")
    c1 = pg.evaluate("() => buraco.comidas")
    pg.keyboard.down("ArrowRight")
    pg.wait_for_timeout(2500)
    pg.keyboard.up("ArrowRight")
    n2 = pg.evaluate("() => estrelas.length")
    c2 = pg.evaluate("() => buraco.comidas")
    print("   estrelas %d -> %d | comidas %d -> %d" % (n1, n2, c1, c2))
    confere(n2 == n1, "nenhuma estrela sumiu nem entrou no campo")
    confere(pg.evaluate("() => estrelas.every(e => Math.hypot(e.vx, e.vy) < 0.05)"),
            "as estrelas estao suspensas, paradas no lugar")
    confere(pg.evaluate("() => coracoes.length > 5"), "coracoes vazando das laterais")

    # os poderes continuam valendo: tirar do outro ainda soma
    ant = pg.evaluate("() => buraco.comidas")
    pg.evaluate("""() => { const r = rivais[0]; r.comidas = 40;
                           buraco.dreno = 200; buraco.ritmoDreno = 1;
                           r.x = buraco.x + 10; r.y = buraco.y; }""")
    pg.wait_for_timeout(1200)
    dep = pg.evaluate("() => buraco.comidas")
    print("   dreno no brawl: %d -> %d" % (ant, dep))
    confere(dep > ant, "roubar do adversario ainda soma estrela no brawl")

    # trombada no brawl passa estrela de um para o outro, nao joga no chao
    pg.evaluate("""() => { brawl = 600; esperaColisao = 0;
      // quem perde a trombada e quem tem MENOS estrela: o rival, aqui
      const r = rivais[0]; r.comidas = 40; r.imune = 0; buraco.imune = 0;
      buraco.comidas = 90;
      r.x = buraco.x + 1; r.y = buraco.y; r.vx = r.vy = 0; }""")
    est_a = pg.evaluate("() => estrelas.length")
    meu_a = pg.evaluate("() => buraco.comidas")
    pg.wait_for_timeout(1500)
    est_d = pg.evaluate("() => estrelas.length")
    meu_d = pg.evaluate("() => buraco.comidas")
    print("   trombada no brawl: campo %d -> %d | voce %d -> %d" % (est_a, est_d, meu_a, meu_d))
    confere(est_d == est_a, "a trombada nao despeja estrela no chao congelado")
    confere(meu_d > meu_a, "quem venceu a trombada ficou com as estrelas")
    confere(pg.evaluate("() => rivais[0].comidas") < 40, "e quem perdeu pagou por elas")

    # e acaba sozinho
    pg.evaluate("() => { brawl = 2; }")
    pg.wait_for_timeout(400)
    confere(pg.evaluate("() => brawl === 0"), "o brawl acabou no fim do relogio")
    pg.wait_for_timeout(1500)
    confere(pg.evaluate("() => estrelas.length") >= n2,
            "o campo voltou a repor estrelas depois do brawl")
    confere(pg.evaluate("() => arcoirisPassou && arcoiris === null"),
            "e o cometa nao volta: uma passagem por partida")
    confere(not erros, "sem erro de javascript" + ("" if not erros else ": " + str(erros)))
    nav.close()

print()
if falhas:
    print("%d falha(s)" % len(falhas)); sys.exit(1)
print("tudo certo")
