#!/usr/bin/env python3
"""Cham lai RAO CUNG theo 2 khau vi (current 30/200/-15 vs latest 40/250/-20)
tren chuoi equity NGAY (dung nguyen logic x1_rates.hard_by_year). Offline, khong sim."""
import os, re, sys, json
import pandas as pd, numpy as np

BASES = ["/home/ubuntu/java/devrun", "/home/ubuntu/kaggle_sim/out"]
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")
APP = {"current": (30.0, 200, -15.0), "latest": (40.0, 250, -20.0)}

def equity(base, tag):
    p = os.path.join(base, tag, "logs", "sim.out")
    if not os.path.exists(p):
        return None
    rows = []
    with open(p, errors="ignore") as fh:
        for line in fh:
            m = RX.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    if not rows:
        return None
    e = pd.DataFrame(rows, columns=["d", "equity"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d").equity.sort_index()

def hard(s, dd, uw, q):
    fails = []
    for y, sy in s.groupby(s.index.year):
        d = (sy / sy.cummax() - 1) * 100
        u = sy < sy.cummax()
        um = int(u.groupby((~u).cumsum()).sum().max()) if len(u) else 0
        qe = sy.resample("QE").last()
        q0 = pd.concat([pd.Series([sy.iloc[0]], index=[sy.index[0]]), qe]).iloc[:-1]
        qr = (qe.values / q0.values - 1) * 100
        ry = (sy.iloc[-1] / sy.iloc[0] - 1) * 100
        bad = []
        if d.min() < -dd: bad.append("DD%.1f" % d.min())
        if um > uw: bad.append("UW%d" % um)
        if ry < 0: bad.append("ret%.2f" % ry)
        if qr.min() < q: bad.append("q%.1f" % qr.min())
        if bad: fails.append("%d:%s" % (y, "/".join(bad)))
    return fails

def main():
    out = {}
    for base in BASES:
        if not os.path.isdir(base): continue
        for tag in sorted(os.listdir(base)):
            s = equity(base, tag)
            if s is None: continue
            fcur = hard(s, *APP["current"])
            flat = hard(s, *APP["latest"])
            out.setdefault(tag, {"base": [], "cur": None, "lat": None,
                                 "cur_f": None, "lat_f": None})
            out[tag]["base"].append(os.path.basename(base))
            if out[tag]["cur"] is None:
                out[tag]["cur"] = not fcur; out[tag]["cur_f"] = fcur
                out[tag]["lat"] = not flat; out[tag]["lat_f"] = flat
    diff = {t: v for t, v in out.items() if v["cur"] != v["lat"]}
    print("TONG TAG CHAM: %d | SO TAG DOI VERDICT (current->latest): %d" % (len(out), len(diff)))
    for t, v in sorted(diff.items()):
        print("%-38s %-18s cur=%s lat=%s | cur_fail=%s | lat_fail=%s" % (
            t, ",".join(v["base"]), "PASS" if v["cur"] else "FAIL",
            "PASS" if v["lat"] else "FAIL", ";".join(v["cur_f"]), ";".join(v["lat_f"])))
    json.dump({t: {"cur": v["cur"], "lat": v["lat"], "cur_f": v["cur_f"], "lat_f": v["lat_f"]}
               for t, v in diff.items()},
              open("/tmp/recheck_p12_diff.json", "w"), indent=1)

if __name__ == "__main__":
    main()
