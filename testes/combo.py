# -*- coding: utf-8 -*-
"""Prêmio do combo (x10 +1, x20 +2, x30 +3...), quebra da sequência e cor do número.
Uso: combo.py [url]  — salva prints em /tmp/combo_*.png"""
import sys
from playwright.sync_api import sync_playwright
url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8085/"
PREMIOS = """() => {
  jogar(); buraco.combo = 0; buraco.comboT = 0;
  const ganhos = [];
  for (let i = 1; i <= 40; i++) {
    const antes = buraco.comidas; contarCombo(buraco);
    if (buraco.comidas !== antes) ganhos.push([buraco.combo, buraco.comidas - antes]);
  }
  buraco.comboT = 0;                       // a janela fechou: recomeça
  contarCombo(buraco);
  return { ganhos: ganhos, depoisDaQuebra: buraco.combo, janela: CFG.COMBO_JANELA };
}"""
PREPARA = """(n) => { buraco.combo = n; buraco.comboT = 999; comboPop = 0; }"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":420,"height":820})
    erros = []; pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(url); pg.wait_for_timeout(1300)
    print(pg.evaluate(PREMIOS))
    for n in (4, 14):
        pg.evaluate(PREPARA, n); pg.wait_for_timeout(250)
        x = pg.evaluate("paraTelaX(buraco.x)") * 2; y = pg.evaluate("paraTelaY(buraco.y)") * 2
        pg.screenshot(path=f"/tmp/combo_{n}.png",
                      clip={"x": max(0, x - 100), "y": max(0, y - 160), "width": 200, "height": 220})
    print("erros:", erros or "nenhum")
    b.close()
