"""C3 baseline — do lai toan bo sau khi sua 3 bug B1/B2/B3 (docs/PREREG_C3.md).

Them so voi w1_rates.py:
  - phan bo profit cua WINNER (p10/p25/med/p75/p90/max)  <- B1 doi HINH DANG cai nay
  - mean(margin) theo NAM                                <- phep kiem B3 (phai tang theo equity)
  - dem lenh nhanh STRONG vs WEAK (symbolPred <= TS_PNOPUMP_WEAK_THR = STRONG)
  - mean(margin) cua LEG-1 (gom cum theo (sym,end), leg dau = start som nhat) <- cong hieu chuan
  - CAGR
  - block-72h bootstrap CI x1.21 cho cau GATE

Usage:
  python3 c3_rates.py TAG [TAG ...]
  python3 c3_rates.py --ci TAG_A TAG_B
"""
import logging
import re
import sys

import math

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

B = "/home/ubuntu/java/devrun"
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")
QS = ['2022Q1', '2022Q2', '2022Q3', '2022Q4', '2023Q1',
      '2023Q2', '2023Q3', '2023Q4', '2024Q1', '2024Q2',
      '2024Q3', '2024Q4', '2025Q1', '2025Q2', '2025Q3', '2025Q4']
WEAK_THR = 0.29          # Configs.TS_PNOPUMP_WEAK_THR; <= thr => STRONG (cap 0.08)
BLOCK_H = 72
NREP = 2000
# ---------------------------------------------------------------------------
# [CHUAN HOA 2026-09-17] docs/AUDIT_CI_INFLATE_STANDARDIZATION.md
#   He so no rong CI cho multiplicity PHAI la sqrt(2 ln k) voi k = SO UNG VIEN
#   duoc kiem dinh so voi baseline TRONG DUNG round do (baseline KHONG tinh).
#   Hang so cu 1.21 ung voi k = exp(1.21^2/2) = 2.079 - khong phai so nguyen,
#   khong co can cu. No da lan truyen qua 11/24 round (5 round vien dan cau SAI
#   "x1.21 da bao k=3"; 2 round nhan CHONG 1.21 x sqrt(2 ln 3) = 1.7936).
#   Nay `CI_INFLATE` KHONG con doc duoc: moi truy cap NEM AttributeError
#   (xem __getattr__ cuoi file). Dung inflate(k).
LEGACY_CI_INFLATE = 1.21   # CHI de tai lap NGUYEN VAN doc cu. KHONG dung cho round moi.


def inflate(k):
    """He so no rong CI cho multiplicity. k = so ung vien trong round (>=1).

    k = 1  -> 1.0 (khong co multiplicity, giu CI goc)
    k >= 2 -> sqrt(2 ln k)
    KHONG co gia tri mac dinh o bat ky call-site nao: k phai duoc truyen vao.
    """
    if k is None:
        raise ValueError("inflate(k): k la BAT BUOC, khong co default. "
                         "k = so ung vien so voi baseline trong round nay.")
    k = int(k)
    if k < 1:
        raise ValueError("inflate(k): k phai >= 1, nhan duoc %r" % (k,))
    if k == 1:
        return 1.0
    return float(math.sqrt(2.0 * math.log(k)))
SEED = 20260905


def equity(tag):
    rows = []
    with open(f"{B}/{tag}/logs/sim.out", errors="ignore") as fh:
        for line in fh:
            m = RX.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "equity"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d").equity


