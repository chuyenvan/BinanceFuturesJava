#!/usr/bin/env python3
"""Keo (CHI DOC) mau file predictionSymbol/<day>/<ts>.features tu 242 ve Oracle, theo lo nho + nghi (giam tai mang 242).
Mau: phut % 15 == 0, va phut % 60 == 2 (kiem bien gio). Cua so: >= 2026-10-16 18:00 +07."""
import os, subprocess, time, sys
T0 = 1792148400000
OUT = "/home/ubuntu/claude_master/parity_1020/raw242/psym"
SSH = ["ssh", "-p", "2222", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-i", "/home/ubuntu/.ssh/id_rsa_chuyennd", "root@103.157.218.242"]
BASE = "/home/chuyennd/java/v_t_m/storage/data/predictionSymbol"
sel = []
for day in ["20261016", "20261017", "20261018", "20261019", "20261020"]:
    r = subprocess.run(SSH + ["ls %s/%s" % (BASE, day)], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
    for f in r.stdout.split():
        if not f.endswith(".features"):
            continue
        ts = int(f.split(".")[0])
        if ts < T0:
            continue
        mm = (ts // 60000) % 60
        if mm % 15 == 0 or mm == 2:
            sel.append((day, f))
print("selected", len(sel), flush=True)
os.makedirs(OUT, exist_ok=True)
have = set(os.listdir(OUT))
todo = [x for x in sel if x[1] not in have]
B = 20
for i in range(0, len(todo), B):
    chunk = todo[i:i + B]
    args = " ".join("%s/%s" % (d, f) for d, f in chunk)
    cmd = "cd %s && nice -n 19 tar cf - %s" % (BASE, args)
    p = subprocess.run(SSH + [cmd], stdin=subprocess.DEVNULL, capture_output=True, timeout=300)
    if p.returncode != 0:
        print("ERR", p.stderr[:300], flush=True)
        time.sleep(5)
        continue
    t = subprocess.run(["tar", "xf", "-", "-C", OUT, "--strip-components=1"], input=p.stdout, capture_output=True)
    print("batch", i // B, "bytes", len(p.stdout), "rc", t.returncode, flush=True)
    time.sleep(2)
print("DONE", len(os.listdir(OUT)), flush=True)
