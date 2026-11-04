#!/usr/bin/env python3
"""Kiem DOC LAP (khong import pipeline research/parity_v11/py) cho 1 ngay UTC D: P3 va P1/P1-m/P1-F.
Viet lai theo audit OC1023 audA (p3_audit.py, p1_audit.py): giai ma buffer GRR1 truc tiep (struct+crc32+snappy), doc log
RAW pull242 (khong qua log_window), q gio h = a[floor(P*(m-1))] tren record ts < h (luat 'normal' cho moi gio),
P1 tu feat_dump pull242 + out_BT. argv: D (YYYY-MM-DD) out.json"""
import datetime as dt
import glob
import gzip
import json
import re
import struct
import sys
import zlib

import numpy as np
import onnxruntime as ort
import pandas as pd
import snappy

D, OUTP = sys.argv[1], sys.argv[2]
PULL = "/home/ubuntu/claude_master/pull242"
W = "/home/ubuntu/claude_master/parity_v11w"
d0 = int(dt.datetime.strptime(D, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
T0, T1, H = d0, d0 + 86400000 - 60000, 3600000
res = {"day": D}
# ---- P3
nxt = (dt.date.fromisoformat(D) + dt.timedelta(days=1)).isoformat()
bf = sorted(glob.glob(PULL + "/%s/run/gate_ratio_live.bin.gz" % nxt) + glob.glob(PULL + "/%s/run/gate_ratio_live.bin.gz" % D))[-1]
B = gzip.open(bf).read()
i, T, R, bad = 0, [], [], 0
while i + 12 <= len(B):
    mg, ln, crc = struct.unpack(">iiI", B[i:i + 12])
    if mg != 0x47525231 or ln < 0 or i + 12 + ln > len(B):
        bad += 1
        i += 1
        continue
    c = B[i + 12:i + 12 + ln]
    if zlib.crc32(c) & 0xffffffff != crc:
        bad += 1
        i += 1
        continue
    a = np.frombuffer(snappy.uncompress(c), dtype=np.dtype([("t", ">i8"), ("r", ">f4")]))
    T.append(a["t"].astype(np.int64))
    R.append(a["r"].astype(np.float32))
    i += 12 + ln
t = np.concatenate(T)
r = np.concatenate(R)
o = np.argsort(t, kind="stable")
t, r = t[o], r[o]
lg = sorted(glob.glob(PULL + "/%s/logs/full.log@*" % nxt) + glob.glob(PULL + "/%s/logs/full.log@*" % D))[-1]
pat = re.compile(r"^(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)")
P = 0.99995083
q = {}
for s in gzip.open(lg, "rt", errors="ignore"):
    if "[GATE-RATIO] q_t=" in s and "q_t9=" in s:
        m = pat.match(s)
        d_, mo, y, hh, mi, ss = map(int, m.groups())
        tt = int(dt.datetime(y, mo, d_, hh, mi, ss, tzinfo=dt.timezone(dt.timedelta(hours=7))).timestamp() * 1000)
        q[(tt // H) * H - H] = float(re.search(r"q_t9=([0-9.]+)", s).group(1))
rows = []
for h in range(T0 // H * H, T1 // H * H + H, H):
    if h not in q:
        rows.append({"h": h, "missing": True})
        continue
    lo, hi = np.searchsorted(t, h - 90 * 86400000, "left"), np.searchsorted(t, h, "left")
    a = np.sort(r[lo:hi])
    m = len(a)
    qr = float(a[min(int(np.floor(P * (m - 1))), m - 1)])
    rows.append({"h": h, "q_log": q[h], "q_rep": qr, "rel": abs(q[h] - qr) / qr})
res["P3"] = {"buffer_file": bf, "log_file": lg, "n_records": int(len(t)), "bad": bad,
             "hours": len(rows), "missing": sum(1 for x in rows if x.get("missing")),
             "n_rel_gt_1e-6": sum(1 for x in rows if not x.get("missing") and x["rel"] > 1e-6),
             "max_rel": max((x["rel"] for x in rows if not x.get("missing")), default=None)}
# ---- P1 (can out_BT cua ngay)
bt = W + "/d/%s/runs/out_BT.csv.gz" % D
try:
    Bt = pd.read_csv(bt)
except FileNotFoundError:
    Bt = None
if Bt is not None:
    fs = sorted(glob.glob(PULL + "/%s/dumps/feat_dump_*.csv.gz" % D))
    L = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    L = L[(L.symbol == "BTCUSDT") & (L.ts >= T0) & (L.ts < T1 + 60000)].copy()
    L["min"] = L.ts // 60000 * 60000
    L = L.drop_duplicates("min", keep="last")
    FE = [c for c in L.columns if c not in ("ts", "symbol", "p15_out", "rateDownAvg", "rateUpAvg", "rateDown15MAvg",
                                            "rateUp15MAvg", "min")]
    J = L.merge(Bt, on="min", suffixes=("_l", ""))
    X = J[FE].copy()
    for c in ["fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend"]:
        X[c] = J[c + "_l"]
    s = ort.InferenceSession("/home/ubuntu/claude_master/parity_1020/raw242/models/ai_ml_data/ai_models_reg_v3/"
                             "Model_Regressor_Return15M.onnx", providers=["CPUExecutionProvider"])
    nm = s.get_inputs()[0].name
    po = np.asarray(s.run(None, {nm: X.values.astype(np.float32)})[0]).ravel()
    pl = np.asarray(s.run(None, {nm: J[[c + "_l" for c in FE]].values.astype(np.float32)})[0]).ravel()
    rel = np.abs(J.p15_out.values - po) / np.abs(po)
    NF = [c for c in FE if not c.startswith("funding")]
    ok = np.ones(len(J), bool)
    for c in NF:
        a, b = J[c + "_l"].values, J[c].values
        ok &= (np.abs(a - b) <= 1e-6 * (1 + np.abs(b))) | (np.isnan(a) & np.isnan(b))
    res["P1"] = {"n": int(len(J)), "nfeat": len(FE), "median_rel": float(np.median(rel)),
                 "frac_le_1e-3": float((rel <= 1e-3).mean()), "max_rel": float(rel.max()),
                 "P1m_max_rel": float((np.abs(pl - J.p15_out.values) / np.abs(J.p15_out.values)).max()),
                 "P1F_all_match": "%d/%d" % (ok.sum(), len(ok)),
                 "P1F_bad_p07": [(pd.to_datetime(x, unit="ms") + pd.Timedelta(hours=7)).strftime("%m-%d %H:%M") for x in J["min"][~ok]]}
json.dump(res, open(OUTP, "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
