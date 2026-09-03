"""NBETS buoc 3: Cau 3 — hang doc lap theo chieu ngang (PREREG_NBETS section 5)."""
import logging, sys, json
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/ubuntu/nbets")
import nb_lib as N

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/nbets/step3.out", "w"),
                              logging.StreamHandler()])
L = logging.getLogger("s3")
SINGLE = ["C2b", "C2_g015", "N4_a8s175", "A6_ts96", "D1_full_ts", "A6_ts336",
          "R2_ts120", "R0_parity", "R2_ts240", "S3_ts168", "S4_ts720"]
NS = 10 ** 9


def trades(tag):
    p = pd.read_csv("%s/%s/storage/printDone.csv" % (N.B, tag))
    p = p[["sym", "start", "end", "pnl", "margin", "time_order"]].copy()
    p["t0"] = pd.to_datetime(p.start, format="%Y%m%d %H:%M", errors="coerce")
    p["t1"] = pd.to_datetime(p.end, format="%Y%m%d %H:%M", errors="coerce")
    p = p.dropna(subset=["t0", "t1"]).reset_index(drop=True)
    p["roi"] = p.pnl / p.margin
    p["e0"] = p.t0.values.astype("datetime64[ns]").astype("int64")
    p["e1"] = p.t1.values.astype("datetime64[ns]").astype("int64")
    return p


def icc_anova(groups):
    g = [np.asarray(v, float) for v in groups if len(v) >= 2]
    if len(g) < 2:
        return np.nan, 0, 0, np.nan
    ks = np.array([len(v) for v in g])
    Nn = ks.sum()
    J = len(g)
    gm = np.concatenate(g).mean()
    msb = sum(len(v) * (v.mean() - gm) ** 2 for v in g) / (J - 1)
    msw = sum(((v - v.mean()) ** 2).sum() for v in g) / (Nn - J)
    k0 = (Nn - (ks ** 2).sum() / Nn) / (J - 1)
    return (msb - msw) / (msb + (k0 - 1) * msw), J, int(Nn), k0


L.info("=== 5.1 CUNG GIU DONG THOI (luoi 60 phut, 20220101..20240630) ===")
grid = pd.date_range("2022-01-01", "2024-06-30", freq="60min")
gv = grid.values.astype("datetime64[ns]").astype("int64")
res, TR = {}, {}
for t in SINGLE:
    p = trades(t)
    TR[t] = p
    cnt = (np.searchsorted(np.sort(p.e0.values), gv, "right")
           - np.searchsorted(np.sort(p.e1.values), gv, "right"))
    nsym = p.groupby(p.t0.dt.floor("1D")).sym.nunique()
    res[t] = dict(n=len(p), mean=float(cnt.mean()), med=float(np.median(cnt)),
                  p90=float(np.percentile(cnt, 90)), mx=int(cnt.max()),
                  mean_pos=float(cnt[cnt >= 1].mean()), frac0=float((cnt == 0).mean()),
                  med_margin=float(p.margin.median()),
                  med_hold_h=float(p.time_order.median()),
                  p90_hold_h=float(np.percentile(p.time_order, 90)),
                  nsym_total=int(p.sym.nunique()))
    L.info("%-12s n=%4d mean=%5.2f med=%3.0f p90=%4.0f max=%3d mean|>=1=%5.2f "
           "frac0=%.3f med_margin=%7.1f nsym=%3d", t, len(p), cnt.mean(),
           np.median(cnt), np.percentile(cnt, 90), cnt.max(), cnt[cnt >= 1].mean(),
           (cnt == 0).mean(), p.margin.median(), p.sym.nunique())

L.info("\n=== 5.2 ICC trong cohort (theo thoi diem VAO) + so cuoc hieu dung ===")
L.info("%-12s %-6s %5s %6s %6s %9s %10s %9s", "run", "cohort", "J", "N", "k0",
       "ICC", "neff(kbar)", "neff(30)")
