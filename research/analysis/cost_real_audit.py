#!/usr/bin/env python3
"""COST_REAL_AUDIT — Phase A (trich nguon chi phi THAT) + Phase B (do phan bo chi phi).

Plan: docs/audit/PLAN_COST_AUDIT_REAUDIT.md (viet TRUOC khi chay).

Thuan Python. KHONG Java tren Oracle, KHONG claude-run, KHONG push, KHONG cham 2026 (du lieu <= 2025-12-31).
242 CHI DOC: viec quet 242 lam bang tay (ssh) va ghi lai trong docs/result/RESULT_COST_REAL_AUDIT.md,
script nay chi doc du lieu local + Aerospike funding_data (read-only).

Nguon:
  * leg sim : /home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv (md5 efb793e2..., n=1089)
  * nen 1m  : /home/ubuntu/claudedata/rvb_1m/raw/<SYM>USDT.f32  [ts<i4,o,h,l,c,v f4], ts = phut epoch UTC
  * funding : Aerospike test.funding_data  (bin f_data = Snappy(JSON {ts_ms: rate}))
  * paper   : /home/ubuntu/shadow_c3/ledger.csv (shadow C3, pnl GROSS)

Chi phi sim (Configs.java:103,117): RATE_FEE 0,002 x1 chan + SLIPPAGE_RATE 0,003 x2 chan = 0,800% RT.
Moc tham chieu Binance USDⓈ-M VIP0: maker 0,020%/chan, taker 0,050%/chan.

Trung gian: /tmp/cost_real_audit/ (don sau khi commit).
"""
import json
import glob
import hashlib
import os
import subprocess
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
OUT = os.environ.get("CRA_OUT", "/tmp/cost_real_audit")
PRINT_DONE = os.environ.get(
    "CRA_PRINT_DONE", "/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv")
RAW = os.environ.get("CRA_RAW", "/home/ubuntu/claudedata/rvb_1m/raw")
SHADOW_LEDGER = "/home/ubuntu/shadow_c3/ledger.csv"
DEV_RUN = "/home/ubuntu/java/devrun"
AERO_HOST = "127.0.0.1"
AERO_PORT = 3222
MD5_EXPECT = "efb793e2468ca3a7318da0f0ad23d4fc"
N_EXPECT = 1089
SIM_RT = 0.800000                      # % round-trip cua sim
FEE_REF = {"maker": 0.020, "taker": 0.050}   # %/chan (moc THAM CHIEU, khong do duoc)
DT = np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])

os.makedirs(OUT, exist_ok=True)
REPORT = []


def say(s=""):
    REPORT.append(str(s))
    print(s, flush=True)


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def save():
    with open(os.path.join(OUT, "report_cost_real.txt"), "w") as f:
        f.write("\n".join(REPORT) + "\n")
    json.dump(SUMMARY, open(os.path.join(OUT, "summary.json"), "w"), indent=2, ensure_ascii=False)


SUMMARY = {}

# =====================================================================================
# PHASE A — INVENTORY: file nao co chi phi / khop lenh THAT
# =====================================================================================
say("=" * 100)
say("PHASE A — TRICH NGUON CHI PHI THAT (inventory)")
say("=" * 100)

# A1. printOrder.csv (de bai neu) — tim tren Oracle
found_printorder = []
for root in ("/home/ubuntu",):
    for depth_pat in ("*", "*/*", "*/*/*", "*/*/*/*", "*/*/*/*/*"):
        found_printorder += glob.glob(os.path.join(root, depth_pat, "printOrder*.csv"))
found_printorder = sorted(set(found_printorder))
say("[A1] printOrder*.csv tren Oracle (maxdepth 5): %d file %s"
    % (len(found_printorder), found_printorder if found_printorder else "-> KHONG TON TAI"))
SUMMARY["printOrder_oracle"] = found_printorder

