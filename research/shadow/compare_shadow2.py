#!/usr/bin/env python3
"""QUEUE_1015 P3 — so lệnh paper shadow #2 (`shadow-c3b`, K24 + skipFull) với sim
cùng cấu hình (K24 + GATE_QUOTA_SKIP_WHEN_FULL=true, chi phí vào OFF) chạy trên
dữ liệu Vision cùng giai đoạn.

Thước + luật: `docs/prereg/PREREG_SHADOW2_PROMOTION.md` (tiêu chí vận hành, KHÔNG
ngưỡng PnL). Script chỉ SO KHỚP CƠ CHẾ, không chấm promote.

Nguồn:
  shadow : `~/shadow_c3b/ledger.csv` (sym,ts_entry,entry,qty,rank,symbol_pred,
           ts_exit,exit_price,reason,pnl)  — CHỈ ĐỌC.
  sim    : `<sim_out>/storage/printDone.csv` (sym,side,entry,tp,profit,status,
           start,time_start_format,end,level,...,pnl,...) — Kernel output Kaggle.

Chuẩn hoá:
  * symbol: bỏ hậu tố USDT/USDC/BUSD (sim in `GRASS`, shadow in `GRASSUSDT`).
  * thời gian: shadow lưu epoch ms (UTC); sim in `start` theo giờ host sim
    (Asia/Ho_Chi_Minh, GMT+7) ⇒ quy shadow về GMT+7 trước khi so.

Khớp: cùng symbol và phút vào lệch ≤ `tol_min` (mặc định ±1').
Báo cáo: tỉ lệ khớp, chênh giá vào, chênh PnL, lệnh một-bên + lý do.

Cửa sổ bị loại (không đạt chuẩn, theo QUEUE_1015): 2026-10-12 09:06 → 2026-10-15 14:49.

Usage:
  python3 compare_shadow2.py --sim /path/printDone.csv \
      [--shadow ~/shadow_c3b/ledger.csv] [--start 2026-10-11 --end 2026-10-12T09:00]
      [--tol-min 1] [--json out.json]
"""
import argparse
import csv
import datetime as dt
import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    stream=sys.stderr)
log = logging.getLogger("cmp_shadow2")

TZ = dt.timezone(dt.timedelta(hours=7))          # Asia/Ho_Chi_Minh
EXCLUDED = ((dt.datetime(2026, 10, 12, 9, 6, tzinfo=TZ),
             dt.datetime(2026, 10, 15, 14, 49, tzinfo=TZ)))
SYM_QUOTE = ("USDT", "USDC", "BUSD", "FDUSD")


def norm_sym(s):
    s = (s or "").strip().upper()
    for q in SYM_QUOTE:
        if s.endswith(q) and len(s) > len(q):
            return s[:-len(q)]
    return s


def minute(dtv):
    return dtv.replace(second=0, microsecond=0)


def _f(x):
    try:
        return float(x)
    except Exception:
        return None


