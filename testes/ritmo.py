# -*- coding: utf-8 -*-
"""Onde a partida acelera: tempo para cada marco de 50 estrelas."""
import sys, json, statistics
from playwright.sync_api import sync_playwright
SIM = """(cfg) => {
  Object.assign(CFG, cfg); gerarCamadas(); jogar();
  const marcos = {}; const campo = [];
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
    const m = Math.floor(buraco.comidas / 50) * 50;
    if (m > 0 && !(m in marcos)) marcos[m] = q / 60;
    if (q % 1800 === 0) campo.push(estrelas.length);
  }
  toque.ativo = false; espiral = 0;
  return { marcos, campo, s: q / 60, nivel: buraco.nivel };
}"""
casos = json.load(open(sys.argv[1]))
n = int(sys.argv[2]) if len(sys.argv) > 2 else 8
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":390,"height":780})
    pg.goto("http://127.0.0.1:8085/"); pg.wait_for_timeout(1300)
    for nome, cfg in casos:
        cfg = dict(cfg); cfg["RIVAIS"] = 1
        rs = [pg.evaluate(SIM, cfg) for _ in range(n)]
        print(nome)
        ant = 0
        for m in range(50, 301, 50):
            ts = [r["marcos"][str(m)] for r in rs if str(m) in r["marcos"]]
            if not ts: print("   %3d: nunca" % m); continue
            t = statistics.mean(ts)
            print("   %3d estrelas: %5.1fs  (+%4.1fs)  [%d de %d partidas]"
                  % (m, t, t - ant, len(ts), n)); ant = t
        campo = [r["campo"] for r in rs]
        maxlen = max(len(c) for c in campo)
        med = [round(statistics.mean(c[i] for c in campo if len(c) > i)) for i in range(maxlen)]
        print("   estrelas no campo a cada 30s:", med)
    b.close()
