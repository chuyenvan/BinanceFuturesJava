#!/usr/bin/env python3
"""GHEP CAP THEO TICK — do MDE80 o tang tick va so voi tang equity (docs/PREREG_TICKLOG.md muc 6).

Phuong phap CHOT TRUOC o PREREG_TICKLOG muc 6.2 (theo docs/PREREG_CI.md, khong doi mot chu):
khoi 72h chinh (do ben 24h/168h), N_REP=2000, SEED=20260903, ghep cap tren CUNG danh sach chi so
khoi, CI95 percentile, MDE80 = 2.80158*sd_boot.

Bon dai luong bao cao (PREREG_TICKLOG muc 6.3/6.4/6.5):
  E0a  tang equity CAGR, mau 1 ngay, khoi 21 ngay      (tai lap PAIRED_CALIB)
  E0b  tang equity, dai luong TONG LUONG, khoi 72h     (DOI CHUNG do dai khoi)
  E1   tang tick,  dai luong TONG LUONG, khoi 72h      (DAI LUONG CHINH)
  E2   tang tick,  roimean_tick, khoi 72h              (dai luong PHU)

Dung: tick_paired.py <TAG_A> <TAG_B> [tickdir]
"""
import sys
import os
import gzip
import logging
import numpy as np

BASE = "/home/ubuntu/java/devrun"
TICK = "/home/ubuntu/tick"
CAPITAL_START = 35000.0
N_REP = 2000
SEED = 20260903
BLOCK_HOURS = (24, 72, 168)
BLOCK_MAIN = 72
EQ_BLOCKS = (10, 21, 42)
EQ_MAIN = 21
Z975 = 1.959963985
Z80 = 0.841621234
MDE_K = Z975 + Z80          # 2.80158
HOUR_MS = 3600_000
LOG = logging.getLogger("tick_paired")

DT_TICK = np.dtype([("ts", ">i8"), ("pool", ">i2"), ("npass", ">i2"), ("ncand", ">i2"),
                    ("nactive", ">i2"), ("bal", ">f4"), ("prof", ">f4"),
                    ("unreal", ">f4"), ("margin", ">f4")])
DT_POS = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("flags", "i1"), ("status", "i1"),
                   ("leg", "i1"), ("p1", "i1"), ("p2", "i1"), ("p3", "i1"),
                   ("entry", ">f4"), ("last", ">f4"), ("peak", ">f4"), ("sl", ">f4")])
DT_CAND = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("rank", ">i2"), ("dec", "i1"),
                    ("lvl", "i1"), ("leg", "i1"), ("pad", "i1"), ("score", ">f4"),
                    ("dynthr", ">f4"), ("predret", ">f4"), ("price", ">f4")])


def read_stream(path, dt):
    with gzip.open(path, "rb") as fh:
        raw = fh.read()
    magic = int.from_bytes(raw[0:4], "big")
    ver = int.from_bytes(raw[4:8], "big")
    reclen = int.from_bytes(raw[8:12], "big")
    if magic != 0x544B4C47 or ver != 1 or reclen != dt.itemsize:
        raise SystemExit("%s: header sai (magic=%x ver=%d recLen=%d, cho %d)"
                         % (path, magic, ver, reclen, dt.itemsize))
    body = raw[16:]
    n = len(body) // dt.itemsize
    if len(body) % dt.itemsize:
        raise SystemExit("%s: %d byte du (file bi cat?)" % (path, len(body) % dt.itemsize))
    return np.frombuffer(body[:n * dt.itemsize], dtype=dt)


def ci_of(v):
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


def pack(reps, d, extra=None):
    lo, hi = ci_of(reps)
    sd = float(reps.std(ddof=1))
    out = {"d": float(d), "ci": [lo, hi], "sd": sd, "mde80": MDE_K * sd,
           "excl0": bool(lo > 0 or hi < 0), "p_gt0": float((reps > 0).mean()),
           "t": (float(d) / sd) if sd > 0 else float("nan")}
    if extra:
        out.update(extra)
    return out


