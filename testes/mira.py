# -*- coding: utf-8 -*-
"""Mede o COMPORTAMENTO pedido: quando a CPU vai para cima de alguem, com que
frequencia esse alguem e o lider? E quanto ela tira de quem esta na frente?"""
import sys, json, statistics
from playwright.sync_api import sync_playwright
SIM = """([cfg, segundos]) => {
  Object.assign(CFG, cfg); CFG.META = 99999; gerarCamadas(); jogar();
  let caca = 0, noLider = 0, tirouDoLider = 0;
  const antes = new Map();
  for (let q = 0; q < 60 * segundos; q++) {
    let alvo = null, md = Infinity;
    for (const o of [terra, marte, saturno, jupiter, urano, netuno])
      if (o && Math.hypot(o.x-buraco.x, o.y-buraco.y) < visaoL()*0.5) alvo = o;
    if (!alvo) for (const e of estrelas) { const d = Math.hypot(e.x-buraco.x, e.y-buraco.y);
      if (d < md) { md = d; alvo = e; } }
    if (alvo) buraco.ang = Math.atan2(alvo.y-buraco.y, alvo.x-buraco.x);
    toque.ativo = true; toque.ax = 0; toque.ay = 0;
    toque.x = Math.cos(buraco.ang)*99; toque.y = Math.sin(buraco.ang)*99;
    const todosAgora = todos();
    let chefe = todosAgora[0];
    for (const p of todosAgora) if (p.comidas > chefe.comidas) chefe = p;
    const marca = chefe.comidas;
    passo();
    // quantos rivais estao mirando um ADVERSARIO (e nao uma estrela/planeta)
    for (const r of rivais) {
      if (!r.alvo || todosAgora.indexOf(r.alvo) < 0) continue;
      caca++;
      if (r.alvo === chefe) noLider++;
    }
    if (chefe !== buraco || true) {
      const perdeu = marca - chefe.comidas;
      if (perdeu > 0) tirouDoLider += perdeu;
    }
  }
  toque.ativo = false; espiral = 0;
  return { caca, noLider, tirouDoLider };
}"""
casos = json.load(open(sys.argv[1]))
rivais = int(sys.argv[2]) if len(sys.argv) > 2 else 3
n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":390,"height":780})
    pg.goto("http://127.0.0.1:8085/"); pg.wait_for_timeout(1300)
    print("%d rival(is), %d rodadas de 90s" % (rivais, n))
    for nome, cfg in casos:
        cfg = dict(cfg); cfg["RIVAIS"] = rivais
        rs = [pg.evaluate(SIM, [cfg, 90]) for _ in range(n)]
        caca = sum(r["caca"] for r in rs); lid = sum(r["noLider"] for r in rs)
        print("  %-28s investidas miradas no LIDER: %4.1f%% | estrelas tiradas de quem lidera: %5.1f"
              % (nome, 100.0*lid/max(1,caca), statistics.mean(r["tirouDoLider"] for r in rs)))
    b.close()
