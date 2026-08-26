#!/usr/bin/env python3
"""So parity: kaggle/jobstore dump vs baseline Oracle, join theo (seq,block).
Usage: compare_parity.py <baseline.jsonl> <candidate.jsonl>
Tiêu chí: trades KHỚP CHÍNH XÁC, note KHỚP, calmar & pnl reltol<=1e-3 (sim tất định).
In: PARITY MATCH/MISMATCH + chi tiết cell lệch. Chỉ so các cell CÓ ở CẢ hai file (partial OK).
"""
import json, sys, logging

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("parity")

RELTOL = 1e-3

def load(path):
    d = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            o = json.loads(line)
            key = (int(o["seq"]), str(o["block"]))
            m = o["metrics"]
            d[key] = {
                "calmar": float(m.get("calmar", 0)),
                "pnl": float(m.get("pnl", 0)),
                "trades": int(m.get("trades", -1)),
                "note": str(m.get("note", "?")),
            }
    return d

def rel(a, b):
    denom = max(abs(a), abs(b), 1e-9)
    return abs(a - b) / denom

def main():
    base = load(sys.argv[1])
    cand = load(sys.argv[2])
    common = sorted(set(base) & set(cand))
    only_base = sorted(set(base) - set(cand))
    only_cand = sorted(set(cand) - set(base))
    mism = []
    for k in common:
        b, c = base[k], cand[k]
        if b["trades"] != c["trades"]:
            mism.append((k, "trades", b["trades"], c["trades"]))
        if b["note"] != c["note"]:
            mism.append((k, "note", b["note"], c["note"]))
        if rel(b["calmar"], c["calmar"]) > RELTOL:
            mism.append((k, "calmar", b["calmar"], c["calmar"]))
        if rel(b["pnl"], c["pnl"]) > RELTOL:
            mism.append((k, "pnl", b["pnl"], c["pnl"]))
    verdict = "MATCH" if not mism else "MISMATCH"
    log.info("PARITY %s | so %d cell chung (base=%d cand=%d)", verdict, len(common), len(base), len(cand))
    if only_base:
        log.info("  chi co trong baseline (%d): %s", len(only_base), only_base[:12])
    if only_cand:
        log.info("  chi co trong candidate (%d): %s", len(only_cand), only_cand[:12])
    for (k, field, bv, cv) in mism[:40]:
        log.info("  LECH seq=%d block=%s %s: oracle=%s cand=%s", k[0], k[1], field, bv, cv)
    sys.exit(0 if verdict == "MATCH" else 1)

if __name__ == "__main__":
    main()
