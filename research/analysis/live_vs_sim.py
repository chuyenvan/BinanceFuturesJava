"""LIVE_VS_SIM - so SHADOW/LIVE (forward, lenh that paper) voi SIM T170 theo notional.

Chot truoc: docs/PREREG_LIVE_VS_SIM.md (commit edcc551). KHONG tune, khong push,
khong chay Java tren Oracle, khong ghi 242. Thuan Python, chi DOC du lieu nguon.

Ghi ra /tmp/live_vs_sim/ (JSON + txt) de dan vao docs/RESULT_LIVE_VS_SIM.md.
"""
import csv
import datetime as dt
import json
import logging
import math
import os
import random
import statistics
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("live_vs_sim")

SHADOW_LEDGER = "/home/ubuntu/shadow_c3/ledger.csv"
SHADOW_FROMLOG = "/home/ubuntu/shadow_c3/ledger_from_log.csv"
SIM_PRINTDONE = "/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv"
OUT_DIR = "/tmp/live_vs_sim"

NREP = 2000
SEED = 20260923
BLOCK_H = 72
SHADOW_UTC = dt.timezone.utc          # ledger.csv: ts_entry la epoch ms (UTC)
SHADOW_C_T170 = 0.008                 # phi gia dinh = mo hinh sim (RATE_FEE 0.002 + slip 0.003x2)
SHADOW_C_REAL = 0.001                 # phi gia dinh xap xi taker 2 chan THAT (gia dinh, khong do duoc)
SIM_NET_C = 0.008                     # mo hinh phi cua sim (chi de doi chieu, khong ap vao shadow chinh)


# ---------------------------------------------------------------- loaders
def load_shadow():
    """ledger.csv -> list dict: ret_gross%, notional, hold_h, day, reason, sym, level(neu co)."""
    out = []
    with open(SHADOW_LEDGER) as fh:
        for r in csv.DictReader(fh):
            entry = float(r["entry"])
            exitp = float(r["exit_price"])
            qty = float(r["qty"])
            t0 = int(r["ts_entry"])
            t1 = int(r["ts_exit"])
            if entry <= 0 or qty <= 0:
                continue
            out.append({
                "sym": r["sym"],
                "t0": t0,
                "t1": t1,
                "day": dt.datetime.fromtimestamp(t0 / 1000, SHADOW_UTC).strftime("%Y-%m-%d"),
                "notional": qty * entry,
                "ret_gross": 100.0 * (exitp - entry) / entry,
                "pnl_gross": qty * (exitp - entry),
                "hold_h": (t1 - t0) / 3600000.0,
                "reason": r["reason"],
                "level": "PREDICT_SYMBOL_TRADE",
            })
    return out


def load_shadow_fromlog():
    """ledger_from_log.csv -> chi de DEM tan suat entry (khong co exit)."""
    out = []
    with open(SHADOW_FROMLOG) as fh:
        for r in csv.DictReader(fh):
            t0 = int(r["ts_entry"])
            out.append({
                "sym": r["sym"], "t0": t0,
                "day": dt.datetime.fromtimestamp(t0 / 1000, SHADOW_UTC).strftime("%Y-%m-%d"),
                "level": r["market_level"],
                "budget": float(r["budget"]) if r["budget"] else None,
            })
    return out


