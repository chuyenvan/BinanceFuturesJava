#!/usr/bin/env python3
"""FUNDING_SIGN_RECONCILE — truy lai + do lai QUY UOC DAU funding, 2 tang doc lap.

Pre-reg: docs/PREREG_LIMIT_ENTRY.md (commit TRUOC khi chay).
Thuan Python, chi DOC. Khong Java tren Oracle, khong claude-run, khong push, khong cham 2026.

Tang A: phan bo FUNDING RATE (unconditional, moi (symbol,T) co T < 2026-01-01) tu Aerospike funding_data.
Tang B: PnL funding cua LONG tren cua so giu lenh THAT (1089 lenh canonical printDone).

Quy uoc KHOa: rate>0 => LONG TRA; f_pp = 100*sum(rate) (%/notional); >0 = TRA, <0 = THU.
             pnl_fund_pp = -f_pp (>0 = duoc NHAN).

Out (ngoai repo): /home/ubuntu/claudedata/funding_sign/{report.txt,summary.json,fund_cache.npz}
"""
import os
import json
import time

import numpy as np
import pandas as pd
import aerospike
import cramjam

OUT = os.environ.get("FSG_OUT", "/home/ubuntu/claudedata/funding_sign")
PRINTDONE = os.environ.get(
    "FSG_PRINTDONE", "/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv")
MD5_EXPECT = "efb793e2468ca3a7318da0f0ad23d4fc"
AERO = ("127.0.0.1", 3222)
CUT2026 = 1767225600000          # 2026-01-01T00:00:00Z in ms (loai bo >= moc nay)
DEV_LO = 1640995200000           # 2022-01-01Z
DEV_HI = 1767225600000           # 2026-01-01Z (exclusive)
RAW = "/home/ubuntu/claudedata/rvb_1m/raw"

os.makedirs(OUT, exist_ok=True)
REP = []


def say(s=""):
    REP.append(str(s))
    print(s, flush=True)


def md5(p):
    import hashlib
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def utc(ms):
    return pd.Timestamp(int(ms), unit="ms", tz="UTC").strftime("%Y-%m-%d %H:%M")


SUM = {}

# =====================================================================================
# TANG A — SCAN funding_data (unconditional)
# =====================================================================================
say("=" * 98)
say("TANG A — PHAN BO FUNDING RATE (unconditional) tu Aerospike test.funding_data")
say("=" * 98)

cache_path = os.path.join(OUT, "fund_cache.npz")
if os.environ.get("FSG_REUSE") == "1" and os.path.exists(cache_path):
    z = np.load(cache_path, allow_pickle=True)
    syms = list(z["syms"])
    ts_all = z["ts"]; rt_all = z["rt"]; sid_all = z["sid"]
    say("[A0] reuse cache %s (%d cap symbol/rate, %d symbol)" % (cache_path, len(ts_all), len(syms)))
else:
    cli = aerospike.client({"hosts": [AERO], "policies": {"timeout": 60000}}).connect()
    syms = []
    ts_l, rt_l, sid_l = [], [], []
    t0 = time.time()
    nerr = 0

    def cb(*a):
        # aerospike python client goi cb(key, meta, rec) hoac cb((key, meta, rec))
        global nerr
        if len(a) == 1:
            key, meta, rec = a[0]
        else:
            key, meta, rec = a[0], a[1], a[2]
        try:
            sym = key[2] if isinstance(key, tuple) else key
            if sym is None:
                return
            bd = rec.get("f_data")
            if bd is None:
                return
            d = json.loads(bytes(cramjam.snappy.decompress_raw(bytes(bd))))
            if not d:
                return
            ks = np.fromiter((int(k) for k in d), dtype=np.int64, count=len(d))
            vs = np.fromiter((float(d[str(k)]) for k in ks), dtype=np.float32, count=len(ks))
            o = np.argsort(ks, kind="stable")
            ks = ks[o]; vs = vs[o]
            sid = len(syms)
            syms.append(str(sym))
            ts_l.append(ks); rt_l.append(vs)
            sid_l.append(np.full(len(ks), sid, dtype=np.int32))
        except Exception:
            nerr += 1

    cli.scan("test", "funding_data").foreach(cb)
    cli.close()
    ts_all = np.concatenate(ts_l); rt_all = np.concatenate(rt_l); sid_all = np.concatenate(sid_l)
    np.savez(cache_path, syms=np.array(syms, dtype=object), ts=ts_all, rt=rt_all, sid=sid_all)
    say("[A0] scan xong: %d symbol, %d cap (symbol,settle), loi doc %d, el=%.0fs"
        % (len(syms), len(ts_all), nerr, time.time() - t0))

