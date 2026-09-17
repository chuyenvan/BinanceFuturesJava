"""CHAY MOT LAN theo SPEC_FROZEN.md. Khong sua sau khi thay ket qua."""
import os, sys, csv, json, hashlib, datetime
import numpy as np
import pandas as pd
import warnings
warnings.simplefilter("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
INV = os.path.join(HERE, "inventory.csv")

# ---- THAM SO KHOA (SPEC muc 1) ----
MA_LBS = (50, 100, 200)
TARGET_VOL = 0.40
VOL_WIN = 30
MAX_SIZE = 1.00
BAND = 0.20
EXEC_LAG = 1
MIN_HIST = 200
BPY = 252.0
FEE = 0.0005
GAP_CUT = 30
NPERM = 1000
rng = np.random.default_rng(20260830)

meta = {r["symbol"]: r for r in csv.DictReader(open(INV, encoding="utf-8"))}


def fname(sym):
    return sym.replace("^", "IDX_").replace("=", "_") + ".csv"


def load(sym):
    d = pd.read_csv(os.path.join(RAW, fname(sym)))
    d["date"] = pd.to_datetime(d["date"])
    d = d[["date", "close"]].set_index("date").astype(float)
    d = d[d["close"] > 0]
    # SPEC: cat bo phan truoc lo hong cuoi cung > 30 ngay
    gaps = d.index.to_series().diff().dt.days
    big = np.where(gaps.values > GAP_CUT)[0]
    cut = int(big[-1]) if len(big) else 0
    return d.iloc[cut:]


def positions(px):
    ret = px.pct_change().fillna(0.0)
    sig = None
    for l in MA_LBS:
        ma = px.rolling(l, min_periods=l).mean()
        s = (px > ma).astype(float).where(ma.notna())
        sig = s if sig is None else sig + s
    sig = sig / len(MA_LBS)
    rv = ret.rolling(VOL_WIN, min_periods=VOL_WIN).std() * np.sqrt(BPY)
    size = (TARGET_VOL / rv).clip(upper=MAX_SIZE)
    hist = pd.Series(np.arange(1, len(px) + 1), index=px.index)
    raw = (sig * size).where((hist >= MIN_HIST) & sig.notna() & size.notna())
    raw = raw.shift(EXEC_LAG)
    v = raw.values
    held = 0.0
    out = np.zeros(len(v))
    for i in range(len(v)):
        t = v[i]
        if not np.isfinite(t):
            held = 0.0; out[i] = 0.0; continue
        if held == 0.0 or t == 0.0 or abs(t - held) / max(held, 1e-9) > BAND:
            held = t
        out[i] = held
    return pd.Series(out, index=px.index), ret


def perf(pos, ret):
    turn = np.abs(np.diff(pos, prepend=0.0))
    r = pos * ret - turn * FEE
    eq = np.cumprod(1 + r)
    sd = r.std() * np.sqrt(BPY)
    sh = (r.mean() * BPY) / sd if sd > 0 else 0.0
    dd = (eq / np.maximum.accumulate(eq) - 1).min()
    return sh, dd, eq[-1], r


def sharpe_shift(pos, ret, k):
    p = np.roll(pos, k % len(pos))
    turn = np.abs(np.diff(p, prepend=0.0))
    r = p * ret - turn * FEE
    sd = r.std() * np.sqrt(BPY)
    return (r.mean() * BPY) / sd if sd > 0 else 0.0


print("=" * 112)
print("HOLDOUT NGOAI VU TRU — CHAY MOT LAN | spec sha256 92f29890b6ee...")
print("thoi diem chay:", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 112)
print("%-11s %-24s %-9s %6s %-10s | %7s %7s | %8s %8s | %7s" % (
    "ma", "ten", "lop", "nam", "tu ngay", "Sh CL", "Sh MG", "DD CL", "DD MG", "expo"))

rows = []
for sym, m in meta.items():
    px = load(sym)["close"]
    if len(px) < MIN_HIST + 252:
        print("%-11s BO QUA: qua ngan sau khi cat lo hong (%d nen)" % (sym, len(px)))
        continue
    pos, ret = positions(px)
    use = np.arange(len(px)) >= MIN_HIST
    p = pos.values[use]; r = ret.values[use]
    sh_s, dd_s, mult_s, rr = perf(p, r)
    sh_h, dd_h, mult_h, _ = perf(np.ones(len(r)), r)
    rows.append(dict(sym=sym, name=m["name"], cls=m["class"],
                     yrs=len(r) / BPY, start=str(px.index[use][0].date()),
                     sh_s=sh_s, sh_h=sh_h, dd_s=dd_s, dd_h=dd_h,
                     mult_s=mult_s, mult_h=mult_h, expo=p.mean(), pos=p, ret=r))
    print("%-11s %-24s %-9s %6.1f %-10s | %+7.3f %+7.3f | %7.1f%% %7.1f%% | %6.1f%%" % (
        sym, m["name"][:24], m["class"], len(r) / BPY, str(px.index[use][0].date()),
        sh_s, sh_h, dd_s * 100, dd_h * 100, p.mean() * 100))

N = len(rows)
sh_s = np.array([x["sh_s"] for x in rows]); sh_h = np.array([x["sh_h"] for x in rows])
dd_s = np.array([x["dd_s"] for x in rows]); dd_h = np.array([x["dd_h"] for x in rows])

print()
print("=" * 112)
print("### TONG HOP %d TAI SAN ###" % N)
print("  Sharpe TB   : chien luoc %+.4f | mua-giu %+.4f | hieu %+.4f" % (
    sh_s.mean(), sh_h.mean(), sh_s.mean() - sh_h.mean()))
print("  Sharpe trung vi: chien luoc %+.4f | mua-giu %+.4f" % (
    np.median(sh_s), np.median(sh_h)))
print("  maxDD TB    : chien luoc %.1f%% | mua-giu %.1f%% | cai thien %.1f%%" % (
    dd_s.mean() * 100, dd_h.mean() * 100,
    (1 - abs(dd_s.mean()) / abs(dd_h.mean())) * 100))
print("  So tai san chien luoc > mua-giu (Sharpe): %d/%d" % ((sh_s > sh_h).sum(), N))
print("  So tai san chien luoc > mua-giu (maxDD) : %d/%d" % ((dd_s > dd_h).sum(), N))
print("  Exposure TB : %.1f%%" % (np.mean([x["expo"] for x in rows]) * 100))

print()
print("### KIEM DINH HOAN VI (null: xoay CUNG mot so nen cho tat ca tai san, %d lan) ###" % NPERM)
KS = rng.integers(60, 5000, NPERM)
null = np.empty(NPERM)
for j, k in enumerate(KS):
    null[j] = np.mean([sharpe_shift(x["pos"], x["ret"], int(k)) for x in rows])
obs = sh_s.mean()
p_val = (null >= obs).mean()
z = (obs - null.mean()) / null.std()
print("  Sharpe TB quan sat : %+.4f" % obs)
print("  Null: TB %+.4f | sd %.4f | 95%% %+.4f | 99%% %+.4f | max %+.4f" % (
    null.mean(), null.std(), np.percentile(null, 95), np.percentile(null, 99), null.max()))
print("  p-value = %.4f   Z = %+.2f" % (p_val, z))

print()
print("### THEO LOP TAI SAN ###")
print("%-11s %4s %9s %9s %9s %9s %9s" % (
    "lop", "n", "Sh CL", "Sh MG", "Sh null", "DD CL", "DD MG"))
cls_pass = 0
for c in ["equity", "commodity", "fx", "bond"]:
    ix = [i for i, x in enumerate(rows) if x["cls"] == c]
    if not ix: continue
    o = sh_s[ix].mean()
    nl = np.array([np.mean([sharpe_shift(rows[i]["pos"], rows[i]["ret"], int(k)) for i in ix])
                   for k in KS[:300]])
    ok = o > nl.mean()
    cls_pass += ok
    print("%-11s %4d %+9.4f %+9.4f %+9.4f %8.1f%% %8.1f%%  %s" % (
        c, len(ix), o, sh_h[ix].mean(), nl.mean(), dd_s[ix].mean() * 100,
        dd_h[ix].mean() * 100, "vuot null" if ok else "KHONG vuot"))

print()
print("=" * 112)
print("### DOI CHIEU TIEU CHI SONG/CHET (SPEC muc 4) ###")
c1 = sh_s.mean() > sh_h.mean()
c2 = p_val < 0.01
c3 = cls_pass >= 3
imp = (1 - abs(dd_s.mean()) / abs(dd_h.mean()))
c4 = imp >= 0.30
print("  (1) Sharpe TB chien luoc > mua-giu        : %+.4f vs %+.4f   -> %s" % (
    sh_s.mean(), sh_h.mean(), "DAT" if c1 else "TRUOT"))
print("  (2) p-value hoan vi < 0.01                : p = %.4f          -> %s" % (
    p_val, "DAT" if c2 else "TRUOT"))
print("  (3) >= 3/4 lop tai san vuot null          : %d/4               -> %s" % (
    cls_pass, "DAT" if c3 else "TRUOT"))
print("  (4) Cai thien maxDD >= 30%%                : %.1f%%             -> %s" % (
    imp * 100, "DAT" if c4 else "TRUOT"))
print()
allp = c1 and c2 and c3 and c4
if allp:
    verdict = "DAT — trend following la quy luat cau truc"
elif p_val >= 0.05:
    verdict = "CHET — p >= 0.05, bo huong nay lam loi"
else:
    verdict = "TRUNG GIAN — edge co that nhung yeu hon ket qua crypto goi y"
print("  KET LUAN: %s" % verdict)
print("=" * 112)

with open(os.path.join(HERE, "RESULT.json"), "w") as f:
    json.dump(dict(n=N, sharpe_strat=float(sh_s.mean()), sharpe_hold=float(sh_h.mean()),
                   p_value=float(p_val), z=float(z), null_mean=float(null.mean()),
                   dd_strat=float(dd_s.mean()), dd_hold=float(dd_h.mean()),
                   dd_improve=float(imp), classes_pass=int(cls_pass),
                   c1=bool(c1), c2=bool(c2), c3=bool(c3), c4=bool(c4),
                   verdict=verdict,
                   per_asset=[{k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                               for k, v in x.items() if k not in ("pos", "ret")} for x in rows]),
              f, indent=1)
print("Ket qua ghi ra RESULT.json")
print("DONE")
