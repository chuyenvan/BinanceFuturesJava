"""Dung buffer K24 tuong duong-native cho 242: K16 native (hang 1..16) + 8 record tong hop hang 17..24
(r16 * rho_k, rho_k do tren K24 native sau 14:57) + K24 native sau switch. Khong dung record Oracle."""
import sys, glob, logging, numpy as np, pandas as pd
from grr_lib import load, q_of, ms, f
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("hyb")
t16, r16, _ = load("b242_k16.bin")
tc, rc, _ = load("bc3b.bin")
tl, rl, _ = load("b242.bin")
key_c = set(zip(tc.tolist(), np.float32(rc).tolist()))
nat = np.array([(a, b) not in key_c for a, b in zip(tl.tolist(), np.float32(rl).tolist())])
T_nat = tl[nat].min()
log.info("b242: %d rec, native %d, native tu %s; record sau T_nat ma KHONG native: %d", len(tl), nat.sum(), f(T_nat), (~nat & (tl >= T_nat)).sum())
log.info("K16 native %s..%s n=%d", f(t16.min()), f(t16.max()), len(t16))
# rho_k tu K24 native: theo phut, r sap giam, chia cho r hang 16
N = pd.DataFrame({"m": tl[nat] // 60000, "r": rl[nat]})
rows = []
for m, g in N.groupby("m"):
    x = np.sort(g.r.values)[::-1]
    if len(x) == 24: rows.append(x / x[15])
R = np.array(rows); rho = np.median(R[:, 16:], axis=0)
log.info("phut K24 native du 24: %d ; rho_17..24 = %s ; p5 hang24 %.3f p95 %.3f", len(R), " ".join("%.3f" % v for v in rho), np.quantile(R[:, 23], .05), np.quantile(R[:, 23], .95))
log.info("don dieu trong phut: max(r hang17..24 / r hang16) = %.3f (phai <=1)", R[:, 16:].max())
# K16 native: so record/phut
K = pd.DataFrame({"t": t16, "r": r16}); K["m"] = K.t // 60000
cnt = K.groupby("m").size(); log.info("K16 rec/phut: %s", cnt.value_counts().head(5).to_dict())
# gap K16 end -> T_nat: lap tu sel_dump (hang 1..16) r = kappa * p15/gate, kappa hieu chinh tren gio cuoi K16
S = pd.read_parquet("sel.parquet") if glob.glob("sel.parquet") else None
syn_t, syn_r = [], []
if S is not None:
    S = S.copy(); S["pg"] = S.p15 / S.gateValue
    ov = S[(S.m >= (t16.max() // 60000) - 120) & (S.m <= t16.max() // 60000) & (S["rank"] <= 16)]
    kap = []
    for m, g in ov.groupby("m"):
        x = np.sort(K.r[K.m == m].values)[::-1]; y = np.sort(g.pg.values)[::-1]
        if len(x) == len(y) == 16: kap.append(np.median(x / y))
    kap = np.array(kap); kappa = float(np.median(kap)) if len(kap) else float("nan")
    log.info("kappa (r/(p15/gate)) tren %d phut chong: med %.6f p5 %.6f p95 %.6f", len(kap), kappa, *(np.quantile(kap, [.05, .95]) if len(kap) else [0, 0]))
    gap = S[(S.m > t16.max() // 60000) & (S.m < T_nat // 60000) & (S["rank"] <= 16)]
    log.info("gap %s..%s: %d phut tu sel_dump; p15 max %.5f", f(t16.max()), f(T_nat), gap.m.nunique(), gap.p15.max() if len(gap) else -1)
    for m, g in gap.groupby("m"):
        x = np.sort(g.pg.values * kappa)[::-1]
        for v in x: syn_t.append(int(g.ts.iloc[0])); syn_r.append(v)
G = pd.DataFrame({"t": syn_t, "r": syn_r}); G["m"] = G.t // 60000 if len(G) else []
base = pd.concat([K[["t", "r", "m"]], G[["t", "r", "m"]]], ignore_index=True)
# them 8 record tong hop / phut (chi phut du 16 record)
add_t, add_r = [], []
for m, g in base.groupby("m"):
    x = np.sort(g.r.values)[::-1]
    if len(x) == 16:
        for v in rho: add_t.append(int(g.t.iloc[0])); add_r.append(float(x[15] * v))
H = pd.concat([base[["t", "r"]], pd.DataFrame({"t": add_t, "r": add_r})], ignore_index=True)
H = H[H.t < T_nat].sort_values("t", kind="stable")
H.to_csv("hyb_base_lt_Tnat.csv", index=False)
log.info("hyb base (< T_nat): n=%d %s..%s; T_nat=%d", len(H), f(H.t.min()), f(H.t.max()), T_nat)
full = np.concatenate([H.r.values, rl[nat]])
log.info("q hyb (base + native) = %.5f n=%d | q hien tai 242 = %.5f | q K16 native = %.5f", q_of(full), len(full), q_of(rl), q_of(r16))
top = np.argsort(-H.r.values)[:16]
log.info("top16 hyb: %s", "; ".join("%s %.5f" % (f(H.t.values[j]), H.r.values[j]) for j in top))
# do nhay: cung tap nhung chi tu 10-08 14:49 (nhu c3b)
w = H.t.values >= ms("10-08 14:49")
log.info("q hyb neu chi tu 10-08 14:49 = %.5f", q_of(np.concatenate([H.r.values[w], rl[nat]])))
open("T_nat.txt", "w").write(str(int(T_nat)))