say("[A0b] BTCUSDT co trong set: %s" % ("BTCUSDT" in set(syms)))
m26 = ts_all >= CUT2026
say("[A0c] cap co T >= 2026-01-01 (LOAI, khong cham holdout): %d" % int(m26.sum()))
ts_all = ts_all[~m26]; rt_all = rt_all[~m26]; sid_all = sid_all[~m26]
say("[A0d] cap dung duoc: %d | %d symbol | %s .. %s"
    % (len(ts_all), len(syms), utc(ts_all.min()), utc(ts_all.max())))
say("[A0e] rate: min %+.6f max %+.6f (tran Binance thuong ±0,0075) | |rate|>0,0075: %d"
    % (rt_all.min(), rt_all.max(), int((np.abs(rt_all) > 0.0075).sum())))

yr = pd.to_datetime(ts_all, unit="ms", utc=True).year.values


def dist(mask, label, out=None):
    r = rt_all[mask]
    if len(r) == 0:
        say("  %-34s N=0" % label)
        return None
    pos = float((r > 0).mean()); neg = float((r < 0).mean()); zer = float((r == 0).mean())
    q = np.percentile(r, [1, 25, 50, 75, 99]) * 1e4
    row = dict(n=int(len(r)), pos_pct=100 * pos, neg_pct=100 * neg, zero_pct=100 * zer,
               mean_bp=float(r.mean() * 1e4), med_bp=float(np.median(r) * 1e4),
               p01=q[0], p25=q[1], p75=q[3], p99=q[4])
    say("  %-34s N=%9d | %%rate>0 %5.1f | %%<0 %5.1f | %%=0 %4.1f | mean %+7.4f bp | med %+7.4f bp | p01 %+8.3f p99 %+8.3f"
        % (label, row["n"], row["pos_pct"], row["neg_pct"], row["zero_pct"],
           row["mean_bp"], row["med_bp"], row["p01"], row["p99"]))
    if out is not None:
        out[label] = row
    return row


say()
say("-- Tang A1: TOAN BO (moi symbol trong set) --")
SUM["A_all"] = {}
dist(np.ones(len(rt_all), bool), "ALL 2021..2025", SUM["A_all"])
for y in sorted(set(yr)):
    dist(yr == y, "  year %d" % y, SUM["A_all"])

say()
say("-- Tang A2: chi trong DEV 2022-01..2025-12 --")
devm = (ts_all >= DEV_LO) & (ts_all < DEV_HI)
SUM["A_dev"] = {}
dist(devm, "DEV 2022..2025", SUM["A_dev"])
for y in sorted(set(yr)):
    dist(devm & (yr == y), "  DEV year %d" % y, SUM["A_dev"])

# cross-sectional: mean rate qua cac symbol tai tung moc T
say()
say("-- Tang A3: CROSS-SECTIONAL (mean rate qua symbol tai tung moc settle T) --")
uT, inv, cnt = np.unique(ts_all, return_inverse=True, return_counts=True)
s = np.bincount(inv, weights=rt_all.astype(np.float64))
cs = s / cnt
say("  so moc T (>=MIN_SYM): %d | so symbol/moc: med %.0f max %d"
    % (len(uT), np.median(cnt), cnt.max()))
okc = cnt >= 20
csd = cs[okc]; uTd = uT[okc]
say("  cross-sectional mean rate: mean %+7.4f bp | med %+7.4f bp | p25 %+7.4f p75 %+7.4f"
    % (csd.mean() * 1e4, np.median(csd) * 1e4, np.percentile(csd, 25) * 1e4, np.percentile(csd, 75) * 1e4))
say("  %% moc T co cross-sectional mean > 0: %.1f%% (n=%d)" % (100 * (csd > 0).mean(), len(csd)))
ym = pd.to_datetime(uTd, unit="ms", utc=True).year.values
for y in sorted(set(ym)):
    v = csd[ym == y]
    if len(v):
        say("    year %d: n=%d | mean %+7.4f bp | %%moc>0 %.1f%%" % (y, len(v), v.mean() * 1e4, 100 * (v > 0).mean()))
SUM["A_cs"] = dict(n=int(len(csd)), mean_bp=float(csd.mean() * 1e4), med_bp=float(np.median(csd) * 1e4),
                   pct_ts_pos=float(100 * (csd > 0).mean()))