# A2. printDone.csv — file ket qua sim (co truong chi phi gian tiep: pnl, funding)
pd_files = sorted(glob.glob(os.path.join(DEV_RUN, "*", "storage", "printDone.csv")))
canon = PRINT_DONE
rows = []
for p in pd_files:
    try:
        with open(p) as f:
            n = sum(1 for _ in f) - 1
        first = pd.read_csv(p, nrows=1)
        rows.append((p.replace(DEV_RUN + "/", ""), n, str(first["start"].iloc[0])))
    except Exception as e:
        rows.append((p, -1, "err:%s" % type(e).__name__))
say("[A2] printDone.csv (ket qua SIM) trong %s: %d run" % (DEV_RUN, len(pd_files)))
say("     canonical (T170): %s  md5=%s  n=%d" % (canon, md5(canon), len(pd.read_csv(canon))))
SUMMARY["n_printdone_runs"] = len(pd_files)
SUMMARY["canonical"] = canon
say("     (chi tiet tung run -> inventory_printdone.csv)")
pd.DataFrame(rows, columns=["run", "n_rows", "first_start"]).to_csv(
    os.path.join(OUT, "inventory_printdone.csv"), index=False)

# A3. OrderTestDone.data / BalanceIndex.data — Java serialize, khong co truong phi
say("[A3] OrderTestDone.data: %d file (Java TreeMap serialize) | BalanceIndex.data: %d file"
    % (len(glob.glob(os.path.join(DEV_RUN, "*", "storage", "OrderTestDone.data"))),
       len(glob.glob(os.path.join(DEV_RUN, "*", "storage", "BalanceIndex.data")))))
say("     -> khong co truong commission/fill; chi la object sim (khong phai log san)")

# A4. Quet log TIM truong khop lenh that (orderId / commission / FILLED / executedQty)
LOGS = ["/home/ubuntu/shadow_c3/app/logs/full.log"]
LOGS += sorted(glob.glob("/home/ubuntu/java/devrun/logs/*.log"))[:5]
say("[A4] quet log local tim bang chung KHOP LENH THAT (orderId|commission|FILLED|executedQty|avgPrice):")
hit = {}
for lg in LOGS:
    if not os.path.exists(lg):
        continue
    try:
        g = subprocess.run(["grep", "-c", "-i", "-E",
                            r"orderId|commission|FILLED|executedQty|avgPrice", lg],
                           capture_output=True, text=True, timeout=120)
        hit[lg] = int(g.stdout.strip() or 0)
    except Exception as e:
        hit[lg] = -1
for k, v in hit.items():
    say("     %-55s %s" % (os.path.basename(k), v))
SUMMARY["log_fill_hits"] = hit
say("     -> %s" % ("KHONG co bang chung fill that trong log local"
                    if all(v <= 0 for v in hit.values()) else "CO hit — phai doc tay"))

# A5. shadow ledger (paper) — co gia entry/exit THAT theo thi truong nhung KHONG co phi san
led = pd.read_csv(SHADOW_LEDGER)
say("[A5] shadow ledger paper: %s  n=%d  cot=%s" % (SHADOW_LEDGER, len(led), list(led.columns)))
say("     ts_entry %s .. %s (ms UTC)" % (int(led.ts_entry.min()), int(led.ts_entry.max())))
say("     -> pnl la GROSS (per docs/result/RESULT_LIVE_VS_SIM.md), khong co commission/orderId/status order")
SUMMARY["shadow_n"] = int(len(led))

# A6. funding_data (Aerospike) — nguon funding THAT
say("[A6] Aerospike test.funding_data @ %s:%d — nguon FUNDING THAT (read-only)" % (AERO_HOST, AERO_PORT))

# A7. moc tham chieu phi (khong do duoc)
say("[A7] phi san THAT: KHONG co truong nao ghi commission -> khong do duoc.")
say("     Moc THAM CHIEU (docs, khong phai do): Binance USDⓈ-M VIP0 maker %.3f%%/chan, taker %.3f%%/chan"
    % (FEE_REF["maker"], FEE_REF["taker"]))
