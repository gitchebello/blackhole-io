# -*- coding: utf-8 -*-
"""Mede o campo de jogo e confere se a UI cabe em varias telas."""
from playwright.sync_api import sync_playwright
TELAS = [("celular em pe", 390, 780), ("celular pequeno", 360, 640),
         ("celular deitado", 780, 390), ("tablet", 820, 1180),
         ("notebook", 1366, 768), ("desktop", 1920, 1080),
         ("2k", 2560, 1440), ("ultrawide", 3440, 1440)]
J = """() => {
  const caixas = [["jogar", botaoJogar()], ["online", botaoOnline()],
                  ["som", botaoSom()], ["fundo", botaoFundo()], ["visual", botaoVisual()]];
  for (let i = 0; i < CFG.OPCOES_RIVAIS.length; i++) caixas.push(["op" + i, botaoOponente(i)]);
  const bl = blocoTitulo();
  // dentro da tela?
  const fora = caixas.filter(([n, r]) =>
    r.x < 0 || r.y < 0 || r.x + r.l > VL || r.y + r.a > VA).map(([n]) => n);
  // um por cima do outro? (o titulo conta como uma caixa da largura da tela)
  const todas = caixas.concat([["titulo", { x: 0, y: bl.topo, l: VL, a: bl.fim - bl.topo }]]);
  const bate = [];
  for (let i = 0; i < todas.length; i++)
    for (let j = i + 1; j < todas.length; j++) {
      const a = todas[i][1], b = todas[j][1];
      if (a.x < b.x + b.l && b.x < a.x + a.l &&
          a.y < b.y + b.a && b.y < a.y + a.a) bate.push(todas[i][0] + "/" + todas[j][0]);
    }
  // a tela de visuais: as 16 celulas dentro da tela e sem se encostar
  const lv = layoutVisual(), cel = [];
  for (let i = 0; i < 8; i++) { cel.push(["cor" + i, celulaVisual(lv.cor, i)]); cel.push(["enf" + i, celulaVisual(lv.enf, i)]); }
  cel.push(["sairV", botaoSair()]);
  for (const [n, r] of cel) if (r.x < 0 || r.y < 0 || r.x + r.l > VL || r.y + r.a > VA) fora.push(n);
  for (let i = 0; i < cel.length; i++) for (let j = i + 1; j < cel.length; j++) {
    const a = cel[i][1], b = cel[j][1];
    if (a.x < b.x + b.l && b.x < a.x + a.l && a.y < b.y + b.a && b.y < a.y + a.a) bate.push(cel[i][0] + "/" + cel[j][0]);
  }
  if (lv.msgY + FONTE_H > VA) fora.push("msgVisual");
  return { escala, VL, VA, mundo: [MUNDO.L, MUNDO.A],
           campo: Math.round(VL) + "x" + Math.round(VA),
           fora: fora, bate: bate, sub: bl.cabeSub,
           estrelas0: (jogar(), estrelas.length) };
}"""
import sys
URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8085/"
ruins = []
with sync_playwright() as p:
    b = p.chromium.launch()
    print("%-17s %-11s %-6s %-11s %-9s %-8s %s" % (
        "tela","janela","escala","campo","estrelas","UI cabe","titulo"))
    for nome, w, h in TELAS:
        pg = b.new_page(viewport={"width": w, "height": h})
        erros = []; pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.goto(URL); pg.wait_for_timeout(1100)
        r = pg.evaluate(J)
        problema = []
        if r["fora"]: problema.append("fora da tela: " + ",".join(r["fora"]))
        if r["bate"]: problema.append("sobrepostos: " + ",".join(r["bate"]))
        if erros: problema.append("js: " + str(erros))
        if problema: ruins.append(nome + " -> " + "; ".join(problema))
        print("%-17s %-11s %-6d %-11s %-9d %-8s %s" % (
            nome, "%dx%d" % (w, h), r["escala"], r["campo"], r["estrelas0"],
            "sim" if not problema else "NAO", "com subtitulo" if r["sub"] else "sem subtitulo"))
        pg.close()
    b.close()

print()
if ruins:
    for r in ruins: print("FALHA", r)
    sys.exit(1)
print("a UI cabe e nada se sobrepoe em nenhuma tela")
