"""paired_test.py — phep do GHEP CAP o tang TUNG LENH giua hai run DEV.

Phuong phap chot truoc o `docs/PREREG_PAIRED.md` (commit c96ddb3). KHONG doi
phuong phap trong file nay; moi tham so duoi day la trich tu pre-reg do.

Don vi quan sat : lenh da dong (`printDone.csv`), gan khoi theo THOI DIEM VAO.
Don vi bootstrap: KHOI thoi gian (24h / 72h / 168h), i.i.d. co hoan lai.
Ghep cap       : MOT danh sach chi so khoi dung cho CA HAI run (pre-reg muc 6).
Dai luong      : roisum (chinh), roimean, pnlsum, roisum_gross (robustness).

Doc du lieu dung Y logic da co:
  - printDone.csv: `research/analysis/sim_truth.py:16-21`
    (loc level==PREDICT_SYMBOL_TRADE, margin>0, roi = pnl/margin)
  - sim.out      : regex cua `/home/ubuntu/java/fsrun/qret.py:7` (equity = b+unP)

Dung: python3 paired_test.py <TAG_A> <TAG_B> [<TAG_A2> <TAG_B2> ...]
CAM `print` — moi dau ra qua module `logging`.
"""
import sys
import os
import re
import json
import hashlib
import logging
import numpy as np
import pandas as pd

BASE = "/home/ubuntu/java/devrun"
CAPITAL_START = 35000.0
N_REP = 2000
SEED = 20260903
BLOCK_HOURS = (24, 72, 168)
BLOCK_MAIN = 72
TOL_MIN = 15
Z975 = 1.959963985
Z80 = 0.841621234
LOG = logging.getLogger("paired_test")


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_trades(tag):
    """Y logic sim_truth.py:16-21. Tra ve DataFrame lenh da dong."""
    path = "%s/%s/storage/printDone.csv" % (BASE, tag)
    df = pd.read_csv(path)
    df = df[df.level == "PREDICT_SYMBOL_TRADE"].copy()
    for c in ("margin", "pnl", "profit"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df.margin > 0].copy()
    df["roi"] = df.pnl / df.margin
    df["roi_gross"] = df.profit / 100.0
    df["ts_in"] = pd.to_datetime(df.start, format="%Y%m%d %H:%M")
    df["ts_out"] = pd.to_datetime(df.end, format="%Y%m%d %H:%M", errors="coerce")
    df = df.dropna(subset=["roi", "ts_in"]).sort_values("ts_in").reset_index(drop=True)
    df["_md5"] = md5_of(path)
    return df


_RX_EQ = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")


def load_equity_tail(tag):
    """Regex y qret.py:7. Tra ve (equity_cuoi, unP_cuoi, so_ngay)."""
    path = "%s/%s/logs/sim.out" % (BASE, tag)
    rows = []
    with open(path, errors="ignore") as fh:
        for line in fh:
            m = _RX_EQ.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)), int(m.group(3))))
    if not rows:
        return (float("nan"), float("nan"), 0)
    e = pd.DataFrame(rows, columns=["d", "b", "unp"]).drop_duplicates("d", keep="last")
    last = e.iloc[-1]
    return (float(last.b + last.unp), float(last.unp), len(e))