def trades(tag):
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv", on_bad_lines="skip")
    for c in ("profit", "margin", "pnl", "symbolPred", "entry", "quantity"):
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["profit"])
    d["ts"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M", errors="coerce")
    d = d.dropna(subset=["ts"])
    # leg index: cum = (sym, end); leg-1 = start som nhat trong cum
    d = d.sort_values(["sym", "end", "ts"], kind="mergesort")
    d["leg"] = d.groupby(["sym", "end"]).cumcount()
    t0 = d.ts.min()
    d["blk"] = ((d.ts - t0) / pd.Timedelta(hours=BLOCK_H)).astype(int)
    return d


def rates(d):
    """Cac rate PRIMARY tinh tren mot bang trade (dung chung cho bootstrap)."""
    if len(d) == 0:
        return {k: float("nan") for k in
                ("n", "win", "tsloss", "mp_sm", "mp_sl", "meanP", "margin")}
    sm = d.loc[d.status == "STOP_MARKET_DONE", "profit"]
    sl = d.loc[d.status == "STOP_LOSS_DONE", "profit"]
    return {
        "n": float(len(d)),
        "win": 100.0 * (d.profit > 0).mean(),
        "tsloss": 100.0 * (d.status == "STOP_LOSS_DONE").mean(),
        "mp_sm": sm.mean() if len(sm) else float("nan"),
        "mp_sl": sl.mean() if len(sl) else float("nan"),
        "meanP": d.profit.mean(),
        "margin": d.margin.mean(),
    }


def stats(tag):
    d = trades(tag)
    s = equity(tag)
    r = rates(d)

    qe = s.resample("QE").last()
    q0 = pd.concat([pd.Series([s.iloc[0]], index=[s.index[0]]), qe]).iloc[:-1]
    qr = dict(zip((str(p) for p in qe.index.to_period("Q")),
                  (qe.values / q0.values - 1) * 100))
    ye = s.resample("YE").last()
    y0 = pd.concat([pd.Series([s.iloc[0]], index=[s.index[0]]), ye]).iloc[:-1]
    yr = dict(zip((str(p.year) for p in ye.index.to_period("Y")),
                  (ye.values / y0.values - 1) * 100))
    dd = (s / s.cummax() - 1) * 100
    uw = s < s.cummax()
    years = (s.index[-1] - s.index[0]).days / 365.25
    cagr = ((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100

    win = d.loc[d.profit > 0, "profit"]
    dist = {k: (win.quantile(q) if len(win) else float("nan"))
            for k, q in (("p10", .10), ("p25", .25), ("med", .50),
                         ("p75", .75), ("p90", .90))}
    dist["max"] = win.max() if len(win) else float("nan")
    dist["n_win"] = len(win)

    # STRONG/WEAK theo symbolPred cua LEG-1 (dai dien cum, dung luat B1)
    lead = d[d.leg == 0]
    known = lead.symbolPred.notna()
    strong = int((lead.symbolPred[known] <= WEAK_THR).sum())
    weak = int((lead.symbolPred[known] > WEAK_THR).sum())
    nopred = int((~known).sum())

    marg_year = {str(y): float(g.margin.mean())
                 for y, g in d.groupby(d.ts.dt.year)}

    r.update({
        "tag": tag, "end": s.iloc[-1], "cagr": cagr,
        "maxDD": dd.min(), "uw": int(uw.groupby((~uw).cumsum()).sum().max()),
        "medP": d.profit.median(), "qr": qr, "yr": yr,
        "qmin": min(qr.values()), "neg_year": [y for y, v in yr.items() if v < 0],
        "dist": dist, "strong": strong, "weak": weak, "nopred": nopred,
        "marg_year": marg_year, "margin_leg1": float(lead.margin.mean()),
        "n_leg1": len(lead), "n_dca": int((d.leg > 0).sum()),
    })
    return r


KEYS = ("n", "win", "tsloss", "mp_sm", "mp_sl", "meanP", "margin")


def ci_pair(tag_a, tag_b):
    """Block-72h paired bootstrap CI cua hieu (A - B), nhan CI_INFLATE.

    Hai chan chay tren CUNG lich su nen dung CHUNG luoi khoi: moi rep rut khoi
    (co hoan lai) tu hop cac khoi, roi lay trade cua tung chan trong cac khoi do.
    => giu tuong quan thoi gian giua hai chan (paired), khong tron doc lap.
    """
    da, db = trades(tag_a), trades(tag_b)
    blocks = np.union1d(da.blk.unique(), db.blk.unique())
    ga = {k: v for k, v in da.groupby("blk")}
    gb = {k: v for k, v in db.groupby("blk")}
    rng = np.random.default_rng(SEED)
    obs = {k: rates(da)[k] - rates(db)[k] for k in KEYS}
    draws = {k: [] for k in KEYS}
    for _ in range(NREP):
        pick = rng.choice(blocks, size=len(blocks), replace=True)
        sa = pd.concat([ga[b] for b in pick if b in ga]) if any(b in ga for b in pick) else da.iloc[:0]
        sb = pd.concat([gb[b] for b in pick if b in gb]) if any(b in gb for b in pick) else db.iloc[:0]
        ra, rb = rates(sa), rates(sb)
        for k in KEYS:
            draws[k].append(ra[k] - rb[k])
    out = {}
    for k in KEYS:
        arr = np.asarray(draws[k], dtype=float)
        arr = arr[np.isfinite(arr)]
        lo, hi = np.percentile(arr, [2.5, 97.5])
        c = (lo + hi) / 2.0
        lo, hi = c - (c - lo) * CI_INFLATE, c + (hi - c) * CI_INFLATE
        out[k] = (obs[k], lo, hi, not (lo <= 0.0 <= hi))
    return out


def report(tags):
    rows = [stats(t) for t in tags]
    log.info("=== BANG CHINH (equity/CAGR KHONG phai tieu chi) ===")
    log.info("%-12s %5s %6s %7s %8s %8s %8s %8s %7s %5s %8s %7s",
             "tag", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP",
             "mMargin", "maxDD%", "UW", "equity", "CAGR%")
    for r in rows:
        log.info("%-12s %5.0f %6.2f %7.2f %8.3f %8.3f %8.3f %8.0f %7.2f %5d %8.0f %7.2f",
                 r["tag"], r["n"], r["win"], r["tsloss"], r["mp_sm"], r["mp_sl"],
                 r["meanP"], r["margin"], r["maxDD"], r["uw"], r["end"], r["cagr"])

    log.info("")
    log.info("=== PHAN BO PROFIT CUA WINNER (B1 doi hinh dang cai nay) ===")
    log.info("%-12s %6s %8s %8s %8s %8s %8s %8s", "tag", "n_win",
             "p10", "p25", "med", "p75", "p90", "max")
    for r in rows:
        dd = r["dist"]
        log.info("%-12s %6d %8.3f %8.3f %8.3f %8.3f %8.3f %8.2f", r["tag"], dd["n_win"],
                 dd["p10"], dd["p25"], dd["med"], dd["p75"], dd["p90"], dd["max"])

    log.info("")
    log.info("=== NHANH TRAILING (symbolPred leg-1; <= %.2f = STRONG cap 0.08) ===", WEAK_THR)
    log.info("%-12s %8s %8s %8s %9s", "tag", "STRONG", "WEAK", "no-pred", "STRONG%")
    for r in rows:
        tot = r["strong"] + r["weak"] + r["nopred"]
        log.info("%-12s %8d %8d %8d %8.1f%%", r["tag"], r["strong"], r["weak"],
                 r["nopred"], 100.0 * r["strong"] / tot if tot else float("nan"))

    log.info("")
    log.info("=== mean(margin) THEO NAM (phep kiem B3: phai TANG theo equity) ===")
    log.info("%-12s %10s %10s %10s %12s %8s %7s", "tag", "2022", "2023", "2024",
             "margin_leg1", "n_leg1", "n_dca")
    for r in rows:
        m = r["marg_year"]
        log.info("%-12s %10.1f %10.1f %10.1f %12.2f %8d %7d", r["tag"],
                 m.get("2022", float("nan")), m.get("2023", float("nan")),
                 m.get("2024", float("nan")), r["margin_leg1"], r["n_leg1"], r["n_dca"])

    log.info("")
    log.info("=== RETURN THEO QUY (%%) ===")
    log.info("%-12s %s", "tag", " ".join(f"{q:>7}" for q in QS))
    for r in rows:
        log.info("%-12s %s", r["tag"],
                 " ".join(f"{r['qr'].get(q, float('nan')):7.1f}" for q in QS))

    log.info("")
    log.info("=== RANG BUOC CUNG (maxDD<=15, UW<=120, khong nam am, khong quy < -5) ===")
    for r in rows:
        bad = []
        if r["maxDD"] < -15:
            bad.append(f"maxDD={r['maxDD']:.2f}")
        if r["uw"] > 120:
            bad.append(f"UW={r['uw']}")
        if r["neg_year"]:
            bad.append(f"nam_am={r['neg_year']}")
        if r["qmin"] < -5:
            bad.append(f"quy_min={r['qmin']:.1f}")
        log.info("%-12s %-6s nam=%s qmin=%.1f", r["tag"],
                 "PASS" if not bad else "FAIL", {k: round(v, 1) for k, v in r["yr"].items()},
                 r["qmin"])
        if bad:
            log.info("%-12s   vi pham: %s", "", " ".join(bad))


def main(argv):
    if argv and argv[0] == "--ci":
        a, b = argv[1], argv[2]
        log.info("=== CI khoi %dh x%.2f, %d rep, seed %d: (%s) - (%s) ===",
                 BLOCK_H, CI_INFLATE, NREP, SEED, a, b)
        out = ci_pair(a, b)
        log.info("%-10s %10s %10s %10s %8s", "rate", "hieu", "lo", "hi", "ngoai_CI")
        nout = 0
        for k in KEYS:
            o, lo, hi, sig = out[k]
            nout += int(sig)
            log.info("%-10s %10.3f %10.3f %10.3f %8s", k, o, lo, hi, "CO" if sig else "-")
        log.info("So rate NGOAI CI = %d (nguong de goi la KHAC: >= 2 cung huong)", nout)
    else:
        report(argv)


if __name__ == "__main__":
    main(sys.argv[1:])


def __getattr__(name):
    """[CHUAN HOA 2026-09-17] chan viec vo tinh dung lai hang so CI_INFLATE cu."""
    if name == "CI_INFLATE":
        raise AttributeError(
            "c3_rates.CI_INFLATE DA BI GO (2026-09-17). He so no rong CI phai tinh tu so "
            "ung vien cua round: dung c3_rates.inflate(k) voi k BAT BUOC truyen vao "
            "(k=1 -> 1.0 ; k>=2 -> sqrt(2 ln k)). Muon tai lap NGUYEN VAN mot doc cu thi dung "
            "c3_rates.LEGACY_CI_INFLATE (=1.21) VA ghi ro trong doc. "
            "Xem docs/AUDIT_CI_INFLATE_STANDARDIZATION.md")
    raise AttributeError("module %r has no attribute %r" % (__name__, name))
