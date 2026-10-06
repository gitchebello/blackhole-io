# -*- coding: utf-8 -*-
"""Desenha os cinco planetas lado a lado, ampliados, para comparar."""
from playwright.sync_api import sync_playwright
J = """() => {
  desenhar = () => {
  const R = CFG.TERRA_RAIO, P = 30;
  ctx.fillStyle = COR.vazio; ctx.fillRect(0, 0, VL, VA);
  const nomes = ["terra","marte","saturno","jupiter","urano","netuno"];
  const spr = { terra: terraSprite, marte: marteSprite, saturno: saturnoSprite,
                jupiter: jupiterSprite, urano: uranoSprite, netuno: netunoSprite };
  nomes.forEach((n, i) => {
    const cx = Math.round(VL / 2), cy = 22 + i * P;
    if (n === "saturno") anelSaturno(cx, cy, R, false);
    if (n === "urano") anelUrano(cx, cy, R, false);
    anel(cx, cy, R + 1, 1.6, COR["cont" + n[0].toUpperCase() + n.slice(1)]);
    ctx.drawImage(spr[n], cx - R, cy - R);
    if (n === "saturno") anelSaturno(cx, cy, R, true);
    if (n === "urano") anelUrano(cx, cy, R, true);
    texto(n, 8, cy - 4, COR.hud, 1);
  });
  };
  return true;
}"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":390,"height":780},
                                             device_scale_factor=4)
    pg.goto("http://127.0.0.1:8085/"); pg.wait_for_timeout(1200)
    pg.evaluate("() => { aplicarFundo(false); }"); pg.wait_for_timeout(700)
    pg.evaluate(J)
    pg.screenshot(path="/tmp/planetas.png", clip={"x":0,"y":0,"width":390,"height":320})
    b.close()