# gioi han universe: 627 symbol cua raw/*.f32
rv = sorted(os.path.basename(p)[:-4] for p in os.listdir(RAW) if p.endswith(".f32"))
symset = set(syms)
inrv = np.isin(sid_all, np.array([syms.index(s) for s in rv if s in symset], dtype=np.int32)) if len(rv) else None
if inrv is not None:
    say()
    say("-- Tang A4: chi 627 symbol universe raw/*.f32 (devm) --")
    dist(inrv & devm, "DEV & universe627", SUM.setdefault("A_u627", {}))

# =====================================================================================
# TANG B — PnL FUNDING cua LONG tren 1089 lenh
# =====================================================================================
say()
say("=" * 98)
say("TANG B — PnL FUNDING CUA LONG tren cua so giu lenh THAT (1089 lenh canonical)")
say("=" * 98)

df = pd.read_csv(PRINTDONE)
say("[G1] md5 printDone = %s (cho %s) %s | n=%d"
    % (md5(PRINTDONE), MD5_EXPECT, "OK" if md5(PRINTDONE) == MD5_EXPECT else "**LECH**", len(df)))
t7 = pd.to_datetime(df["start"].astype(str), format="%Y%m%d %H:%M")
df["t_ms"] = ((t7.astype("int64") // 10 ** 9) - 7 * 3600) * 1000
tE = pd.to_datetime(df["end"].astype(str).str.strip().str.lstrip("'"), format="%Y%m%d %H:%M")
df["te_ms"] = ((tE.astype("int64") // 10 ** 9) - 7 * 3600) * 1000
say("[G2] so dong >=2026: %d (phai 0) | entry %s .. %s"
    % (int((df["t_ms"] >= CUT2026).sum()), utc(df["t_ms"].min()), utc(df["t_ms"].max())))
df["symfull"] = df["sym"].astype(str) + "USDT"
df["notional"] = df["quantity"] * df["entry"]
df["gross"] = df["profit"].astype(float)
df["net_sim"] = 100.0 * df["pnl"] / df["notional"]
df["cost_sim"] = df["gross"] - df["net_sim"]
df["funding_sim_pp"] = df["cost_sim"] - 0.80          # %/lenh, >0 = TRA, <0 = THU

pos_s = {s: i for i, s in enumerate(syms)}
need = sorted(df["symfull"].unique())
miss = [s for s in need if s not in pos_s]
say("[B0] coverage funding_data: %d/%d symbol cua 1089 lenh (thieu %d %s)"
    % (len(need) - len(miss), len(need), len(miss), miss[:6]))

# tach mang theo symbol
order_by_sid = np.argsort(sid_all, kind="stable")
sid_s = sid_all[order_by_sid]; ts_s = ts_all[order_by_sid]; rt_s = rt_all[order_by_sid]
uniq_sid, st = np.unique(sid_s, return_index=True)
st = np.append(st, len(sid_s))


def sym_arr(name):
    i = pos_s.get(name)
    if i is None:
        return None
    j = np.searchsorted(uniq_sid, i)
    if j >= len(uniq_sid) or uniq_sid[j] != i:
        return None
    return ts_s[st[j]:st[j + 1]], rt_s[st[j]:st[j + 1]]


def win_fpp(r, cap=None):
    """sum rate*100 trong (t_entry, t_exit]; cap = tran |rate| (khao sat do ben)."""
    a = sym_arr(r["symfull"])
    if a is None:
        return np.nan, 0
    ts, rr = a
    m = (ts > r["t_ms"]) & (ts <= r["te_ms"])
    if not m.any():
        return np.nan, 0
    v = rr[m]
    if cap is not None:
        v = np.clip(v, -cap, cap)
    return 100.0 * float(v.sum()), int(m.sum())


f_pp = np.full(len(df), np.nan)
nst = np.zeros(len(df), dtype=int)
for i, r in df.iterrows():
    f_pp[i], nst[i] = win_fpp(r)
df["f_pp"] = f_pp
df["n_settle"] = nst

ok = df[np.isfinite(df["f_pp"])].copy()
say()
say("-- B1: cua so (t_entry, t_exit] | %d/%d lenh co >=1 ky settle | n_settle: mean %.2f med %d max %d"
    % (len(ok), len(df), ok["n_settle"].mean(), int(ok["n_settle"].median()), ok["n_settle"].max()))
posn = int((ok["f_pp"] > 0).sum()); negn = int((ok["f_pp"] < 0).sum()); zern = int((ok["f_pp"] == 0).sum())
say("   QUY UOC f_pp (%/notional): >0 = TRA, <0 = THU")
say("   TRA (f_pp>0) : %4d  %5.1f%%" % (posn, 100 * posn / len(ok)))
say("   THU (f_pp<0) : %4d  %5.1f%%" % (negn, 100 * negn / len(ok)))
say("   = 0          : %4d  %5.1f%%" % (zern, 100 * zern / len(ok)))
say("   mean f_pp = %+.4f%%/lenh | median = %+.4f%%/lenh" % (ok["f_pp"].mean(), ok["f_pp"].median()))
say("   ==> mean pnl_fund_pp = -mean f_pp = %+.4f%%/lenh (>0 = duoc NHAN)" % (-ok["f_pp"].mean()))
epos = ok.loc[ok["f_pp"] > 0, "f_pp"]; eneg = ok.loc[ok["f_pp"] < 0, "f_pp"]
say("   phan ra: P(tra)*E[|f|,tra] = %+.4f | -P(thu)*E[|f|,thu] = %+.4f"
    % (len(epos) / len(ok) * epos.mean(), -len(eneg) / len(ok) * (-eneg.mean())))
say("   |f_pp| khi TRA: mean %.4f%% | khi THU: mean %.4f%%" % (epos.mean(), -eneg.mean()))
say("   per-settle: mean f_pp/n_settle = %+.5f%%/ky | median %+.5f%%/ky"
    % ((ok["f_pp"] / ok["n_settle"]).mean(), (ok["f_pp"] / ok["n_settle"]).median()))
SUM["B"] = dict(n=int(len(ok)), n_tra=posn, n_thu=negn, pct_tra=100 * posn / len(ok), pct_thu=100 * negn / len(ok),
                mean_f_pp=float(ok["f_pp"].mean()), med_f_pp=float(ok["f_pp"].median()),
                mean_pnl_fund=float(-ok["f_pp"].mean()), mean_per_settle=float((ok["f_pp"] / ok["n_settle"]).mean()),
                mean_n_settle=float(ok["n_settle"].mean()))
say()
say("-- B2: doi chieu voi cot funding CUA SIM (suy tu pnl; cung quy uoc: >0 = TRA) --")
simg = df["funding_sim_pp"]
say("   sim: TRA %5.1f%% | THU %5.1f%% | mean %+.4f%%/lenh | median %+.4f%%/lenh"
    % (100 * (simg > 0).mean(), 100 * (simg < 0).mean(), simg.mean(), simg.median()))
d = (df["f_pp"] - df["funding_sim_pp"]).dropna()
say("   lech (real - sim): mean %+.4f pp | median %+.4f pp | corr %.3f"
    % (d.mean(), d.median(), float(df["f_pp"].corr(df["funding_sim_pp"]))))
say()
say("-- B3: CO PHAN TAP TRUNG? (gia thuyet: vai lenh THU LON chi phoi mean) --")
o = ok.sort_values("f_pp")
say("   top-5 am nhat (THU lon):")
for _, r in o.head(5).iterrows():
    say("     %-14s %s -> %s | n_ky %3d | f_pp %+8.4f%% | notional %.0f | level %s"
        % (r["symfull"], utc(r["t_ms"]), utc(r["te_ms"]), r["n_settle"], r["f_pp"], r["notional"], r["level"]))
cont = -o["f_pp"].sum() * 0 + (o["f_pp"] < 0).sum()
tot_abs = ok["f_pp"].abs().sum()
say("   - 10 lenh THU nhat dong gop %+.4f%%/lenh vao mean (tong %+.4f%%) | chiem %.1f%% tong |f_pp|"
    % (o["f_pp"].head(10).sum() / len(ok), o["f_pp"].head(10).sum(), 100 * o["f_pp"].head(10).abs().sum() / tot_abs))
say("   - 10 lenh TRA nhieu nhat dong gop %+.4f%%/lenh vao mean"
    % (o["f_pp"].tail(10).sum() / len(ok)))
say("   - bo 10 lenh THU nhat: mean f_pp = %+.4f%%/lenh (n=%d)"
    % (o["f_pp"].iloc[10:].mean(), len(o) - 10))
bins = [0, 1, 2, 4, 8, 16, 32, 10000]
ok["band"] = pd.cut(ok["n_settle"], bins=bins, right=False)
say("   theo n_settle: band | n | mean f_pp | mean f_pp/ky | %TRA")
for b, g in ok.groupby("band", observed=True):
    say("     %-12s n=%4d | mean %+7.4f%% | per-ky %+7.5f%% | %%TRA %5.1f"
        % (str(b), len(g), g["f_pp"].mean(), (g["f_pp"] / g["n_settle"]).mean(), 100 * (g["f_pp"] > 0).mean()))
SUM["B_conc"] = dict(top10_thu_share=float(100 * o["f_pp"].head(10).abs().sum() / tot_abs),
                     mean_pp_drop_top10thu=float(o["f_pp"].iloc[10:].mean()))
say()
say("-- B4: DOI CHUNG UNCONDITIONAL TREN CHINH 358 SYMBOL/THOI KY CUA LENH --")
ids = np.array([pos_s[s] for s in need if s in pos_s], dtype=np.int32)
sub = np.isin(sid_all, ids)
sub_dev = sub & (ts_all >= DEV_LO) & (ts_all < DEV_HI)
dist(sub_dev, "358 sym, DEV 2022..2025", SUM.setdefault("B_ctrl", {}))
say("   (so sanh: per-settle trong cua so lenh = %+.5f%%/ky)"
    % (ok["f_pp"] / ok["n_settle"]).mean())

# ---- B5: toan bo 1089 (lenh khong co ky settle = 0) ----
allf = df["f_pp"].fillna(0.0)
say()
say("-- B5: tren CA 1089 lenh (khong co ky settle => 0) --")
say("   TRA %5.1f%% | THU %5.1f%% | 0 %5.1f%% | mean %+.4f%%/lenh"
    % (100 * (allf > 0).mean(), 100 * (allf < 0).mean(), 100 * (allf == 0).mean(), allf.mean()))

with open(os.path.join(OUT, "report.txt"), "w") as f:
    f.write("\n".join(REP) + "\n")

# ---- B6: DO BEN — tran |rate| (Binance chuan ±0,75%/ky) + cua so FTX ----
say()
say("-- B6: DO BEN cua `mean f_pp` (net credit co phu thuoc duoi cuc tri khong?) --")
rob = {}
for cap, lab in ((0.0075, "clip |rate|<=0,75%/ky (chuan)"), (0.02, "clip |rate|<=2%/ky"), (None, "KHONG clip (goc)")):
    v = np.full(len(df), np.nan); nn = np.zeros(len(df), int)
    for i, r in df.iterrows():
        v[i], nn[i] = win_fpp(r, cap=cap)
    o2 = v[np.isfinite(v)]
    say("   %-30s n=%d | %%TRA %5.1f | mean f_pp %+.4f%%/lenh | median %+.4f%% | mean pnl_fund %+.4f%%"
        % (lab, len(o2), 100 * (o2 > 0).mean(), o2.mean(), np.median(o2), -o2.mean()))
    rob[lab] = dict(n=int(len(o2)), pct_tra=float(100 * (o2 > 0).mean()), mean_f_pp=float(o2.mean()),
                    med_f_pp=float(np.median(o2)), mean_pnl_fund=float(-o2.mean()))
SUM["B_robust"] = rob

say()
say("-- B7: theo NAM vao lenh (cua so goc) --")
yrin = pd.to_datetime(ok["t_ms"], unit="ms", utc=True).dt.year.values
for y in sorted(set(yrin)):
    g = ok[yrin == y]
    say("   %d: n=%4d | %%TRA %5.1f | mean f_pp %+8.4f%% | mean pnl_fund %+8.4f%%"
        % (y, len(g), 100 * (g["f_pp"] > 0).mean(), g["f_pp"].mean(), -g["f_pp"].mean()))

say()
say("-- B8: vai episode CUC TRI dong gop bao nhieu vao net credit? --")
epi = ((ok["t_ms"] >= 1667865600000) & (ok["t_ms"] <= 1668384000000))   # 2022-11-08..2022-11-13 (FTX)
g = ok[epi]
say("   cua so FTX (2022-11-08..11-13): n=%d | tong f_pp %+.1f%% | dong gop %+.4f%%/lenh vao mean (toan bo 673)"
    % (len(g), g["f_pp"].sum(), g["f_pp"].sum() / len(ok)))
say("   bo cua so FTX: mean f_pp = %+.4f%%/lenh (n=%d)" % (ok[~epi]["f_pp"].mean(), int((~epi).sum())))
SUM["B_epi"] = dict(n_ftx=int(len(g)), sum_ftx=float(g["f_pp"].sum()),
                    contrib=float(g["f_pp"].sum() / len(ok)), mean_ex_ftx=float(ok[~epi]["f_pp"].mean()))

json.dump(SUM, open(os.path.join(OUT, "summary.json"), "w"), indent=2, ensure_ascii=False, default=float)
say()
say("[xong] trung gian: %s" % OUT)
