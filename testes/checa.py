#!/usr/bin/env python3
"""Confere a sintaxe do <script> do jogo com o node. Sai 0 se estiver ok."""
import io, re, subprocess, sys, tempfile, os
alvo = sys.argv[1] if len(sys.argv) > 1 else "/home/rebello/blackhole-io/game.html"
html = io.open(alvo, encoding="utf-8").read()
m = re.search(r"<script>(.*)</script>", html, re.S)
if not m:
    print("nao achei o <script>"); sys.exit(1)
with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
    f.write(m.group(1)); tmp = f.name
r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True)
os.unlink(tmp)
if r.returncode:
    print(r.stderr.strip()[:2000]); sys.exit(1)
print("sintaxe ok (%d KB de script)" % (len(m.group(1)) // 1024))
