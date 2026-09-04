"""F3 - NGUON CUNG hay TANG QUYET DINH? Do OFFLINE (khong Java, khong train).
A  duong cong cung theo universe (log-log, year FE, o decile trong-nam) + MDE
A7 thong ke thu tu: top-8 co TOT LEN khi universe to hon khong (test quyet dinh)
G  chan dong thoi gian: gate thi truong (p15) la bien MUC TICK, khong phu thuoc universe
B  chat luong theo do sau rank tren POOL (n = 774k dong)
C  tran cung: co hoi tot moi gio, doi chieu 970 lenh that
D  khe K=8 (sim) vs K=5 (live)
Nguon: /home/ubuntu/ledger/cand_dev.parquet (ledger.py: pool = coin co label tai tick
15m ma gate thi truong MO p15>=0.008; gate_dyn_ok = p15 >= dyn_thr(score_g015)).
"""
import logging
import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
L = logging.getLogger("f3")
LED = "/home/ubuntu/ledger/cand_dev.parquet"
PD = "/home/ubuntu/java/devrun/C2b/storage/printDone.csv"
GOOD = 0.07
H = 3600000
pd.set_option("display.width", 260)


def ols(X, y):
    XtXi = np.linalg.pinv(X.T @ X)
    b = XtXi @ (X.T @ y)
    r = y - X @ b
    n = X.shape[0]
    dof = n - np.linalg.matrix_rank(X)
    se = np.sqrt(np.diag(((r @ r) / dof) * XtXi))
    r2 = 1.0 - (r @ r) / ((y - y.mean()) ** 2).sum()
    return b, se, r2, n, dof


def slope_line(tag, b, se, r2, n, dof, idx=1):
    tc = stats.t.ppf(0.975, dof)
    lo, hi = b[idx] - tc * se[idx], b[idx] + tc * se[idx]
    mde = 2.802 * se[idx]
    L.info("%-44s doc=%+.3f se=%.3f CI95=[%+.3f,%+.3f] t=%+.2f R2=%.3f n=%d MDE80=%.2f",
           tag, b[idx], se[idx], lo, hi, b[idx] / se[idx], r2, n, mde)


