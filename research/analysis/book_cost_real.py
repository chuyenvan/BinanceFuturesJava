#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BOOK_COST_REAL — do chi phi THAT/vong cho book L/S (Track B) + proxy spread DEV tai 00:00 UTC.

Pre-reg: docs/prereg/PREREG_BOOK_COST.md (commit 0b482b4) — chot TRUOC khi do.

Nguon:
  * PHI + MIX + SLIP THAT  : docs/result/RESULT_LIVE_FILLS_AUDIT.md (do tren 991 chan fill that
                             tren live 242; const o duoi co ghi so + nguon).
  * FILL-RATE / p*         : docs/result/RESULT_EXECUTION_MAKER.md
  * SPREAD PROXY (DEV)     : Aerospike local test.kline_1m_opt (Snappy protobuf) — nen 1m quanh
                             00:00 UTC (07:00 GMT+7), ngay 15 moi thang 2021-01..2025-12.
                             CHI OHLC+totalUsdt ⇒ KHONG co bid/ask (PROPOSAL_MICROSTRUCTURE_DATA §1).

Thuan Python, 0 sim, 0 train, khong cham 2026, khong ghi gi vao Aerospike (read-only).
Trung gian: /tmp/book_cost/ (don sau commit).
"""
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import aerospike
from devexport_202609 import parse_minute

OUT = "/tmp/book_cost"
os.makedirs(OUT, exist_ok=True)
NS, SET = "test", "kline_1m_opt"
HOURS = [6, 7]              # GMT+7 06:00..07:59  ==  UTC 23:00..00:59
RB_MIN = "0700"            # GMT+7 07:00        ==  UTC 00:00 (moc rebalance)
BREAKEVEN = 0.414          # %/vong (RESULT_TRACKB_STEP1)
DAYS = [(y, mo) for y in range(2021, 2026) for mo in range(1, 13)]

# --- hang so DO DUOC (RESULT_LIVE_FILLS_AUDIT.md) ---
F_TAKER_LEG = 0.04910      # %/chan : 8,9061 / 18 135,48 (991 chan that)
F_TAKER_CONTRACT = 0.0500  # %/chan : /fapi/v1/commissionRate taker
F_MAKER_CONTRACT = 0.0200  # %/chan : /fapi/v1/commissionRate maker (0/991 chan dung)
SLIP_CLOSE_MED = 0.32952   # %/chan |slip| vs close phut (median)
SLIP_CLOSE_MEAN = 0.71600  # %/chan |slip| vs close phut (mean)
SLIP_OPEN_MED = 0.23308    # %/chan |slip| vs open phut (median)
SLIP_OPEN_MEAN = 0.33202   # %/chan |slip| vs open phut (mean)
SLIP_SIGNED_CLOSE_MEAN = -0.01957  # %/chan slip CO DAU vs close (mean) => ~0
AUDIT_STACK_MED = 0.759    # %/vong (fee 0,100 + slip 0,659) — audit §8
AUDIT_STACK_MEAN = 1.532   # %/vong — audit §8
P_STAR = (0.92, 0.99)      # hoa von maker p* (2 moc slip thuc te) — EXEC_MAKER §5

REPORT = []


def say(s=""):
    REPORT.append(str(s))
    print(s, flush=True)


def key(day, h, mi):
    return "%04d%02d15-%02d%02d" % (day[0], day[1], h, mi)


def main():
    t0 = time.time()
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)],
                            "policies": {"timeout": 6000}}).connect()

    day_keys = []
    for d in DAYS:
        ks = [key(d, h, mi) for h in HOURS for mi in range(60)]
        day_keys.append((d, ks))

    def fetch(args):
        d, ks = args
        out = {}
        for k in ks:
            try:
                r = cli.get((NS, SET, k))
                if r:
                    out[k] = parse_minute(r[2]["data"])
            except Exception:
                pass
        return d, out

    # 60 ngay x 120 phut = 7200 read (moi read tra VE TAT CA symbol cua phut do)
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(fetch, day_keys))
    say("Aerospike xong %d ngay (%.0fs)" % (len(results), time.time() - t0))

    # ---- gom: per (sym, day): closes 120 nut + bar 00:00 UTC ----
    cells = {}      # sym -> list of per-day dict
    vol_sum = {}    # sym -> tong totalUsdt tai 07:00 (liquidity rank)
    vol_n = {}
    for d, data in results:
        per_sym = {}
        for h in HOURS:
            for mi in range(60):
                k = key(d, h, mi)
                v = data.get(k)
                if not v:
                    continue
                syms, arr = v
                for i, nm in enumerate(syms):
                    per_sym.setdefault(nm, {})[h * 60 + mi] = arr[i]
        for nm, mins in per_sym.items():
            rb = mins.get(7 * 60 + 0)          # 07:00 GMT+7 = 00:00 UTC
            if rb is None:
                continue
            o, hi, lo, c, usdt = (float(rb[0]), float(rb[1]), float(rb[2]),
                                  float(rb[3]), float(rb[4]))
            if c <= 0 or hi <= lo:
                continue
            idx = sorted(mins)
            cl = np.array([float(mins[i][3]) for i in idx], dtype=np.float64)
            cl = cl[cl > 0]
            rec = {"day": "%04d-%02d-15" % d, "hl": 100.0 * (hi - lo) / c}
            # Corwin-Schultz (2012) tren 2 khung 1h (23:00 UTC va 00:00 UTC)
            h0 = [float(mins[i][1]) for i in idx if i < 7 * 60]
            l0 = [float(mins[i][2]) for i in idx if i < 7 * 60]
            h1 = [float(mins[i][1]) for i in idx if i >= 7 * 60]
            l1 = [float(mins[i][2]) for i in idx if i >= 7 * 60]
            rec["cs"] = cs_spread(h0, l0, h1, l1)
            # Roll tren 1m log-return cua cua so 120 nut
            rec["roll"] = roll_spread(cl)
            cells.setdefault(nm, []).append(rec)
            vol_sum[nm] = vol_sum.get(nm, 0.0) + usdt
            vol_n[nm] = vol_n.get(nm, 0) + 1

    # ---- top-200 theo thanh khoan TAI moc rebalance (>=12 ngay mau) ----
    elig = [(nm, vol_sum[nm]) for nm in vol_sum if vol_n[nm] >= 12]
    elig.sort(key=lambda x: -x[1])
    top = [nm for nm, _ in elig[:200]]
    say("symbol co mau = %d ; du dieu kien(>=12 ngay) = %d ; top-200 lay = %d"
        % (len(vol_sum), len(elig), len(top)))

    def agg(names, field):
        v = [r[field] for nm in names for r in cells.get(nm, []) if r.get(field) is not None]
        v = np.array(v, dtype=np.float64)
        return v

    maj = [s for s in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT") if s in cells]
    out = {"n_top": len(top), "symbols_top": top,
           "spread_proxy": {}, "cost": {}, "sources": {}}

    for label, names in (("top200", top), ("majors", maj)):
        hl = agg(names, "hl")
        cs = agg(names, "cs")
        rl = agg(names, "roll")
        out["spread_proxy"][label] = {
            "n_cells": int(len(hl)),
            "hl_1m_med_pct": float(np.median(hl)),
            "hl_1m_mean_pct": float(np.mean(hl)),
            "cs_1h_med_pct": float(np.median(cs)) if len(cs) else None,
            "cs_1h_mean_pct": float(np.mean(cs)) if len(cs) else None,
            "roll_1m_valid_frac": float(np.mean(np.isfinite(rl))) if len(rl) else None,
            "roll_1m_med_pct": float(np.nanmedian(rl)) if np.any(np.isfinite(rl)) else None,
        }
        say("[%s] n=%d | 1m (h-l)/c med=%.4f%% mean=%.4f%% | CS(1h) med=%s | Roll(1m) valid=%s med=%s"
            % (label, len(hl), np.median(hl), np.mean(hl),
               "%.4f%%" % np.median(cs) if len(cs) else "n/a",
               "%.2f" % out["spread_proxy"][label]["roll_1m_valid_frac"]
               if out["spread_proxy"][label]["roll_1m_valid_frac"] is not None else "n/a",
               "%.4f%%" % np.nanmedian(rl) if np.any(np.isfinite(rl)) else "n/a"))

    # ---- stack chi phi ----
    def rt(fee_leg, slip_leg):
        return 2.0 * fee_leg + 2.0 * slip_leg

    roll_med = out["spread_proxy"]["top200"]["roll_1m_med_pct"]
    scen = {
        "i_taker_close_med":  rt(F_TAKER_LEG, SLIP_CLOSE_MED),
        "i_taker_close_mean": rt(F_TAKER_LEG, SLIP_CLOSE_MEAN),
        "i_taker_open_med":   rt(F_TAKER_LEG, SLIP_OPEN_MED),
        "i_taker_open_mean":  rt(F_TAKER_LEG, SLIP_OPEN_MEAN),
        "i_taker_signed_close_mean": rt(F_TAKER_LEG, SLIP_SIGNED_CLOSE_MEAN),
        "i_taker_fee_only":   2.0 * F_TAKER_LEG,
        "ii_maker_fee_only":  2.0 * F_MAKER_CONTRACT,
        "iii_mix_actual":     rt(F_TAKER_LEG, SLIP_CLOSE_MED),
        # san chi phi: CHI fee + spread do duoc (Roll), CHUA cong impact (khong do duoc)
        "floor_fee_plus_roll_spread": 2.0 * F_TAKER_LEG + (roll_med if roll_med else 0.0),
    }
    for k, v in scen.items():
        out["cost"][k] = float(v)
        say("cost_rt %-28s = %.4f %%  (hoa von %.3f%%)  %s"
            % (k, v, BREAKEVEN, "PASS" if v <= BREAKEVEN else "FAIL"))
    out["breakeven_pct"] = BREAKEVEN
    out["p_star_maker"] = P_STAR
    out["sources"] = {
        "fee_taker_leg_pct": F_TAKER_LEG,
        "fee_taker_leg_src": "RESULT_LIVE_FILLS_AUDIT.md §3+§5 (8,9061/18135,48; 991 chan that)",
        "fee_maker_leg_pct": F_MAKER_CONTRACT,
        "fee_maker_leg_src": "RESULT_LIVE_FILLS_AUDIT.md §5 (/fapi/v1/commissionRate=0.000200; 0/991 chan dung)",
        "slip_close_med_pct": SLIP_CLOSE_MED, "slip_close_mean_pct": SLIP_CLOSE_MEAN,
        "slip_open_med_pct": SLIP_OPEN_MED, "slip_open_mean_pct": SLIP_OPEN_MEAN,
        "slip_signed_close_mean_pct": SLIP_SIGNED_CLOSE_MEAN,
        "slip_src": "RESULT_LIVE_FILLS_AUDIT.md §7 (976 chan that khop nen 1m)",
        "audit_stack_med_pct": AUDIT_STACK_MED, "audit_stack_mean_pct": AUDIT_STACK_MEAN,
        "mix_actual": "100% taker (991/991 chan; 388/388 lenh MARKET) — RESULT_LIVE_FILLS_AUDIT §4+§6",
        "spread_ref": "KHONG CO bid/ask trong DEV — PROPOSAL_MICROSTRUCTURE_DATA.md §1",
    }
    with open(os.path.join(OUT, "book_cost_real.json"), "w") as f:
        json.dump(out, f, indent=1)
    with open(os.path.join(OUT, "report.txt"), "w") as f:
        f.write("\n".join(REPORT) + "\n")
    say("-> %s/book_cost_real.json (%.0fs)" % (OUT, time.time() - t0))


def cs_spread(h0, l0, h1, l1):
    """Corwin-Schultz (2012) spread uoc luong tu H/L 2 khung lien tiep. Tra ve % hoac None."""
    try:
        H0, L0, H1, L1 = max(h0), min(l0), max(h1), min(l1)
        if L0 <= 0 or L1 <= 0 or H0 <= L0 or H1 <= L1:
            return None
        beta = math.log(H0 / L0) ** 2 + math.log(H1 / L1) ** 2
        gamma = math.log(max(H0, H1) / min(L0, L1)) ** 2
        k = 3.0 - 2.0 * math.sqrt(2.0)
        alpha = (math.sqrt(2.0 * beta) - math.sqrt(beta)) / k - math.sqrt(gamma / k)
        if alpha <= 0:
            return 0.0
        return 100.0 * 2.0 * (math.exp(alpha) - 1.0) / (1.0 + math.exp(alpha))
    except Exception:
        return None


def roll_spread(cl):
    """Roll (1984): s = 2*sqrt(-cov(r_t, r_{t-1})). Tra ve % (None neu cov>=0 / thieu mau)."""
    if len(cl) < 30:
        return None
    r = np.diff(np.log(cl))
    r = r[np.isfinite(r)]
    if len(r) < 20:
        return None
    c = np.cov(r[1:], r[:-1])[0, 1]
    if not np.isfinite(c) or c >= 0:
        return float("nan")
    return 100.0 * 2.0 * math.sqrt(-c)


if __name__ == "__main__":
    main()
