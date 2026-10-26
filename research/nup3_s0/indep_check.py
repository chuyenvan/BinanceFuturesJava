#!/usr/bin/env python3
"""NUP3-S0 kiem DOC LAP (chi csv/datetime, KHONG import s0/pipeline): seed a1 DEV, W_book + W_quiet.
Brute force: cum = (sym, end); t0 = min start; match greedy +-60s; U = sum notional leg B0 (start < t <= end) / (35000 + sum pnl leg B0 end < t).
So voi docs/result/nup3_s0/groups_by_seed.csv."""
import csv
import datetime as dt
import sys

KS = "/home/ubuntu/kaggle_sim/out/%s/storage/printDone.csv"
G = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/nup3_s0/groups_by_seed.csv"


def P(s):
    return dt.datetime.strptime(s.strip(), "%Y%m%d %H:%M")


def legs(tag):
    out = []
    with open(KS % tag, newline="") as f:
        rd = csv.reader(f)
        h = [c.strip() for c in next(rd)]
        ix = {c: i for i, c in enumerate(h)}
        for r in rd:
            q, e, p = float(r[ix["quantity"]]), float(r[ix["entry"]]), float(r[ix["pnl"]])
            out.append((r[ix["sym"]].strip(), P(r[ix["start"]]), P(r[ix["end"]]), p, q * e))
    return out


def clus(L):
    g = {}
    for s, a, b, p, n in L:
        k = (s, b)
        if k not in g:
            g[k] = [s, a, b, 0.0, 0.0]
        g[k][1] = min(g[k][1], a)
        g[k][3] += p
        g[k][4] += n
    return sorted(g.values(), key=lambda x: (x[1], x[0], x[2]))


A0, B0 = dt.datetime(2022, 1, 1), dt.datetime(2026, 1, 1)
la, lb = legs("nup-a2-a1"), legs("tsx-x14-a1")
ca, cb = clus(la), clus(lb)
A = [c for c in ca if A0 <= c[1] < B0]
B = [c for c in cb if A0 <= c[1] < B0]
used = [False] * len(B)
extra = []
for c in A:
    best, bd = None, 61
    for j, d in enumerate(B):
        if used[j] or d[0] != c[0]:
            continue
        x = abs((d[1] - c[1]).total_seconds())
        if x < bd:
            bd, best = x, j
    if best is not None and bd <= 60:
        used[best] = True
    else:
        extra.append(c)
print("a2_cl", len(A), "b0_cl", len(B), "extra", len(extra), "common", len(A) - len(extra))
res = {}
for c in extra:
    t = c[1]
    on = sum(n for s, a, b, p, n in lb if a < t <= b)
    eq = 35000.0 + sum(p for s, a, b, p, n in lb if b < t)
    book = on / eq >= 0.20
    quiet_in = any(t - dt.timedelta(hours=24) <= d[1] < t for d in cb)
    st = c[3] - 0.002 * c[4]
    for per in ("DEV_T", str(t.year)):
        for W, fl in (("W_book", book), ("W_quiet", quiet_in)):
            k = (per, W, "TRONG" if fl else "NGOAI")
            r = res.setdefault(k, [0, 0.0])
            r[0] += 1
            r[1] += st
ok = True
with open(G, newline="") as f:
    for r in csv.DictReader(f):
        if r["phase"] != "DEV" or r["seed"] != "a1" or r["W"] not in ("W_book", "W_quiet"):
            continue
        k = (r["period"], r["W"], r["group"])
        mine = res.get(k, [0, 0.0])
        dn, dp = int(r["n"]) - mine[0], float(r["pnl_s"]) - mine[1]
        good = dn == 0 and abs(dp) < 1e-6
        ok &= good
        print(k, "pipeline n=%s pnl_s=%.4f | indep n=%d pnl_s=%.4f | %s" % (r["n"], float(r["pnl_s"]), mine[0], mine[1], "OK" if good else "DIFF"))
print("INDEP_OK", ok)
sys.exit(0 if ok else 1)
