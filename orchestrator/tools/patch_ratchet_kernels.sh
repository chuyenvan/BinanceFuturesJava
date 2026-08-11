#!/usr/bin/env bash
# Bat TS_RATCHET_DECOUPLED=true cho 5 kernel wfo-worker-{1..5} (confirm RIENG, khong gop bien
# voi min-rate 0.03 da confirm o exit003). Chay TREN Oracle qua ssh.
set -e
for i in 1 2 3 4 5; do
  f=/home/ubuntu/claudedata/.run/kernels/wfo-worker-$i/run_worker.py
  cp "$f" "$f.bak_before_ratchet"
  if ! grep -q TS_RATCHET_DECOUPLED "$f"; then
    python3 - "$f" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
anchor = '# TICKER_SOURCE=file da nam trong config.properties java-run-lc. KHONG set WFO_SMART_CACHE (file source).\n'
assert anchor in s, "anchor khong tim thay trong " + p
inject = anchor + '# CONFIRM ratchet-decouple (2026-07-30 toi) - doi "true"->"false" de tat, push lai de doi hanh vi:\nenv.update({"TS_RATCHET_DECOUPLED": "true"})\n'
s = s.replace(anchor, inject, 1)
open(p, "w").write(s)
print("patched", p)
PY
  fi
done
echo PATCH_DONE
for i in 1 2 3 4 5; do
  grep -n TS_RATCHET_DECOUPLED /home/ubuntu/claudedata/.run/kernels/wfo-worker-$i/run_worker.py
done
