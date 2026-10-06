# -*- coding: utf-8 -*-
"""Forca da CPU sem o ruido do 'quem cruza 300 primeiro': partida de duracao
FIXA, meta inalcancavel, e mede quantas estrelas cada lado juntou."""
import sys, json, statistics
from playwright.sync_api import sync_playwright
SIM = """([cfg, segundos]) => {
  Object.assign(CFG, cfg); CFG.META = 99999; gerarCamadas(); jogar();
  for (let q = 0; q < 60 * segundos; q++) {
    let alvo = null, md = Infinity;
    for (const o of [terra, marte, saturno, jupiter, urano, netuno])
      if (o && Math.hypot(o.x-buraco.x, o.y-buraco.y) < visaoL()*0.5) alvo = o;
    if (!alvo) for (const e of estrelas) { const d = Math.hypot(e.x-buraco.x, e.y-buraco.y);
      if (d < md) { md = d; alvo = e; } }
    if (alvo) buraco.ang = Math.atan2(alvo.y-buraco.y, alvo.x-buraco.x);
    toque.ativo = true; toque.ax = 0; toque.ay = 0;
    toque.x = Math.cos(buraco.ang)*99; toque.y = Math.sin(buraco.ang)*99;
    passo();
  }
  toque.ativo = false; espiral = 0;
  return { eu: buraco.comidas, rivais: rivais.map(r => r.comidas) };
}"""
casos = json.load(open(sys.argv[1]))
rivais = int(sys.argv[2]) if len(sys.argv) > 2 else 3
n = int(sys.argv[3]) if len(sys.argv) > 3 else 8
segs = int(sys.argv[4]) if len(sys.argv) > 4 else 90
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":390,"height":780})
    pg.goto("http://127.0.0.1:8085/"); pg.wait_for_timeout(1300)
    print("%d rival(is), %ds de partida, %d rodadas" % (rivais, segs, n))
    for nome, cfg in casos:
        cfg = dict(cfg); cfg["RIVAIS"] = rivais
        rs = [pg.evaluate(SIM, [cfg, segs]) for _ in range(n)]
        eu = statistics.mean(r["eu"] for r in rs)
        mel = statistics.mean(max(r["rivais"]) for r in rs)
        tod = statistics.mean(statistics.mean(r["rivais"]) for r in rs)
        print("  %-30s jogador %5.1f | melhor rival %5.1f | media dos rivais %5.1f | vantagem %+5.1f"
              % (nome, eu, mel, tod, eu - mel))
    b.close()
