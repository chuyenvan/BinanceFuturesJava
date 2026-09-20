"""HEDGE_OVERLAY_A — Phuong an A: overlay hedge BTC COUNTERFACTUAL tren sach T170.

Thuc thi DUNG theo docs/PREREG_HEDGE_OVERLAY_A.md (commit 03c037e). KHONG sua .java,
KHONG chay sim. Sach long giu nguyen byte-identical: script nay chi DOC printDone.csv +
sim.out cua T170 va cong mot chuoi PnL hedge tinh ngoai engine.

Nguon: xem pre-reg muc 2. Ghi ra /home/ubuntu/hedge_a/hedge_overlay_a.json.
LUAT REPO: dung module logging, KHONG dung print().
"""
import ast
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c3_rates as C  # noqa: E402
import beta_decomp_t170 as BD  # noqa: E402  (tai su dung ols_hac / btc_at_or_before / CTIME)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("hedge_a")

TAG = "X1_GS_T170_2021"
WIN_START = pd.Timestamp("2021-07-01")
WIN_END = pd.Timestamp("2025-12-31 23:59:59")
FUNDING_CSV = "/home/ubuntu/hedge_a/funding_btcusdt.csv"
OUT_JSON = "/home/ubuntu/hedge_a/hedge_overlay_a.json"
NBETS_STEP3 = os.path.join(HERE, "nbets_step3_crosssec.py")

ROLL_DAYS = 60          # pre-reg muc 3 — CHOT 1 gia tri, khong do nhieu N
MIN_OBS = 20            # pre-reg muc 3
COST_RATE = 0.0006      # pre-reg muc 6: taker 0.05% + slippage 1bp
HOUR_MS = 3600 * 1000
GMT7_MS = 7 * HOUR_MS


def load_icc_anova():
    """Nap NGUYEN VAN ham icc_anova() tu nbets_step3_crosssec.py (khong import ca module vi
    module do chay phan tich ngay o top-level). Dam bao cong thuc ICC la DUNG cai chuan."""
    tree = ast.parse(open(NBETS_STEP3).read())
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "icc_anova"]
    if len(fn) != 1:
        raise RuntimeError("khong tim thay icc_anova trong %s" % NBETS_STEP3)
    ns = {"np": np}
    exec(compile(ast.Module(body=fn, type_ignores=[]), NBETS_STEP3, "exec"), ns)
    return ns["icc_anova"]


icc_anova = load_icc_anova()


