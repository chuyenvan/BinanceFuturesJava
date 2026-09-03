"""CAU HOI QUYET DINH: he co san feature nao noi duoc "luc nay la regime xau" khong,
ngoai p15? BR da chung minh khong co che phoi nhiem nao cuu duoc DD cua viec noi gate;
cai thieu la TIN HIEU REGIME. Ma feat_v2 co 40 cot thi TAT CA deu o muc COIN.

Cach do: gop ve MUC TICK.
  y_tick = g1lite trung binh cua top-8 theo p_g015 tai tick do (= cai he thuc su bat duoc)
  x      = p15 (dau vao thi truong DUY NHAT hien nay) + cac dai luong GOP tu feature coin
           (trung vi, do rong, do phan tan) — nhung dai luong nay chua tung duoc dung.
Neu cac dai luong gop KHONG them thong tin ngoai p15 => du lieu hien co het dat,
   phai dau tu NGUON DU LIEU MOI. Neu CO => con dat, dang mot vong feature.
Do OOS theo nam de khong tu lua."""
import numpy as np, pandas as pd
from scipy.stats import spearmanr

H = 3600000
AGG = ["vol_7d", "ret_7d", "ret_3d", "dd_7d", "rs_btc_7d", "fund_last", "oi_delta24h",
       "ls_global", "taker_buy", "vol_ratio"]

C = pd.read_parquet("/home/ubuntu/ledger/cand_dev3.parquet",
                    columns=["ts", "sym", "p15", "p_g015", "g1lite"])
C = C[C.g1lite.notna() & C.p_g015.notna()]
print("ledger v3:", C.shape, "ticks", C.ts.nunique())

# y_tick = g1lite TB cua top-8 theo p_g015 (cao = tu tin)
C["rk"] = C.groupby("ts").p_g015.rank(ascending=False, method="first")
Y = C[C.rk <= 8].groupby("ts").agg(y=("g1lite", "mean"), n=("g1lite", "size"),
                                   p15=("p15", "first")).reset_index()
Ypool = C.groupby("ts").g1lite.median().rename("y_pool")
Y = Y.merge(Ypool, on="ts")
Y = Y[Y.n >= 5]
Y["yr"] = pd.to_datetime(Y.ts, unit="ms").dt.year
print("ticks dung duoc:", len(Y), "| y TB theo nam:",
      Y.groupby("yr").y.mean().round(4).to_dict())

# --- dai luong GOP tu feature coin, theo GIO ---
F = pd.read_parquet("/home/ubuntu/featv2/feat_v2.parquet", columns=["ts", "sym"] + AGG)
g = F.groupby("ts")
A = pd.DataFrame({"ts_h": g.size().index})
A = A.set_index("ts_h")
for c in AGG:
    A[f"med_{c}"] = g[c].median()
    A[f"std_{c}"] = g[c].std()
A["breadth_ret7"] = g.ret_7d.apply(lambda s: (s > 0).mean())
A["breadth_dd7"] = g.dd_7d.apply(lambda s: (s > -0.10).mean())
A["n_coin"] = g.size()
A = A.reset_index()
del F, g
print("dai luong gop:", A.shape)

Y["ts_h"] = (Y.ts // H) * H
D = Y.merge(A, left_on="ts_h", right_on="ts_h", how="left")
XCOLS = [c for c in D.columns if c.startswith(("med_", "std_", "breadth_", "n_coin"))]
D = D.dropna(subset=["y", "p15"])
print("sau join:", D.shape, "| do phu dai luong gop: %.3f" % D[XCOLS[0]].notna().mean())

print("\n=== 1. Tuong quan tung dai luong voi y_tick (top8 g1lite), TOAN BO va TUNG NAM ===")
print("%-22s %8s %8s %8s %8s  %s" % ("bien", "all", "2022", "2023", "2024", "dau nhat quan?"))
rows = []
for c in ["p15"] + XCOLS:
    s = D[[c, "y", "yr"]].dropna()
    if len(s) < 1000: continue
    a = spearmanr(s[c], s.y).correlation
    per = {}
    for yv, gy in s.groupby("yr"):
        per[int(yv)] = spearmanr(gy[c], gy.y).correlation if len(gy) > 300 else np.nan
    v = [per.get(y, np.nan) for y in (2022, 2023, 2024)]
    cons = "CO" if np.all(np.sign([x for x in v if x == x]) == np.sign(v[0])) else "khong"
    rows.append((c, a, v, cons))
for c, a, v, cons in sorted(rows, key=lambda r: -abs(r[1])):
    print("%-22s %+8.4f %+8.4f %+8.4f %+8.4f  %s" % (c, a, v[0], v[1], v[2], cons))

print("\n=== 2. CAU HOI CHINH: gop them co du bao duoc gi NGOAI p15 khong? (OOS theo nam) ===")
import xgboost as xgb
def oos(cols, tag):
    out = []
    for test_yr in (2023, 2024):
        tr = D[D.yr < test_yr]; te = D[D.yr == test_yr]
        if len(tr) < 2000 or len(te) < 300: continue
        m = xgb.XGBRegressor(n_estimators=200, max_depth=3, learning_rate=0.05,
                             subsample=0.8, colsample_bytree=0.8, min_child_weight=50,
                             tree_method="hist", random_state=42, n_jobs=4)
        m.fit(tr[cols], tr.y)
        p = m.predict(te[cols])
        out.append((test_yr, spearmanr(p, te.y).correlation, len(te)))
    for yv, r, n in out:
        print("   %-28s test %d  rho_OOS=%+.4f  n=%d" % (tag, yv, r, n))
    return np.mean([r for _, r, _ in out]) if out else np.nan

a = oos(["p15"], "CHI p15")
b = oos(["p15"] + XCOLS, "p15 + dai luong gop")
print("   => rho_OOS trung binh: chi p15 = %+.4f | them gop = %+.4f | CHENH = %+.4f" % (a, b, b - a))
print("   (chenh <= 0.02 => du lieu hien co HET DAT cho tin hieu regime)")

print("\n=== 3. 2022 co that su khac biet o cac dai luong nay khong ===")
print(D.groupby("yr")[["p15", "med_vol_7d", "breadth_ret7", "med_rs_btc_7d", "med_fund_last", "y"]]
      .median().round(4).to_string())
