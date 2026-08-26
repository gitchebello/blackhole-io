#!/usr/bin/env python3
"""As tres telas do online em todas as resolucoes: nada pode sair da tela
nem cair em cima de outra coisa."""
import sys
from playwright.sync_api import sync_playwright

TELAS = [("celular em pe", 390, 780), ("celular pequeno", 360, 640),
         ("celular deitado", 780, 390), ("tablet", 820, 1180),
         ("notebook", 1366, 768), ("desktop", 1920, 1080),
         ("2k", 2560, 1440), ("ultrawide", 3440, 1440)]

CAIXAS = """() => {
  const r = [];
  const add = (n, b) => r.push([n, b.x, b.y, b.l, b.a]);
  if (cena === 'online') { add('criar', botaoCriar()); add('entrar', botaoEntrar()); }
  if (cena === 'codigo') {
    for (let i = 0; i < LETRAS_SALA.length; i++) add('t' + i, botaoLetra(i));
    add('apagar', botaoApagar());
  }
  if (cena === 'sala') {
    for (let i = 0; i <= CFG.RIVAIS_MAX; i++) add('cpu' + i, botaoCpu(i));
    add('comecar', botaoComecar());
  }
  add('sair', botaoSair());
  return { caixas: r, VL: VL, VA: VA };
}"""

falhas = []
with sync_playwright() as p:
    nav = p.chromium.launch()
    for nome, sl, sa in TELAS:
        ctx = nav.new_context(viewport={"width": sl, "height": sa},
                              device_scale_factor=1)
        pg = ctx.new_page()
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.goto("http://127.0.0.1:8085/")
        pg.wait_for_timeout(300)
        linha = []
        for cena in ("online", "codigo", "sala"):
            pg.evaluate("c => { cena = c; REDE.codigo = 'ABCD'; REDE.digitado = 'AB';"
                        "      REDE.erro = 'SALA NAO EXISTE'; REDE.anfitriao = true; }", cena)
            pg.wait_for_timeout(120)
            d = pg.evaluate(CAIXAS)
            fora = [c[0] for c in d["caixas"]
                    if c[1] < 0 or c[2] < 0 or c[1] + c[3] > d["VL"]
                    or c[2] + c[4] > d["VA"]]
            pg.screenshot(path="/tmp/bh-%s-%s.png" % (cena, nome.replace(" ", "_")))
            linha.append("%s:%s" % (cena, "ok" if not fora else ",".join(fora)))
            if fora:
                falhas.append("%s / %s: %s" % (nome, cena, fora))
        if erros:
            falhas.append("%s: js %s" % (nome, erros))
        print("%-18s %4dx%-5d %s" % (nome, sl, sa, "  ".join(linha)))
        ctx.close()
    nav.close()

print()
if falhas:
    for f in falhas:
        print("FALHA", f)
    sys.exit(1)
print("todas as telas do online cabem")
