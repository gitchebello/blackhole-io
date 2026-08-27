#!/usr/bin/env python3
"""O jogo no teclado do computador: setas, wasd, diagonais, espaco, e as duas
armadilhas classicas (tecla presa por causa do shift, e alt-tab no meio)."""
import sys
from playwright.sync_api import sync_playwright
falhas = []
def ok(c, o):
    print(("  ok  " if c else "FALHA ") + o)
    if not c: falhas.append(o)

with sync_playwright() as p:
    nav = p.chromium.launch()
    ctx = nav.new_context(viewport={"width": 1366, "height": 768}, device_scale_factor=1)
    pg = ctx.new_page(); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto("http://127.0.0.1:8085/"); pg.wait_for_timeout(400)

    ok(pg.evaluate("() => PONTEIRO_FINO"), "o jogo reconheceu que ha mouse, nao dedo")
    pg.evaluate("() => jogar()"); pg.wait_for_timeout(200)
    ok(pg.evaluate("() => dicaTeclado > 0"), "a dica de teclado aparece ao comecar")
    pg.screenshot(path="/tmp/bh-dica-teclado.png")

    # Cada etapa comeca do meio do mapa e parada. Sem isso uma etapa herda a
    # velocidade e a posicao da anterior, e o boneco quica na beirada da arena
    # bem no meio da medicao — o teste acusava erro que nao existia no jogo.
    def zerar():
        # os rivais tambem vao para longe: sem isso um deles trombava com o
        # boneco no meio da medicao e o empurrao entrava na conta
        pg.evaluate("""() => { buraco.x = MUNDO.L/2; buraco.y = MUNDO.A/2;
          buraco.vx = buraco.vy = 0; espiral = 0; buraco.atordoado = 0;
          const L = limites();
          rivais.forEach((r, i) => { r.x = L.x0 + 6 + i * 4; r.y = L.y0 + 6;
                                     r.vx = r.vy = 0; }); }""")
        pg.wait_for_timeout(120)

    def anda(teclas, seg=0.7):
        zerar()
        x0, y0 = pg.evaluate("() => [buraco.x, buraco.y]")
        for t in teclas: pg.keyboard.down(t)
        pg.wait_for_timeout(int(seg * 1000))
        for t in teclas: pg.keyboard.up(t)
        pg.wait_for_timeout(450)
        x1, y1 = pg.evaluate("() => [buraco.x, buraco.y]")
        return x1 - x0, y1 - y0

    print("\n— cada direcao —")
    for teclas, esperado in ((["ArrowRight"], "x+"), (["ArrowLeft"], "x-"),
                             (["ArrowUp"], "y-"), (["ArrowDown"], "y+"),
                             (["d"], "x+"), (["a"], "x-"),
                             (["w"], "y-"), (["s"], "y+")):
        dx, dy = anda(teclas)
        eixo, sinal = esperado[0], esperado[1]
        v = dx if eixo == "x" else dy
        bom = v > 25 if sinal == "+" else v < -25
        ok(bom, "%-11s move para %s (dx %.0f dy %.0f)" % ("+".join(teclas), esperado, dx, dy))

    print("\n— diagonal —")
    dx, dy = anda(["ArrowRight", "ArrowUp"])
    ok(dx > 20 and dy < -20, "duas setas juntas andam na diagonal (dx %.0f dy %.0f)" % (dx, dy))

    print("\n— sucção —")
    zerar()
    pg.keyboard.down("ArrowRight"); pg.wait_for_timeout(600)
    v0 = pg.evaluate("() => Math.hypot(buraco.vx, buraco.vy)")
    pg.keyboard.up("ArrowRight")
    pg.keyboard.down(" "); pg.wait_for_timeout(800)
    esp, v1 = pg.evaluate("() => [espiral, Math.hypot(buraco.vx, buraco.vy)]")
    ok(esp > 0.9, "a barra de espaco liga o modo succao (espiral %.2f)" % esp)
    ok(v1 < v0 * 0.15, "e freia o boneco: %.2f -> %.2f" % (v0, v1))
    dx, dy = anda(["ArrowRight"], 0.5)   # com espaco ainda apertado
    ok(abs(dx) < 12, "segurando espaco ele nao sai passeando (andou %.1f)" % dx)
    pg.keyboard.up(" "); zerar()
    pg.keyboard.down("Shift"); pg.wait_for_timeout(400)
    ok(pg.evaluate("() => espiral") > 0.9, "shift tambem serve, para quem preferir")
    pg.keyboard.up("Shift"); pg.wait_for_timeout(300)

    print("\n— tecla presa —")
    # segura 'd', aperta shift, solta 'd': o navegador entrega o keyup como 'D'
    zerar()
    pg.keyboard.down("d"); pg.wait_for_timeout(200)
    pg.keyboard.down("Shift"); pg.wait_for_timeout(200)
    pg.keyboard.up("d"); pg.keyboard.up("Shift"); pg.wait_for_timeout(600)
    x0 = pg.evaluate("() => buraco.x"); pg.wait_for_timeout(700)
    ok(abs(pg.evaluate("() => buraco.x") - x0) < 6,
       "soltar a tecla com shift apertado nao deixa o boneco correndo sozinho")

    print("\n— sair da janela —")
    zerar()
    pg.keyboard.down("ArrowRight"); pg.wait_for_timeout(300)
    pg.evaluate("() => window.dispatchEvent(new Event('blur'))")
    ok(pg.evaluate("() => Object.keys(teclas).filter(k => teclas[k]).length") == 0,
       "as teclas foram soltas na hora")
    pg.wait_for_timeout(700)
    x0 = pg.evaluate("() => buraco.x"); pg.wait_for_timeout(700)
    ok(abs(pg.evaluate("() => buraco.x") - x0) < 6,
       "alt-tab solta as teclas em vez de deixar o comando preso")
    pg.keyboard.up("ArrowRight")

    ok(pg.evaluate("() => dicaTeclado <= 0"), "a dica ja sumiu depois de jogar um pouco")
    ok(not erros, "sem erro de javascript" + ("" if not erros else ": " + str(erros)))
    nav.close()

print()
if falhas: print("%d falha(s)" % len(falhas)); sys.exit(1)
print("tudo certo")