def load_shadow(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            ts = _f(r.get("ts_entry"))
            if ts is None:
                continue
            t = dt.datetime.fromtimestamp(ts / 1000.0, tz=dt.timezone.utc).astimezone(TZ)
            rows.append({"sym": norm_sym(r["sym"]), "t": t, "min": minute(t),
                         "entry": _f(r.get("entry")), "pnl": _f(r.get("pnl")),
                         "reason": r.get("reason"), "src": "shadow"})
    return rows


def load_sim(path):
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            st = (r.get("start") or "").strip()          # "YYYYMMDD HH:MM"
            if not st:
                continue
            try:
                t = dt.datetime.strptime(st[:15], "%Y%m%d %H:%M").replace(tzinfo=TZ)
            except Exception:
                continue
            rows.append({"sym": norm_sym(r.get("sym")), "t": t, "min": minute(t),
                         "entry": _f(r.get("entry")), "pnl": _f(r.get("pnl")),
                         "reason": r.get("status"), "src": "sim"})
    return rows


def in_window(t, start, end, drop_excluded=True):
    if start and t < start:
        return False
    if end and t > end:
        return False
    if drop_excluded:
        for a, b in EXCLUDED:
            if a <= t <= b:
                return False
    return True


def match(shadow, sim, tol_min):
    """Greedy 1-1 match on (sym, |Δmin| <= tol_min); nearest minute wins."""
    used = set()
    matches, sh_only = [], []
    sim_by = {}
    for i, s in enumerate(sim):
        sim_by.setdefault((s["sym"], s["min"]), []).append(i)
    for a in shadow:
        best = None
        for d in range(0, tol_min + 1):
            for sign in ({0} if d == 0 else (d, -d)):
                k = (a["sym"], a["min"] + dt.timedelta(minutes=sign))
                for i in sim_by.get(k, []):
                    if i in used:
                        continue
                    best = (i, (a["min"] - sim[k][0]["min"]))
                    break
                if best:
                    break
            if best:
                break
        if best is None:
            sh_only.append(a)
        else:
            i, _ = best
            used.add(i)
            matches.append((a, sim[i]))
    sim_only = [s for i, s in enumerate(sim) if i not in used]
    return matches, sh_only, sim_only


def summarize(matches):
    n = len(matches)
    if not n:
        return {}
    de = []
    dp = []
    for a, b in matches:
        if a["entry"] and b["entry"] and a["entry"] > 0:
            de.append((b["entry"] - a["entry"]) / a["entry"])
        if a["pnl"] is not None and b["pnl"] is not None:
            dp.append(b["pnl"] - a["pnl"])
    med = lambda v: sorted(v)[len(v) // 2] if v else None
    return {"n_matched": n,
            "entry_rel_median": med(de), "entry_rel_mean": (sum(de) / len(de)) if de else None,
            "entry_rel_maxabs": max((abs(x) for x in de), default=None),
            "pnl_diff_median": med(dp), "pnl_diff_mean": (sum(dp) / len(dp)) if dp else None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim", required=True)
    ap.add_argument("--shadow", default=os.path.expanduser("~/shadow_c3b/ledger.csv"))
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--tol-min", type=int, default=1)
    ap.add_argument("--drop-excluded", type=lambda x: x.lower() != "false", default=True)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    def parse_dt(s):
        if not s:
            return None
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return dt.datetime.strptime(s, fmt).replace(tzinfo=TZ)
            except Exception:
                continue
        raise SystemExit("bad datetime: " + s)

    start, end = parse_dt(a.start), parse_dt(a.end)
    sh = [r for r in load_shadow(a.shadow) if in_window(r["t"], start, end, a.drop_excluded)]
    sm = [r for r in load_sim(a.sim) if in_window(r["t"], start, end, a.drop_excluded)]
    log.info("shadow orders=%d sim orders=%d window=%s..%s", len(sh), len(sm), start, end)

    m, sh_only, sm_only = match(sh, sm, a.tol_min)
    res = {
        "shadow_file": a.shadow, "sim_file": a.sim,
        "window": [str(start), str(end)], "tol_min": a.tol_min,
        "drop_excluded": a.drop_excluded,
        "n_shadow": len(sh), "n_sim": len(sm),
        "matched": len(m),
        "match_rate_shadow": (len(m) / len(sh)) if sh else None,
        "match_rate_sim": (len(m) / len(sm)) if sm else None,
        "shadow_only": [{"sym": r["sym"], "min": str(r["min"]), "reason": r["reason"],
                         "pnl": r["pnl"]} for r in sh_only],
        "sim_only": [{"sym": r["sym"], "min": str(r["min"]), "reason": r["reason"],
                      "pnl": r["pnl"]} for r in sm_only],
        "metrics": summarize(m),
    }
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if a.json:
        json.dump(res, open(a.json, "w"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
