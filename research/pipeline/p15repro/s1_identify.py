import numpy as np, pandas as pd, struct, os

PB = "/home/ubuntu/wfo_ds_x1_2021/pred.bin"
raw = open(PB, "rb").read()
n = struct.unpack(">i", raw[:4])[0]
arr = np.frombuffer(raw[4:4+n*16], dtype=np.dtype([("ts",">i8"),("p15",">f4"),("risk",">f4")])).astype([("ts","<i8"),("p15","<f4"),("risk","<f4")])
d = pd.DataFrame({"ts": arr["ts"], "pb": arr["p15"], "risk": arr["risk"]})
d["year"] = pd.to_datetime(d.ts, unit="ms").dt.year
print("pred.bin n=%d ts %s -> %s | p50 %.6f p99 %.6f max %.6f" % (
    n, pd.to_datetime(d.ts.min(),unit="ms"), pd.to_datetime(d.ts.max(),unit="ms"),
    np.percentile(d.pb,50), np.percentile(d.pb,99), d.pb.max()))
print("risk: min %.6f max %.6f" % (d.risk.min(), d.risk.max()))

cands = {
 "wfo_gate_pred.csv(b160a018)": "/home/ubuntu/claudedata/wfo_gate_pred.csv",
 "label_oldbasket(bdd2b16d)": "/home/ubuntu/claudedata/gate_ab_full/wfo_gate_pred_label_oldbasket.csv",
 "label_ret15m": "/home/ubuntu/claudedata/gate_ab_full/wfo_gate_pred_label_ret15m.csv",
 "label_ret60m": "/home/ubuntu/claudedata/gate_ab_full/wfo_gate_pred_label_ret60m.csv",
 "label_retall15m": "/home/ubuntu/claudedata/gate_ab_full2/wfo_gate_pred_label_retall15m.csv",
 "label_retall60m": "/home/ubuntu/claudedata/gate_ab_full2/wfo_gate_pred_label_retall60m.csv",
 "v4v5_label_ret15m": "/home/ubuntu/claudedata/wfo_gate_pred_v4v5_label_ret15m.csv",
 "v4v5_label_ret60m": "/home/ubuntu/claudedata/wfo_gate_pred_v4v5_label_ret60m.csv",
}
rows=[]
for name, p in cands.items():
    if not os.path.exists(p):
        print("MISSING", name); continue
    c = pd.read_csv(p).rename(columns={"timestamp":"ts","predReturn15M":"ref"})
    m = d.merge(c[["ts","ref"]], on="ts", how="inner")
    exact = float((np.abs(m.pb-m.ref) < 1e-7).mean())
    corr = float(np.corrcoef(m.pb, m.ref)[0,1])
    per = m.groupby("year").apply(lambda g: float(np.corrcoef(g.pb,g.ref)[0,1]) if len(g)>2 else np.nan).round(4).to_dict()
    mr = float(m.ref.abs().sum()/m.pb.abs().sum())
    print("\n== %s: n_csv=%d join=%d  exact(1e-7)=%.4f  corr=%.5f  meanratio=%.3f" % (name,len(c),len(m),exact,corr,mr))
    print("   per-year corr:", per)
    rows.append(dict(csv=name,n_csv=len(c),n_join=len(m),exact=exact,corr=corr,meanratio=mr))
pd.DataFrame(rows).to_csv("/tmp/pbrepro/step1.csv", index=False)
print("\nwrote /tmp/pbrepro/step1.csv")
