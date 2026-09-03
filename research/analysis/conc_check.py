"""NUMBER_ORDER_BUDGET=50 nhung MAX_CONCURRENT=40 -> ve ly thuyet 20% von KHONG BAO GIO duoc trien khai.
Nhung dieu do chi co y nghia NEU so lenh dong thoi thuc su cham tran. Do bang printDone.csv."""
import pandas as pd, numpy as np

df = pd.read_csv("/home/ubuntu/java/devrun/C2b/storage/printDone.csv")
df["s"] = pd.to_datetime(df.start, format="%Y%m%d %H:%M", errors="coerce")
df["e"] = pd.to_datetime(df.end,   format="%Y%m%d %H:%M", errors="coerce")
df["margin"] = pd.to_numeric(df.margin, errors="coerce")
df = df.dropna(subset=["s", "e", "margin"])
print("n lenh:", len(df), "| tu", df.s.min(), "den", df.e.max())

ev = pd.concat([pd.DataFrame({"t": df.s, "d": 1, "m": df.margin}),
                pd.DataFrame({"t": df.e, "d": -1, "m": -df.margin})]).sort_values("t")
ev["conc"] = ev.d.cumsum()
ev["mar"] = ev.m.cumsum()
print("\nso lenh dong thoi:  max=%d  p99=%.0f  p95=%.0f  p50=%.0f  trung binh=%.1f"
      % (ev.conc.max(), np.percentile(ev.conc, 99), np.percentile(ev.conc, 95),
         np.percentile(ev.conc, 50), ev.conc.mean()))
print("margin dang chay:   max=%.0f  p95=%.0f  p50=%.0f   (von goc 35000)"
      % (ev.mar.max(), np.percentile(ev.mar, 95), np.percentile(ev.mar, 50)))
print("=> ti le von trien khai: max=%.1f%%  p95=%.1f%%  trung vi=%.1f%%"
      % (100 * ev.mar.max() / 35000, 100 * np.percentile(ev.mar, 95) / 35000,
         100 * np.percentile(ev.mar, 50) / 35000))
n40 = (ev.conc >= 40).mean() * 100
n50 = (ev.conc >= 50).mean() * 100
print("\nti le thoi diem cham tran MAX_CONCURRENT=40: %.2f%%   (>=50: %.2f%%)" % (n40, n50))
print("size trung binh/lenh: %.0f USDT  (BASE_BUDGET ly thuyet = 35000/50 = 700)" % df.margin.mean())
print("size min/max: %.0f / %.0f" % (df.margin.min(), df.margin.max()))