def dd_uw_cagr(s):
    """Dinh nghia DUNG nhu c3_rates.py / x1_rates.py."""
    dd = (s / s.cummax() - 1) * 100
    uw = s < s.cummax()
    years = (s.index[-1] - s.index[0]).days / 365.25
    return {
        "equity_start": float(s.iloc[0]), "equity_end": float(s.iloc[-1]),
        "cagr": float(((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100),
        "maxDD": float(dd.min()),
        "uw": int(uw.groupby((~uw).cumsum()).sum().max()),
    }


def hard_by_year(s):
    out = {}
    for y, sy in s.groupby(s.index.year):
        dd = (sy / sy.cummax() - 1) * 100
        uw = sy < sy.cummax()
        uwmax = int(uw.groupby((~uw).cumsum()).sum().max()) if len(uw) else 0
        qe = sy.resample("QE").last()
        q0 = pd.concat([pd.Series([sy.iloc[0]], index=[sy.index[0]]), qe]).iloc[:-1]
        qr = (qe.values / q0.values - 1) * 100
        ry = (sy.iloc[-1] / sy.iloc[0] - 1) * 100
        out[str(y)] = {"maxDD": float(dd.min()), "uw": uwmax, "ret_year": float(ry),
                       "q_min": float(np.min(qr)),
                       "pass": bool(dd.min() >= -15.0 and uwmax <= 120 and ry >= 0
                                    and np.min(qr) >= -5.0)}
    return out


# ---------------------------------------------------------------- du lieu vao
def load_trades():
    d = C.trades(TAG).copy()                      # tai su dung parser chuan cua repo
    d["t0"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M", errors="coerce")
    d["t1"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M", errors="coerce")
    d = d.dropna(subset=["t0", "t1", "margin", "pnl"])
    d = d[(d.t0 >= WIN_START) & (d.t0 <= WIN_END)].reset_index(drop=True)
    # start/end trong printDone.csv la gio GMT+7 NAIVE -> quy ve UTC ms
    d["s_ms"] = d.t0.values.astype("datetime64[ms]").astype(np.int64) - GMT7_MS
    d["e_ms"] = d.t1.values.astype("datetime64[ms]").astype(np.int64) - GMT7_MS
    d["e_ms"] = np.maximum(d["e_ms"], d["s_ms"])  # an toan
    d["notional"] = d["margin"].astype(float)     # cot margin = NOTIONAL (TASK1 da verify)
    d["roi0"] = d["pnl"].astype(float) / d["notional"]
    d["cohort_day"] = d.t0.dt.floor("1D")
    return d


def hourly_grid():
    t0 = int(pd.Timestamp("2021-07-01").value // 10 ** 6)
    t1 = int(pd.Timestamp("2026-01-01").value // 10 ** 6)
    g = np.arange(t0, t1, HOUR_MS, dtype=np.int64)          # moc UTC, buoc 1h
    px = BD.btc_at_or_before(g)                              # gia BTC 1h gan nhat <= moc
    ok = np.isfinite(px)
    return g[ok], px[ok]


def sum_notional_on_grid(d, grid):
    """Sum notional long dang mo tai moi moc (quy uoc [start, end))."""
    ev_t = np.concatenate([d.s_ms.values, d.e_ms.values])
    ev_v = np.concatenate([d.notional.values, -d.notional.values])
    o = np.argsort(ev_t, kind="mergesort")
    ev_t, ev_v = ev_t[o], np.cumsum(ev_v[o])
    idx = np.searchsorted(ev_t, grid, side="right") - 1
    out = np.where(idx >= 0, ev_v[np.clip(idx, 0, len(ev_v) - 1)], 0.0)
    out = np.maximum(out, 0.0)
    # BUG FIX (phat hien khi code, truoc khi co ket qua cuoi): cumsum dau phay dong de lai
    # can du ~8e-13 sau khi moi vi the da dong => 64.5% gio bi dem nham la "co vi the".
    # Notional nho nhat cua mot lenh that la 266.4 USDT => nguong 1e-6 la khong nhap nhang.
    out[out < 1e-6] = 0.0
    return out


def load_funding():
    f = pd.read_csv(FUNDING_CSV)
    ts = f.ts_ms.values.astype(np.int64)
    rate = f.rate.values.astype(float)
    o = np.argsort(ts)
    return ts[o], rate[o]


# ------------------------------------------------------- beta rolling CAUSAL
def rolling_beta(daily, nopen_day):
    """pre-reg muc 3: beta_roll(D) = he so goc OLS tren N=60 ngay lich KET THUC o D-1
    (chi dung d <= D-1), toi thieu 20 quan sat.

    SUA THIET KE (thuc hien TRUOC khi co bat ky ket qua gia thuyet nao — xem
    docs/RESULT_HEDGE_OVERLAY_A.md muc "minh bach"): dang pre-reg goc la OLS cua
    y = dPnL/Nopen tren x = r_b. Dang do ILL-POSED vi chia cho Nopen co the rat nho
    (ngay chi co 1 lenh mo 1 gio => Nopen ~ notional/24) => diem don bay gia tao.
    Chan doan (diag2, luat quyet dinh chot TRUOC khi chay): 1.42% so ngay co |beta|>10,
    vuot nguong 1% => chuyen sang dang TUONG DUONG nhung well-posed:
        dPnL(d) = a + b * (Nopen(d) * r_b(d)) + e
    b van DUNG la "beta tren mot don vi notional long" ma cong thuc hedge o pre-reg muc 4
    can (hedge_notional = b x Nopen), chi khac o trong so (WLS voi trong so Nopen^2) va
    khong con phep chia cho so nho. Ngay khong co vi the (Nopen=0 => z=0) van la quan sat
    hop le va duoc giu.
    """
    df = daily.copy()
    df["nopen"] = nopen_day.reindex(df.index).fillna(0.0).values
    df["dpnl"] = df["equity"].diff()
    with np.errstate(divide="ignore", invalid="ignore"):
        df["y"] = np.where(df["nopen"].values > 0, df["dpnl"].values / df["nopen"].values, np.nan)
    df["z"] = df["nopen"].values * df["r_b"].values
    days = df.index.values.astype("datetime64[ns]")
    y = df["dpnl"].values.astype(float)
    x = df["z"].values.astype(float)
    valid = np.isfinite(y) & np.isfinite(x)
    beta = np.zeros(len(df))
    nobs = np.zeros(len(df), dtype=int)
    lo_all = np.searchsorted(days, days - np.timedelta64(ROLL_DAYS, "D"), side="left")
    hi_all = np.searchsorted(days, days, side="left")          # loai bo chinh ngay D
    for i in range(len(df)):
        lo, hi = lo_all[i], hi_all[i]
        m = valid[lo:hi]
        n = int(m.sum())
        nobs[i] = n
        if n < MIN_OBS:
            continue
        yy, xx = y[lo:hi][m], x[lo:hi][m]
        vx = float(np.var(xx))
        if vx <= 0:
            continue
        beta[i] = float(np.cov(yy, xx, bias=True)[0, 1] / vx)   # = OLS slope co he so chan
    return pd.Series(beta, index=df.index), pd.Series(nobs, index=df.index), df


# --------------------------------------------------------------- hedge PnL
def eq_day_of(grid):
    """Nhan NGAY cua chuoi equity ma moc UTC `t` thuoc ve.

    Da kiem tren sim.out: moi ngay CHI co 1 ban ghi 'Update YYYYMMDD 07:00' (gio JVM GMT+7)
    = 00:00 UTC cung ngay. Vay equity(D) la anh chup tai 00:00 UTC ngay D, va r_s(D) phu
    UTC [D-1 00:00, D 00:00). Moc UTC trong khoang do thuoc ngay equity D => +1 ngay.
    """
    return pd.to_datetime(grid, unit="ms").floor("D") + pd.Timedelta(days=1)


def hedge_series(d, grid, px, nopen_grid, beta_day):
    local_day = eq_day_of(grid)
    b = beta_day.reindex(local_day).fillna(0.0).values
    hn = b * nopen_grid                                  # notional SHORT BTC tai moi moc
    nxt = np.empty_like(px)
    nxt[:-1] = px[1:]
    nxt[-1] = px[-1]
    price_pnl = -hn * (nxt / px - 1.0)                   # SHORT: lai khi BTC giam
    fts, frate = load_funding()
    j = np.searchsorted(fts, grid, side="left")          # settlement roi vao [t, t+1h)
    inside = (j < len(fts)) & (fts[np.clip(j, 0, len(fts) - 1)] < grid + HOUR_MS)
    rate_at = np.where(inside, frate[np.clip(j, 0, len(fts) - 1)], 0.0)
    funding_pnl = hn * rate_at                           # SHORT NHAN khi rate > 0 (Binance that)
    dhn = np.diff(hn, prepend=0.0)
    cost = COST_RATE * np.abs(dhn)
    cost[-1] += COST_RATE * abs(hn[-1])                  # dong chan hedge cuoi ky
    total = price_pnl + funding_pnl - cost
    return hn, price_pnl, funding_pnl, cost, total, local_day


# --------------------------- phan bo ve tung lenh (KHOA SAN o pre-reg muc 7)
def allocate(d, grid, hedge_pnl):
    """pro-rata theo notional_i x thoi luong chong lan_i / Sum_j(...) trong tung khoang 1h."""
    H = len(grid)
    W = np.zeros(H)
    per = []
    s, e, nt = d.s_ms.values, d.e_ms.values, d.notional.values
    for i in range(len(d)):
        i0 = max(0, int(np.searchsorted(grid, s[i], side="right")) - 1)
        i1 = int(np.searchsorted(grid, e[i], side="right")) - 1
        if i1 < i0 or i1 < 0 or i0 >= H:
            per.append((np.empty(0, dtype=int), np.empty(0)))
            continue
        i1 = min(i1, H - 1)
        idx = np.arange(i0, i1 + 1)
        ov = (np.minimum(e[i], grid[idx] + HOUR_MS) - np.maximum(s[i], grid[idx])) / HOUR_MS
        ov = np.clip(ov, 0.0, 1.0)
        w = nt[i] * ov
        W[idx] += w
        per.append((idx, w))
    good = W > 0
    last_good = np.maximum.accumulate(np.where(good, np.arange(H), -1))
    eff = np.zeros(H)
    m = last_good >= 0
    np.add.at(eff, last_good[m], hedge_pnl[m])
    unalloc = float(hedge_pnl[~m].sum())
    r = np.where(good, eff / np.where(good, W, 1.0), 0.0)
    share = np.array([float((w * r[idx]).sum()) if len(idx) else 0.0 for idx, w in per])
    return share, W, unalloc


# --------------------------------------------------------------- k_bar / n_eff
def k_bar(d):
    """Cach dem cua nbets_step3_crosssec.py muc 5.1: luoi 60 phut, so vi the giu dong thoi."""
    g = pd.date_range(d.t0.min().floor("D"), d.t1.max().ceil("D"), freq="60min")
    gv = g.values.astype("datetime64[ns]").astype("int64")
    e0 = d.t0.values.astype("datetime64[ns]").astype("int64")
    e1 = d.t1.values.astype("datetime64[ns]").astype("int64")
    cnt = (np.searchsorted(np.sort(e0), gv, "right") - np.searchsorted(np.sort(e1), gv, "right"))
    return float(cnt[cnt >= 1].mean()), float((cnt == 0).mean()), float(cnt.mean())


def icc_block(d, roi_col):
    gs = [v.values for _, v in d.groupby("cohort_day")[roi_col]]
    icc, J, N, k0 = icc_anova(gs)
    return {"icc": float(icc), "J": int(J), "N": int(N), "k0": float(k0)}


def neff(k, icc):
    i2 = max(icc, 0.0)
    return float(k / (1 + (k - 1) * i2)), (float(1.0 / i2) if i2 > 0 else float("inf"))


def beta_block(equity_series, label):
    """Dung DUNG phuong phap beta_decomp_t170.py (ols_hac, HAC lags=5) tren chuoi equity."""
    idx = equity_series.index
    target_ms = idx.values.astype("datetime64[ms]").astype(np.int64)
    btc = BD.btc_at_or_before(target_ms)
    df = pd.DataFrame({"equity": equity_series.values.astype(float), "btc": btc}, index=idx)
    df["r_s"] = np.log(df["equity"] / df["equity"].shift(1))
    df["r_b"] = np.log(df["btc"] / df["btc"].shift(1))
    full = df.dropna(subset=["r_s", "r_b"])
    res = BD.ols_hac(full["r_s"], full["r_b"])
    res["pct_beta_of_total"] = BD.pct_beta_of_total(res["beta"], float(full["r_b"].sum()),
                                                    float(full["r_s"].sum()))
    res["label"] = label
    return res, df


def verdict(icc0, icch, b0, bh, dd0, ddh, cagrh, ne0, neh):
    c1 = (icch <= 0.70 * icc0) and (icch < 0.15)
    c2 = abs(bh) <= 0.30 * abs(b0)
    c3 = (ddh >= 1.25 * dd0) and (cagrh > 0)
    c4 = neh >= 1.20 * ne0
    if c1 and c2 and c3 and c4:
        v = "TIN HIEU DUONG"
    elif (icch > 0.85 * icc0) or (ddh < 1.50 * dd0):
        v = "NULL"
    else:
        v = "KHONG KET LUAN DUOC (HON HOP)"
    return v, {"c1_icc": bool(c1), "c2_beta": bool(c2), "c3_risk": bool(c3), "c4_neff": bool(c4)}


def main():
    d = load_trades()
    log.info("T170: n_lenh=%d  window=%s..%s  sum_pnl=%.1f  mean_notional=%.1f",
             len(d), d.t0.min(), d.t1.max(), d.pnl.sum(), d.notional.mean())

    grid, px = hourly_grid()
    nopen_grid = sum_notional_on_grid(d, grid)
    local_day = eq_day_of(grid)          # ngay equity (UTC [D-1 00:00, D 00:00)) — xem eq_day_of
    nopen_day = pd.Series(nopen_grid, index=local_day).groupby(level=0).mean()
    log.info("luoi 1h: n=%d  Nopen mean=%.1f  max=%.1f  %%gio khong vi the=%.1f%%",
             len(grid), nopen_grid.mean(), nopen_grid.max(), 100.0 * (nopen_grid == 0).mean())

    daily = BD.daily_frame(TAG)
    daily = daily[(daily.index >= WIN_START) & (daily.index <= WIN_END)]
    # [TASK C 2026-09-20] BIEN THE MO TA THEM SAU KHI RESULT DA CONG BO, KHONG tham gia phan
    # quyet muc 9: HEDGE_BETA_CONST=1 dung MOT beta CO DINH = beta OLS TOAN KY in-sample
    # (KHONG causal, nhin ca tuong lai) tren dung dang well-posed dPnL = a + b*(Nopen*r_b).
    # Day la "can tren lac quan": mot beta biet truoc CA QUA KHU LAN TUONG LAI, khong the dung
    # live, chi de xem hedge "tot nhat co the" (khong nhieu do uoc luong rolling causal) co
    # giam duoc ICC hay khong.
    beta_const_mode = os.environ.get("HEDGE_BETA_CONST", "0") not in ("0", "", "false", "False")
    b_const = None
    if beta_const_mode:
        nopen_full = nopen_day.reindex(daily.index).fillna(0.0).values
        dpnl_full = daily["equity"].diff().values.astype(float)
        z_full = nopen_full * daily["r_b"].values.astype(float)
        mfull = np.isfinite(dpnl_full) & np.isfinite(z_full)
        vx_full = float(np.var(z_full[mfull]))
        b_const = float(np.cov(dpnl_full[mfull], z_full[mfull], bias=True)[0, 1] / vx_full) \
            if vx_full > 0 else 0.0
        log.info("*** BIEN THE MO TA (HEDGE_BETA_CONST, KHONG causal, can tren lac quan): "
                 "beta CO DINH toan ky in-sample = %+.6f (n=%d) ***", b_const, int(mfull.sum()))
        beta_day = pd.Series(b_const, index=daily.index)
        nobs_day = pd.Series(int(mfull.sum()), index=daily.index)
    else:
        beta_day, nobs_day, dbg = rolling_beta(daily, nopen_day)
    # SENSITIVITY MO TA (khong nam trong phan quyet muc 9, chay RIENG qua bien moi truong):
    # kep beta ve [-CLIP, +CLIP] de kiem xem ket luan co bi lai boi duoi |beta| lon hay khong.
    clip = float(os.environ.get("HEDGE_BETA_CLIP", "0"))
    if clip > 0:
        log.info("*** BIEN THE MO TA: beta_roll bi kep ve [-%.1f, +%.1f] ***", clip, clip)
        beta_day = beta_day.clip(-clip, clip)
    act = beta_day[beta_day != 0]
    log.info("beta_roll(N=%dd, min %d obs): %d/%d ngay CO hedge; mean=%.6f med=%.6f "
             "p05=%.6f p95=%.6f", ROLL_DAYS, MIN_OBS, len(act), len(beta_day),
             float(act.mean()) if len(act) else float("nan"),
             float(act.median()) if len(act) else float("nan"),
             float(act.quantile(.05)) if len(act) else float("nan"),
             float(act.quantile(.95)) if len(act) else float("nan"))

    hn, ppnl, fpnl, cost, hp, _ = hedge_series(d, grid, px, nopen_grid, beta_day)
    log.info("hedge notional: mean=%.1f max=%.1f | PnL gia=%.1f funding=%.1f cost=%.1f "
             "TONG=%.1f | turnover=%.0f", hn.mean(), np.abs(hn).max(), ppnl.sum(),
             fpnl.sum(), cost.sum(), hp.sum(), np.abs(np.diff(hn, prepend=0.0)).sum())

    share, W, unalloc = allocate(d, grid, hp)
    log.info("phan bo: sum(share)=%.6f  sum(hedge_pnl)=%.6f  unallocated=%.6f  sai so=%.2e",
             share.sum(), hp.sum(), unalloc, abs(share.sum() - (hp.sum() - unalloc)))
    d["hedge_share"] = share
    d["roih"] = (d.pnl.astype(float) + d.hedge_share) / d.notional

    # ---- (b) ICC + n_eff
    i0 = icc_block(d, "roi0")
    ih = icc_block(d, "roih")
    kb, frac0, kmean = k_bar(d)
    ne0, cap0 = neff(kb, i0["icc"])
    neh, caph = neff(kb, ih["icc"])
    log.info("ICC cohort=ngay: GOC=%+.4f (J=%d N=%d) -> HEDGED=%+.4f | k_bar=%.2f "
             "(%%gio trong=%.1f%%) | n_eff %.2f -> %.2f | tran 1/ICC %.2f -> %.2f",
             i0["icc"], i0["J"], i0["N"], ih["icc"], kb, 100 * frac0, ne0, neh, cap0, caph)

    # ---- MO TA (KHONG tham gia phan quyet muc 9): ICC theo cohort 72h / tuan
    icc_rob = {}
    e0ns = d.t0.values.astype("datetime64[ns]").astype("int64")
    NS = 10 ** 9
    for lab, key in (("72h", e0ns // (72 * 3600 * NS)), ("tuan", e0ns // (7 * 24 * 3600 * NS))):
        for nm, col in (("orig", "roi0"), ("hedged", "roih")):
            gs = [v.values for _, v in d.groupby(key)[col]]
            ic, _J, _N, _k0 = icc_anova(gs)
            icc_rob["%s|%s" % (lab, nm)] = float(ic)
    log.info("MO TA ICC cohort khac: %s", {k: round(v, 4) for k, v in icc_rob.items()})

    # ---- chuoi equity hedged
    hp_day = pd.Series(hp, index=local_day).groupby(level=0).sum()
    eq0 = daily["equity"]
    cum = hp_day.reindex(eq0.index).fillna(0.0).cumsum()
    eqh = eq0 + cum

    # ---- (a) beta / alpha
    b0, _ = beta_block(eq0, "T170_GOC")
    bh, _ = beta_block(eqh, "T170_HEDGED")
    log.info("BETA ngay GOC   : beta=%+.5f t_alpha=%+.3f r2=%.4f pct_beta=%.1f%% n=%d",
             b0["beta"], b0["t_alpha"], b0["r2"], b0["pct_beta_of_total"], b0["n"])
    log.info("BETA ngay HEDGED: beta=%+.5f t_alpha=%+.3f r2=%.4f pct_beta=%.1f%% n=%d",
             bh["beta"], bh["t_alpha"], bh["r2"], bh["pct_beta_of_total"], bh["n"])

    # ---- (c) CAGR / maxDD / UW
    m0, mh = dd_uw_cagr(eq0), dd_uw_cagr(eqh)
    log.info("GOC   : equity %.0f->%.0f CAGR=%.2f%% maxDD=%.2f%% UW=%d",
             m0["equity_start"], m0["equity_end"], m0["cagr"], m0["maxDD"], m0["uw"])
    log.info("HEDGED: equity %.0f->%.0f CAGR=%.2f%% maxDD=%.2f%% UW=%d",
             mh["equity_start"], mh["equity_end"], mh["cagr"], mh["maxDD"], mh["uw"])

    v, crit = verdict(i0["icc"], ih["icc"], b0["beta"], bh["beta"],
                      m0["maxDD"], mh["maxDD"], mh["cagr"], ne0, neh)
    log.info("############ PHAN QUYET (nguong khoa o PREREG muc 9): %s ############", v)
    log.info("  c1 ICC<=0.70*ICC0 va <0.15 : %s", crit["c1_icc"])
    log.info("  c2 |beta_h|<=0.30*|beta_0| : %s", crit["c2_beta"])
    log.info("  c3 maxDD>=1.25*DD0 & CAGR>0: %s", crit["c3_risk"])
    log.info("  c4 n_eff tang >=20%%        : %s", crit["c4_neff"])

    res = {
        "prereg": "docs/PREREG_HEDGE_OVERLAY_A.md (commit 03c037e)",
        "tag": TAG, "window": [str(WIN_START.date()), str(WIN_END.date())],
        "roll_days": ROLL_DAYS, "min_obs": MIN_OBS, "cost_rate": COST_RATE,
        "n_trades": int(len(d)),
        "hedge": {"notional_mean": float(hn.mean()), "notional_absmax": float(np.abs(hn).max()),
                  "pnl_price": float(ppnl.sum()), "pnl_funding": float(fpnl.sum()),
                  "cost": float(cost.sum()), "pnl_total": float(hp.sum()),
                  "turnover": float(np.abs(np.diff(hn, prepend=0.0)).sum()),
                  "unallocated": unalloc,
                  "beta_days_active": int(len(act)), "beta_days_total": int(len(beta_day)),
                  "beta_mean": float(act.mean()) if len(act) else None},
        "icc": {"orig": i0, "hedged": ih, "k_bar": kb, "frac_hours_flat": frac0,
                "n_eff_orig": ne0, "n_eff_hedged": neh, "cap_orig": cap0, "cap_hedged": caph,
                "note_c2b_history": 0.2468, "robustness_cohort": icc_rob},
        "beta_daily": {"orig": b0, "hedged": bh},
        "perf": {"orig": m0, "hedged": mh},
        "hard_by_year": {"orig": hard_by_year(eq0), "hedged": hard_by_year(eqh)},
        "verdict": v, "criteria": crit,
    }
    res["beta_clip_sensitivity"] = clip
    res["beta_const_mode"] = beta_const_mode
    res["beta_const_value"] = b_const
    suffix = ("_betaconst" if beta_const_mode else "") + ("_clip%g" % clip if clip > 0 else "")
    out = OUT_JSON if not suffix else OUT_JSON.replace(".json", suffix + ".json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(res, f, indent=2, default=str)
    log.info("wrote %s", out)


if __name__ == "__main__":
    main()
