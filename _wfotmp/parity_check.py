#!/usr/bin/env python3
"""PARITY GATE — so kết quả Kaggle (candidate) vs baseline Oracle, join theo (seq,block).
Usage: parity_check.py <candidate.jsonl> <baseline_oracle.jsonl>
Tiêu chí (sim tất định): trades KHỚP CHÍNH XÁC · note KHỚP · calmar & pnl reltol <= 1e-3.
Ghi parity_result.json cạnh candidate. Exit 0 = MATCH, 1 = MISMATCH, 2 = ERROR (thiếu cell/file).
Chỉ so cell CÓ ở CẢ hai file; nếu candidate thiếu cell của baseline -> MISMATCH (không âm thầm bỏ qua)."""
import json, sys, os, logging

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
            m = o.get("metrics", o)
            d[(int(o["seq"]), str(o["block"]))] = {
                "calmar": float(m.get("calmar", 0)),
                "pnl": float(m.get("pnl", 0)),
                "trades": int(m.get("trades", -1)),
                "note": str(m.get("note", "?")),
            }
    return d


def rel(a, b):
    return abs(a - b) / max(abs(a), abs(b), 1e-9)


def main():
    if len(sys.argv) != 3:
        log.error("usage: parity_check.py <candidate.jsonl> <baseline_oracle.jsonl>")
        sys.exit(2)
    cand_path, base_path = sys.argv[1], sys.argv[2]
    for p in (cand_path, base_path):
        if not os.path.exists(p):
            log.error("ERROR thiếu file: %s", p)
            sys.exit(2)
    cand, base = load(cand_path), load(base_path)
    if not base:
        log.error("ERROR baseline rỗng")
        sys.exit(2)
    missing = sorted(set(base) - set(cand))
    common = sorted(set(base) & set(cand))
    mism = []
    for k in common:
        b, c = base[k], cand[k]
        for field in ("trades", "note"):
            if b[field] != c[field]:
                mism.append({"seq": k[0], "block": k[1], "field": field, "oracle": b[field], "kaggle": c[field]})
        for field in ("calmar", "pnl"):
            if rel(b[field], c[field]) > RELTOL:
                mism.append({"seq": k[0], "block": k[1], "field": field, "oracle": b[field], "kaggle": c[field],
                             "reltol": round(rel(b[field], c[field]), 6)})
    for k in missing:
        mism.append({"seq": k[0], "block": k[1], "field": "MISSING_IN_CANDIDATE", "oracle": base[k]["trades"], "kaggle": None})
    verdict = "MATCH" if not mism else "MISMATCH"
    out = {"verdict": verdict, "n_baseline": len(base), "n_common": len(common),
           "n_missing": len(missing), "n_mismatch": len(mism), "mismatches": mism[:50]}
    res_path = os.path.join(os.path.dirname(os.path.abspath(cand_path)), "parity_result.json")
    json.dump(out, open(res_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    log.info("PARITY %s | baseline=%d common=%d missing=%d mismatch=%d -> %s",
             verdict, len(base), len(common), len(missing), len(mism), res_path)
    for x in mism[:20]:
        log.info("  LỆCH %s", x)
    sys.exit(0 if verdict == "MATCH" else 1)


if __name__ == "__main__":
    main()
