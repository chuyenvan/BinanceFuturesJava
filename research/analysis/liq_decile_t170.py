#!/usr/bin/env python3
"""LIQ_DECILE_T170 — VIEC (2): decile THANH KHOAN / BIEN DONG cua tung leg T170 (causal tai entry).

Pre-reg: docs/PREREG_COST_LIQUIDITY.md (commit cd5e758, chot TRUOC khi do; KHONG sua thiet ke).

Nguon:
  * leg:  /home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv (md5 efb793e2468ca3a7318da0f0ad23d4fc)
  * nen:  /home/ubuntu/claudedata/rvb_1m/raw/<SYM>USDT.f32  [ts<i4, o,h,l,c,v <f4], ts = PHUT EPOCH UTC
          v == totalUsdt (da kiem chung voi Aerospike test/kline_1m_opt, bin data = Snappy(MinuteDataFinal))

Bien causal tai t (phut UTC cua nen vao lenh), MOI cua so ket thuc tai t-1:
  L60  = mean totalUsdt tren [t-60, t-1]        (CHINH, >= 48/60)
  L240 = mean totalUsdt tren [t-240, t-1]       (phu,  >= 192/240)
  R1   = (h-l)/open cua nen t-1                 (phu)
  R15  = (max h - min l)/open tren [t-15, t-1]  (phu, >= 13/15)
  slip_proxy = 0.5*(h-l)/close tai nen t (convention repo) — UOC LUONG, khong phai so do thuc.

Trung gian: $LQ_OUT/legs.npz (resume duoc). Thuan Python, khong Java, khong 2026, khong push.
"""
import os
import sys
import json
import hashlib
import datetime as dt

import numpy as np
import pandas as pd

OUT = os.environ.get("LQ_OUT", "/tmp/liq_decide")
PRINT_DONE = os.environ.get(
    "LQ_PRINT_DONE", "/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv")
RAW = os.environ.get("LQ_RAW", "/home/ubuntu/claudedata/rvb_1m/raw")
MD5_EXPECT = "efb793e2468ca3a7318da0f0ad23d4fc"   # md5 THAT cua file (task goc ghi thua "0f" — da doi chieu md5sum)
N_EXPECT = 1089

DT = np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])
UTC = dt.timezone.utc
DECILES = 10
COV_L60 = 48
COV_L240 = 192
COV_R15 = 13
CUT_PCTS = (0, 5, 10, 20, 30, 40, 50, 60)
NBOOT = 2000
SEED = 20260923
os.makedirs(OUT, exist_ok=True)