def block_arrays(df, t0, n_blocks, hours):
    """Gop lenh len khoi. Khoi rong => 0 (pre-reg muc 3.2, KHONG bo)."""
    bid = ((df.ts_in - t0).dt.total_seconds() // (3600.0 * hours)).astype(int).values
    out = {}
    for name, col in (("roisum", "roi"), ("pnlsum", "pnl"), ("roisum_gross", "roi_gross")):
        a = np.zeros(n_blocks, dtype=np.float64)
        np.add.at(a, bid, df[col].values.astype(np.float64))
        out[name] = a
    cnt = np.zeros(n_blocks, dtype=np.float64)
    np.add.at(cnt, bid, 1.0)
    out["count"] = cnt
    out["pnlsum"] = out["pnlsum"] / CAPITAL_START
    return out


def ci_of(vals):
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


def boot_mean_diff(a, b, idx):
    """Hieu cua trung binh theo khoi, ghep cap tren CUNG idx."""
    return a[idx].mean(axis=1) - b[idx].mean(axis=1)


def boot_ratio_diff(sa, ca, sb, cb, idx):
    """Uoc luong ti so (roimean). Bo rep co count==0 o bat ky ben nao."""
    na = sa[idx].sum(axis=1)
    da = ca[idx].sum(axis=1)
    nb = sb[idx].sum(axis=1)
    db = cb[idx].sum(axis=1)
    ok = (da > 0) & (db > 0)
    d = np.full(idx.shape[0], np.nan)
    d[ok] = na[ok] / da[ok] - nb[ok] / db[ok]
    return d, int((~ok).sum())


def match_trades(a, b, tol_min):
    """Ghep tham lam theo (sym, side) trong dung sai tol_min phut.
    CHI dung cho bang phan ra (pre-reg muc 3.3), KHONG dung cho phan quyet."""
    tol = tol_min * 60.0
    ai = a.reset_index(drop=True)
    bi = b.reset_index(drop=True)
    ta = ai.ts_in.values.astype("datetime64[s]").astype(np.int64)
    tb = bi.ts_in.values.astype("datetime64[s]").astype(np.int64)
    ga = {}
    for i, k in enumerate(zip(ai.sym.values, ai.side.values)):
        ga.setdefault(k, []).append(i)
    gb = {}
    for j, k in enumerate(zip(bi.sym.values, bi.side.values)):
        gb.setdefault(k, []).append(j)
    pairs = []
    for k, ilist in ga.items():
        jlist = gb.get(k)
        if not jlist:
            continue
        cand = []
        for i in ilist:
            for j in jlist:
                dt = abs(int(ta[i]) - int(tb[j]))
                if dt <= tol:
                    cand.append((dt, i, j))
        cand.sort()
        ua, ub = set(), set()
        for dt, i, j in cand:
            if i in ua or j in ub:
                continue
            ua.add(i)
            ub.add(j)
            pairs.append((i, j))
    mi = set(i for i, _ in pairs)
    mj = set(j for _, j in pairs)
    only_a = [i for i in range(len(ai)) if i not in mi]
    only_b = [j for j in range(len(bi)) if j not in mj]
    return pairs, only_a, only_b


def decomp_arrays(a, b, t0, n_blocks, hours, tol_min):
    """3 thanh phan cua hieu tong roi, dang mang theo khoi (de bootstrap cung idx)."""
    pairs, only_a, only_b = match_trades(a, b, tol_min)
    ai = a.reset_index(drop=True)
    bi = b.reset_index(drop=True)
    bid_a = ((ai.ts_in - t0).dt.total_seconds() // (3600.0 * hours)).astype(int).values
    bid_b = ((bi.ts_in - t0).dt.total_seconds() // (3600.0 * hours)).astype(int).values
    roi_a = ai.roi.values.astype(np.float64)
    roi_b = bi.roi.values.astype(np.float64)
    arr = {k: np.zeros(n_blocks) for k in ("common", "only_a", "only_b")}
    for i, j in pairs:
        arr["common"][bid_a[i]] += roi_a[i] - roi_b[j]
    for i in only_a:
        arr["only_a"][bid_a[i]] += roi_a[i]
    for j in only_b:
        arr["only_b"][bid_b[j]] -= roi_b[j]
    meta = {"n_common": len(pairs), "n_only_a": len(only_a), "n_only_b": len(only_b),
            "roi_common_a": float(sum(roi_a[i] for i, _ in pairs)),
            "roi_common_b": float(sum(roi_b[j] for _, j in pairs)),
            "roi_only_a": float(sum(roi_a[i] for i in only_a)),
            "roi_only_b": float(sum(roi_b[j] for j in only_b))}
    return arr, meta


def verdict(ci_by_h):
    """Pre-reg muc 5. ci_by_h: {hours: (lo, hi)}."""
    excl = {h: (lo > 0 or hi < 0) for h, (lo, hi) in ci_by_h.items()}
    sgn = {h: (1 if lo > 0 else (-1 if hi < 0 else 0)) for h, (lo, hi) in ci_by_h.items()}
    code = "".join("Y" if excl[h] else "n" for h in BLOCK_HOURS)
    if all(excl.values()) and len(set(sgn.values())) == 1:
        return "THANG", code
    return "KHONG PHAN BIET DUOC", code


def run_pair(tag_a, tag_b):
    a = load_trades(tag_a)
    b = load_trades(tag_b)
    identical = (a._md5.iloc[0] == b._md5.iloc[0]) or (tag_a == tag_b)
    eq_a = load_equity_tail(tag_a)
    eq_b = load_equity_tail(tag_b)
    LOG.info("")
    LOG.info("=" * 100)
    LOG.info("CAP: %s  vs  %s", tag_a, tag_b)
    LOG.info("=" * 100)
    LOG.info("  %-14s n_lenh=%5d  md5=%s  equity_cuoi=%9.0f  unP_cuoi=%8.0f  ngay=%d",
             tag_a, len(a), a._md5.iloc[0][:12], eq_a[0], eq_a[1], eq_a[2])
    LOG.info("  %-14s n_lenh=%5d  md5=%s  equity_cuoi=%9.0f  unP_cuoi=%8.0f  ngay=%d",
             tag_b, len(b), b._md5.iloc[0][:12], eq_b[0], eq_b[1], eq_b[2])
    LOG.info("  printDone.csv giong nhau tung byte: %s", "CO => NUT TRO (VOID)" if identical else "KHONG")
    t0 = min(a.ts_in.min(), b.ts_in.min())
    tmax = max(a.ts_in.max(), b.ts_in.max())
    LOG.info("  span vao lenh: %s .. %s  (%.1f ngay)", t0, tmax,
             (tmax - t0).total_seconds() / 86400.0)
    res = {"tag_a": tag_a, "tag_b": tag_b, "identical": bool(identical),
           "n_a": len(a), "n_b": len(b), "unp_a": eq_a[1], "unp_b": eq_b[1],
           "equity_a": eq_a[0], "equity_b": eq_b[0], "blocks": {}}
    for hours in BLOCK_HOURS:
        n_blocks = int((tmax - t0).total_seconds() // (3600.0 * hours)) + 1
        ba = block_arrays(a, t0, n_blocks, hours)
        bb = block_arrays(b, t0, n_blocks, hours)
        rng = np.random.default_rng(SEED)
        idx = rng.integers(0, n_blocks, size=(N_REP, n_blocks))
        blk = {"n_blocks": n_blocks,
               "occ_a": int((ba["count"] > 0).sum()), "occ_b": int((bb["count"] > 0).sum()),
               "stats": {}}
        for name in ("roisum", "pnlsum", "roisum_gross"):
            d = float(ba[name].mean() - bb[name].mean())
            reps = boot_mean_diff(ba[name], bb[name], idx)
            blk["stats"][name] = pack(d, reps, hours, 0)
        dr, ndrop = boot_ratio_diff(ba["roisum"], ba["count"], bb["roisum"], bb["count"], idx)
        dpt = float(ba["roisum"].sum() / max(ba["count"].sum(), 1e-12)
                    - bb["roisum"].sum() / max(bb["count"].sum(), 1e-12))
        blk["stats"]["roimean"] = pack(dpt, dr[~np.isnan(dr)], hours, ndrop)
        blk["decomp"] = {}
        for tol in (0, TOL_MIN):
            arr, meta = decomp_arrays(a, b, t0, n_blocks, hours, tol)
            comp = {}
            for k in ("common", "only_a", "only_b"):
                reps = arr[k][idx].mean(axis=1)
                lo, hi = ci_of(reps)
                comp[k] = {"point": float(arr[k].mean()), "ci": [lo, hi],
                           "total": float(arr[k].sum())}
            blk["decomp"]["tol%d" % tol] = {"meta": meta, "comp": comp}
        res["blocks"][hours] = blk
    return res


def pack(d, reps, hours, ndrop):
    reps = np.asarray(reps, dtype=np.float64)
    lo, hi = ci_of(reps)
    sd = float(reps.std(ddof=1)) if reps.size > 1 else 0.0
    p_gt = float((reps > 0).mean())
    p2 = 2.0 * min(float((reps <= 0).mean()), float((reps >= 0).mean()))
    per_year = 365.0 * 24.0 / hours
    return {"d": float(d), "ci": [lo, hi], "sd": sd, "p_gt0": p_gt, "p_two": min(p2, 1.0),
            "mde80": (Z975 + Z80) * sd, "mde50": Z975 * sd, "mde_gs256": 2.35 * sd,
            "mde80_year_pct": (Z975 + Z80) * sd * per_year * 100.0,
            "d_year_pct": float(d) * per_year * 100.0,
            "ci_year_pct": [lo * per_year * 100.0, hi * per_year * 100.0],
            "n_drop": ndrop}


def report(res):
    ta, tb = res["tag_a"], res["tag_b"]
    for name in ("roisum", "roimean", "pnlsum", "roisum_gross"):
        ci_by_h = {}
        LOG.info("")
        LOG.info("  --- dai luong %s%s ---", name,
                 "  [CHINH]" if name == "roisum" else "")
        LOG.info("  %-5s %-7s %-7s %12s %26s %10s %8s %10s",
                 "khoi", "n_blk", "occA/B", "d", "CI95 cua HIEU", "sd_boot", "P(d>0)", "MDE80")
        for hours in BLOCK_HOURS:
            blk = res["blocks"][hours]
            s = blk["stats"][name]
            ci_by_h[hours] = tuple(s["ci"])
            LOG.info("  %-5d %-7d %3d/%-3d %12.6f  [%11.6f, %11.6f] %10.6f %8.3f %10.6f",
                     hours, blk["n_blocks"], blk["occ_a"], blk["occ_b"], s["d"],
                     s["ci"][0], s["ci"][1], s["sd"], s["p_gt0"], s["mde80"])
        v, code = verdict(ci_by_h)
        if res["identical"]:
            v = "VOID - NUT TRO (printDone.csv giong nhau tung byte)"
        m = res["blocks"][BLOCK_MAIN]["stats"][name]
        LOG.info("  loai tru 0 (%s) = %s  =>  PHAN QUYET: %s",
                 "/".join(str(h) for h in BLOCK_HOURS), code, v)
        LOG.info("  quy doi nam (khong lai kep, khoi %dh): d = %+.3f%%/nam  CI95 [%+.3f, %+.3f]"
                 "  MDE80 = %.3f%%/nam", BLOCK_MAIN, m["d_year_pct"],
                 m["ci_year_pct"][0], m["ci_year_pct"][1], m["mde80_year_pct"])
        LOG.info("  nguong GS N=256 (sqrt(2 ln 256)=2.35 * sd): |d| can > %.6f ; |d| do duoc = %.6f"
                 " => %s", m["mde_gs256"], abs(m["d"]),
                 "QUA" if abs(m["d"]) > m["mde_gs256"] else "KHONG QUA")
        LOG.info("  p-value bootstrap 2 phia (khoi %dh) = %.4f", BLOCK_MAIN, m["p_two"])
        if m["n_drop"]:
            LOG.info("  CANH BAO: %d/%d rep bi bo (count==0 mot ben)", m["n_drop"], N_REP)


def report_decomp(res):
    ta, tb = res["tag_a"], res["tag_b"]
    for hours in (BLOCK_MAIN,):
        blk = res["blocks"][hours]
        for tol in (0, TOL_MIN):
            dc = blk["decomp"]["tol%d" % tol]
            mt, cp = dc["meta"], dc["comp"]
            LOG.info("")
            LOG.info("  --- PHAN RA hieu roisum (khoi %dh, dung sai ghep %d phut) ---", hours, tol)
            LOG.info("  lenh chung=%d | chi %s=%d | chi %s=%d",
                     mt["n_common"], ta, mt["n_only_a"], tb, mt["n_only_b"])
            LOG.info("  %-34s %14s %14s %26s", "thanh phan", "tong roi", "trung binh/khoi", "CI95/khoi")
            rows = [("lenh CHUNG (roi_A - roi_B) [EXIT]", "common"),
                    ("chi %s co (+) [CHON/GATE]" % ta, "only_a"),
                    ("chi %s co (-) [CHON/GATE]" % tb, "only_b")]
            tot = 0.0
            for lab, k in rows:
                c = cp[k]
                tot += c["total"]
                LOG.info("  %-34s %14.4f %14.6f  [%11.6f, %11.6f]",
                         lab, c["total"], c["point"], c["ci"][0], c["ci"][1])
            LOG.info("  %-34s %14.4f  (kiem: tong roi_A - tong roi_B = %.4f)",
                     "TONG", tot, res["_tot_diff"])



# ---------------------------------------------------------------------------
# THAM CHIEU TANG EQUITY — de tra loi "tang tung lenh co NHAY HON khong" tren
# CUNG mot cap, CUNG seed. Phuong phap: docs/PREREG_CI.md muc 2 (block 21 ngay
# chinh, kiem 10 va 42; moving-block CIRCULAR; ghep cap; 2000 rep; seed
# 20260903). Khong thay the phan quyet cua tang tung lenh.
# ---------------------------------------------------------------------------
EQ_BLOCKS = (10, 21, 42)
EQ_MAIN = 21


def load_daily_returns(tag):
    path = "%s/%s/logs/sim.out" % (BASE, tag)
    rows = []
    with open(path, errors="ignore") as fh:
        for line in fh:
            m = _RX_EQ.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "equity"]).drop_duplicates("d", keep="last")
    eq = e.equity.values.astype(np.float64)
    prev = np.concatenate(([CAPITAL_START], eq[:-1]))
    return eq / prev - 1.0


def _mb_index(rng, n, L, n_rep):
    """Moving-block circular: chon diem bat dau, ghep cho du n, cat khoi cuoi."""
    k = int(np.ceil(n / L))
    st = rng.integers(0, n, size=(n_rep, k))
    off = np.arange(L)
    idx = (st[:, :, None] + off[None, None, :]) % n
    return idx.reshape(n_rep, k * L)[:, :n]


def equity_reference(tag_a, tag_b):
    ra = load_daily_returns(tag_a)
    rb = load_daily_returns(tag_b)
    n = min(len(ra), len(rb))
    ra, rb = ra[:n], rb[:n]
    out = {"n_days": n, "blocks": {}}
    la = np.log1p(ra)
    lb = np.log1p(rb)
    for L in EQ_BLOCKS:
        rng = np.random.default_rng(SEED)
        idx = _mb_index(rng, n, L, N_REP)
        ca = np.expm1(la[idx].sum(axis=1) * (365.0 / n)) * 100.0
        cb = np.expm1(lb[idx].sum(axis=1) * (365.0 / n)) * 100.0
        reps = ca - cb
        d = (np.expm1(la.sum() * 365.0 / n) - np.expm1(lb.sum() * 365.0 / n)) * 100.0
        lo, hi = ci_of(reps)
        sd = float(reps.std(ddof=1))
        out["blocks"][L] = {"d_pp": float(d), "ci_pp": [lo, hi], "sd_pp": sd,
                           "mde80_pp": (Z975 + Z80) * sd, "n_eff": int(np.ceil(n / L)),
                           "p_gt0": float((reps > 0).mean())}
    return out


def report_equity_reference(tag_a, tag_b, eqr, trade_mde80_year_pct):
    LOG.info("")
    LOG.info("  --- THAM CHIEU tang EQUITY/CAGR (PREREG_CI muc 2, cung seed) ---")
    LOG.info("  %-5s %-7s %12s %26s %10s %10s", "block", "n_eff", "d (pp CAGR)",
             "CI95 cua HIEU (pp)", "sd_boot", "MDE80")
    for L in EQ_BLOCKS:
        b = eqr["blocks"][L]
        LOG.info("  %-5d %-7d %12.3f  [%11.3f, %11.3f] %10.3f %10.3f", L, b["n_eff"],
                 b["d_pp"], b["ci_pp"][0], b["ci_pp"][1], b["sd_pp"], b["mde80_pp"])
    em = eqr["blocks"][EQ_MAIN]["mde80_pp"]
    LOG.info("  SO SANH DO NHAY (MDE80, don vi %s/nam cua von):", "%")
    LOG.info("    tang equity/CAGR (block 21 ngay) : %8.3f pp/nam", em)
    LOG.info("    tang tung lenh (pnlsum, khoi 72h): %8.3f %%/nam", trade_mde80_year_pct)
    if trade_mde80_year_pct > 0:
        LOG.info("    ti le equity/lenh = %.2fx  => tang tung lenh %s",
                 em / trade_mde80_year_pct,
                 "NHAY HON" if trade_mde80_year_pct < em else "KHONG nhay hon")


def main(argv):
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    if len(argv) < 3 or len(argv) % 2 == 0:
        LOG.error("dung: paired_test.py <TAG_A> <TAG_B> [<TAG_A2> <TAG_B2> ...]")
        return 2
    LOG.info("paired_test — phuong phap: docs/PREREG_PAIRED.md (commit c96ddb3)")
    LOG.info("N_REP=%d SEED=%d khoi=%s dai luong CHINH=roisum=sum(pnl/margin) theo khoi",
             N_REP, SEED, BLOCK_HOURS)
    allres = []
    for k in range(1, len(argv), 2):
        ta, tb = argv[k], argv[k + 1]
        res = run_pair(ta, tb)
        a = load_trades(ta)
        b = load_trades(tb)
        res["_tot_diff"] = float(a.roi.sum() - b.roi.sum())
        report(res)
        report_decomp(res)
        try:
            eqr = equity_reference(ta, tb)
            report_equity_reference(
                ta, tb, eqr,
                res["blocks"][BLOCK_MAIN]["stats"]["pnlsum"]["mde80_year_pct"])
            res["equity_ref"] = eqr
        except (OSError, ValueError) as e:
            LOG.warning("  khong tinh duoc tham chieu equity: %s", e)
        allres.append(res)
    out = "/home/ubuntu/paired/paired_out.json"
    try:
        with open(out, "w") as fh:
            json.dump(allres, fh, indent=1, default=float)
        LOG.info("")
        LOG.info("json => %s", out)
    except OSError as e:
        LOG.warning("khong ghi duoc json: %s", e)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
