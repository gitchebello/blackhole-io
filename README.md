# blackhole.io

Jogo casual no estilo *Hole.io*: você é um buraco negro em pixel art que engole estrelas, planetas e jogadores menores para crescer. Tem power-ups (como Júpiter, que te deixa maior por um tempo), cometa, salas online de até 4 pessoas completadas por CPUs e uma contagem regressiva nos últimos pontos da partida.

O jogo inteiro é um arquivo só: `game.html`.

## Rodar

```bash
python3 servir.py          # http://localhost:8085 (jogo + WebSocket das salas em /ws)
python3 servir.py 9000     # outra porta
```

`servir.py` usa só a biblioteca padrão do Python. Ele serve a página sem cache e repassa as mensagens das salas; quem simula a partida é o navegador do anfitrião. A pasta `serve/` é a versão publicada (PWA, com manifesto e ícones).

## Testes

`testes/` tem scripts Python de verificação: `checa.py` confere a sintaxe do `<script>` com o `node`, e os outros jogam cenários com Playwright (instale em um `venv` dentro de `testes/`).
