# -*- coding: utf-8 -*-
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":1920,"height":1080})
    erros=[]; pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto("http://127.0.0.1:8085/"); pg.wait_for_timeout(1200)
    pg.screenshot(path="/tmp/d_menu.png")
    pg.evaluate("() => { jogar(); for(let i=0;i<60*45;i++) passo(); }")
    pg.wait_for_timeout(300); pg.screenshot(path="/tmp/d_jogo.png")
    # teclado: anda e suga
    pg.evaluate("() => { buraco.vx = buraco.vy = 0; }")
    x0 = pg.evaluate("() => [buraco.x, buraco.y]")
    pg.keyboard.down("d"); pg.evaluate("() => { for(let i=0;i<30;i++) passo(); }"); pg.keyboard.up("d")
    x1 = pg.evaluate("() => [buraco.x, buraco.y]")
    pg.keyboard.down("Shift"); pg.evaluate("() => { for(let i=0;i<30;i++) passo(); }")
    esp = pg.evaluate("() => espiral"); pg.keyboard.up("Shift")
    pg.evaluate("() => { for(let i=0;i<40;i++) passo(); }")
    print("andou com D:", round(x1[0]-x0[0], 1), "px | espiral com shift:", round(esp,2),
          "| depois de soltar:", round(pg.evaluate("() => espiral"),2))
    # placar final
    pg.evaluate("() => { buraco.comidas = CFG.META; terminar(buraco); }")
    pg.evaluate("() => { for(let i=0;i<40;i++) passo(); }"); pg.wait_for_timeout(200)
    pg.screenshot(path="/tmp/d_fim.png")
    print("erros:", erros)
    b.close()
