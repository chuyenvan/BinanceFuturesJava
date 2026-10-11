#!/usr/bin/env python3
"""HO4-P0b Q1: nhan det l1 vs DEV chi tren tick du 72h nhin truoc trong end-arg (2025-10-01..10-09 UTC). Chi ty le."""
import glob, json, sys
sys.path.insert(0, "/home/ubuntu/claude_master/1011/ho4b")
sys.argv = ["x", "-", "-", "-"]
import ho4b_detcmp as D
L1 = D.load_lab(glob.glob("/home/ubuntu/claude_master/1011/ho4b/kaggle/out/ho4b-det/out/l1/*.pb"))
LD = D.load_lab(["/home/ubuntu/ds_label15m/funding_label_20251001_to_20260101.pb"])
r = D.cmp_lab(L1, LD)
D.log.info("LAB %s", r)
json.dump(r, open("/home/ubuntu/claude_master/1011/ho4b/detcmp_lab.json", "w"))
