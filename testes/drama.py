# -*- coding: utf-8 -*-
"""Duração da engolida por tamanho da vítima (tempo real, com o laço rodando).
Uso: drama.py [url]"""
import sys
from playwright.sync_api import sync_playwright
url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8085/"
MEDE = """async ([eu, ele]) => {
  jogar();
  buraco.nivel = eu; raioTela = raioTelaBase = raioTelaNivel(eu); zoom = zoomAlvo = zoomDoNivel(eu);
  const r = rivais[0];
  r.nivel = ele; r.imune = 0; r.cuspido = 0; r.digerindo = 0; buraco.digerindo = 0;
  r.x = buraco.x + raioDe(buraco) * 0.5; r.y = buraco.y;
  const rel = raioDe(r) / raioDe(buraco);
  const t0 = performance.now();
  engolirRival(buraco, r);
  const dur = r.engolido, faixa = drama ? drama.soco : 0;
  while (r.engolido > 0) await new Promise(ok => setTimeout(ok, 5));
  return { rel: rel.toFixed(2), quadros: dur, ms: Math.round(performance.now() - t0),
           zoom: faixa.toFixed(2), lento: lentoForca.toFixed(2) };
}"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":420,"height":820})
    erros = []; pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(url); pg.wait_for_timeout(1300)
    for eu, ele in [(16, 0), (12, 4), (8, 3), (8, 5), (6, 4), (8, 6), (16, 14)]:
        print("eu", eu, "ele", ele, pg.evaluate(MEDE, [eu, ele]))
    print("erros:", erros or "nenhum")
    b.close()