REPORT = []
def say(s=""):
    REPORT.append(s)
    print(s)


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def load_legs():
    md = md5(PRINT_DONE)
    df = pd.read_csv(PRINT_DONE)
    say("[G1] md5 printDone = %s (cho %s) %s" % (md, MD5_EXPECT, "OK" if md == MD5_EXPECT else "**LECH**"))
    say("[G1] n_dong  = %d (cho %d) %s" % (len(df), N_EXPECT, "OK" if len(df) == N_EXPECT else "**LECH**"))
    # start la GMT+7
    t7 = pd.to_datetime(df["start"], format="%Y%m%d %H:%M")
    df["t_min"] = ((t7.astype("int64") // 10**9) - 7 * 3600) // 60          # phut epoch UTC
    df["day"] = ((t7.astype("int64") // 10**9 - 7 * 3600) // 86400)         # ngay UTC (block bootstrap)
    df["symfull"] = df["sym"].astype(str) + "USDT"
    df["ret_net"] = 100.0 * df["pnl"] / df["margin"]
    df["ret_gross"] = df["profit"].astype(float)
    df["win"] = (df["pnl"] > 0).astype(int)
    return df


def measures(df):
    """Tra bang do luong causal cho tung leg + co cross-check volume."""
    cache = {}
    cols = {k: np.full(len(df), np.nan) for k in
            ("L60", "L240", "R1", "R15", "slip_proxy", "n60", "n240", "n15", "vol_entry")}
    miss_file, miss_bar, bad_entry = [], [], []
    for i, r in df.reset_index(drop=True).iterrows():
        s = r["symfull"]
        p = os.path.join(RAW, s + ".f32")
        if not os.path.exists(p):
            miss_file.append(s)
            continue
        if s not in cache:
            cache[s] = np.fromfile(p, dtype=DT)
        a = cache[s]
        ts = a["ts"].astype(np.int64)
        m = int(r["t_min"])

        # --- G3: nen tai t phai co va khop entry ---
        j = np.searchsorted(ts, m)
        if j >= len(ts) or ts[j] != m:
            miss_bar.append((s, int(r["start"].replace(" ", ""))))
            continue
        ent = float(a["c"][j])
        if not (abs(ent / float(r["entry"]) - 1.0) <= 0.005):
            bad_entry.append((s, ent, float(r["entry"])))
            continue
        cols["vol_entry"][i] = float(a["v"][j])
        cols["slip_proxy"][i] = 0.5 * (float(a["h"][j]) - float(a["l"][j])) / ent

        # --- cua so ket thuc tai t-1 (KHONG bao gio doc nen t) ---
        def win(before, after):
            """cua so [t-before, t-after) — dung ngay (60,1) = [t-60, t-1] (bao gom nen t-1)."""
            k0 = np.searchsorted(ts, m - before)
            k1 = np.searchsorted(ts, m - after)
            return a[k0:k1] if k1 > k0 else a[0:0]

        w60 = win(60, 1)          # [t-60, t-1]
        if len(w60) > 0:
            cols["n60"][i] = len(w60)
            cols["L60"][i] = float(np.mean(w60["v"].astype(np.float64)))
        w240 = win(240, 1)
        if len(w240) > 0:
            cols["n240"][i] = len(w240)
            cols["L240"][i] = float(np.mean(w240["v"].astype(np.float64)))
        w15 = win(15, 1)
        if len(w15) > 0:
            cols["n15"][i] = len(w15)
            o0 = float(w15["o"][0])
            cols["R15"][i] = (float(np.max(w15["h"])) - float(np.min(w15["l"]))) / o0
        jp = np.searchsorted(ts, m - 1)
        if jp < len(ts) and ts[jp] == m - 1:
            cols["R1"][i] = (float(a["h"][jp]) - float(a["l"][jp])) / float(a["o"][jp])
        if i % 200 == 0:
            print("  leg %d/%d el=-" % (i, len(df)), flush=True)
    for k, v in cols.items():
        df[k] = v
    g2_file = os.path.join(OUT, "diag.json")
    json.dump({"miss_file": miss_file, "miss_bar": miss_bar,
               "bad_entry": bad_entry[:20], "n_bad_entry": len(bad_entry)},
              open(g2_file, "w"), indent=1)
    say("[G2/G3] thieu file raw: %d | thieu nen tai t: %d | entry lech >0,5%%: %d"
        % (len(miss_file), len(miss_bar), len(bad_entry)))
    if miss_bar:
        say("        vi du thieu nen: %s" % (miss_bar[:5],))
    sub = df[np.isfinite(df["vol_entry"])]
    if len(sub):
        rel = np.abs(sub["vol_entry"] - sub["volume"].astype(float)) / np.maximum(
            1.0, np.abs(sub["volume"].astype(float)))
        say("[G2] raw.v == cot volume(printDone): %d/%d dong khop <=1%% (max lech %.2e) => %s"
            % (int((rel <= 0.01).sum()), len(sub), float(rel.max()) if len(rel) else -1.0,
               "OK" if len(sub) and (rel <= 0.01).mean() >= 0.95 else "**CHUA DAT**"))
    return df


def decile_order(v):
    """Thu tu rank-based tat dinh: sort (gia tri tang, -pnl, sym)."""
    return None


def assign_deciles(df, col):
    """Tra mang decile 1..10 (decile 1 = gia tri NHO NHAT = kem thanh khoan / bien dong nho nhat)."""
    ok = np.isfinite(df[col].to_numpy(dtype=float))
    idx = np.where(ok)[0]
    # np.lexsort: key CUOI cung la khoa CHINH => (tertiary, secondary, primary)
    key = np.lexsort((df["sym"].to_numpy()[idx], -df["pnl"].to_numpy()[idx],
                      df[col].to_numpy()[idx]))
    order = idx[key]
    n = len(order)
    d = np.full(len(df), -1, dtype=int)
    edges = np.linspace(0, n, DECILES + 1).round().astype(int)
    for k in range(DECILES):
        d[order[edges[k]:edges[k + 1]]] = k + 1
    return d


def block_boot_ci(val, blk, nboot=NBOOT, seed=SEED):
    """CI95 cho mean(val) bang bootstrap block (blk = id ngay)."""
    if len(val) == 0:
        return np.nan, np.nan
    uq, inv = np.unique(blk, return_inverse=True)
    s = np.bincount(inv, weights=val, minlength=len(uq))
    c = np.bincount(inv, minlength=len(uq))
    rng = np.random.default_rng(seed)
    B = rng.integers(0, len(uq), size=(nboot, len(uq)))
    ss = s[B].sum(axis=1)
    cc = c[B].sum(axis=1)
    r = np.where(cc > 0, ss / np.maximum(cc, 1), np.nan)
    return float(np.nanpercentile(r, 2.5)), float(np.nanpercentile(r, 97.5))


def decile_table(df, col, dec, tag):
    say("")
    say("### Decile theo `%s` (%s) — decile 1 = THAP NHAT" % (col, tag))
    say("")
    say("| d | n | SumPnL (USDT) | SumMargin | meanP_net (%) | mean_gross (%) | win% | slip_proxy (%) | L_med | %SumPnL | Cum%SumPnL |")
    say("|---|---|---|---|---|---|---|---|---|---|---|")
    tot = df["pnl"].sum()
    rows = []
    for k in range(1, DECILES + 1):
        m = dec == k
        s = df[m]
        val = s["ret_net"].to_numpy(dtype=float)
        sp = float(np.nanmean(s["slip_proxy"])) * 100.0
        lo, hi = block_boot_ci(val, s["day"].to_numpy())
        r = dict(d=k, n=len(s), sumpnl=float(s["pnl"].sum()), summarg=float(s["margin"].sum()),
                 meanp=float(s["pnl"].sum() / s["margin"].sum() * 100.0),
                 gross=float(s["ret_gross"].mean()), win=float(s["win"].mean() * 100.0),
                 slip=sp, lmed=float(np.nanmedian(s[col])), ci=(lo, hi),
                 share=float(s["pnl"].sum() / tot * 100.0))
        rows.append(r)
        say("| %d | %d | %.1f | %.0f | **%+.3f** | %+.3f | %.1f | %.4f | %.4g | %+.1f%% | |"
            % (r["d"], r["n"], r["sumpnl"], r["summarg"], r["meanp"], r["gross"], r["win"], r["slip"],
               r["lmed"], r["share"]))
    cum = 0.0
    for r in rows[::-1]:
        cum += r["share"]
        r["cum"] = cum
    say("")
    say("Cum%SumPnL (tu decile 10 xuong): " + " · ".join(
        "d%d=%.1f%%" % (r["d"], r["cum"]) for r in rows))
    say("")
    for r in rows:
        say("- d%d n=%d meanP_net=%+.3f%% CI95(block-ngay)=[%+.3f%%, %+.3f%%] %s"
            % (r["d"], r["n"], r["meanp"], r["ci"][0], r["ci"][1],
               "<-- CI NGOAI 0 (AM)" if r["ci"][1] < 0 else
               ("<-- CI NGOAI 0 (DUONG)" if r["ci"][0] > 0 else "(CI chua 0)")))
    # cau hoi quyet dinh
    lo_r, hi_r = rows[0], rows[-1]
    say("")
    say("**Cau hoi quyet dinh:** decile kem thanh khoan nhat (d1) net = %+.3f%%/lenh (SumPnL %+.1f USDT, n=%d, win %.1f%%)."
        % (lo_r["meanp"], lo_r["sumpnl"], lo_r["n"], lo_r["win"]))
    say("So lenh LAI/Lo o d1: %d/%d." % (int((df[dec == 1]["pnl"] > 0).sum()), int((dec == 1).sum())))
    say("Phan bo PnL: top-3 decile thanh khoan cao (d8+d9+d10) = %.1f%% tong PnL; d10 mot minh = %.1f%%;"
        % (sum(r["share"] for r in rows if r["d"] >= 8), hi_r["share"]))
    say("bottom-3 (d1+d2+d3) = %.1f%% tong PnL."
        % sum(r["share"] for r in rows if r["d"] <= 3))
    return rows


def threshold_scan(df, col, dec):
    say("")
    say("### Quet nguong CAT theo phan vi `%s` (BAO HET, khong chon nguong tot nhat)" % col)
    say("")
    say("| p (cat duoi) | n giu | %lenh bi cat | SumPnL giu | SumMargin giu | meanP_net giu (%) | win% giu | %SumPnL giu |")
    say("|---|---|---|---|---|---|---|---|")
    tot = df["pnl"].sum()
    base = None
    out = []
    for p in CUT_PCTS:
        thr = np.nanpercentile(df[col].to_numpy(dtype=float), p) if p > 0 else -np.inf
        keep = (df[col].to_numpy(dtype=float) >= thr) & np.isfinite(dec)
        s = df[keep]
        mp = float(s["pnl"].sum() / s["margin"].sum() * 100.0)
        r = dict(p=p, n=len(s), cut=100.0 * (1 - len(s) / len(df)),
                 sumpnl=float(s["pnl"].sum()), summarg=float(s["margin"].sum()), meanp=mp,
                 win=float(s["win"].mean() * 100.0), share=float(s["pnl"].sum() / tot * 100.0))
        out.append(r)
        if p == 0:
            base = r
        say("| %d | %d | %.1f%% | %.1f | %.0f | **%+.3f** | %.1f | %+.1f%% |"
            % (r["p"], r["n"], r["cut"], r["sumpnl"], r["summarg"], r["meanp"], r["win"], r["share"]))
    say("")
    mono = all(out[i + 1]["meanp"] > out[i]["meanp"] for i in range(len(out) - 1))
    lo_neg = None
    return out, mono

def corr_section(dl):
    say("")
    say("### Tuong quan hang (Spearman) giua chi so va net%/lenh")
    say("")
    say("| Chi so | rho | p (2 phia) | n |")
    say("|---|---|---|---|")
    try:
        from scipy.stats import spearmanr
        have = True
    except Exception:
        have = False
    for col in ("L60", "L240", "R1", "R15"):
        v = dl[col].to_numpy(dtype=float)
        y = dl["ret_net"].to_numpy(dtype=float)
        m = np.isfinite(v) & np.isfinite(y)
        if not m.any():
            continue
        if have:
            rho, p = spearmanr(v[m], y[m])
            say("| `%s` | **%+.4f** | %.3g | %d |" % (col, rho, p, int(m.sum())))
        else:
            rv = np.argsort(np.argsort(v[m])).astype(float)
            ry = np.argsort(np.argsort(y[m])).astype(float)
            rho = float(np.corrcoef(rv, ry)[0, 1])
            say("| `%s` | **%+.4f** | (scipy vang, rank-Pearson) | %d |" % (col, rho, int(m.sum())))
    say("")


def main():
    say("=== LIQ_DECILE_T170 — VIEC (2) ===")
    say("Pre-reg docs/PREREG_COST_LIQUIDITY.md, commit cd5e758. Thuan Python.")
    df = load_legs()
    say("[G5] khoang ngay GMT+7: %s .. %s" % (df["start"].min(), df["start"].max()))
    bad2026 = df["start"] >= "20260101"
    say("[G5] so dong ngay >= 2026-01-01: %d => %s" % (int(bad2026.sum()),
                                                      "OK" if not bad2026.any() else "**CO 2026 => DUNG**"))
    if bad2026.any():
        raise SystemExit("VI PHAM: co du lieu 2026")
    df = measures(df)
    np.savez(os.path.join(OUT, "legs.npz"),
             **{c: df[c].to_numpy() for c in df.columns})
    ok = (np.isfinite(df["L60"].to_numpy()) & (df["n60"].to_numpy() >= COV_L60))
    say("")
    say("Coverage: L60 du (%d/%d nen) o **%d/%d** lenh (%.1f%%)"
        % (COV_L60, 60, int(ok.sum()), len(df), 100.0 * ok.mean()))
    dl = df[ok].reset_index(drop=True)
    say("Bang dung: **%d lenh** (dung so leg T170 co du lieu, khong them universe)." % len(dl))
    ncut = int((df["n60"].to_numpy() < COV_L60).sum())
    say("Loai vi thieu nen L60: %d lenh." % ncut)

    dec60 = assign_deciles(dl, "L60")
    corr_section(dl)
    t60 = decile_table(dl, "L60", dec60, "CHINH")
    scan60, mono60 = threshold_scan(dl, "L60", dec60)

    say("")
    say("**Doc theo quy tac chot truoc (§3.4):**")
    d1 = t60[0]
    core = [r for r in scan60 if 5 <= r["p"] <= 40]
    seq = [r for r in scan60 if r["p"] == 0] + core
    mono_all = all(seq[i + 1]["meanp"] > seq[i]["meanp"] for i in range(len(seq) - 1))
    say("- meanP_net tang DON DIEU o moi p in {5..40}? **%s** (chuoi: %s)"
        % ("CO" if mono_all else "KHONG",
           " -> ".join("%d:%.3f" % (r["p"], r["meanp"]) for r in seq)))
    say("- CI95 decile thap nhat nam ngoai 0 ve phia AM? **%s** (CI [%+.3f, %+.3f])"
        % ("CO" if d1["ci"][1] < 0 else "KHONG", d1["ci"][0], d1["ci"][1]))
    decision = "NEN CAT" if (mono_all and d1["ci"][1] < 0) else "KHONG CAT"
    say("- => **%s** theo luat da chot (xem the them o RESULT)." % decision)

    # phu: L240 / R1 / R15
    ok240 = np.isfinite(dl["L240"].to_numpy()) & (dl["n240"].to_numpy() >= COV_L240)
    say("")
    say("## PHU — decile theo chi so khac")
    say("")
    dec240 = assign_deciles(dl[ok240].reset_index(drop=True), "L240")
    decile_table(dl[ok240].reset_index(drop=True), "L240", dec240, "phu")
    dec1 = assign_deciles(dl[np.isfinite(dl["R1"].to_numpy())].reset_index(drop=True), "R1")
    decile_table(dl[np.isfinite(dl["R1"].to_numpy())].reset_index(drop=True), "R1", dec1,
                 "phu (bien dong nen t-1)")
    ok15 = np.isfinite(dl["R15"].to_numpy()) & (dl["n15"].to_numpy() >= COV_R15)
    dec15 = assign_deciles(dl[ok15].reset_index(drop=True), "R15")
    decile_table(dl[ok15].reset_index(drop=True), "R15", dec15, "phu (bien dong 15 phut)")

    with open(os.path.join(OUT, "report_liq.txt"), "w") as f:
        f.write("\n".join(REPORT) + "\n")
    json.dump({"decision": decision, "mono": bool(mono_all),
               "d1_ci": [d1["ci"][0], d1["ci"][1]], "n_used": len(dl), "n_dropped_l60": ncut},
              open(os.path.join(OUT, "summary.json"), "w"), indent=1)
    print("\nSAVED", os.path.join(OUT, "report_liq.txt"))


if __name__ == "__main__":
    main()
