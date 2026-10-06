# -*- coding: utf-8 -*-
"""Regressao: partidas completas, poderes alcancaveis, fps e erros de JS."""
import sys
from playwright.sync_api import sync_playwright
URL = "http://127.0.0.1:8085/"
PARTIDA = """(n) => {
  CFG.RIVAIS = n; gerarCamadas(); jogar();
  const pegou = {terra:0, marte:0, saturno:0, jupiter:0, urano:0, netuno:0, cometa:0, cadente:0};
  let q = 0;
  while (cena === "jogo" && q < 60 * 400) {
    let alvo = null, md = Infinity;
    for (const o of [terra, marte, saturno, jupiter, urano, netuno])
      if (o && Math.hypot(o.x-buraco.x, o.y-buraco.y) < visaoL()*0.5) alvo = o;
    if (!alvo) for (const e of estrelas) { const d = Math.hypot(e.x-buraco.x, e.y-buraco.y);
      if (d < md) { md = d; alvo = e; } }
    if (alvo) buraco.ang = Math.atan2(alvo.y-buraco.y, alvo.x-buraco.x);
    toque.ativo = true; toque.ax = 0; toque.ay = 0;
    toque.x = Math.cos(buraco.ang)*99; toque.y = Math.sin(buraco.ang)*99;
    const t0 = turbo, i0 = ima, s0 = buraco.tiro, d0 = buraco.dreno, m0 = buraco.imune, j0 = buraco.inchado,
          e0 = buraco.enjoo, c0 = buraco.comidas;
    passo(); q++;
    if (turbo > t0) pegou.terra++;
    if (ima > i0) pegou.marte++;
    if (buraco.tiro > s0) pegou.saturno++;
    if (buraco.dreno > d0) pegou.urano++;
    if (buraco.inchado > j0) pegou.jupiter++;
    if (buraco.imune > m0) pegou.netuno++;
    if (buraco.enjoo > e0) pegou.cometa++;
    if (buraco.comidas - c0 >= CFG.CADENTE_PREMIO) pegou.cadente++;
  }
  toque.ativo = false; espiral = 0;
  return { s: Math.round(q/60), eu: buraco.comidas, eles: rivais.map(r => r.comidas),
           venceu: vencedor === buraco, pegou };
}"""
FPS = """() => {
  jogar(); buraco.nivel = CFG.NIVEL_MAX; buraco.comidas = 200;
  turbo = 300; ima = 300; buraco.tiro = 300; buraco.dreno = 300; buraco.imune = 300;
  buraco.inchado = 300; buraco.nivelIncha = CFG.NIVEL_MAX + 1;
  for (let i = 0; i < 30; i++) passo();
  const t0 = performance.now(); let n = 0;
  while (performance.now() - t0 < 1000) { passo(); desenhar(); n++; }
  return n;
}"""
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 390, "height": 780})
    erros = []; pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(1300)
    for n in (1, 2, 3):
        r = pg.evaluate(PARTIDA, n)
        print("%d rival(is): %3ds | voce %3d %s | eles %s" % (
            n, r["s"], r["eu"], "venceu" if r["venceu"] else "perdeu", r["eles"]))
        print("   pegou:", r["pegou"])
    pg.evaluate("() => { sair(); }")
    print("menu->jogo->menu:", pg.evaluate("() => { const a = cena; jogar(); const b = cena; sair(); return [a, b, cena]; }"))
    print("fps nivel 15 com tudo ligado:", pg.evaluate(FPS))
    print("erros de JS:", erros if erros else "nenhum")
    b.close()
    sys.exit(1 if erros else 0)
