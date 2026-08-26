# -*- coding: utf-8 -*-
"""Confere que o modo succao freia e so liga com o jogador parado."""
from playwright.sync_api import sync_playwright
J = """() => {
  jogar();
  // acelera para a direita ate a velocidade de cruzeiro
  teclas.d = true;
  for (let i = 0; i < 90; i++) passo();
  const vAntes = Math.hypot(buraco.vx, buraco.vy) * zoom;
  teclas.d = false; teclas[" "] = true;
  const trilha = [];
  for (let i = 0; i < 40; i++) {
    passo();
    trilha.push([i + 1, +(Math.hypot(buraco.vx, buraco.vy) * zoom).toFixed(3), +espiral.toFixed(2)]);
  }
  // e enquanto anda COM a tecla apertada, tentando fugir
  teclas.d = true;
  for (let i = 0; i < 30; i++) passo();
  const andandoV = Math.hypot(buraco.vx, buraco.vy) * zoom, andandoE = espiral;
  teclas.d = false; teclas[" "] = false;
  for (let i = 0; i < 20; i++) passo();
  return { vAntes: +vAntes.toFixed(2), trilha,
           andando: [+andandoV.toFixed(2), +andandoE.toFixed(2)],
           depoisDeSoltar: +espiral.toFixed(2) };
}"""
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width":1920,"height":1080})
    erros=[]; pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto("http://127.0.0.1:8085/"); pg.wait_for_timeout(1200)
    r = pg.evaluate(J)
    print("velocidade de cruzeiro:", r["vAntes"], "px de tela por quadro")
    print("quadro | velocidade | espiral")
    for q, v, e in r["trilha"]:
        if q <= 12 or q % 6 == 0: print("  %2d   |   %6.3f   |  %.2f" % (q, v, e))
    print("segurando espaco e apertando D:", r["andando"], "(velocidade, espiral)")
    print("espiral ao soltar:", r["depoisDeSoltar"])
    print("erros:", erros)
    b.close()
