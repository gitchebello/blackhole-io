# -*- coding: utf-8 -*-
"""Mostra a marca de borda em varios angulos, ampliada."""
import sys
from playwright.sync_api import sync_playwright
J = """() => {
  desenhar = () => {
    ctx.fillStyle = COR.vazio; ctx.fillRect(0, 0, VL, VA);
    const cx = VL / 2, cy = VA / 2;
    for (let k = 0; k < 8; k++) {
      const a = k / 8 * Math.PI * 2;
      const R = Math.min(VL, VA) * 0.9;
      marcaNaBorda(cx + Math.cos(a) * R, cy + Math.sin(a) * R, [COR.rivais[0].disco[4], COR.rivais[0].disco[6]]);
    }
  };
  return true;
}"""
saida = sys.argv[1] if len(sys.argv) > 1 else "/tmp/setas.png"
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":390,"height":600},
                                             device_scale_factor=3)
    pg.goto("http://127.0.0.1:8085/"); pg.wait_for_timeout(1200)
    pg.evaluate("() => { jogar(); }")
    pg.evaluate(J); pg.wait_for_timeout(400)
    pg.screenshot(path=saida)
    b.close()
