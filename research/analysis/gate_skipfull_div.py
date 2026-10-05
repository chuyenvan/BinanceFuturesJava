import re
import pandas as pd
O = "/home/ubuntu/kaggle_sim/out/%s/"
P = [("A1", "n700-a1"), ("S7", "gabl-seed7"), ("S13", "gsb-s13"), ("S21", "gsb-s21"), ("S99", "gsb-s99"),
     ("S123", "gsb-s123"), ("S777", "gsb-s777"), ("S2024", "gsb-s2024")]


def keyset(tag):
    d = pd.read_csv(O % tag + "storage/printDone.csv", on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    k = (d["start"].astype(str).str.strip() + "|" + d["sym"].astype(str).str.strip()).tolist()
    return set(k)


def qline(tag):
    t = open(O % tag + "logs/full.log", errors="ignore").read()
    m = re.search(r"GATE-RATIO on [^\n]*", t).group(0)
    return {a + "Q" + b: int(p) for a, b, p, s in re.findall(r"(\d{4})Q(\d):(\d+)/(\d+)", m) if a == "2022"}


for s, off in P:
    on = "gqsf-" + s.lower()
    a, b = keyset(off), keyset(on)
    diff = sorted((a ^ b))
    first = diff[0] if diff else None
    last = diff[-1] if diff else None
    print(s, "only_off", len(a - b), "only_on", len(b - a), "first_diff", first, "last_diff", last,
          "q22 off", qline(off), "on", qline(on))
