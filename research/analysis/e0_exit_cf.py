"""E0: offline counterfactual measurement of the exit horizon (time-stop) for C2b.

Reproduces the live exit logic OFFLINE from hourly closes, then re-runs it with only
the time-stop horizon changed. No Java sim, no model training.

Exit logic reproduced (pre-registered, not swept):
  * long only; ARM when unrealised gain first reaches +7% (SIM_RATE_PROFIT_STOP_MARKET=0.07)
  * after ARM: trailing stop with giveback = min(peak_gain * 0.5, cap),
    cap = 0.08 when STRONG, 0.03 when WEAK; WEAK <=> symbolPred < 0.29
  * never armed within the horizon -> market time-stop at the horizon bar
  * no stop-loss before ARM

Measurements: M3 (correctness gate, reported first), M1 (arm-hour distribution),
M2 (counterfactual PnL per horizon), M4 (time-stopped orders' maxFav).

LIMITATIONS OF THIS MEASUREMENT
  * Per-order `margin` is taken AS-IS from printDone.csv. Sizing is NOT re-simulated.
    A shorter horizon frees capital earlier and would change position sizing and which
    orders get opened at all; that second-order effect is invisible here.
  * The order set is frozen: the same 970 entries are replayed for every horizon.
    A shorter horizon would in reality alter the sequence of future entries.
  * Price path is hourly closes (CLOSES_1H.bin). Intra-hour excursions are invisible,
    so ARM times are upper bounds and trailing exits are coarse.
  * pnl is modelled as margin * (profit% - COST_PCT)/100 with COST_PCT calibrated
    from the baseline (median of pnl/margin*100 - profit == -0.800).
"""

import logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("e0_exit_cf")

PRINT_DONE = "/home/ubuntu/java/devrun/C2b/storage/printDone.csv"
CLOSES = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
SYMMAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"
DOC_OUT = "/home/ubuntu/src/BinanceFuturesJava/docs/experiment/E0_EXIT_CF.md"

H_MS = 3_600_000
TZ_OFFSET_H = 7          # printDone `start` is GMT+7, CLOSES_1H.bin ts is UTC
ARM = 0.07               # SIM_RATE_PROFIT_STOP_MARKET
GIVEBACK_FRAC = 0.5
CAP_STRONG = 0.08
CAP_WEAK = 0.03
PRED_HINGE = 0.29
MAX_H = 168
HORIZONS = [48, 72, 96, 120, 144, 168]
COST_PCT = 0.80          # calibrated flat cost, see LIMITATIONS
CLOSES_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])


def load_prices():
    arr = np.fromfile(CLOSES, dtype=CLOSES_DT)
    arr = arr[np.lexsort((arr["ts"], arr["sym"]))]
    sid = arr["sym"].astype(np.int64)
    ts = arr["ts"].astype(np.int64)
    cl = arr["c"].astype(np.float64)
    uniq, starts, counts = np.unique(sid, return_index=True, return_counts=True)
    bounds = {int(u): (int(s), int(s + c)) for u, s, c in zip(uniq, starts, counts)}
    LOG.info("closes: n=%d symbols=%d", len(arr), len(bounds))
    return ts, cl, bounds