def load():
    D = pd.read_parquet(LED)
    L.info("=== 0. DU LIEU ===")
    L.info("rows=%d  dup(ts,sym)=%d", len(D), D.duplicated(["ts", "sym"]).sum())
    D["dt"] = pd.to_datetime(D.ts, unit="ms", utc=True)
    D["yr"] = D.dt.dt.year
    D["ym"] = D.dt.dt.strftime("%Y-%m")
    D["hr"] = (D.ts // H) * H
    D["good"] = D.maxFav_72h >= GOOD
    D["gp"] = D.good & D.gate_dyn_ok
    span = (D.ts.max() - D.ts.min()) / H + 1
    L.info("ts %s -> %s | tick15m=%d | gio-gate-mo=%d / %.0f gio lich = %.2f%% | coin=%d",
           D.dt.min(), D.dt.max(), D.ts.nunique(), D.hr.nunique(), span,
           100 * D.hr.nunique() / span, D.sym.nunique())
    L.info("score_g015 co = %.4f (2021 KHONG co G015)", D.score_g015.notna().mean())
    L.info("P(good = maxFav_72h>=%.2f) toan pool = %.4f  |  gate_dyn_ok = %.4f",
           GOOD, D.good.mean(), D.gate_dyn_ok.mean())
    L.info("CANH BAO: 'good' KHONG hiem - 60%% ung vien cham +7%%. Day la nguong ARM,")
    L.info("khong phai nguong THANG. E0_EXIT_CF: nhom chet la nhom khong bao gio chay.")
    return D


def hourly(D):
    """Dem theo COIN DISTINCT trong gio (khong dem lai coin xuat hien nhieu tick)."""
    g = D.groupby("hr")
    hh = pd.DataFrame({
        "U": g.sym.nunique(), "rows": g.sym.size(), "nticks": g.ts.nunique(),
        "npass": D[D.gate_dyn_ok].groupby("hr").sym.nunique(),
        "ngood": D[D.good].groupby("hr").sym.nunique(),
        "ngoodpass": D[D.gp].groupby("hr").sym.nunique()}).fillna(0)
    for c in ("npass", "ngood", "ngoodpass"):
        hh[c] = hh[c].astype(int)
    hh["yr"] = pd.to_datetime(hh.index, unit="ms", utc=True).year
    hh["ym"] = pd.to_datetime(hh.index, unit="ms", utc=True).strftime("%Y-%m")
    return hh


def sec_a(hh):
    L.info("")
    L.info("=== A. DUONG CONG CUNG THEO UNIVERSE ===")
    L.info("Don vi = GIO CO GATE MO. U/N_good/N_pass dem COIN DISTINCT trong gio.")
    m = hh.groupby("ym").agg(hours=("U", "size"), ticks=("nticks", "sum"),
                             U=("U", "mean"), Ngood=("ngood", "mean"),
                             Npass=("npass", "mean"), Ngoodpass=("ngoodpass", "mean"))
    m["yr"] = m.index.str[:4].astype(int)
    m["Pgood"] = m.Ngood / m.U
    L.info("\n%s", m.round(3).to_string())
    for name, s in (("full 2021-04..2024-06", m), ("DEV 2022-01..2024-06", m[m.yr >= 2022])):
        x = np.log(s.U.values)
        X = np.column_stack([np.ones(len(s)), x])
        slope_line(f"A1 log(Ngood/h)~log(U) [{name}]", *ols(X, np.log(s.Ngood.values)))
        slope_line(f"A3 log(P(good))~log(U) [{name}]", *ols(X, np.log(s.Pgood.values)))
    L.info("")
    L.info("--- A-confound: U co lan voi THOI GIAN khong ---")
    for y, s in m.groupby("yr"):
        L.info("nam %d n_thang=%2d U min=%.1f p50=%.1f max=%.1f spread/median=%.2f",
               y, len(s), s.U.min(), s.U.median(), s.U.max(),
               (s.U.max() - s.U.min()) / s.U.median())
    r = stats.spearmanr(np.arange(len(m)), m.U.values)
    L.info("spearman(U, thu tu thang) = %+.3f  p=%.2g  => U ~ THOI GIAN gan nhu hoan hao",
           r.statistic, r.pvalue)
    for name, s in (("full", m), ("2022+", m[m.yr >= 2022])):
        d = pd.get_dummies(s.yr, prefix="y", drop_first=True).astype(float)
        X = np.column_stack([np.ones(len(s)), np.log(s.U.values), d.values])
        slope_line(f"A4 log(Ngood/h)~log(U)+yearFE [{name}]", *ols(X, np.log(s.Ngood.values)))
    for y, s in m.groupby("yr"):
        if len(s) < 6:
            L.info("A5 within-year %d: n=%d qua nho => BO", y, len(s))
            continue
        X = np.column_stack([np.ones(len(s)), np.log(s.U.values)])
        slope_line(f"A5 within-year {y}", *ols(X, np.log(s.Ngood.values)))
    return m


def sec_a6(hh):
    L.info("")
    L.info("--- A6: o (nam x decile U theo GIO), bien thien U hoan toan TRONG-NAM ---")
    rows = []
    for y, s in hh.groupby("yr"):
        if len(s) < 100:
            L.info("nam %d chi %d gio => BO", y, len(s))
            continue
        q = pd.qcut(s.U.rank(method="first"), 10, labels=False)
        for k, c in s.groupby(q):
            rows.append(dict(yr=y, dec=int(k), hours=len(c), U=c.U.mean(),
                             Ngood=c.ngood.mean(), Pgood=c.ngood.sum() / c.U.sum()))
    C = pd.DataFrame(rows)
    L.info("\n%s", C.round(3).to_string(index=False))
    d = pd.get_dummies(C.yr, prefix="y", drop_first=True).astype(float)
    X = np.column_stack([np.ones(len(C)), np.log(C.U.values), d.values])
    slope_line("A6 log(Ngood/h)~log(U)+yearFE [o decile]", *ols(X, np.log(C.Ngood.values)))
    slope_line("A6b log(P(good))~log(U)+yearFE [o decile]", *ols(X, np.log(C.Pgood.values)))


def sec_gate(D):
    """G: gate_dyn_ok = p15 (MUC TICK) >= dyn_thr(score). Universe KHONG doi duoc p15."""
    L.info("")
    L.info("=== G. CHAN DONG THOI GIAN: gate thi truong la bien MUC TICK ===")
    t = D.groupby("ts").agg(U=("sym", "size"), p15=("p15", "mean"),
                            p15sd=("p15", "std"), npass=("gate_dyn_ok", "sum"),
                            nsc=("score_g015", "count"))
    L.info("p15 bien thien TRONG tick: sd tb = %.3g (0 => p15 la bien muc tick)",
           t.p15sd.fillna(0).mean())
    S = t[t.nsc > 0]
    L.info("tick co score: %d | co >=1 gate pass: %d (%.2f%%)",
           len(S), (S.npass > 0).sum(), 100 * (S.npass > 0).mean())
    S = S.copy()
    S["p15d"] = pd.qcut(S.p15, 10, labels=False, duplicates="drop")
    tb = S.groupby("p15d").agg(ticks=("U", "size"), p15=("p15", "mean"), U=("U", "mean"),
                               npass=("npass", "mean"), any_pass=("npass", lambda s: (s > 0).mean()))
    tb["pass_rate"] = S.groupby("p15d").apply(lambda s: s.npass.sum() / s.U.sum(),
                                              include_groups=False)
    L.info("theo decile p15:\n%s", tb.round(4).to_string())
    L.info("spearman(npass, p15)=%+.3f | spearman(npass, U)=%+.3f",
           stats.spearmanr(S.npass, S.p15).statistic,
           stats.spearmanr(S.npass, S.U).statistic)


def sec_a7(S):
    """A7 (test QUYET DINH): universe to hon co lam TOP-8 tot len khong?
    Neu score cua coin moi rut tu cung phan phoi thi thong ke thu tu phai cai thien.
    Do o muc TICK => khong can chuan hoa thoi gian; khu confound bang year FE."""
    L.info("")
    L.info("=== A7. THONG KE THU TU: top-8 co tot len khi U to hon? ===")
    t8 = S[S.rk <= 8]
    t = pd.DataFrame({
        "U": S.groupby("ts").sym.size(),
        "yr": S.groupby("ts").yr.first(),
        "g8": t8.groupby("ts").g1lite.mean(),
        "good8": t8.groupby("ts").good.mean(),
        "sc8": t8.groupby("ts").score_g015.mean(),
        "sc1": S[S.rk <= 1].groupby("ts").score_g015.mean()}).dropna()
    L.info("ticks=%d  U: min=%d p50=%d max=%d", len(t), t.U.min(), int(t.U.median()), t.U.max())
    for y, s in t.groupby("yr"):
        L.info("nam %d: n_tick=%4d U p10=%.0f p50=%.0f p90=%.0f", y, len(s),
               s.U.quantile(.1), s.U.median(), s.U.quantile(.9))
    rows = []
    for y, s in t.groupby("yr"):
        if len(s) < 100:
            continue
        q = pd.qcut(s.U.rank(method="first"), 10, labels=False)
        for k, c in s.groupby(q):
            rows.append(dict(yr=y, dec=int(k), ticks=len(c), U=c.U.mean(), g8=c.g8.mean(),
                             good8=c.good8.mean(), sc8=c.sc8.mean(), sc1=c.sc1.mean()))
    C = pd.DataFrame(rows)
    L.info("\n%s", C.round(4).to_string(index=False))
    d = pd.get_dummies(C.yr, prefix="y", drop_first=True).astype(float)
    X = np.column_stack([np.ones(len(C)), np.log(C.U.values), d.values])
    for col, lab in (("g8", "mean g1lite top8"), ("good8", "P(good) top8"),
                     ("sc8", "mean score top8 (thap=tot)"), ("sc1", "score rank1")):
        slope_line(f"A7 {lab} ~ log(U)+yearFE", *ols(X, C[col].values))
    L.info("Dau ky vong neu MO UNIVERSE co loi: g8 tang, good8 tang, sc8/sc1 GIAM.")


BINS = [(1, 2), (3, 5), (6, 8), (9, 16), (17, 32), (33, 10 ** 9)]


def bname(lo, hi):
    return f"{lo}-{'inf' if hi > 10 ** 8 else hi}"


def rank_pool(D):
    S = D[D.score_g015.notna()].copy()
    S["rk"] = S.groupby("ts").score_g015.rank(method="first")
    return S


def sec_b(S):
    L.info("")
    L.info("=== B. CHAT LUONG THEO DO SAU RANK (POOL) ===")
    L.info("rank trong tick theo score_g015 tang dan (thap=tot, ledger.py:55).")
    L.info("n=%d dong, %d tick (2022+; 2021 khong co G015)", len(S), S.ts.nunique())
    for lab, X in (("POOL", S), ("chi dong QUA GATE", S[S.gate_dyn_ok])):
        rows = []
        for lo, hi in BINS:
            b = X[(X.rk >= lo) & (X.rk <= hi)]
            if not len(b):
                continue
            g = b[b.good]
            rows.append(dict(bin=bname(lo, hi), n=len(b), P_good=b.good.mean(),
                             mean_g1lite=b.g1lite.mean(),
                             g1lite_win=g.g1lite.mean() if len(g) else np.nan,
                             med_g1lite_win=g.g1lite.median() if len(g) else np.nan,
                             g1lite_lose=b[~b.good].g1lite.mean(),
                             maxFav_win=g.maxFav_72h.mean() if len(g) else np.nan,
                             gate_ok=b.gate_dyn_ok.mean(), score=b.score_g015.mean()))
        L.info("[%s]\n%s", lab, pd.DataFrame(rows).round(5).to_string(index=False))
    L.info("--- B2: Welch t-test bin 1-2 vs cac bin sau ---")
    for col, cond in (("g1lite|good", S.good), ("good(0/1)", S.good == S.good)):
        a = S[(S.rk <= 2) & cond]
        av = (a.g1lite if col.startswith("g1") else a.good.astype(float)).values
        for lo, hi in BINS[1:]:
            b = S[(S.rk >= lo) & (S.rk <= hi) & cond]
            bv = (b.g1lite if col.startswith("g1") else b.good.astype(float)).values
            tt, p = stats.ttest_ind(av, bv, equal_var=False)
            L.info("%-11s 1-2=%.4f (n=%d) vs %-7s=%.4f (n=%d) d=%+.4f t=%+.1f p=%.2g",
                   col, av.mean(), len(av), bname(lo, hi), bv.mean(), len(bv),
                   bv.mean() - av.mean(), tt, p)


def sec_c(hh):
    L.info("")
    L.info("=== C. TRAN CUNG ===")
    L.info("Chi tinh tren %d GIO CO GATE MO (86.4%% gio lich khong co ung vien nao).", len(hh))
    q = [.1, .25, .5, .75, .9, .99]
    L.info("Ngood/gio (coin distinct):\n%s", hh.ngood.describe(percentiles=q).round(2).to_string())
    L.info("Ngood&gate/gio:\n%s", hh.ngoodpass.describe(percentiles=q).round(2).to_string())
    L.info("P(gio co >=1 good)=%.4f  >=8=%.4f | P(gio co >=1 good&gate)=%.4f  >=8=%.4f",
           (hh.ngood >= 1).mean(), (hh.ngood >= 8).mean(),
           (hh.ngoodpass >= 1).mean(), (hh.ngoodpass >= 8).mean())
    nz = hh[hh.ngoodpass > 0]
    L.info("Trong %d gio CO good&gate (%.2f%%): mean=%.2f median=%.1f max=%d",
           len(nz), 100 * len(nz) / len(hh), nz.ngoodpass.mean(),
           nz.ngoodpass.median(), nz.ngoodpass.max())
    by = hh.groupby("yr").agg(hours=("U", "size"), U=("U", "mean"), Ngood=("ngood", "mean"),
                              Ngood_med=("ngood", "median"), Npass=("npass", "mean"),
                              Ngoodpass=("ngoodpass", "mean"),
                              pct_hr_goodpass=("ngoodpass", lambda s: (s > 0).mean()))
    L.info("theo NAM:\n%s", by.round(3).to_string())
    hh2 = hh.copy()
    hh2["Ubin"] = pd.cut(hh2.U, [0, 100, 125, 150, 175, 200, 250, 10 ** 6])
    bu = hh2.groupby("Ubin", observed=True).agg(
        hours=("U", "size"), U=("U", "mean"), Ngood=("ngood", "mean"),
        Ngoodpass=("ngoodpass", "mean"), pct_hr_goodpass=("ngoodpass", lambda s: (s > 0).mean()))
    bu["Pgood"] = hh2.groupby("Ubin", observed=True).apply(
        lambda s: s.ngood.sum() / s.U.sum(), include_groups=False)
    L.info("theo BIN UNIVERSE:\n%s", bu.round(4).to_string())


def sec_c2(hh):
    L.info("")
    L.info("--- C2: doi chieu 970 lenh THAT (printDone C2b) ---")
    T = pd.read_csv(PD)
    T = T[T.start.notna()]
    st = pd.to_datetime(T.start, format="%Y%m%d %H:%M")
    en = pd.to_datetime(T.end, format="%Y%m%d %H:%M", errors="coerce")
    st_ms = (st.astype("int64") // 10 ** 6) - 7 * H   # printDone = gio VN
    en_ms = (en.astype("int64") // 10 ** 6) - 7 * H
    ent = pd.Series((st_ms // H) * H).value_counts().rename("entries")
    j = hh.join(ent, how="left")
    j["entries"] = j.entries.fillna(0)
    L.info("lenh=%d | SANITY %.3f entry-gio nam trong gio-gate-mo (gan 1.0 = TZ dung)",
           len(T), ent.index.isin(hh.index).mean())
    L.info("entries/gio-gate-mo mean=%.3f P(>=1)=%.4f tong-trong-cua-so=%d",
           j.entries.mean(), (j.entries >= 1).mean(), int(j.entries.sum()))
    L.info("=> CO HOI TOT BO LO / GIO-GATE-MO: %.2f (moi good) | %.2f (good & qua gate)",
           j.ngood.mean() - j.entries.mean(), j.ngoodpass.mean() - j.entries.mean())
    L.info("=> ti le CHIEM DUNG cung qua-gate: %.4f (=%d entry / %d coin-gio good&gate)",
           j.entries.sum() / max(j.ngoodpass.sum(), 1), int(j.entries.sum()),
           int(j.ngoodpass.sum()))
    hrs = np.arange(st_ms.min() // H, en_ms.max() // H + 1) * H
    occ = pd.Series(0, index=hrs)
    for a, b in zip(st_ms.values, en_ms.values):
        if b != b:
            continue
        occ.loc[(a // H) * H:(b // H) * H] += 1
    L.info("vi the dang giu (moi gio trong cua so lenh): mean=%.3f median=%.1f max=%d rong=%.1f%%",
           occ.mean(), occ.median(), occ.max(), 100 * (occ == 0).mean())
    o = occ.reindex(hh.index).dropna()
    L.info("vi the dang giu TRONG gio-gate-mo: mean=%.3f rong=%.1f%% (n=%d)",
           o.mean(), 100 * (o == 0).mean(), len(o))


def sec_d(S):
    L.info("")
    L.info("=== D. KHE K=8 (sim) vs K=5 (live) ===")
    for lab, X in (("toan pool", S), ("chi dong qua gate_dyn_ok", S[S.gate_dyn_ok])):
        n5 = int((X.rk <= 5).sum())
        n8 = int((X.rk <= 8).sum())
        g5 = int(((X.rk <= 5) & X.good).sum())
        g8 = int(((X.rk <= 8) & X.good).sum())
        s5 = X.loc[X.rk <= 5, "g1lite"].sum()
        s8 = X.loc[X.rk <= 8, "g1lite"].sum()
        L.info("[%s] slot top5=%d top8=%d (slot 6-8 = %.1f%% cua top8)",
               lab, n5, n8, 100 * (n8 - n5) / max(n8, 1))
        L.info("  good top5=%d top8=%d => MAT khi ha ve K=5: %d = %.2f%% cung good cua top8",
               g5, g8, g8 - g5, 100 * (g8 - g5) / max(g8, 1))
        L.info("  P(good): top5=%.4f rank6-8=%.4f top8=%.4f",
               g5 / max(n5, 1), (g8 - g5) / max(n8 - n5, 1), g8 / max(n8, 1))
        L.info("  tong g1lite: top5=%.1f top8=%.1f => rank6-8 = %.1f (%.1f%% cua top8)",
               s5, s8, s8 - s5, 100 * (s8 - s5) / max(abs(s8), 1e-9))
        L.info("  mean g1lite: top5=%.5f rank6-8=%.5f (chenh %.1f%%)",
               s5 / max(n5, 1), (s8 - s5) / max(n8 - n5, 1),
               100 * ((s8 - s5) / max(n8 - n5, 1)) / (s5 / max(n5, 1)) - 100)
    L.info("LUU Y: day la do LON cua khe, KHONG phai dau P&L. F1 da cho thay rank sau")
    L.info("hon lam Sharpe GIAM => khong the ket luan K=5 'mat tien' tu do nay.")


def sec_c3(D, hh):
    """C3: gio CO co hoi qua gate va gio CO entry co trung nhau khong?"""
    L.info("")
    L.info("--- C3: gio-co-hoi vs gio-vao-lenh ---")
    T = pd.read_csv(PD)
    T = T[T.start.notna()]
    st = pd.to_datetime(T.start, format="%Y%m%d %H:%M")
    st_ms = (st.astype("int64") // 10 ** 6) - 7 * H
    eh = set(((st_ms // H) * H).tolist())
    oh = set(hh.index[hh.ngoodpass > 0].tolist())
    ph = set(hh.index[hh.npass > 0].tolist())
    L.info("gio co >=1 gate pass = %d | co >=1 good&gate = %d | co entry = %d",
           len(ph), len(oh), len(eh))
    L.info("giao(entry, good&gate) = %d => %.1f%% gio-co-hoi CO entry, %.1f%% gio-entry co co-hoi",
           len(eh & oh), 100 * len(eh & oh) / max(len(oh), 1),
           100 * len(eh & oh) / max(len(eh), 1))
    L.info("giao(entry, gate-pass) = %d => %.1f%% gio-entry nam trong gio-co-gate-pass",
           len(eh & ph), 100 * len(eh & ph) / max(len(eh), 1))
    act = hh.loc[sorted(oh)]
    L.info("trong gio-co-hoi: mean npass=%.1f mean good&gate=%.1f (cap SELECTOR_RANK_TOPK=8/tick)",
           act.npass.mean(), act.ngoodpass.mean())
    t = D[D.gate_dyn_ok].groupby("ts").sym.size()
    L.info("gate pass / TICK (chi tick co >=1): mean=%.1f p50=%.0f p90=%.0f max=%d, P(>8)=%.3f",
           t.mean(), t.median(), t.quantile(.9), t.max(), (t > 8).mean())
    L.info("=> so slot bo lo trong 1 tick co co hoi = mean(min(npass,inf)) - 8 = %.1f", t.mean() - 8)

if __name__ == "__main__":
    D = load()
    hh = hourly(D)
    sec_a(hh)
    sec_a6(hh)
    sec_gate(D)
    S = rank_pool(D)
    sec_a7(S)
    sec_b(S)
    sec_c(hh)
    sec_c2(hh)
    sec_c3(D, hh)
    sec_d(S)
    L.info("DONE")