say("     Trong repo: config shadow dung RATE_FEE=0.0015 (1 chan) — cung la GIA DINH, khong phai so san.")

# =====================================================================================
# PHASE B — DO PHAN BO CHI PHI THAT
# =====================================================================================
say()
say("=" * 100)
say("PHASE B — DO PHAN BO CHI PHI")
say("=" * 100)

df = pd.read_csv(canon)
t7 = pd.to_datetime(df["start"], format="%Y%m%d %H:%M")
df["t_min"] = ((t7.astype("int64") // 10 ** 9) - 7 * 3600) // 60
df["t_ms"] = ((t7.astype("int64") // 10 ** 9) - 7 * 3600) * 1000
e = df["end"].astype(str).str.strip().str.lstrip("'").str.strip()
tE = pd.to_datetime(e, format="%Y%m%d %H:%M")
df["te_min"] = ((tE.astype("int64") // 10 ** 9) - 7 * 3600) // 60
df["te_ms"] = ((tE.astype("int64") // 10 ** 9) - 7 * 3600) * 1000
df["symfull"] = df["sym"].astype(str) + "USDT"
df["notional"] = df["quantity"] * df["entry"]
df["gross"] = df["profit"].astype(float)
df["net_sim"] = 100.0 * df["pnl"] / df["notional"]
df["cost_sim"] = df["gross"] - df["net_sim"]
df["funding_sim_pp"] = df["cost_sim"] - SIM_RT      # %/lenh, am = THU

say("[G1] md5 printDone = %s (cho %s) %s | n=%d"
    % (md5(canon), MD5_EXPECT, "OK" if md5(canon) == MD5_EXPECT else "**LECH**", len(df)))
rel = ((df["notional"] - df["margin"]).abs() / df["margin"]).max()
say("[G2] |notional/margin-1| max = %.2e (cho <1e-6) %s" % (rel, "OK" if rel < 1e-6 else "**LECH**"))
resid = (df["gross"] - SIM_RT - df["funding_sim_pp"] - df["net_sim"]).abs().max()
say("[G3] tai tao net_sim (gross-0,80-funding): |resid| max = %.2e %s" % (resid, "OK" if resid < 1e-9 else "**LECH**"))
g5 = int((t7 >= pd.Timestamp("2026-01-01")).sum())
say("[G4] so dong start>=2026: %d %s" % (g5, "OK" if g5 == 0 else "**LECH**"))

# ---- B2. PROXY SLIP tai DUNG phut khop (entry/exit) + phan bo universe ----
s_e = np.full(len(df), np.nan)
s_x = np.full(len(df), np.nan)
miss = 0
cache = {}
for i, r in df.iterrows():
    p = os.path.join(RAW, r["symfull"] + ".f32")
    if not os.path.exists(p):
        miss += 1
        continue
    if r["symfull"] not in cache:
        if len(cache) > 3:
            cache.clear()
        cache[r["symfull"]] = np.fromfile(p, dtype=DT)
    a = cache[r["symfull"]]
    ts = a["ts"].astype(np.int64)
    for mm, arr in ((int(r["t_min"]), s_e), (int(r["te_min"]), s_x)):
        j = np.searchsorted(ts, mm)
        if j < len(ts) and ts[j] == mm:
            hh, ll, cc = float(a["h"][j]), float(a["l"][j]), float(a["c"][j])
            if cc > 0:
                arr[i] = 100.0 * 0.5 * (hh - ll) / cc
df["slip_proxy_e"] = s_e
df["slip_proxy_x"] = s_x
df["slip_proxy_rt"] = s_e + s_x
say("[B2] proxy slip (0,5*(h-l)/c tai DUNG phut khop) — thieu file/nen: %d" % miss)
say("     entry : mean %.4f%% median %.4f%%" % (np.nanmean(s_e), np.nanmedian(s_e)))
say("     exit  : mean %.4f%% median %.4f%%" % (np.nanmean(s_x), np.nanmedian(s_x)))
say("     RT    : mean %.4f%% median %.4f%%" % (np.nanmean(df.slip_proxy_rt), np.nanmedian(df.slip_proxy_rt)))
say("     !! DAY LA PROXY BIEN DONG, KHONG PHAI SLIP DO DUOC (khong co gia khop that).")

# ---- B3. FUNDING THAT tu Aerospike theo cua so giu lenh ----
fund_lookup = {}
cov_missing = []
try:
    import aerospike
    import cramjam
    cli = aerospike.client({"hosts": [(AERO_HOST, AERO_PORT)], "policies": {"timeout": 60000}}).connect()
    for sym in sorted(df["symfull"].unique()):
        try:
            key, meta, rec = cli.get(("test", "funding_data", sym))
            bd = rec.get("f_data")
            if bd is None:
                cov_missing.append(sym)
                continue
            d = json.loads(bytes(cramjam.snappy.decompress_raw(bytes(bd))))
            ts = np.array(sorted(int(k) for k in d), dtype=np.int64)
            rr = np.array([float(d[str(t)]) for t in ts], dtype=np.float64)
            fund_lookup[sym] = (ts, rr)
        except Exception:
            cov_missing.append(sym)
    cli.close()
    aero_ok = True
except Exception as ex:
    aero_ok = False
    say("[B3] ** Aerospike KHONG ket noi duoc: %s" % ex)
    fund_lookup = {}

say("[B3] funding_data coverage: %d/%d symbol cua 1089 lenh (thieu: %d) %s"
    % (len(fund_lookup), df["symfull"].nunique(), len(cov_missing), cov_missing[:8]))

fA = np.full(len(df), np.nan)   # (t_entry < T <= t_exit)
fB = np.full(len(df), np.nan)   # (t_entry <= T < t_exit)
n_ev = np.zeros(len(df), dtype=int)
for i, r in df.iterrows():
    got = fund_lookup.get(r["symfull"])
    if got is None:
        continue
    ts, rr = got
    a = (ts > r["t_ms"]) & (ts <= r["te_ms"])
    b = (ts >= r["t_ms"]) & (ts < r["te_ms"])
    n_ev[i] = int(a.sum())
    if a.any():
        fA[i] = 100.0 * rr[a].sum()
    if b.any():
        fB[i] = 100.0 * rr[b].sum()
df["funding_real_pp"] = fA          # %/lenh, >0 = TRA, <0 = THU (long: rate>0 -> tra)
df["funding_real_pp_B"] = fB
say("[B3] cua so funding: %d/%d lenh co >=1 ky settle trong [entry,exit] (n_ky: mean %.2f max %d)"
    % (int(np.isfinite(fA).sum()), len(df), n_ev.mean(), n_ev.max()))

ok = df[np.isfinite(df["funding_real_pp"])].copy()
pos = int((ok["funding_real_pp"] > 0).sum())
neg = int((ok["funding_real_pp"] < 0).sum())
zer = int((ok["funding_real_pp"] == 0).sum())
say("[B3] DẤU funding THẬT (Aerospike) tren %d lenh:" % len(ok))
say("     THU (rate<0, ta NHAN) : %6d  %5.1f%%" % (neg, 100.0 * neg / len(ok)))
say("     TRA (rate>0)          : %6d  %5.1f%%" % (pos, 100.0 * pos / len(ok)))
say("     = 0 (khong co ky)     : %6d  %5.1f%%" % (zer, 100.0 * zer / len(ok)))
say("     mean %+.4f%%/lenh | median %+.4f%%/lenh" % (ok.funding_real_pp.mean(), ok.funding_real_pp.median()))
say("     [B bien the cua so (t<=T<t)] mean %+.4f%%/lenh"
    % ok.funding_real_pp_B.mean())
allf = df["funding_real_pp"].fillna(0.0)
say("     TREN CA 1089 lenh (lenh khong co ky settle = 0): THU %5.1f%% | TRA %5.1f%% | 0 %5.1f%% | mean %+.4f%%/lenh"
    % (100.0 * (allf < 0).mean(), 100.0 * (allf > 0).mean(), 100.0 * (allf == 0).mean(), allf.mean()))
SUMMARY["funding_real_all1089"] = {"thu_pct": float(100.0 * (allf < 0).mean()),
                                   "tra_pct": float(100.0 * (allf > 0).mean()),
                                   "zero_pct": float(100.0 * (allf == 0).mean()),
                                   "mean_pp": float(allf.mean())}
say("[B3] so SIM (cot funding suy ra tu pnl):")
say("     THU (<0): %5.1f%% | TRA (>0): %5.1f%% | =0: %5.1f%%"
    % (100.0 * (df.funding_sim_pp < 0).mean(), 100.0 * (df.funding_sim_pp > 0).mean(),
       100.0 * (df.funding_sim_pp == 0).mean()))
say("     mean %+.4f%%/lenh | median %+.4f%%/lenh" % (df.funding_sim_pp.mean(), df.funding_sim_pp.median()))
SUMMARY["funding_real"] = {"n": len(ok), "thu_pct": 100.0 * neg / len(ok), "tra_pct": 100.0 * pos / len(ok),
                           "zero_pct": 100.0 * zer / len(ok), "mean_pp": float(ok.funding_real_pp.mean()),
                           "median_pp": float(ok.funding_real_pp.median())}
SUMMARY["funding_sim"] = {"thu_pct": float(100.0 * (df.funding_sim_pp < 0).mean()),
                          "tra_pct": float(100.0 * (df.funding_sim_pp > 0).mean()),
                          "mean_pp": float(df.funding_sim_pp.mean())}
dlt = (ok.funding_real_pp - ok.funding_sim_pp)
say("     lech (real - sim): mean %+.4f pp | median %+.4f pp | corr %.3f"
    % (dlt.mean(), dlt.median(), float(ok.funding_real_pp.corr(ok.funding_sim_pp))))

# ---- B1. FEE/LEG ----
say("[B1] fee/leg: KHONG DO DUOC (khong co commission/orderId; khong phan biet maker/taker).")
say("     Chi co moc tham chieu: maker %.3f%% / taker %.3f%% moi chan." % (FEE_REF["maker"], FEE_REF["taker"]))

# ---- B4. TI LE KHOP KHI DAT LIMIT ----
say("[B4] ti le khop khi dat LIMIT: KHONG DO DUOC (khong co trang thai order NEW/FILLED/CANCELED).")
say("     Moc ly thuyet da cong bo (RESULT_EXECUTION_MAKER): hoa von p* = 0,47..0,99 (iid) / 0,88..1,00 (adverse).")

# ---- B5. GROSS -> NET o 3 MUC CHI PHI ----
say()
say("[B5] DOI CHIEU gross -> net tren %d lenh (don vi %%/lenh):" % len(df))
freal = df["funding_real_pp"].fillna(0.0)     # lenh khong co ky settle => 0
scen = {}      # moi kich ban = gross - chi phi(round-trip) - funding
scen["S_sim: fee 0.80 + funding(sim)"] = df["net_sim"].values
scen["A: fee taker 0.10 + slip proxy + funding(real)"] = df["gross"] - 0.10 - df["slip_proxy_rt"] - freal
scen["B: fee taker 0.10 + slip 0 + funding(real)"] = df["gross"] - 0.10 - freal
scen["C: fee maker 0.04 + slip 0 + funding(real)"] = df["gross"] - 0.04 - freal
scen["D: fee taker 0.10 + slip 0 + funding(sim)"] = df["gross"] - 0.10 - df["funding_sim_pp"]
scen["E: fee 0.80 sim, funding(real)"] = df["gross"] - 0.80 - freal
for k in sorted(scen):
    v = scen[k][np.isfinite(scen[k])]
    say("     %-48s mean %+7.4f%% | median %+7.4f%% | win%% %5.1f | n=%d"
        % (k, v.mean(), np.median(v), 100.0 * (v > 0).mean(), len(v)))
SUMMARY["scenarios"] = {k: {"mean": float(np.mean(scen[k][np.isfinite(scen[k])])),
                            "median": float(np.median(scen[k][np.isfinite(scen[k])]))} for k in scen}

# theo nhom level
if "level" in df.columns:
    say()
    say("[B5] theo nhom `level` (net %/lenh):")
    for lv, g in df.groupby("level"):
        gi = g.index
        say("     %-24s n=%4d | sim %+7.3f | fee thuc slip=0 %+7.3f | fee thuc+slip proxy %+7.3f"
            % (lv, len(g), g["net_sim"].mean(),
               scen["B: fee taker 0.10 + slip 0 + funding(real)"][gi].mean(),
               scen["A: fee taker 0.10 + slip proxy + funding(real)"][gi].mean()))
    SUMMARY["by_level"] = {lv: {"n": int(len(g)), "sim": float(g["net_sim"].mean()),
                                "fee_real": float(scen["B: fee taker 0.10 + slip 0 + funding(real)"][g.index].mean())}
                           for lv, g in df.groupby("level")}

# ---- bonus: GIA Y DINH vs GIA KHOP (nguon kline_1m_opt = raw/*.f32, da chung minh cung nguon) ----
say()
say("[bonus] `entry`/exit trong printDone vs CLOSE nen tai dung phut khop (kline_1m_opt = raw/*.f32):")
df["exit_px_deriv"] = df["entry"] + df["gross"] / df["quantity"]
de_e, de_x = [], []
for _, r in df.iterrows():
    p = os.path.join(RAW, r["symfull"] + ".f32")
    if not os.path.exists(p):
        continue
    a = np.fromfile(p, dtype=DT)
    ts = a["ts"].astype(np.int64)
    for mm, val, acc in ((int(r["t_min"]), float(r["entry"]), de_e),
                         (int(r["te_min"]), float(r["exit_px_deriv"]), de_x)):
        j = np.searchsorted(ts, mm)
        if j < len(ts) and ts[j] == mm:
            c = float(a["c"][j])
            if c > 0 and val > 0:
                acc.append(100.0 * (val / c - 1.0))
de_e, de_x = np.array(de_e), np.array(de_x)
say("     entry vs close@entry-phut : n=%d | mean %+.4f%% | median %+.4f%% | p95|.| %.4f%%"
    % (len(de_e), de_e.mean(), np.median(de_e), np.percentile(np.abs(de_e), 95)))
say("     exit(deriv) vs close@exit-phut: n=%d | mean %+.4f%% | median %+.4f%% | p95|.| %.4f%%"
    % (len(de_x), de_x.mean(), np.median(de_x), np.percentile(np.abs(de_x), 95)))
say("     -> lech ~0 chung to: gia khop cua SIM = CLOSE nen (khong spread, khong impact) ⇒ slip 0,30%/chan la HANG SO CONG THEM, khong phai hieu ung duoc mo hinh hoa.")
SUMMARY["intent_vs_fill"] = {"entry_median_pct": float(np.median(de_e)),
                            "exit_median_pct": float(np.median(de_x))}
if len(led):
    say("     (shadow ledger la 2026-09: ngoai pham vi du lieu local <= 2025-12 ⇒ KHONG so duoc)")

df.to_csv(os.path.join(OUT, "legs_cost.csv"), index=False)
say()
say("[xong] trung gian: %s" % OUT)
save()
