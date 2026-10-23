#!/usr/bin/env python3
"""FUNDNEG_T1 checks V1 (Vision CSV raw compare + offsets), V2 (dtypes/dups), V4 (manual 10 trades), V5 (funding sign)."""
import io, json, os, sys, types, zipfile, csv, glob
import numpy as np, pandas as pd, pyarrow.parquet as pq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import core
from core import accrue, FK, HMS, MMS, DMS

OUTD = core.WK + "/out"
DL = core.WK + "/vision_dl"
res = {}

# ---------------- V1
F = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(core.FUND + "/202[2-5]/*.parquet"))], ignore_index=True)
F["sym"] = F.sym.astype(str)
off = F.ts % HMS
res["V1_offset_ms_max"] = int(off.max())
res["V1_offset_le_60s_all"] = bool((off < 60000).all())
cmp = []
for sym, mo in [("BTCUSDT", "2024-03"), ("1000000BOBUSDT", "2025-06"), ("ETHUSDT", "2022-06")]:
    z = os.path.join(DL, "%s-fundingRate-%s.zip" % (sym, mo))
    if not os.path.exists(z):
        cmp.append({"sym": sym, "mo": mo, "error": "zip missing"}); continue
    with zipfile.ZipFile(z) as zf:
        raw = zf.read(zf.namelist()[0]).decode()
    rows = list(csv.reader(io.StringIO(raw)))
    hdr = rows[0]
    R = pd.DataFrame(rows[1:], columns=hdr)
    R["calc_time"] = R.calc_time.astype(np.int64)
    R["last_funding_rate"] = R.last_funding_rate.astype(float)
    R["funding_interval_hours"] = R.funding_interval_hours.astype(int)
    q = F[(F.sym == sym) & (F.ts >= R.calc_time.min()) & (F.ts <= R.calc_time.max())]
    m = R.merge(q, left_on="calc_time", right_on="ts", how="outer", indicator=True)
    cmp.append({"sym": sym, "mo": mo, "header": hdr, "n_csv": len(R), "n_parq": len(q),
                "merge": m._merge.value_counts().to_dict(),
                "max_abs_drate": float((m.last_funding_rate - m.rate).abs().max()),
                "interval_mismatch": int((m.funding_interval_hours != m.interval_h).sum()),
                "calc_time_offset_max_ms": int((R.calc_time % HMS).max())})
res["V1_vision_csv_compare"] = cmp

# ---------------- V2
res["V2_funding_ts_int64"] = str(F.ts.dtype)
F["tau"] = F.ts - F.ts % MMS
res["V2_funding_dup_sym_tau"] = int(F.duplicated(["sym", "tau"]).sum())
T = {}
for f in sorted(glob.glob(OUTD + "/trades_*.parquet")):
    x = pd.read_parquet(f)
    nm = os.path.basename(f)[7:-8]
    T[nm] = x
    res.setdefault("V2_trades", {})[nm] = {"tau_dtype": str(x.tau.dtype), "t_in_dtype": str(x.t_in.dtype),
                                           "t_out_dtype": str(x.t_out.dtype), "dup_sym_tau": int(x.duplicated(["sym", "tau"]).sum()),
                                           "tin_gt_tau_all": bool((x.t_in > x.tau).all()),
                                           "tau_on_hour_all": bool((x.tau % HMS == 0).all())}
ph = pd.read_parquet(sorted(glob.glob(core.PANEL + "/h-*.parquet"))[-1])
res["V2_panel_hr_dtype"] = str(ph.hr.dtype)