def load_sim():
    """printDone.csv -> list dict: ret_gross% (cot profit), net_ret%, notional, hold_h, day, status, level."""
    out = []
    with open(SIM_PRINTDONE, newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                qty = float(r["quantity"])
                entry = float(r["entry"])
                profit = float(r["profit"])
                pnl = float(r["pnl"])
                t0 = dt.datetime.strptime(r["start"], "%Y%m%d %H:%M")
                t1 = dt.datetime.strptime(r["end"], "%Y%m%d %H:%M")
            except (ValueError, KeyError, TypeError):
                continue
            if qty <= 0 or entry <= 0:
                continue
            notional = qty * entry
            out.append({
                "sym": r["sym"], "day": t0.strftime("%Y-%m-%d"),
                "notional": notional,
                "ret_gross": profit,
                "pnl_net": pnl,
                "net_ret": 100.0 * pnl / notional,
                "hold_h": (t1 - t0).total_seconds() / 3600.0,
                "status": r["status"],
                "level": r["level"],
                "ts": t0,
                "t0": int(t0.replace(tzinfo=SHADOW_UTC).timestamp() * 1000),
            })
    return out


# ---------------------------------------------------------------- stats
def stats(rows, key="ret_gross"):
    v = [r[key] for r in rows if r.get(key) is not None and math.isfinite(r[key])]
    if not v:
        return {"n": 0}
    return {
        "n": len(v),
        "mean": statistics.fmean(v),
        "median": statistics.median(v),
        "win": 100.0 * sum(1 for x in v if x > 0) / len(v),
        "p10": _q(v, 0.10), "p25": _q(v, 0.25), "p75": _q(v, 0.75), "p90": _q(v, 0.90),
        "min": min(v), "max": max(v),
    }


def _q(v, p):
    s = sorted(v)
    i = p * (len(s) - 1)
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    return s[lo] + (s[hi] - s[lo]) * (i - lo)


def blocks_of(rows, tkey):
    """Gan blk = chi so khoi 72h ke tu min(tkey)."""
    if not rows:
        return rows
    t0 = min(r[tkey] for r in rows)
    for r in rows:
        r["blk"] = int((r[tkey] - t0) / (BLOCK_H * 3600000.0))
    return rows


def boot_block(rows, key="ret_gross", nrep=NREP, seed=SEED):
    """Block bootstrap theo ngay/72h (rut khoi co hoan lai). Tra CI95 mean/median/win%."""
    if not rows:
        return {}
    by = {}
    for r in rows:
        by.setdefault(r["blk"], []).append(r)
    blks = sorted(by)
    rng = random.Random(seed)
    means, meds, wins, holds = [], [], [], []
    for _ in range(nrep):
        pick = [blks[rng.randrange(len(blks))] for _ in range(len(blks))]
        samp = [r for b in pick for r in by[b]]
        vals = [r[key] for r in samp if r.get(key) is not None and math.isfinite(r[key])]
        if not vals:
            continue
        means.append(statistics.fmean(vals))
        meds.append(statistics.median(vals))
        wins.append(100.0 * sum(1 for x in vals if x > 0) / len(vals))
        holds.append(statistics.median([r["hold_h"] for r in samp]))
    def ci(a):
        if not a:
            return (float("nan"), float("nan"))
        a = sorted(a)
        return (a[int(0.025 * (len(a) - 1))], a[int(0.975 * (len(a) - 1))])
    return {"n_blk": len(blks), "ci_mean": ci(means), "ci_median": ci(meds),
            "ci_win": ci(wins), "ci_hold_med": ci(holds)}


def freq(rows, tkey="t0", label=""):
    """Tan suat theo 4 cach dem (muc 5.1 cua pre-reg)."""
    if not rows:
        return {}
    ts = [r[tkey] for r in rows]
    span_d = (max(ts) - min(ts)) / 86400000.0 + 1e-9
    days = sorted(set(r["day"] for r in rows))
    slots = len(set((r[tkey] // 900000) for r in rows))     # luoi 15m
    return {
        "label": label, "n": len(rows),
        "span_days": span_d,
        "n_active_days": len(days),
        "per_calendar_day": len(rows) / span_d if span_d > 0 else float("nan"),
        "per_active_day": len(rows) / len(days),
        "n_slots": slots,
        "per_slot": len(rows) / slots,
        "slots_per_active_day": slots / len(days),
        "n_coins": len(set(r["sym"] for r in rows)),
        "coins_per_active_day": len(set(r["sym"] for r in rows)) / len(days),
    }


def q(s, k):
    """Ep kieu cho JSON (tuple -> list, float -> round)."""
    if isinstance(s, dict):
        return {kk: q(vv, kk) for kk, vv in s.items()}
    if isinstance(s, (list, tuple)):
        return [q(x, None) for x in s]
    if isinstance(s, float):
        return None if not math.isfinite(s) else round(s, 4)
    return s


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    sh = load_shadow()
    shl = load_shadow_fromlog()
    sim = load_sim()
    log.info("shadow ledger: %d lenh dong | shadow from_log: %d entry | sim: %d leg",
             len(sh), len(shl), len(sim))

    # --- tach theo dot config (gia thuyet (b))
    sh_0609 = [r for r in sh if r["day"] == "2026-09-06"]        # gate PHANG (truoc fix 18/09)
    sh_1819 = [r for r in sh if r["day"].startswith("2026-09-18") or r["day"].startswith("2026-09-19")]
    sim_sm = [r for r in sim if r["status"] == "STOP_MARKET_DONE"]
    sim_sl = [r for r in sim if r["status"] == "STOP_LOSS_DONE"]

    for rows, tk in ((sh, "t0"), (sim, "t0")):
        blocks_of(rows, tk)

    # --- phan bo theo ngay (de lo tinh khong-dung)
    per_day = {}
    for r in sh:
        per_day.setdefault(r["day"], []).append(r["ret_gross"])
    per_day_out = {d: {"n": len(v), "mean": statistics.fmean(v),
                       "median": statistics.median(v),
                       "win": 100.0 * sum(1 for x in v if x > 0) / len(v)}
                   for d, v in sorted(per_day.items())}

    # --- subset so NGANG HANG: shadow 100% PREDICT_SYMBOL_TRADE => so rieng PST cua sim
    sim_pst = [r for r in sim if r["level"] == "PREDICT_SYMBOL_TRADE"]
    sim_pst_sm = [r for r in sim_pst if r["status"] == "STOP_MARKET_DONE"]
    sim_pst_sl = [r for r in sim_pst if r["status"] == "STOP_LOSS_DONE"]
    sim_sm_pos = [r for r in sim_sm if r["ret_gross"] > 0]
    sim_sl_ts = [r for r in sim_sl if r["hold_h"] >= 167.0]
    sim_sl_hard = [r for r in sim_sl if r["hold_h"] < 167.0]
    for rows, tk in ((sim_pst, "t0"), (sim_sm_pos, "t0")):
        blocks_of(rows, tk)

    res = {
        "shadow_all_closed": stats(sh),
        "sim_PST": stats(sim_pst),
        "sim_PST_SM": stats(sim_pst_sm),
        "sim_PST_SL": stats(sim_pst_sl),
        "sim_SM_positive_only": stats(sim_sm_pos),
        "sim_SL_timestop_168h": stats(sim_sl_ts),
        "sim_SL_hard": stats(sim_sl_hard),
        "shadow_0609_flatgate": stats(sh_0609),
        "shadow_1819_t170": stats(sh_1819),
        "shadow_trailing_only": stats([r for r in sh if r["reason"] == "TRAILING_STOP"]),
        "shadow_timestop_only": stats([r for r in sh if r["reason"] == "TIME_STOP_168H"]),
        "sim_all": stats(sim),
        "sim_STOP_MARKET_DONE": stats(sim_sm),
        "sim_STOP_LOSS_DONE": stats(sim_sl),
        "shadow_net_c0008": stats([{**r, "ret_net": r["ret_gross"] - 100 * SHADOW_C_T170} for r in sh], "ret_net"),
        "shadow_net_c0001": stats([{**r, "ret_net": r["ret_gross"] - 100 * SHADOW_C_REAL} for r in sh], "ret_net"),
        "sim_net": stats(sim, "net_ret"),
        "sim_net_STOP_MARKET_DONE": stats(sim_sm, "net_ret"),
        "holds": {
            "shadow_h_mean": statistics.fmean([r["hold_h"] for r in sh]),
            "shadow_h_median": statistics.median([r["hold_h"] for r in sh]),
            "shadow_h_max": max(r["hold_h"] for r in sh),
            "sim_h_mean": statistics.fmean([r["hold_h"] for r in sim]),
            "sim_h_median": statistics.median([r["hold_h"] for r in sim]),
            "sim_h_max": max(r["hold_h"] for r in sim),
            "sim_sm_h_median": statistics.median([r["hold_h"] for r in sim_sm]),
            "sim_sl_h_median": statistics.median([r["hold_h"] for r in sim_sl]),
        },
        "levels": {
            "shadow": _cnt(sh, "level"),
            "sim": _cnt(sim, "level"),
        },
        "ci": {
            "shadow": boot_block(sh),
            "shadow_1819": boot_block(sh_1819, seed=SEED + 2),
            "sim": boot_block(sim, seed=SEED + 1),
            "sim_SM": boot_block(sim_sm, seed=SEED + 3),
            "sim_PST": boot_block(sim_pst, seed=SEED + 4),
            "sim_SM_positive_only": boot_block(sim_sm_pos, seed=SEED + 5),
        },
        "freq": {
            "shadow_all": freq(sh, "t0", "shadow 65 lenh (3 ngay co lenh)"),
            "shadow_1819": freq(sh_1819, "t0", "shadow 51 lenh 18-19/09 (T170)"),
            "shadow_fromlog_1819": freq([{**r, "day": r["day"]} for r in shl], "t0", "shadow 60 entry log 18-19/09"),
            "sim_all": freq(sim, "t0", "sim T170 (4,4 nam)"),
        },
        "per_day": per_day_out,
    }

    # --- sim theo nam + 90 ngay cuoi (regime, gia thuyet (d))
    res["sim_by_year"] = _by_year(sim)

    with open(os.path.join(OUT_DIR, "live_vs_sim.json"), "w") as fh:
        json.dump(q(res, None), fh, indent=1, ensure_ascii=False)

    # --- bao cao van ban
    L = []
    def w(s=""):
        L.append(s)
        log.info(s)

    w("=== (1) TAN SUAT (4 cach dem) ===")
    for k in ("shadow_all", "shadow_1819", "shadow_fromlog_1819", "sim_all"):
        f = res["freq"][k]
        w("%-32s n=%-5d span=%.1fd active=%-3d %6.2f/ngay-lich %6.2f/ngay-hd slots=%-4d %5.2f/slot %5.1f coin"
          % (f["label"], f["n"], f["span_days"], f["n_active_days"], f["per_calendar_day"],
             f["per_active_day"], f["n_slots"], f["per_slot"], f["n_coins"]))
    w("")
    w("=== (2) PnL/notional GROSS (%) theo tap ===")
    for k in ("shadow_all_closed", "shadow_0609_flatgate", "shadow_1819_t170",
              "shadow_trailing_only", "shadow_timestop_only", "sim_all",
              "sim_PST", "sim_PST_SM", "sim_PST_SL",
              "sim_STOP_MARKET_DONE", "sim_STOP_LOSS_DONE",
              "sim_SM_positive_only", "sim_SL_timestop_168h", "sim_SL_hard"):
        s = res[k]
        w("%-26s n=%-5d mean=%7.3f med=%7.3f win=%6.2f%% p10=%7.2f p90=%7.2f min=%8.2f max=%8.2f"
          % (k, s["n"], s["mean"], s["median"], s["win"], s["p10"], s["p90"], s["min"], s["max"]))
    w("")
    w("=== (3) NET (%/notional) — doi chieu mo hinh phi ===")
    for k in ("shadow_net_c0008", "shadow_net_c0001", "sim_net", "sim_net_STOP_MARKET_DONE"):
        s = res[k]
        w("%-26s n=%-5d mean=%7.3f med=%7.3f win=%6.2f%%" % (k, s["n"], s["mean"], s["median"], s["win"]))
    w("")
    w("=== (4) THOI GIAN GIU (h) ===")
    h = res["holds"]
    w("shadow mean=%.1f med=%.1f max=%.1f | sim mean=%.1f med=%.1f max=%.1f (SM med=%.1f SL med=%.1f)"
      % (h["shadow_h_mean"], h["shadow_h_median"], h["shadow_h_max"],
         h["sim_h_mean"], h["sim_h_median"], h["sim_h_max"],
         h["sim_sm_h_median"], h["sim_sl_h_median"]))
    w("")
    w("=== (5) CI block-72h (2000 rep, seed %d) ===" % SEED)
    for side, c in res["ci"].items():
        w("%s n_blk=%d mean CI=[%.3f, %.3f] median CI=[%.3f, %.3f] win CI=[%.2f, %.2f] hold_med CI=[%.1f, %.1f]"
          % (side, c["n_blk"], c["ci_mean"][0], c["ci_mean"][1], c["ci_median"][0], c["ci_median"][1],
             c["ci_win"][0], c["ci_win"][1], c["ci_hold_med"][0], c["ci_hold_med"][1]))
    w("")
    w("=== (6) PHAN BO THEO NGAY (shadow) ===")
    for d, v in res["per_day"].items():
        w("%s n=%2d mean=%7.3f med=%7.3f win=%6.2f%%" % (d, v["n"], v["mean"], v["median"], v["win"]))
    w("")
    w("=== (7) LEVEL ===")
    w("shadow: %s" % res["levels"]["shadow"])
    w("sim   : %s" % res["levels"]["sim"])
    w("")
    w("=== (7b) TAN SUAT tren NGAY CON SONG (shadow post-fix) ===")
    alive = [_alive_days()]
    w("shadow 18/09 11:00Z -> 23/09 06:00Z = %.1f ngay CON SONG; 60 entry log => %.2f entry/ngay-song"
      % (alive[0], 60.0 / alive[0]))
    w("sim 1588 ngay lich, 110 ngay CO entry (%.1f%%) | shadow 2/%.1f ngay song = %.1f%%"
      % (100.0 * 110 / 1588.2, alive[0], 100.0 * 2 / alive[0]))
    w("")
    w("=== (8) SIM THEO NAM (leg/ngay) ===")
    for y, v in sorted(res["sim_by_year"].items()):
        w("%s n=%-4d %5.2f leg/ngay-lich  %5.2f/ngay-hoat-dong (active=%d)" %
          (y, v["n"], v["per_calendar_day"], v["per_active_day"], v["n_active_days"]))

    with open(os.path.join(OUT_DIR, "report.txt"), "w") as fh:
        fh.write("\n".join(L) + "\n")


def _alive_days():
    """So ngay shadow CON SONG ke tu restart 18/09 11:00Z den 23/09 06:00Z (health.log cuoi)."""
    a = dt.datetime(2026, 9, 18, 11, 0, tzinfo=SHADOW_UTC)
    b = dt.datetime(2026, 9, 23, 6, 0, tzinfo=SHADOW_UTC)
    return (b - a).total_seconds() / 86400.0


def _cnt(rows, key):
    c = {}
    for r in rows:
        c[r[key]] = c.get(r[key], 0) + 1
    return c


def _by_year(rows):
    out = {}
    for r in rows:
        out.setdefault(r["day"][:4], []).append(r)
    res = {}
    for y, v in out.items():
        days = sorted(set(r["day"] for r in v))
        t = [r["ts"] for r in v]
        span = (max(t) - min(t)).total_seconds() / 86400.0 + 1e-9
        res[y] = {"n": len(v), "n_active_days": len(days),
                  "per_calendar_day": len(v) / span if span > 0 else float("nan"),
                  "per_active_day": len(v) / len(days)}
    return res


if __name__ == "__main__":
    main()