icc_out = {}
for t in SINGLE:
    p = TR[t]
    kb = res[t]["mean_pos"]
    keys = [("ngay", p.t0.dt.floor("1D").values),
            ("72h", p.e0.values // (72 * 3600 * NS)),
            ("tuan", p.e0.values // (7 * 24 * 3600 * NS))]
    for lab, key in keys:
        gs = [v.values for _, v in p.groupby(key).roi]
        icc, J, Nn, k0 = icc_anova(gs)
        i2 = max(icc, 0.0)
        ne = kb / (1 + (kb - 1) * i2)
        n30 = 30.0 / (1 + 29 * i2)
        icc_out["%s|%s" % (t, lab)] = dict(icc=float(icc), J=J, N=Nn, k0=float(k0),
                                           neff_kbar=float(ne), neff_30=float(n30))
        L.info("%-12s %-6s %5d %6d %6.2f %+9.4f %10.2f %9.2f", t, lab, J, Nn, k0,
               icc, ne, n30)


L.info("\n=== 5.3 so cuoc hieu dung TOAN CUC: n_eff = N^2*s2/Var(sum ROI) ===")
L.info("   (chuoi tong ROI theo NGAY RA LENH; Var(sum) tu block bootstrap)")
L.info("%-12s %5s %8s %8s %10s %10s", "run", "N", "L", "sd_sum", "n_eff_bets",
       "N/n_eff")
g3 = {}
for t in SINGLE:
    p = TR[t]
    day = p.t1.dt.floor("1D")
    ser = p.groupby(day).roi.sum()
    full = pd.date_range("2022-01-01", "2024-06-29", freq="1D")
    x = ser.reindex(full).fillna(0.0).values
    nn = len(x)
    s2 = p.roi.var(ddof=1)
    Nt = len(p)
    for bl in [3, 7, 10, 21]:
        st, nb = N.boot_starts(nn, bl, N.NREP, N.SEED)
        tot = N.boot_sum(x, bl, st, nb)
        v = tot.var(ddof=1)
        ne = Nt ** 2 * s2 / v if v > 0 else np.nan
        g3["%s|%d" % (t, bl)] = dict(n_eff=float(ne), sd_sum=float(np.sqrt(v)))
        L.info("%-12s %5d %8d %8.4f %10.2f %10.2f", t, Nt, bl, np.sqrt(v), ne,
               Nt / ne)

L.info("\n=== 5.4 THEM LENH CO TANG n_eff KHONG: log(sdCAGR) ~ log(N_lenh) ===")
LRs = {t: N.logret(t)[0] for t in SINGLE}
nD = len(LRs["C2b"])
tab = {}
for bl in [7, 21]:
    xs, ys = [], []
    for t in SINGLE:
        st, nb = N.boot_starts(nD, bl, N.NREP, N.SEED)
        c = np.exp(N.boot_sum(LRs[t], bl, st, nb) * 365.0 / nD) - 1.0
        sd = c.std(ddof=1)
        tab["%s|%d" % (t, bl)] = float(sd)
        xs.append(np.log(res[t]["n"]))
        ys.append(np.log(sd))
    xs, ys = np.array(xs), np.array(ys)
    b1, b0 = np.polyfit(xs, ys, 1)
    r = np.corrcoef(xs, ys)[0, 1]
    se = np.sqrt(((ys - (b0 + b1 * xs)) ** 2).sum() / (len(xs) - 2)
                 / ((xs - xs.mean()) ** 2).sum())
    L.info("  L=%2d  beta=%+.3f (se %.3f, CI95 [%+.3f,%+.3f])  r=%+.3f  "
           "(du doan: beta~0 neu thoi gian lich chi phoi; -0.5 neu so lenh chi phoi)",
           bl, b1, se, b1 - 1.96 * se, b1 + 1.96 * se, r)
    for t in SINGLE:
        L.info("      %-12s N=%4d sdCAGR=%.4f%% MDE80=%.3fpp", t, res[t]["n"],
               tab["%s|%d" % (t, bl)] * 100, N.Z80 * tab["%s|%d" % (t, bl)] * 100)

json.dump(dict(conc=res, icc=icc_out, glob=g3, sdcagr=tab),
          open("/home/ubuntu/nbets/step3.json", "w"), indent=1)
L.info("\nDONE step3")
