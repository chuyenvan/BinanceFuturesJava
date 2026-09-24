"""F1 — noi dong co hoi o TONG EXPOSURE KHONG DOI. Cham diem 4 run F1_* + neo C2b.

Tieu chi PRIMARY (pre-reg docs/prereg/PREREG_F1_FLOW.md): sd(daily equity return), n~900.
C1 = mean(tong margin dang mo / equity) theo ngay -> quyet dinh tinh hop le (+-20% vs F1_parity).
Equity KHONG phai tieu chi (bao cao rieng).
Usage: python3 f1_flow.py
"""
import hashlib
import logging
import re

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

B = "/home/ubuntu/java/devrun"
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")
ANCHOR = "C2b"
ANCHOR_MD5 = "8f7afdfb27b15f5b6d4c886700def93c"
TAGS = ["F1_parity", "F1_k16", "F1_k24", "F1_k32"]
KMAP = {"F1_parity": 8, "F1_k16": 16, "F1_k24": 24, "F1_k32": 32, "C2b": 8}


def equity(tag):
    """Equity cuoi ngay = b + unP, doc tu logs/sim.out."""
    rows = []
    with open(f"{B}/{tag}/logs/sim.out", errors="ignore") as fh:
        for line in fh:
            m = RX.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "equity"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d").equity.astype(float)


def trades(tag):
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv", on_bad_lines="skip")
    d["margin"] = pd.to_numeric(d["margin"], errors="coerce")
    d["ts"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M", errors="coerce")
    d["te"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M", errors="coerce")
    return d.dropna(subset=["ts", "margin"])


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def period_ret(e, freq):
    last = e.resample(freq).last()
    base = last.shift(1)
    base.iloc[0] = e.iloc[0]
    return last / base - 1.0


def daily_open(tag, idx):
    """Voi moi ngay trong idx: so lenh dang mo + tong margin dang mo."""
    t = trades(tag)
    days = idx.values.astype("datetime64[D]")
    s = t.ts.values.astype("datetime64[D]")
    e = t.te.fillna(t.ts).values.astype("datetime64[D]")
    mg = t.margin.values.astype(float)
    n = np.zeros(len(days))
    m = np.zeros(len(days))
    for si, ei, mi in zip(s, e, mg):
        sel = (days >= si) & (days <= ei)
        n[sel] += 1.0
        m[sel] += mi
    return n, m


def metrics(tag):
    e = equity(tag)
    n_open, m_open = daily_open(tag, e.index)
    r = e.pct_change().dropna()
    sd = float(r.std(ddof=1))
    mu = float(r.mean())
    cm = e.cummax()
    uw = (e < cm).values
    best = cur = 0
    for f in uw:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    t = trades(tag)
    yr = period_ret(e, "YE")
    qr = period_ret(e, "QE")
    return {
        "tag": tag, "K": KMAP.get(tag), "n_days": len(e), "n_ret": len(r),
        "sd_daily": sd, "mean_daily": mu,
        "sharpe": mu / sd * np.sqrt(365) if sd > 0 else float("nan"),
        "mean_pos": float(n_open.mean()),
        "c1_deploy": float((m_open / e.values).mean()),
        "max_margin": float(m_open.max()),
        "maxdd": float((e / cm - 1.0).min()),
        "underwater": int(best),
        "equity_end": float(e.iloc[-1]), "n_trades": int(len(t)),
        "worst_year": float(yr.min()), "worst_q": float(qr.min()),
        "yr": yr, "qr": qr,
    }


def main():
    a_md5 = md5(f"{B}/{ANCHOR}/storage/printDone.csv")
    p_md5 = md5(f"{B}/F1_parity/storage/printDone.csv")
    log.info("== PARITY GATE ==")
    log.info("C2b       md5=%s (neo=%s match=%s)", a_md5, ANCHOR_MD5, a_md5 == ANCHOR_MD5)
    log.info("F1_parity md5=%s", p_md5)
    log.info("PARITY=%s", "PASS" if p_md5 == a_md5 == ANCHOR_MD5 else "FAIL")

    rows = [metrics(t) for t in [ANCHOR] + TAGS]
    base = [m for m in rows if m["tag"] == "F1_parity"][0]

    log.info("")
    log.info("== C1 VON TRIEN KHAI (mean margin_open/equity theo ngay) ==")
    for m in rows:
        dev = m["c1_deploy"] / base["c1_deploy"] - 1.0
        ok = "-" if m["tag"] == ANCHOR else ("OK" if abs(dev) <= 0.20 else "FAIL")
        log.info("%-10s c1=%.4f  dev_vs_parity=%+.1f%%  %s", m["tag"], m["c1_deploy"], 100 * dev, ok)

    log.info("")
    log.info("== SANITY: vi the dong thoi trung binh ==")
    for m in rows:
        log.info("%-10s K=%-3s mean_pos=%.2f  max_margin=%.0f  n_trades=%d",
                 m["tag"], m["K"], m["mean_pos"], m["max_margin"], m["n_trades"])

    log.info("")
    log.info("== PRIMARY: sd(daily return) + Sharpe ==")
    log.info("%-10s %-4s %-6s %-10s %-10s %-8s", "tag", "K", "n_ret", "sd_daily", "mean_daily", "sharpe")
    for m in rows:
        log.info("%-10s %-4s %-6d %-10.6f %-10.6f %-8.3f",
                 m["tag"], m["K"], m["n_ret"], m["sd_daily"], m["mean_daily"], m["sharpe"])

    log.info("")
    log.info("== RANG BUOC CUNG (maxDD<=15%%, uw<=120d, year>=0, q>=-5%%) ==")
    for m in rows:
        v = []
        if m["maxdd"] < -0.15: v.append("maxDD")
        if m["underwater"] > 120: v.append("underwater")
        if m["worst_year"] < 0: v.append("year_neg")
        if m["worst_q"] < -0.05: v.append("q_lt_-5%")
        log.info("%-10s maxDD=%.2f%% uw=%dd worst_year=%+.2f%% worst_q=%+.2f%% -> %s",
                 m["tag"], 100 * m["maxdd"], m["underwater"], 100 * m["worst_year"],
                 100 * m["worst_q"], "PASS" if not v else "LOAI:" + ",".join(v))

    log.info("")
    log.info("== EQUITY (KHONG PHAI TIEU CHI) ==")
    for m in rows:
        log.info("%-10s equity_end=%.0f n_trades=%d", m["tag"], m["equity_end"], m["n_trades"])

    log.info("")
    log.info("== QUY / NAM chi tiet ==")
    for m in rows:
        log.info("-- %s", m["tag"])
        log.info("year: %s", {str(k.year): round(100 * v, 2) for k, v in m["yr"].items()})
        log.info("quarter: %s", {str(k.to_period("Q")): round(100 * v, 2) for k, v in m["qr"].items()})


if __name__ == "__main__":
    main()
