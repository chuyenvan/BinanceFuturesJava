#!/usr/bin/env python3
"""ERRATA3 E11a - ca TONG HOP (CHI tu fixture dev 10-30): symbol cua cum co nhan ARM_CUNG_NEN vao lai top-K NGAY phut sau khi
REF-nhip thoat. Dung fixture tam (symlink fixture dev, sua 2 file):
  - klines: nen phut t+1' cua symbol: O := max(O, 1.002*SL) (REF-nen KHONG thoat tai mo cua => cu "dang giu" qua quyet dinh
    phut t neu giu theo REF-nen);
  - sel: them 1 dong DAU phut quyet dinh b = t (thoat REF-nhip o nhip j>=1 cua phut t => jar trong tu quyet dinh b = t)
    key nho nhat (hang 1), gateValue 0.01, p15 0.5 (qua cong).
Chay REF moi (HEAD) va REF cu (1302fd81, giu theo REF-nen) tren cung fixture tam (khong --fills: C_eff = C3_CAPITAL).
Ky vong: REF moi SUBMITTED symbol o b; REF cu KHONG (coi dang giu). In DUNG/SAI.
argv: --fx DIR(dev) --env FILE --work DIR --old-ref FILE
"""
import argparse, csv, gzip, json, os, shutil, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("--fx", required=True)
ap.add_argument("--env", required=True)
ap.add_argument("--work", required=True)
ap.add_argument("--old-ref", required=True)
a = ap.parse_args()
T = os.path.dirname(os.path.abspath(__file__))
MIN = 60000
man = json.load(open(a.fx + "/manifest.json"))
assert man["START"] != 1793836800000, "CAM fixture 11-05"
os.makedirs(a.work, exist_ok=True)


def ref(script, fx, out):
    os.makedirs(out, exist_ok=True)
    r = subprocess.run([sys.executable, script, "--fx", fx, "--env", a.env, "--out", out, "--venue", "FAKE", "--capital", "10000",
                        "--flags", "on"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return list(csv.DictReader(open(out + "/ref_clusters.csv"))), list(csv.DictReader(open(out + "/ref_legs.csv")))


# 1. REF moi tren fixture dev goc: chon cum co nhan, giai phong o nhip j>=1 (phut t)
cl, _ = ref(T + "/ref_v12.py", a.fx, a.work + "/base")
cand = [c for c in cl if c["giai_phong_nhip"] and int(c["giai_phong_nhip"].split(":")[1]) >= 1]
if not cand:
    cand = [c for c in cl if c["nhip_label"] == "1" and c["nhip_k"] not in ("", "0")]
assert cand, "khong co cum co nhan thoat nhip j>=1"
c = cand[0]
sym, t, sl = c["symbol"], int(c["nhip_exit_bar"]), float(c["nhip_sl"] or c["sl"])
print("cum", sym, c["b0"], "REF-nhip thoat phut", t, "nhip", c["nhip_k"], "SL", sl, "REF-nen thoat", c["exit_bar"], "at_open", c["at_open"])
# 2. fixture tam
fx2 = a.work + "/fx_syn"
shutil.rmtree(fx2, ignore_errors=True)
os.makedirs(fx2)
for f in os.listdir(a.fx):
    if f not in ("klines.csv.gz", "sel.csv.gz"):
        os.symlink(os.path.join(a.fx, f), os.path.join(fx2, f))
with gzip.open(a.fx + "/klines.csv.gz", "rt") as fh, gzip.open(fx2 + "/klines.csv.gz", "wt") as out:
    r, w = csv.reader(fh), csv.writer(out, lineterminator="\n")
    w.writerow(next(r))
    nmod = 0
    for x in r:
        if x[0] == sym and int(x[1]) == t + MIN:
            o = max(float(x[2]), sl * 1.002)
            x[2] = repr(o)
            x[3] = repr(max(float(x[3]), o))
            nmod += 1
        w.writerow(x)
assert nmod == 1
b = t
with gzip.open(a.fx + "/sel.csv.gz", "rt") as fh:
    r = csv.reader(fh)
    head = next(r)
    rows = list(r)
keys = [float(x[2]) for x in rows if int(x[0]) == b]
ins = [str(b), sym, repr((min(keys) if keys else 0.0) - 1.0), "1", "0.01", "0.5"]
pos = next((i for i, x in enumerate(rows) if int(x[0]) == b), None)
rows = (rows[:pos] + [ins] + rows[pos:]) if pos is not None else sorted(rows + [ins], key=lambda z: int(z[0]))
with gzip.open(fx2 + "/sel.csv.gz", "wt") as out:
    w = csv.writer(out, lineterminator="\n")
    w.writerow(head)
    w.writerows(rows)
# 3. REF moi + REF cu tren fixture tam
_, lnew = ref(T + "/ref_v12.py", fx2, a.work + "/new")
_, lold = ref(a.old_ref, fx2, a.work + "/old")
pick = lambda L: [(x["level"], x["outcome"]) for x in L if x["symbol"] == sym and int(x["decision_ts"]) == b]  # noqa: E731
pn, po = pick(lnew), pick(lold)
okn = ("PREDICT_SYMBOL_TRADE", "SUBMITTED") in pn
oko = ("PREDICT_SYMBOL_TRADE", "SUBMITTED") not in po
print("quyet dinh b=%d %s: REF moi %s | REF cu (giu theo REF-nen) %s" % (b, sym, pn or "(khong leg)", po or "(khong leg: coi dang giu)"))
print("E11a REF moi vao lai ngay phut sau: %s ; REF cu giu them (minh hoa loi cu): %s" % ("DUNG" if okn else "SAI", "DUNG" if oko else "SAI"))
sys.exit(0 if okn and oko else 1)