# ---------------------------------------------------------------------------
# tang TICK
# ---------------------------------------------------------------------------
def tick_flow_blocks(tk, t0, n_blocks, hours):
    """Tong luong equity theo khoi: S_b = Sigma (eq(t) - eq(t-1)) / 35000."""
    eq = (tk["bal"].astype(np.float64) + tk["prof"].astype(np.float64)
          + tk["unreal"].astype(np.float64))
    f = np.empty_like(eq)
    f[0] = eq[0] - CAPITAL_START
    f[1:] = np.diff(eq)
    bid = ((tk["ts"].astype(np.int64) - t0) // (HOUR_MS * hours)).astype(int)
    a = np.zeros(n_blocks)
    np.add.at(a, bid, f / CAPITAL_START)
    return a


def pos_roimean_blocks(ps, t0, n_blocks, hours):
    """Trung binh theo tick cua ROI trung binh cac cum DANG MO (chi tick tren luoi 15 phut).

    Tra ve (sum_theo_khoi, so_tick_theo_khoi) — chia o ngoai de con bo khoi rong o CA HAI run.
    """
    m = (ps["ts"] % 900000 == 0) & ((ps["flags"] & 2) == 0)   # bo dong CLOSED (ghi ngoai luoi)
    ts = ps["ts"][m].astype(np.int64)
    entry = ps["entry"][m].astype(np.float64)
    last = ps["last"][m].astype(np.float64)
    ok = np.isfinite(entry) & np.isfinite(last) & (entry > 0)
    ts, roi = ts[ok], last[ok] / entry[ok] - 1.0
    # buoc 1: trung binh theo TICK
    uts, inv = np.unique(ts, return_inverse=True)
    s = np.zeros(len(uts)); c = np.zeros(len(uts))
    np.add.at(s, inv, roi); np.add.at(c, inv, 1.0)
    per_tick = s / c
    # buoc 2: gop len khoi
    bid = ((uts - t0) // (HOUR_MS * hours)).astype(int)
    bs = np.zeros(n_blocks); bc = np.zeros(n_blocks)
    np.add.at(bs, bid, per_tick); np.add.at(bc, bid, 1.0)
    return bs, bc


# ---------------------------------------------------------------------------
# tang EQUITY (tu sim.out) — E0a tai lap PAIRED_CALIB, E0b doi chung khoi 72h
# ---------------------------------------------------------------------------
import re
_RX_EQ = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")


def load_daily_equity(tag):
    rows = []
    with open("%s/%s/logs/sim.out" % (BASE, tag), errors="ignore") as fh:
        for line in fh:
            m = _RX_EQ.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    seen = {}
    for d, e in rows:
        seen[d] = e            # giu ban ghi CUOI trong ngay (PREREG_CI muc 1)
    days = sorted(seen)
    return np.array(days), np.array([seen[d] for d in days], dtype=np.float64)


def _mb_index(rng, n, L, n_rep):
    k = int(np.ceil(n / L))
    st = rng.integers(0, n, size=(n_rep, k))
    off = np.arange(L)
    idx = (st[:, :, None] + off[None, None, :]) % n
    return idx.reshape(n_rep, k * L)[:, :n]


def equity_cagr(tag_a, tag_b):
    """E0a — y het paired_test.equity_reference / PREREG_CI muc 2."""
    _, ea = load_daily_equity(tag_a)
    _, eb = load_daily_equity(tag_b)
    n = min(len(ea), len(eb))
    ea, eb = ea[:n], eb[:n]
    ra = ea / np.concatenate(([CAPITAL_START], ea[:-1])) - 1.0
    rb = eb / np.concatenate(([CAPITAL_START], eb[:-1])) - 1.0
    la, lb = np.log1p(ra), np.log1p(rb)
    out = {"n_days": n, "blocks": {}}
    for L in EQ_BLOCKS:
        rng = np.random.default_rng(SEED)
        idx = _mb_index(rng, n, L, N_REP)
        ca = np.expm1(la[idx].sum(axis=1) * (365.0 / n)) * 100.0
        cb = np.expm1(lb[idx].sum(axis=1) * (365.0 / n)) * 100.0
        d = (np.expm1(la.sum() * 365.0 / n) - np.expm1(lb.sum() * 365.0 / n)) * 100.0
        out["blocks"][L] = pack(ca - cb, d, {"n_eff": int(np.ceil(n / L))})
    return out


def equity_flow(tag_a, tag_b, hours):
    """E0b — CUNG dai luong tong luong nhu E1, nhung mau 1 NGAY, khoi `hours`."""
    da, ea = load_daily_equity(tag_a)
    db, eb = load_daily_equity(tag_b)
    n = min(len(ea), len(eb))
    ea, eb = ea[:n], eb[:n]
    days = int(round(hours / 24.0))
    n_blocks = int(np.ceil(n / days))
    bid = (np.arange(n) // days).astype(int)
    per_year = 8760.0 / hours

    def blk(e):
        f = np.empty(n); f[0] = e[0] - CAPITAL_START; f[1:] = np.diff(e)
        a = np.zeros(n_blocks); np.add.at(a, bid, f / CAPITAL_START)
        return a
    A, B = blk(ea), blk(eb)
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, n_blocks, size=(N_REP, n_blocks))
    reps = (A[idx].mean(axis=1) - B[idx].mean(axis=1)) * per_year * 100.0
    d = (A.mean() - B.mean()) * per_year * 100.0
    return pack(reps, d, {"n_blocks": n_blocks})


def cand_summary(tag):
    p = "%s/%s/cand.bin.gz" % (TICK, tag)
    if not os.path.exists(p):
        return None
    cd = read_stream(p, DT_CAND)
    names = {0: "ENTERED", 1: "ALREADY_OPEN", 2: "NO_TICKER", 3: "NO_PRED", 4: "GATE_REJECT",
             5: "NO_BUDGET", 6: "TIER3_DCA", 7: "GRID_EXHAUSTED", 8: "TOPK_CUT"}
    u, c = np.unique(cd["dec"], return_counts=True)
    return len(cd), {names.get(int(k), str(k)): int(v) for k, v in zip(u, c)}


def main(argv):
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    if len(argv) < 3:
        LOG.error("dung: tick_paired.py <TAG_A> <TAG_B> [tickdir_A] [tickdir_B]")
        return 2
    ta, tb = argv[1], argv[2]
    dira = argv[3] if len(argv) > 3 else ta
    dirb = argv[4] if len(argv) > 4 else tb

    LOG.info("=== GHEP CAP THEO TICK: %s vs %s ===", ta, tb)
    LOG.info("N_REP=%d SEED=%d MDE80=%.5f*sd  (docs/PREREG_TICKLOG.md muc 6)", N_REP, SEED, MDE_K)

    tka = read_stream("%s/%s/tick.bin.gz" % (TICK, dira), DT_TICK)
    tkb = read_stream("%s/%s/tick.bin.gz" % (TICK, dirb), DT_TICK)
    LOG.info("tick.bin: A=%d dong  B=%d dong", len(tka), len(tkb))
    if not np.array_equal(tka["ts"], tkb["ts"]):
        LOG.info("  CANH BAO: luoi tick hai run KHONG trung nhau -> giao nhau")
        common = np.intersect1d(tka["ts"], tkb["ts"])
        tka = tka[np.isin(tka["ts"], common)]
        tkb = tkb[np.isin(tkb["ts"], common)]
        LOG.info("  sau giao: %d tick", len(tka))
    t0 = int(min(tka["ts"][0], tkb["ts"][0]))
    t1 = int(max(tka["ts"][-1], tkb["ts"][-1]))
    LOG.info("span tick: %d .. %d (%.2f ngay)", t0, t1, (t1 - t0) / 86400000.0)

    # ---- E0a: equity CAGR, khoi 21 ngay (tai lap PAIRED_CALIB) ----
    eqc = equity_cagr(ta, tb)
    LOG.info("")
    LOG.info("--- E0a  tang EQUITY / CAGR (mau 1 ngay, moving-block circular) ---")
    LOG.info("%-6s %-7s %10s %26s %9s %10s", "block", "n_eff", "d (pp)", "CI95 (pp)", "sd", "MDE80(pp)")
    for L in EQ_BLOCKS:
        b = eqc["blocks"][L]
        LOG.info("%-6d %-7d %10.3f  [%11.3f, %11.3f] %9.3f %10.3f", L, b["n_eff"], b["d"],
                 b["ci"][0], b["ci"][1], b["sd"], b["mde80"])
    e0a = eqc["blocks"][EQ_MAIN]["mde80"]

    # ---- E0b: equity, tong luong, khoi 72h (doi chung) ----
    LOG.info("")
    LOG.info("--- E0b  tang EQUITY, dai luong TONG LUONG (mau 1 ngay), khoi 72h ---")
    LOG.info("%-6s %-7s %10s %26s %9s %10s", "block", "n_blk", "d (%/nam)", "CI95 (%/nam)", "sd", "MDE80(%)")
    e0b = {}
    for h in BLOCK_HOURS:
        r = equity_flow(ta, tb, h)
        e0b[h] = r
        LOG.info("%-6d %-7d %10.3f  [%11.3f, %11.3f] %9.3f %10.3f", h, r["n_blocks"], r["d"],
                 r["ci"][0], r["ci"][1], r["sd"], r["mde80"])

    # ---- E1: tick, tong luong ----
    LOG.info("")
    LOG.info("--- E1  tang TICK (mau 15 phut), dai luong TONG LUONG [CHINH] ---")
    LOG.info("%-6s %-7s %10s %26s %9s %10s %6s", "block", "n_blk", "d (%/nam)", "CI95 (%/nam)",
             "sd", "MDE80(%)", "excl0")
    e1 = {}
    for h in BLOCK_HOURS:
        n_blocks = int((t1 - t0) // (HOUR_MS * h)) + 1
        A = tick_flow_blocks(tka, t0, n_blocks, h)
        B = tick_flow_blocks(tkb, t0, n_blocks, h)
        rng = np.random.default_rng(SEED)
        idx = rng.integers(0, n_blocks, size=(N_REP, n_blocks))
        per_year = 8760.0 / h
        reps = (A[idx].mean(axis=1) - B[idx].mean(axis=1)) * per_year * 100.0
        d = (A.mean() - B.mean()) * per_year * 100.0
        r = pack(reps, d, {"n_blocks": n_blocks})
        e1[h] = r
        LOG.info("%-6d %-7d %10.3f  [%11.3f, %11.3f] %9.3f %10.3f %6s", h, n_blocks, r["d"],
                 r["ci"][0], r["ci"][1], r["sd"], r["mde80"], "Y" if r["excl0"] else "n")

    # ---- E2: tick, roimean ----
    LOG.info("")
    LOG.info("--- E2  tang TICK, roimean_tick (ROI trung binh cum dang mo) [PHU] ---")
    psa = read_stream("%s/%s/pos.bin.gz" % (TICK, dira), DT_POS)
    psb = read_stream("%s/%s/pos.bin.gz" % (TICK, dirb), DT_POS)
    LOG.info("pos.bin: A=%d dong  B=%d dong", len(psa), len(psb))
    LOG.info("%-6s %-7s %10s %26s %9s %10s %6s", "block", "n_kept", "d (ROI)", "CI95 (ROI)",
             "sd", "MDE80", "excl0")
    e2 = {}
    for h in BLOCK_HOURS:
        n_blocks = int((t1 - t0) // (HOUR_MS * h)) + 1
        sa, ca = pos_roimean_blocks(psa, t0, n_blocks, h)
        sb, cb = pos_roimean_blocks(psb, t0, n_blocks, h)
        keep = (ca > 0) & (cb > 0)
        A = sa[keep] / ca[keep]
        B = sb[keep] / cb[keep]
        nk = int(keep.sum())
        rng = np.random.default_rng(SEED)
        idx = rng.integers(0, nk, size=(N_REP, nk))
        reps = A[idx].mean(axis=1) - B[idx].mean(axis=1)
        r = pack(reps, A.mean() - B.mean(), {"n_blocks": nk, "n_drop": n_blocks - nk})
        e2[h] = r
        LOG.info("%-6d %-7d %10.6f  [%11.6f, %11.6f] %9.6f %10.6f %6s", h, nk, r["d"],
                 r["ci"][0], r["ci"][1], r["sd"], r["mde80"], "Y" if r["excl0"] else "n")

    # ---- phan quyet ----
    m1 = e1[BLOCK_MAIN]["mde80"]
    mb = e0b[BLOCK_MAIN]["mde80"]
    ratio = m1 / mb if mb > 0 else float("nan")
    LOG.info("")
    LOG.info("=== PHAN QUYET (PREREG_TICKLOG muc 6.6) ===")
    LOG.info("  MDE80 E0a (equity CAGR, khoi 21 ngay)      = %8.3f pp/nam", e0a)
    LOG.info("  MDE80 E0b (equity tong luong, khoi 72h)    = %8.3f %%/nam   <-- DOI CHUNG", mb)
    LOG.info("  MDE80 E1  (tick  tong luong, khoi 72h)     = %8.3f %%/nam   <-- CHINH", m1)
    LOG.info("  ti le E1/E0b = %.4f", ratio)
    if ratio < 0.75:
        v = "CAI THIEN THAT (< 0.75)"
    elif ratio <= 1.3333:
        v = "KHONG CAI THIEN (0.75 - 1.33)"
    else:
        v = "TE HON (> 1.33)"
    LOG.info("  => %s", v)
    LOG.info("  ti le E1/E0a = %.4f (bao cao de doi chieu PAIRED_CALIB, KHONG dung lam bang chung)",
             m1 / e0a if e0a > 0 else float("nan"))

    for t in (dira, dirb):
        cs = cand_summary(t)
        if cs:
            LOG.info("")
            LOG.info("cand.bin %s: %d dong  %s", t, cs[0], cs[1])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
