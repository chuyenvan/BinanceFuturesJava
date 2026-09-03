"""SU THAT GOC: S1 thang G015 trong sim la nho CHON COIN TOT HON, hay nho so lenh / thoi diem?
So sanh truc tiep printDone.csv cua cac lan chay DEV."""
import os, numpy as np, pandas as pd

B = "/home/ubuntu/java/devrun"
runs = [("C2_g015 (baseline G015)", "C2_g015"), ("C2_s1a4", "C2_s1a4"), ("C2_s1b2", "C2_s1b2"),
        ("C2_s1b4", "C2_s1b4"), ("C2a (S1)", "C2a"), ("C2b (S1, chot)", "C2b")]

print("%-26s %6s %9s %9s %9s %8s %9s %9s" %
      ("run", "n", "roi_tb", "roi_tv", "winrate", "margin", "pnl_tong", "pnl/lenh"))
out = {}
for name, d in runs:
    f = f"{B}/{d}/storage/printDone.csv"
    if not os.path.exists(f):
        print("%-26s (khong co)" % name); continue
    df = pd.read_csv(f)
    df = df[df.level == "PREDICT_SYMBOL_TRADE"].copy()
    for c in ["margin", "pnl"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df.margin > 0]
    df["roi"] = df.pnl / df.margin
    out[name] = df
    print("%-26s %6d %9.4f %9.4f %9.3f %8.0f %9.0f %9.2f"
          % (name, len(df), df.roi.mean(), df.roi.median(), (df.roi > 0).mean(),
             df.margin.mean(), df.pnl.sum(), df.pnl.mean()))

print("\n=== phan ra nguon chenh lech: C2b (S1) vs C2_g015 ===")
a = out.get("C2b (S1, chot)"); b = out.get("C2_g015 (baseline G015)")
if a is not None and b is not None:
    print("  so lenh        : S1=%d  G015=%d   (%+.1f%%)" % (len(a), len(b), 100*(len(a)/len(b)-1)))
    print("  pnl/lenh (USDT): S1=%.2f  G015=%.2f  (%+.1f%%)" % (a.pnl.mean(), b.pnl.mean(), 100*(a.pnl.mean()/b.pnl.mean()-1)))
    print("  roi/lenh       : S1=%.4f  G015=%.4f" % (a.roi.mean(), b.roi.mean()))
    print("  margin/lenh    : S1=%.0f  G015=%.0f" % (a.margin.mean(), b.margin.mean()))
    print("  pnl TONG       : S1=%.0f  G015=%.0f  (%+.0f)" % (a.pnl.sum(), b.pnl.sum(), a.pnl.sum()-b.pnl.sum()))
    print("  => neu pnl/lenh KHONG hon ma tong hon => loi tu SO LENH / SIZE, khong phai chon coin tot hon")
    # trung lap coin: hai selector chon giong nhau bao nhieu?
    ka = set(zip(a.sym, a.start)); kb = set(zip(b.sym, b.start))
    print("\n  lenh trung nhau (cung coin+cung gio vao): %d / %d cua S1 (%.1f%%)"
          % (len(ka & kb), len(ka), 100*len(ka & kb)/max(1, len(ka))))
    only_a = a[~a.set_index(["sym", "start"]).index.isin(kb)]
    only_b = b[~b.set_index(["sym", "start"]).index.isin(ka)]
    print("  lenh CHI S1 co  : n=%d  roi_tb=%+.4f  winrate=%.3f" % (len(only_a), only_a.roi.mean(), (only_a.roi>0).mean()))
    print("  lenh CHI G015 co: n=%d  roi_tb=%+.4f  winrate=%.3f" % (len(only_b), only_b.roi.mean(), (only_b.roi>0).mean()))
    print("  => day moi la phep so sanh CHON COIN dung nghia")
