#!/usr/bin/env python3
"""HO4-P0b Q1: so output ho4b-t1x (bo 10 symbol chi-file + market DEV nap san) voi DEV: gate g1, Tool1 t1 (khoi 10-01),
t1e (khoi 09-15) va t1 vs t1e. Chi ty le. Usage: ho4b_t1xcmp.py <out_dir> <out.json>"""
import glob, json, os, sys
sys.path.insert(0, "/home/ubuntu/claude_master/1011/ho4b")
OD, OUT = sys.argv[1], sys.argv[2]
sys.argv = ["x", "-", "-", "-"]
import ho4b_detcmp as D
f = lambda pat: (sorted(glob.glob(os.path.join(OD, pat))) or [None])[0]
R = {}
R["gate_t1x_vs_dev"] = D.cmp_gate(D.load_gate(f("g1/*.csv*")), D.load_gate(D.GA.STORE))
TD = D.load_t1(os.path.join(D.G.T1_DIR, "features_20251001_to_20260101*"))
T1 = D.load_t1(f("t1/*.t1c*"))
TE = D.load_t1(f("t1e/*.t1c*"))
R["tool1_t1_vs_dev"] = D.cmp_t1(T1, TD)
R["tool1_t1e_vs_dev"] = D.cmp_t1(TE, TD)
R["tool1_t1_vs_t1e"] = D.cmp_t1(T1, TE)
for k, v in R.items():
    D.log.info("%s %s", k, v)
json.dump(R, open(OUT, "w"), indent=1)
