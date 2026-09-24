import csv
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("an")
D = r"D:\claudedata\ofi_v3"
V = json.load(open(D + r"\vision_aggtrades_monthly.json", encoding="utf-8"))
SM = {r["symbol"]: int(r["symId"]) for r in csv.DictReader(open(D + r"\symbol_map.csv"))}
MONTHS = [f"{y}-{m:02d}" for y in range(2021, 2026) for m in range(1, 13) if (y, m) >= (2021, 7)]
assert len(MONTHS) == 54
OLD15 = ["AIAUSDT", "PEOPLEUSDT", "UNFIUSDT", "ALCHUSDT", "MASKUSDT", "MYXUSDT", "BLZUSDT", "ALICEUSDT",
         "COAIUSDT", "EVAAUSDT", "RSRUSDT", "1000PEPEUSDT", "WIFUSDT", "CHRUSDT", "SOLUSDT"]


def stats(syms):
    n_sm, mb, nsym = 0, 0.0, 0
    for s in syms:
        d = V.get(s) or {}
        ms = [m for m in MONTHS if m in d]
        if ms:
            nsym += 1
        n_sm += len(ms)
        mb += sum(d[m] for m in ms) / 1e6
    return nsym, n_sm, mb


inwin = [s for s, d in V.items() if d and any(m in d for m in MONTHS)]
log.info("vision dirs=%d, co >=1 thang trong 2021-07..2025-12: %d", len(V), len(inwin))
usdt = [s for s in inwin if s.endswith("USDT")]
log.info("  trong do USDT: %d", len(usdt))
inmap = [s for s in inwin if s in SM]
log.info("symbol_map=%d; symbol_map co data trong cua so: %d", len(SM), len(inmap))
miss = [s for s in SM if s not in inwin]
log.info("symbol_map KHONG co data vision trong cua so: %d (vd %s)", len(miss), miss[:15])
for name, S in [("OLD15", OLD15), ("ALL_inwin", inwin), ("USDT_inwin", usdt), ("SYMMAP_inwin", inmap)]:
    nsym, n_sm, mb = stats(S)
    log.info("%-14s nsym=%4d symbol-thang=%6d  MB=%10.0f  MB/sm=%.1f", name, nsym, n_sm, mb, mb / max(n_sm, 1))
# phan bo size theo symbol trong symbol_map (top)
per = sorted(((sum((V[s] or {}).get(m, 0) for m in MONTHS) / 1e6, s) for s in inmap), reverse=True)
log.info("top 10 MB: %s", [(s, round(x)) for x, s in per[:10]])
log.info("max symbol MB=%.0f", per[0][0])
# co khi lay moi symbol thu k theo symId
for k in (2, 3, 4):
    S = [s for s in inmap if SM[s] % k == 0]
    nsym, n_sm, mb = stats(S)
    log.info("symId%%%d==0: nsym=%d sm=%d MB=%.0f", k, nsym, n_sm, mb)
json.dump(dict(inmap=sorted(inmap, key=lambda s: SM[s]), per=[(s, x) for x, s in per]),
          open(D + r"\recon_summary.json", "w"))