# ---------------- V4 manual (raw 1m candles)
x = T["thr-0.10_H24"]
rng = np.random.default_rng(7)
pick = x.iloc[np.sort(rng.choice(len(x), 10, replace=False))]
man = []
for _, r in pick.iterrows():
    tau, Hh, s = int(r.tau), 24, r.sym
    def candle(ts_open):
        mo = pd.Timestamp(ts_open, unit="ms").strftime("%Y-%m")
        k = pq.read_table("/home/ubuntu/vz_e1/raw/kline1m-%s.parquet" % mo, columns=["ts", "sym", "close"],
                          filters=[("sym", "=", s), ("ts", "=", ts_open)]).to_pandas()
        return float(k.close.iloc[0]) if len(k) else None
    p0 = candle(tau + MMS)
    p1 = candle(tau + Hh * HMS + MMS)
    fr = F[(F.sym == s) & (F.tau > tau) & (F.tau <= tau + Hh * HMS)].sort_values("tau")
    fsum, flist = 0.0, []
    for _, q in fr.iterrows():
        ps = candle(int(q.tau) - MMS)
        c = -q.rate * ((ps / p0) if ps is not None else 1.0)
        fsum += c
        flist.append([pd.Timestamp(int(q.tau), unit="ms").isoformat(), float(q.rate), ps, c])
    net = (p1 / p0 - 1 + fsum - 0.003) if (p0 and p1) else None
    man.append({"sym": s, "tau": pd.Timestamp(tau, unit="ms").isoformat(), "P0_raw": p0, "P0_pipe": float(r.P0),
                "P1_raw": p1, "P1_pipe": float(r.P1), "delist": bool(r.delist), "fund_list": flist,
                "fund_manual": fsum, "fund_pipe": float(r.fund), "nset_pipe": int(r.nset),
                "net_manual": net, "net_pipe": float(r.net),
                "match": (net is not None and abs(net - r.net) < 1e-12) or (bool(r.delist))})
res["V4_manual"] = man
res["V4_all_match"] = all(m["match"] for m in man)

# ---------------- V5 funding sign via pipeline accrue()
Fs = types.SimpleNamespace()
P0 = 100.0
Fs.code = np.array([0, 0, 0, 0, 1, 2, 2, 2], dtype=np.int64)
t0 = 1_704_067_200_000
Fs.tau = np.array([t0, t0 + 8 * HMS, t0 + 16 * HMS, t0 + 24 * HMS, t0 + 8 * HMS, t0 + 4 * HMS, t0 + 8 * HMS, t0 + 12 * HMS], dtype=np.int64)
Fs.rate = np.array([-0.5, -0.001, -0.001, -0.001, +0.001, -0.002, +0.0005, -0.001])
Fs.pset = np.array([P0, P0, P0, P0, P0, P0 * 1.1, P0 * 0.9, np.nan])
Fs.fkey = Fs.code * FK + Fs.tau
core.Funding.build_cs(Fs)
f, n = accrue(Fs, np.array([0, 1, 2]), np.array([t0, t0, t0]), np.array([t0 + 24 * HMS] * 3), np.array([P0] * 3))
exp = [0.003, -0.001, 0.002 * 1.1 - 0.0005 * 0.9 + 0.001 * 1.0]
res["V5"] = {"case_neg_rate_3x_(tau_excluded,tau+H_included)": [float(f[0]), exp[0], int(n[0])],
             "case_pos_rate": [float(f[1]), exp[1], int(n[1])],
             "case_mixed_with_missing_price": [float(f[2]), exp[2], int(n[2])],
             "pass": bool(np.allclose(f, exp, atol=1e-15, rtol=0) and list(n) == [3, 1, 3])}
# real-data sign sanity: trades whose settlements were all negative must have fund > 0
x = T["thr-0.10_H24"]
res["V5_real_mean_fund_by_sign"] = {"share_fund_pos": float((x.fund > 0).mean()), "mean_fund": float(x.fund.mean())}
json.dump(res, open(OUTD + "/checks.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in res.items() if k != "V4_manual"}, indent=1, default=str))
for m in man:
    print(m["sym"], m["tau"], m["P0_raw"], m["P0_pipe"], m["P1_raw"], m["P1_pipe"], len(m["fund_list"]), m["nset_pipe"],
          "%.6g %.6g" % (m["fund_manual"], m["fund_pipe"]), m["net_manual"], m["net_pipe"], m["match"])
