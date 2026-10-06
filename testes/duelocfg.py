# -*- coding: utf-8 -*-
"""Taxa de vitoria por configuracao. Uso: duelocfg.py casos.json [rivais] [n]"""
import sys, json, statistics
from playwright.sync_api import sync_playwright
PARTIDA = """(cfg) => {
  Object.assign(CFG, cfg); gerarCamadas(); jogar();
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
    passo(); q++;
  }
  toque.ativo = false; espiral = 0;
  return { venceu: vencedor === buraco, eu: buraco.comidas,
           melhorRival: Math.max(...rivais.map(r => r.comidas)), s: Math.round(q/60) };
}"""
casos = json.load(open(sys.argv[1]))
rivais = int(sys.argv[2]) if len(sys.argv) > 2 else 3
n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":390,"height":780})
    pg.goto("http://127.0.0.1:8085/"); pg.wait_for_timeout(1300)
    for nome, cfg in casos:
        cfg = dict(cfg); cfg["RIVAIS"] = rivais
        rs = [pg.evaluate(PARTIDA, cfg) for _ in range(n)]
        v = sum(1 for r in rs if r["venceu"])
        print("%-32s jogador venceu %d/%d | melhor rival medio %3d | %ds" % (
            nome, v, n, statistics.mean(r["melhorRival"] for r in rs),
            statistics.mean(r["s"] for r in rs)))
    b.close()