def load_orders():
    df = pd.read_csv(PRINT_DONE)
    df = df.loc[:, [c for c in df.columns if not c.startswith("Unnamed")]]
    smap = pd.read_csv(SYMMAP)
    smap["base"] = smap["symbol"].str.replace("USDT$", "", regex=True)
    df["symId"] = df["sym"].map(dict(zip(smap["base"], smap["symId"])))
    if df["symId"].isna().any():
        raise RuntimeError("unmapped symbols: %s" % df.loc[df["symId"].isna(), "sym"].unique())
    st = pd.to_datetime(df["start"], format="%Y%m%d %H:%M")
    st_utc = (st.astype("int64") // 10**6).values - TZ_OFFSET_H * H_MS
    # entry bar = first hourly bar strictly after the entry instant
    df["base_ms"] = (st_utc // H_MS) * H_MS + H_MS
    df["cap"] = np.where(df["symbolPred"] < PRED_HINGE, CAP_WEAK, CAP_STRONG)
    df["is_weak"] = df["symbolPred"] < PRED_HINGE
    LOG.info("orders=%d weak=%d strong=%d", len(df), int(df["is_weak"].sum()),
             int((~df["is_weak"]).sum()))
    return df


def build_paths(df, ts, cl, bounds):
    """gains[i, h] = close(entry_bar + h hours) / entry - 1, h = 0..MAX_H. NaN if bar absent."""
    n = len(df)
    gains = np.full((n, MAX_H + 1), np.nan)
    want = np.arange(MAX_H + 1, dtype=np.int64) * H_MS
    n_missing = 0
    for i, row in enumerate(df.itertuples()):
        s, e = bounds[int(row.symId)]
        seg_ts = ts[s:e]
        seg_cl = cl[s:e]
        tgt = row.base_ms + want
        j = np.searchsorted(seg_ts, tgt, side="left")
        ok = (j < len(seg_ts))
        j_clip = np.where(ok, j, 0)
        ok &= (seg_ts[j_clip] == tgt)
        px = np.where(ok, seg_cl[j_clip], np.nan)
        gains[i] = px / row.entry - 1.0
        if not ok.all():
            n_missing += 1
    LOG.info("orders with >=1 missing hourly bar in 0..168: %d", n_missing)
    return gains


def simulate(gains, caps, ts_h):
    """Replay the exit logic with time-stop horizon ts_h. Returns a DataFrame."""
    n = gains.shape[0]
    out = {k: np.zeros(n) for k in ("profit", "exit_h", "arm_h", "peak")}
    out["armed"] = np.zeros(n, dtype=bool)
    out["armed_no_trigger"] = np.zeros(n, dtype=bool)
    for i in range(n):
        cap = caps[i]
        peak = -np.inf
        armed = False
        arm_h = -1
        exit_h = -1
        profit = np.nan
        last_g, last_h = np.nan, -1
        for h in range(0, ts_h + 1):
            g = gains[i, h]
            if not np.isfinite(g):
                continue
            last_g, last_h = g, h
            if g > peak:
                peak = g
            if not armed and g >= ARM:
                armed = True
                arm_h = h
            if armed:
                giveback = min(peak * GIVEBACK_FRAC, cap)
                if g <= peak - giveback:
                    exit_h, profit = h, g
                    break
        if exit_h < 0:                      # no trailing trigger inside the horizon
            exit_h, profit = last_h, last_g
            if armed:
                out["armed_no_trigger"][i] = True
        out["profit"][i] = profit * 100.0
        out["exit_h"][i] = exit_h
        out["arm_h"][i] = arm_h
        out["peak"][i] = peak * 100.0
        out["armed"][i] = armed
    return pd.DataFrame(out)


def pnl_of(profit_pct, margin):
    return margin * (profit_pct - COST_PCT) / 100.0


def hist(values, edges, labels):
    v = np.asarray(values, dtype=float)
    idx = np.digitize(v, edges[1:-1], right=False)
    return [(labels[k], int((idx == k).sum())) for k in range(len(labels))]


def main():
    ts, cl, bounds = load_prices()
    df = load_orders()
    gains = build_paths(df, ts, cl, bounds)
    caps = df["cap"].values
    margin = df["margin"].values
    real_armed = (df["status"] == "STOP_MARKET_DONE").values
    real_profit = df["profit"].values
    real_pnl_sum = float(df["pnl"].sum())

    md = []
    md.append("# E0 - Counterfactual do luong horizon time-stop (offline)\n")
    md.append("Nguon: `printDone.csv` (970 lenh, C2b) + `CLOSES_1H.bin` (hourly closes UTC).")
    md.append("Logic exit tai tao: ARM +7%, trailing giveback = min(peak*0.5, cap), "
              "cap 0.08 STRONG / 0.03 WEAK (symbolPred < 0.29 => WEAK), time-stop khi chua bao gio arm.")
    md.append("Khong chay Java sim, khong train model. Chi horizon time-stop thay doi.\n")

    # ---------------- M3: correctness gate ----------------
    s168 = simulate(gains, caps, MAX_H)
    match = float((s168["armed"].values == real_armed).mean())
    ok = np.isfinite(s168["profit"].values) & np.isfinite(real_profit)
    corr = float(np.corrcoef(s168["profit"].values[ok], real_profit[ok])[0, 1])
    sim_pnl = float(np.nansum(pnl_of(s168["profit"].values, margin)))
    dev = (sim_pnl - real_pnl_sum) / abs(real_pnl_sum) * 100.0
    exit_corr = float(np.corrcoef(s168["exit_h"].values[ok], df["time_order"].values[ok])[0, 1])
    gate = (match >= 0.95) and (corr >= 0.95)
    LOG.info("M3 match=%.4f corr=%.4f sim_pnl=%.1f real=%.1f dev=%.2f%% exit_corr=%.4f GATE=%s",
             match, corr, sim_pnl, real_pnl_sum, dev, exit_corr, "PASS" if gate else "FAIL")

    md.append("## M3. Kiem tinh dung (gate) - **%s**\n" % ("PASS" if gate else "FAIL"))
    md.append("| Kiem tra | Nguong | Do duoc | Ket qua |")
    md.append("|---|---|---|---|")
    md.append("| Khop `status` (armed vs timestop) @ TS_H=168 | >= 95%% | %.2f%% | %s |"
              % (match * 100, "PASS" if match >= 0.95 else "FAIL"))
    md.append("| corr(profit_sim, profit_thuc) | >= 0.95 | %.4f | %s |"
              % (corr, "PASS" if corr >= 0.95 else "FAIL"))
    md.append("| sum(pnl) sim vs %.0f USDT thuc | (bao cao) | %.0f USDT | lech %.2f%% |"
              % (real_pnl_sum, sim_pnl, dev))
    md.append("| corr(exit_hour_sim, `time_order`) | (bao cao) | %.4f | - |" % exit_corr)
    md.append("")
    cm = pd.crosstab(pd.Series(real_armed, name="thuc_armed"),
                     pd.Series(s168["armed"].values, name="sim_armed"))
    md.append("Confusion (hang = thuc, cot = sim):\n\n```\n%s\n```\n" % cm.to_string())
    LOG.info("confusion:\n%s", cm.to_string())

    # --- M3 diagnosis: why the gate fails (diagnosis only, no tuning) ---
    gf = np.where(np.isfinite(gains), gains, -np.inf)
    maxg = gf.max(axis=1) * 100.0
    fn = real_armed & (~s168["armed"].values)
    n_h0 = int((df.loc[real_armed, "time_order"] == 0).sum())
    n_fast = int((df.loc[real_armed, "time_order"] <= 1).sum())
    LOG.info("M3-diag fn=%d fn_maxg_med=%.2f fn_maxg_max=%.2f h0=%d fast=%d",
             int(fn.sum()), float(np.median(maxg[fn])), float(maxg[fn].max()), n_h0, n_fast)
    md.append("### Tai sao gate FAIL (chan doan, khong tune)\n")
    md.append("- **%d lenh thang thuc te ma sim khong bao gio arm.** Max gain tren hourly close cua "
              "chung: median %.2f%%, p75 %.2f%%, **max %.2f%% - khong mot lenh nao cham nguong 7%%**. "
              "He thuc te arm bang gia trong gio (hoac mot chuoi min hon, vd 15m); hourly close "
              "khong bao gio voi toi nguong do."
              % (int(fn.sum()), float(np.median(maxg[fn])), float(np.percentile(maxg[fn], 75)),
                 float(maxg[fn].max())))
    md.append("- **%d / %d lenh thang co `time_order` == 0, %d co `time_order` <= 1 gio**: arm VA "
              "chot ngay trong 1-2 gio dau. Phan giai 1H khong the quan sat duoc nhung lenh nay."
              % (n_h0, int(real_armed.sum()), n_fast))
    md.append("- Gia `entry` trong printDone lech so voi hourly close tai gio entry: median ~2%. "
              "`CLOSES_1H.bin` khong phai chuoi gia ma Java sim da dung.")
    md.append("- **DCA bi loai tru**: `lastentry == entry` cho ca 970 lenh, nen nguyen nhan khong "
              "phai DCA. Funding/fee cung khong phai: chung chi la mot hang so ~0.80% tren pnl.")
    md.append("- Chi %d / %d lenh time-stop thuc te co max hourly-close gain >= 7%%: huong lech gan "
              "nhu MOT chieu - sim bo sot arm, chu khong arm khong."
              % (int((maxg[~real_armed] >= 7).sum()), int((~real_armed).sum())))
    md.append("")
    md.append("**Gate khong dat => M1/M2/M4 duoi day chi la tham khao, KHONG du tin cay de "
              "quyet dinh doi horizon.**\n")

    # ---------------- M1: arm-hour distribution ----------------
    sub = s168.loc[real_armed]
    armed_sub = sub.loc[sub["armed"]]
    arm_h = armed_sub["arm_h"].values
    edges = [0, 24, 48, 72, 96, 120, 144, 169]
    labels = ["0-24", "24-48", "48-72", "72-96", "96-120", "120-144", "144-168"]
    hb = hist(arm_h, edges, labels)
    late = float((arm_h > 72).sum())
    late_pct = late / len(arm_h) * 100.0
    LOG.info("M1 n_real_win=%d sim_armed=%d hist=%s late72=%d (%.2f%%)",
             int(real_armed.sum()), len(arm_h), hb, int(late), late_pct)
    md.append("## M1. Phan bo thoi diem ARM (lenh thang thuc te, n=%d; sim arm duoc %d)\n"
              % (int(real_armed.sum()), len(arm_h)))
    md.append("| Bin gio | So lenh | % |")
    md.append("|---|---|---|")
    for lab, c in hb:
        md.append("| %s | %d | %.1f%% |" % (lab, c, c / len(arm_h) * 100))
    md.append("")
    md.append("**Arm SAU gio 72: %d / %d = %.2f%%** cua cac lenh thang -> day la phan se mat "
              "neu cat time-stop ve 72h.\n" % (int(late), len(arm_h), late_pct))
    n_win_late = int((df.loc[real_armed, "time_order"] > 72).sum())
    LOG.info("M1 gt-bound: wins with time_order>72 = %d / %d (%.2f%%)",
             n_win_late, int(real_armed.sum()), n_win_late / real_armed.sum() * 100)
    md.append("Chan tren tu ground-truth (**khong phu thuoc vao viec dung lai duong gia**): "
              "%d / %d lenh thang co `time_order` > 72h = %.2f%%. Mot lenh arm som nhung chot muon "
              "van song sot duoi time-stop 72h, nen day la CHAN TREN cua so lenh thang bi cat. "
              "No khop bac do lon voi %.2f%% do tu duong gia o tren, nen ket luan M1 la phan "
              "vung nhat cua bao cao nay.\n"
              % (n_win_late, int(real_armed.sum()), n_win_late / real_armed.sum() * 100, late_pct))

    # ---------------- M2: counterfactual per horizon ----------------
    md.append("## M2. Counterfactual PnL theo horizon\n")
    md.append("| TS_H | n_armed | n_timestop | mean%(armed) | mean%(timestop) | sum_pnl_USDT | TSloss_rate% |")
    md.append("|---|---|---|---|---|---|---|")
    rows = []
    for th in HORIZONS:
        s = simulate(gains, caps, th)
        a = s["armed"].values
        p = s["profit"].values
        n_a, n_t = int(a.sum()), int((~a).sum())
        m_a = float(np.nanmean(p[a])) if n_a else float("nan")
        m_t = float(np.nanmean(p[~a])) if n_t else float("nan")
        tot = float(np.nansum(pnl_of(p, margin)))
        tsr = n_t / len(df) * 100.0
        rows.append((th, n_a, n_t, m_a, m_t, tot, tsr))
        md.append("| %d | %d | %d | %+.2f%% | %+.2f%% | %.0f | %.1f%% |"
                  % (th, n_a, n_t, m_a, m_t, tot, tsr))
        LOG.info("M2 TS_H=%d n_armed=%d n_ts=%d mean_a=%+.3f mean_t=%+.3f pnl=%.1f tsr=%.2f",
                 th, n_a, n_t, m_a, m_t, tot, tsr)
    md.append("")
    base = [r for r in rows if r[0] == 168][0]
    md.append("Delta sum_pnl so voi TS_H=168 (%.0f USDT):\n" % base[5])
    md.append("| TS_H | delta_USDT | delta% |")
    md.append("|---|---|---|")
    for r in rows:
        md.append("| %d | %+.0f | %+.1f%% |" % (r[0], r[5] - base[5], (r[5] - base[5]) / abs(base[5]) * 100))
    md.append("")
    # ---------------- M4: the 147 time-stopped orders ----------------
    spread = max(r[5] for r in rows) - min(r[5] for r in rows)
    md.append("**Canh bao**: sum_pnl KHONG don dieu theo horizon (48h > 72h; 96h > 120h/144h). "
              "Bien do dao dong giua cac horizon (%.0f USDT = %.1f%% cua baseline) NHO HON sai so "
              "cua chinh phep do o gate (%.1f%%). Vi vay M2 khong the xep hang cac horizon; "
              "no bi tail cua vai lenh loi rat lon chi phoi."
              % (spread, spread / abs(base[5]) * 100, abs(dev)))
    md.append("")
    ts_mask = ~real_armed
    g_ts = gains[ts_mask]
    g_ts_f = np.where(np.isfinite(g_ts), g_ts, -np.inf)
    maxfav = g_ts_f.max(axis=1) * 100.0
    argfav = g_ts_f.argmax(axis=1)
    e4 = [-1e9, 1.0, 3.0, 5.0, 7.0, 1e9]
    l4 = ["<1%", "1-3%", "3-5%", "5-7%", ">7%"]
    h4 = hist(maxfav, e4, l4)
    LOG.info("M4 n=%d maxfav_hist=%s median_maxfav=%.2f median_hour=%.0f",
             int(ts_mask.sum()), h4, float(np.median(maxfav)), float(np.median(argfav)))
    md.append("## M4. 147 lenh bi time-stop: maxFav trong 168h\n")
    md.append("| maxFav | So lenh | % | gio dat maxFav (median) |")
    md.append("|---|---|---|---|")
    for k, (lab, c) in enumerate(h4):
        idx = np.digitize(maxfav, e4[1:-1], right=False) == k
        hh = float(np.median(argfav[idx])) if c else float("nan")
        md.append("| %s | %d | %.1f%% | %s |"
                  % (lab, c, c / len(maxfav) * 100, "-" if not c else "%.0f" % hh))
    md.append("")
    md.append("maxFav: median %.2f%%, p75 %.2f%%, p90 %.2f%%, max %.2f%%. "
              "Gio dat maxFav: median %.0f, p75 %.0f.\n"
              % (np.median(maxfav), np.percentile(maxfav, 75), np.percentile(maxfav, 90),
                 maxfav.max(), np.median(argfav), np.percentile(argfav, 75)))
    near = int(((maxfav >= 5.0) & (maxfav < 7.0)).sum())
    dead = int((maxfav < 1.0).sum())
    md.append("Suyt arm (5-7%%): %d lenh (%.1f%%). Khong bao gio chay (<1%%): %d lenh (%.1f%%).\n"
              % (near, near / len(maxfav) * 100, dead, dead / len(maxfav) * 100))

    md.append("## Gioi han cua phep do\n")
    md.append("1. **Giu nguyen `margin` tung lenh, KHONG mo phong lai sizing.** Horizon ngan hon "
              "giai phong von som hon -> sizing va ca tap lenh mo ra se khac. Hieu ung bac hai nay "
              "khong nhin thay o day.")
    md.append("2. **Tap lenh dong bang**: cung 970 entry duoc replay cho moi horizon. Thuc te "
              "horizon ngan hon se doi chuoi entry tuong lai (capital rotation).")
    md.append("3. **Duong gia la hourly close**. Bien dong trong gio khong thay duoc: gio ARM la "
              "gioi han tren, va trailing exit bi lam tho. Median |close_1h/entry - 1| tai gio "
              "entry la ~2%, tuc CLOSES_1H.bin khong phai chuoi gia ma Java sim dung.")
    md.append("4. **pnl mo hinh hoa** = margin * (profit%% - %.2f%%)/100, hang so cost hieu chinh "
              "tu baseline (median cua pnl/margin*100 - profit == -0.800). Funding/fee thuc te "
              "tung lenh khong tai tao." % COST_PCT)
    md.append("5. Khong co stop-loss truoc ARM trong logic nay; neu live co thay doi khac thi phep "
              "do lech.")
    md.append("")

    with open(DOC_OUT, "w") as fh:
        fh.write("\n".join(md) + "\n")
    LOG.info("wrote %s", DOC_OUT)


if __name__ == "__main__":
    main()
