"""VIEC A+C: doc series NGAY (b:, m:, max:, run:) tu logs/sim.out cua moi bien the."""
import re, os, json, statistics
pat = re.compile(r"Update (\d{8}) \d{2}:\d{2} => b:(\d+) pD:\s*(-?\d+)\s+m:\s*(-?\d+)\s+max:\s*(-?\d+)\s+(-?\d+)\s+unP:\s*(-?\d+)\s+unPMin:\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)%\s+done:(\d+)/(\d+)/(\d+)\s+run:(\d+)/(\d+)")
gate = re.compile(r"\[GATE\] scale=(\S+) base=(\S+) n_cand=(\d+) n_pass=(\d+)")

RUNS = {
 "P0":       "/home/ubuntu/kaggle_sim/out/t170-x1-2021",
 "L1":       "/home/ubuntu/kaggle_sim/out/tl-l1",
 "L2":       "/home/ubuntu/kaggle_sim/out/tl-l2",
 "L3":       "/home/ubuntu/kaggle_sim/out/tl-l3",
 "F3":       "/home/ubuntu/kaggle_sim/out/pc-close",
 "V1":       "/home/ubuntu/java/devrun/X1_TH_GAP05_2021",
 "V2":       "/home/ubuntu/java/devrun/X1_TH_GAP12_2021",
 "V3":       "/home/ubuntu/java/devrun/X1_TH_WEAK17_2021",
}

def series(d):
    p = os.path.join(d, "logs", "sim.out")
    if not os.path.exists(p):
        return None, None
    rows = []
    g = None
    for l in open(p, errors="replace"):
        m = pat.search(l)
        if m:
            r = m.groups()
            rows.append(dict(date=r[0], b=float(r[1]), m=float(r[3]), mday=float(r[4]),
                             mmonth=float(r[5]), unPMin=float(r[7]), sl=int(r[11]),
                             done=int(r[12]), created=int(r[13]), run=int(r[14]), maxrun=int(r[15])))
        else:
            gm = gate.search(l)
            if gm: g = dict(scale=gm.group(1), base=gm.group(2), n_cand=int(gm.group(3)), n_pass=int(gm.group(4)))
    return rows, g

out = {}
for tag, d in RUNS.items():
    rows, g = series(d)
    if not rows:
        print(tag, "NO sim.out"); out[tag] = None; continue
    # ngay -> b (dedup: giu gia tri cuoi cung cua ngay)
    b = [(r["date"], max(r["m"], r["mday"]), r["b"], r["run"], r["maxrun"], r["unPMin"]) for r in rows]
    out[tag] = dict(dir=d, n_days=len(b), b_first=b[0][2], b_last=b[-1][2], gate=g,
                    rows=[[x[0], x[1], x[2], x[3], x[4], x[5]] for x in b])
    print(tag, "days=%d b=%s->%s gate=%s" % (len(b), b[0][2], b[-1][2], g))

json.dump(out, open("/home/ubuntu/capdiag/simout_series.json", "w"))
print("saved /home/ubuntu/capdiag/simout_series.json")
