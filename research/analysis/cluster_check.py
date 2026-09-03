"""KIEM GIA THUYET LOAD-BEARING: toi da dong nhanh 'noi gate' voi ly do
"lenh THEM VAO bi don cum theo thoi gian trong regime xau". Chua bao gio do.
Neu SAI thi nhanh do mo lai. Do bang chinh printDone cua H1a (noi gate) vs C2b (goc)."""
import numpy as np, pandas as pd

B = "/home/ubuntu/java/devrun"
def load(d):
    df = pd.read_csv(f"{B}/{d}/storage/printDone.csv")
    df = df[df.level == "PREDICT_SYMBOL_TRADE"].copy()
    for c in ("margin", "pnl"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df.margin > 0]
    df["roi"] = df.pnl / df.margin
    df["s"] = pd.to_datetime(df.start, format="%Y%m%d %H:%M", errors="coerce")
    df["e"] = pd.to_datetime(df.end, format="%Y%m%d %H:%M", errors="coerce")
    return df.dropna(subset=["s"])

C2b, H1 = load("C2b"), load("H1a_mom006")
print("C2b n=%d  H1a n=%d  (them %d lenh)" % (len(C2b), len(H1), len(H1) - len(C2b)))

# lenh CHI H1a co = lenh "them vao" do noi gate
k = set(zip(C2b.sym, C2b.start))
extra = H1[~H1.set_index(["sym", "start"]).index.isin(k)].copy()
same = H1[H1.set_index(["sym", "start"]).index.isin(k)].copy()
print("lenh THEM VAO: n=%d  roi_tb=%+.4f  winrate=%.3f  pnl=%+.0f"
      % (len(extra), extra.roi.mean(), (extra.roi > 0).mean(), extra.pnl.sum()))
print("lenh TRUNG C2b: n=%d  roi_tb=%+.4f  winrate=%.3f  pnl=%+.0f"
      % (len(same), same.roi.mean(), (same.roi > 0).mean(), same.pnl.sum()))

print("\n=== 1. CHAT LUONG tung lenh them vao co kem khong ===")
print("   neu roi_tb cua 'them vao' ~ 'trung' => chat luong KHONG phai van de => cum moi la van de")

print("\n=== 2. DON CUM: phan phoi so lenh MOI theo ngay ===")
for nm, d in [("C2b", C2b), ("H1a tat ca", H1), ("H1a chi lenh THEM", extra)]:
    g = d.groupby(d.s.dt.date).size()
    full = g.reindex(pd.date_range(d.s.min().date(), d.s.max().date()).date, fill_value=0)
    print("   %-18s ngay co lenh=%4d/%4d  tb=%.2f  p95=%.0f  max=%3d  he so phan tan(var/mean)=%.2f"
          % (nm, (full > 0).sum(), len(full), full.mean(), full.quantile(.95), full.max(),
             full.var() / full.mean()))
print("   (Poisson ngau nhien => he so phan tan ~ 1. Cang lon cang don cum.)")

print("\n=== 3. Lenh them vao roi vao THANG nao ===")
extra["thang"] = extra.s.dt.to_period("M").astype(str)
C2b["thang"] = C2b.s.dt.to_period("M").astype(str)
t = pd.concat([C2b.groupby("thang").size().rename("C2b"),
               extra.groupby("thang").size().rename("them"),
               extra.groupby("thang").roi.mean().rename("roi_them"),
               extra.groupby("thang").pnl.sum().rename("pnl_them")], axis=1).fillna(0)
t["ti_le_them"] = (t["them"] / t.C2b.replace(0, np.nan)).round(2)
print(t.sort_values("them", ascending=False).head(14).round(4).to_string())

print("\n=== 4. So lenh dong thoi: co phinh khong ===")
for nm, d in [("C2b", C2b), ("H1a", H1)]:
    ev = pd.concat([pd.DataFrame({"t": d.s, "c": 1, "m": d.margin}),
                    pd.DataFrame({"t": d.e, "c": -1, "m": -d.margin})]).dropna().sort_values("t")
    ev["conc"] = ev.c.cumsum(); ev["mar"] = ev.m.cumsum()
    print("   %-5s conc: max=%3d p95=%3d trung vi=%2d | margin: max=%6.0f p95=%6.0f (von 35000)"
          % (nm, ev.conc.max(), np.percentile(ev.conc, 95), np.percentile(ev.conc, 50),
             ev.mar.max(), np.percentile(ev.mar, 95)))

print("\n=== 5. Lenh them vao co roi vao dung luc dang thua lo khong ===")
# equity tho theo thoi diem DONG lenh cua C2b
eq = C2b.dropna(subset=["e"]).sort_values("e")
eq["cum"] = eq.pnl.cumsum(); eq["peak"] = eq.cum.cummax(); eq["dd"] = eq.cum - eq.peak
dd_series = eq.set_index("e").dd
def dd_at(ts):
    i = dd_series.index.searchsorted(ts) - 1
    return dd_series.iloc[i] if i >= 0 else 0.0
extra["dd_luc_vao"] = [dd_at(x) for x in extra.s]
same["dd_luc_vao"] = [dd_at(x) for x in same.s]
print("   dd cua C2b luc VAO lenh:  lenh THEM tb=%+.0f trung vi=%+.0f | lenh TRUNG tb=%+.0f trung vi=%+.0f"
      % (extra.dd_luc_vao.mean(), extra.dd_luc_vao.median(),
         same.dd_luc_vao.mean(), same.dd_luc_vao.median()))
q = extra.dd_luc_vao.quantile([.1, .25, .5, .75, .9]).round(0).to_dict()
print("   phan vi dd luc vao cua lenh THEM:", q)
print("   (dd am nhieu = vao lenh dung luc dang thua lo => dung nghia 'don cum trong regime xau')")
