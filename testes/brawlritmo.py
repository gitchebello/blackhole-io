#!/usr/bin/env python3
"""Com que frequencia o cometa arco-iris pega alguem, em partida de verdade.
O jogador aqui e o mesmo robo da regressao: ele nao desvia da rota para tocar
no cometa, entao o numero e o piso — gente de verdade vai atras quando ve."""
import sys
from playwright.sync_api import sync_playwright

PARTIDA = """(n) => {
  CFG.RIVAIS = n; gerarCamadas(); jogar();
  let q = 0, teveBrawl = false, quemComecou = -1, viuNaTela = 0;
  while (cena === "jogo" && q < 60 * 400) {
    let alvo = null, md = Infinity;
    for (const o of [terra, marte, saturno, jupiter, urano, netuno])
      if (o && Math.hypot(o.x-buraco.x, o.y-buraco.y) < visaoL()*0.5) alvo = o;
    if (!alvo) for (const e of estrelas) { const d = Math.hypot(e.x-buraco.x, e.y-buraco.y);
      if (d < md) { md = d; alvo = e; } }
    if (alvo) buraco.ang = Math.atan2(alvo.y-buraco.y, alvo.x-buraco.x);
    toque.ativo = true; toque.ax = 0; toque.ay = 0;
    toque.x = Math.cos(buraco.ang)*99; toque.y = Math.sin(buraco.ang)*99;
    if (arcoiris && naTela(arcoiris.x, arcoiris.y, 0)) viuNaTela++;
    const b0 = brawl;
    passo(); q++;
    if (brawl > b0 && !teveBrawl) { teveBrawl = true; quemComecou = brawlDono ? brawlDono.slot : -1; }
  }
  toque.ativo = false; espiral = 0;
  return { brawl: teveBrawl, quem: quemComecou, viu: Math.round(viuNaTela/60),
           s: Math.round(q/60) };
}"""

N = int(sys.argv[1]) if len(sys.argv) > 1 else 8
with sync_playwright() as p:
    nav = p.chromium.launch(); pg = nav.new_page()
    pg.goto("http://127.0.0.1:8085/"); pg.wait_for_timeout(400)
    for rivais in (1, 3):
        acertos = 0; visto = []
        for i in range(N):
            r = pg.evaluate(PARTIDA, rivais)
            acertos += 1 if r["brawl"] else 0
            visto.append(r["viu"])
        print("%d rival(is): brawl em %d de %d partidas | cometa visivel %.1f s em media"
              % (rivais, acertos, N, sum(visto) / len(visto)))
    nav.close()
