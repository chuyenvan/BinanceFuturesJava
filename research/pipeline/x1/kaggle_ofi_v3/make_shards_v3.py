"""Chia universe V3 thanh N shard can bang theo MB nen (LPT greedy). Quy tac universe (co hoc):
moi symbol trong symbol_map.csv, TRU nhung symbol ma listing S3 xac nhan 0 thang aggTrades monthly trong
2021-07..2025-12. Listing loi (None) => GIU (build loop tu 404)."""
import csv
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("shard")
D = r"D:\claudedata\ofi_v3"
N = 10
SEC_PER_MB = 5667.5 / 55955.0   # hieu chinh tu vong 15 sym: 5667.5s / 55,955MB nen (486 file OK + 324 file 404)
SEC_404 = 0.3
V = json.load(open(D + r"\vision_aggtrades_monthly.json", encoding="utf-8"))
SM = [(int(r["symId"]), r["symbol"]) for r in csv.DictReader(open(D + r"\symbol_map.csv"))]
MONTHS = [f"{y}-{m:02d}" for y in range(2021, 2026) for m in range(1, 13) if (y, m) >= (2021, 7)]
uni, excl = [], []
for sid, s in SM:
    d = V.get(s, "MISSING_DIR")
    if d is None:  # listing loi
        uni.append((sid, s, 0.0, 0))
        continue
    if d == "MISSING_DIR":
        d = {}
    ms = [m for m in MONTHS if m in d]
    if not ms:
        excl.append(s)
        continue
    uni.append((sid, s, sum(d[m] for m in ms) / 1e6, len(ms)))
log.info("universe=%d excluded(0 thang trong cua so)=%d", len(uni), len(excl))
cost = {s: mb * SEC_PER_MB + (54 - nm) * SEC_404 for sid, s, mb, nm in uni}
bins = [dict(syms=[], sec=0.0, mb=0.0, sm=0) for _ in range(N)]
for sid, s, mb, nm in sorted(uni, key=lambda t: -cost[t[1]]):
    b = min(bins, key=lambda x: x["sec"])
    b["syms"].append([s, sid]); b["sec"] += cost[s]; b["mb"] += mb; b["sm"] += nm
for i, b in enumerate(bins):
    b["syms"].sort(key=lambda t: t[1])
    log.info("shard %d: nsym=%d sm=%d MB=%.0f est_sec=%.0f (%.2fh)", i, len(b["syms"]), b["sm"], b["mb"], b["sec"], b["sec"] / 3600)
log.info("TOTAL est_sec=%.0f (%.1fh), MB=%.0f, sm=%d", sum(b["sec"] for b in bins), sum(b["sec"] for b in bins) / 3600,
         sum(b["mb"] for b in bins), sum(b["sm"] for b in bins))
json.dump(dict(n_shards=N, sec_per_mb=SEC_PER_MB, excluded=excl,
               shards=[{"shard": i, "est_sec": b["sec"], "mb": b["mb"], "n_sym_months_listed": b["sm"],
                        "syms": b["syms"]} for i, b in enumerate(bins)]),
          open(D + r"\ofi_v3_shards.json", "w"), indent=1)
