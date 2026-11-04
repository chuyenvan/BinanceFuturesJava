#!/usr/bin/env python3
"""Test TIEM LOI cho harness PARITY_V12_DRY: tren ban SAO du lieu that cua 1 ngay (mac dinh 2026-11-03), tiem lech gia vao
(a) buffer gate (nhan r lon nhat cua 1 gio x1,5) va (b) gia tri q_t9 trong 1 dong [GATE-RATIO] cua log; chay lai stage p3 +
live_only va verdict v12. KY VONG: control != TRUOT; (a) va (b) => P3 TRUOT => verdict TRUOT. Khong dung den du lieu goc.
Usage: python3 test_inject_v12.py [YYYY-MM-DD]"""
import gzip
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib

import numpy as np
import snappy

D = sys.argv[1] if len(sys.argv) > 1 else "2026-11-03"
TAG = D.replace("-", "")
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.expanduser("~/claude_master/parity_v12w")
H = 3600000


def mkroot(name):
    r = tempfile.mkdtemp(prefix="pv12_inject_%s_" % name, dir=SRC)
    os.makedirs(r + "/d/%s/work" % D)
    os.symlink(SRC + "/univ", r + "/univ")
    os.symlink(SRC + "/shadow_book", r + "/shadow_book")
    os.symlink(SRC + "/exinfo", r + "/exinfo")
    shutil.copytree(SRC + "/d/%s/live" % D, r + "/d/%s/live" % D)
    for f in ("restarts.json", "coverage_%s.json" % TAG, "universe_%s.json" % TAG):
        p = SRC + "/d/%s/work/%s" % (D, f)
        if os.path.exists(p):
            shutil.copy(p, r + "/d/%s/work/" % D)
    return r


def run(root):
    env = dict(os.environ, PV_DAY=D, PV_ROOT=root, LIVE_IS_SHADOW_HOST="true")
    for st in ("p3", "live_only"):
        subprocess.run([sys.executable, HERE + "/day_eval.py", st], env=env, check=True, capture_output=True)
    code = ("import sys,json;sys.path.insert(0,%r);import day_report_v12 as V;v,_,_=V.v12_day(%r);"
            "print(json.dumps({'ket_luan':v['ket_luan'],'P3':v['v11_status']['P3']}))" % (HERE, D))
    r = subprocess.run([sys.executable, "-c", code], env=env, check=True, capture_output=True, text=True)
    return json.loads(r.stdout.strip().splitlines()[-1])


def load_buf(p):
    b = open(p, "rb").read(); i = 0; T = []; R = []
    while i + 12 <= len(b):
        mg, ln, crc = struct.unpack(">iiI", b[i:i + 12])
        c = b[i + 12:i + 12 + ln]
        a = np.frombuffer(snappy.uncompress(c), dtype=np.dtype([("t", ">i8"), ("r", ">f4")]))
        T.append(a["t"].astype(np.int64)); R.append(a["r"].astype(np.float32)); i += 12 + ln
    return np.concatenate(T), np.concatenate(R)


def write_buf(p, t, r):
    raw = np.empty(len(t), dtype=np.dtype([("t", ">i8"), ("r", ">f4")])); raw["t"] = t; raw["r"] = r
    comp = snappy.compress(raw.tobytes())
    open(p, "wb").write(struct.pack(">iiI", 0x47525231, len(comp), zlib.crc32(comp) & 0xffffffff) + comp)


res = {}
# control
r0 = mkroot("ctl"); res["control"] = run(r0)
# (a) buffer: nhan MOI r truoc T0 x1,01 => phan vi q dich ~1 %. (Lan thu dau x1,5 cho 30 r LON NHAT KHONG doi q vi cac
#     phan tu do von nam TREN phan vi — tiem khong hop le, khong phai harness bo sot; da ghi trong bao cao.)
r1 = mkroot("buf")
bp = r1 + "/d/%s/live/gate_ratio_live.bin" % D
t, r = load_buf(bp)
cov = json.load(open(SRC + "/d/%s/work/coverage_%s.json" % (D, TAG)))
sel = np.nonzero(t < cov["T0"])[0]
r[sel] = r[sel] * np.float32(1.01)
write_buf(bp, t, r)
res["inject_buffer_all_pre_T0_x1.01"] = run(r1)
# (b) log: doi q_t9 cua 1 dong [GATE-RATIO] trong cua so (+1 %)
r2 = mkroot("log")
lp = r2 + "/d/%s/live/log_window.gz" % D
L = gzip.open(lp, "rb").read().split(b"\n")
idx = [i for i, x in enumerate(L) if b"[GATE-RATIO] q_t=" in x]
k = idx[len(idx) // 2]
m = re.search(rb"q_t=([0-9.]+) q_t9=([0-9.eE+-]+)", L[k])
q = float(m.group(2)) * 1.01
L[k] = L[k].replace(m.group(0), b"q_t=%.6f q_t9=%.9g" % (q, q))
gzip.open(lp, "wb").write(b"\n".join(L))
res["inject_log_qt9_+1pct"] = run(r2)
for rr in (r0, r1, r2):
    shutil.rmtree(rr, ignore_errors=True)
ok = (not res["control"]["ket_luan"].startswith("TRUOT") and res["inject_buffer_all_pre_T0_x1.01"]["ket_luan"].startswith("TRUOT")
      and res["inject_log_qt9_+1pct"]["ket_luan"].startswith("TRUOT"))
res["TEST_PASS"] = ok
print(json.dumps(res, indent=1, ensure_ascii=False))
sys.exit(0 if ok else 1)
