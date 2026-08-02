# LEG1 EDGE: triple-barrier net-per-trade, selector (g008) vs base-rate (toan universe).
# TP=+3%, FLOOR=-70%, COST=0.8% round-trip. Horizon 72h & 24h. Edge = selector_net - base_net.
import numpy as np, pandas as pd

LAB = "/home/ubuntu/java/simulator/outputs/funding_label.csv"
G008 = "/home/ubuntu/claudedata/entry_universe_g008.csv"
TP = 0.03
FLOOR = -0.70
COST = 0.008
HS = ["72h", "24h"]

cols = ["tEpochMs", "symbol"]
for h in HS:
    cols += [f"maxFav_{h}", f"maxAdv_{h}", f"tHitFav_{h}", f"tHitAdv_{h}", f"retEnd_{h}", f"nBars_{h}"]

print("load label ...", flush=True)
lab = pd.read_csv(LAB, usecols=lambda c: c in cols)
print("label rows", len(lab), flush=True)

g = pd.read_csv(G008, usecols=["ts", "symbol"])
# g008 ts lech pha ~4' so voi luoi 15m cua label -> lam tron XUONG luoi 15m de join khop.
G15 = 15 * 60 * 1000
g["ts15"] = (g["ts"].astype("int64") // G15) * G15
sel = set(zip(g["ts15"], g["symbol"].astype(str)))
key = list(zip(lab["tEpochMs"].astype("int64"), lab["symbol"].astype(str)))
lab["is_sel"] = pd.Series(key).isin(sel).values
print("selector matched in label:", int(lab["is_sel"].sum()), "/ g008", len(g), flush=True)


def econ(df, h):
    fav = df[f"maxFav_{h}"].values
    adv = df[f"maxAdv_{h}"].values
    tf = df[f"tHitFav_{h}"].values
    ta = df[f"tHitAdv_{h}"].values
    ret = df[f"retEnd_{h}"].values
    ok = ~np.isnan(fav) & ~np.isnan(adv) & ~np.isnan(ret)
    fav, adv, tf, ta, ret = fav[ok], adv[ok], tf[ok], ta[ok], ret[ok]
    hit_tp = fav >= TP
    hit_fl = adv <= FLOOR
    tp_first = hit_tp & (~hit_fl | (tf < ta))
    out = np.where(tp_first, TP, np.where(hit_fl, FLOOR, np.clip(ret, -0.99, None)))
    net = out - COST
    return len(net), 100 * tp_first.mean(), 100 * hit_fl.mean(), float(np.mean(out)), float(np.mean(net))


for h in HS:
    print("\n===== HORIZON %s  (TP+3%% floor-70%% cost-0.8%%) =====" % h, flush=True)
    print("%-10s %9s %10s %8s %9s %9s" % ("pop", "n", "%TP-first", "%floor", "avgOut", "avgNET"), flush=True)
    for tag, df in [("BASE(all)", lab), ("SELECTOR", lab[lab.is_sel])]:
        n, tpr, flr, ao, an = econ(df, h)
        print("%-10s %9d %9.1f%% %7.1f%% %8.2f%% %8.2f%%" % (tag, n, tpr, flr, ao * 100, an * 100), flush=True)
    nb, _, _, _, anb = econ(lab, h)
    ns, _, _, _, ans = econ(lab[lab.is_sel], h)
    print("  => EDGE (selector - base) avgNET: %+.2f%%/trade" % ((ans - anb) * 100), flush=True)

print("\nDONE", flush=True)
