#!/usr/bin/env python3
"""E2E_REPLAY E1 (docs/c3live/E2E_REPLAY.md §5): dung lai DOC LAP bang numpy (khong Java) tang quyet dinh tu cung dau vao
(sel rows trong trace + co a1/legacy/held/bookfull do harness ghi + buffer live ts<START) => q moi gio, tap gated/nap r/PASS;
so voi trace Java bit-exact; lenh R0 = PASS REF tru LEGACY tru tu choi hop le. argv: <fx_dir> <run_dir> [shadow_events]
"""
import collections
import csv
import gzip
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.expanduser("~/claude_master/1016/grr"))
import grr_lib  # noqa: E402

START = 1793232000000
H, DAY = 3600000, 86400000
F = np.float32
PCT = float(F(0.999950829))
DYN_MIN, SCORE_BASE, DYN_MULT, GS = F(0.26787), F(0.15), F(1.28760), F(1.55)
TOPK, DAYS = 24, 90


def b2f(b):
    return np.array([int(b)], dtype=np.int32).view(np.float32)[0]


def f2b(x):
    return int(np.array([x], dtype=np.float32).view(np.int32)[0])


def main(fx, run):
    bts, br, nbad = grr_lib.load(fx + "/gate_ratio_live.bin")
    assert nbad == 0
    bts = np.asarray(bts, np.int64)
    br = np.asarray(br, np.float32)
    m0 = (bts < START) & (bts >= START - DAYS * DAY)
    o = np.argsort(bts[m0], kind="stable")
    rec_ts = list(bts[m0][o])
    rec_r = list(br[m0][o])
    rows = collections.OrderedDict()
    with gzip.open(run + "/trace_dec.csv.gz", "rt") as fh:
        for a in csv.DictReader(fh):
            rows.setdefault(int(a["ts"]), []).append(a)
    head = 0
    qcache = {}
    cmp = collections.Counter()
    bad = []
    ref_pass = set()
    ref_app = []
    tf_slots_in_pass_minutes = 0
    for ts, rr in rows.items():
        h = ts // H * H
        # pool TreeMap<Float,String>: put theo thu tu file (rank); trung khoa => gia tri sau de len
        pool = {}
        for a in sorted(rr, key=lambda x: int(x["rank_dump"])):
            pool[f2b(b2f(a["key_bits"]))] = a
        order = sorted(pool.values(), key=lambda a: b2f(a["key_bits"]))
        rank = 0
        ref = {}
        for a in order:
            if a["a1"] == "1":
                continue
            if rank >= TOPK:
                break
            rank += 1
            st = {"rank": rank, "gated": 0, "pass": 0, "q": None}
            ref[a["symbol"]] = st
            if a["held"] == "1":
                continue
            st["gated"] = 1
            if a["bookfull"] == "1":
                continue
            if h not in qcache:
                cut = h - DAYS * DAY
                while head < len(rec_ts) and rec_ts[head] < cut:
                    head += 1
                arr = np.asarray(rec_r[head:], np.float32)
                tsa = np.asarray(rec_ts[head:], np.int64)
                arr = arr[tsa < h]
                m = len(arr)
                k = min(m - 1, max(0, int(math.floor(PCT * (m - 1)))))
                qcache[h] = F(np.partition(arr, k)[k])
            q = qcache[h]
            st["q"] = q
            gv, p15 = b2f(a["gv_bits"]), b2f(a["p15_bits"])
            sc = F(F(gv / SCORE_BASE) * DYN_MULT)
            fac = max(DYN_MIN, sc)
            r = F(p15 / F(fac * GS))
            rec_ts.append(ts)
            rec_r.append(r)
            ref_app.append((ts, f2b(r)))
            thr = F(F(q * fac) * GS)
            st["pass"] = 0 if p15 < thr else 1
            if st["pass"]:
                ref_pass.add((ts, a["symbol"]))
        anyp = any(v["pass"] for v in ref.values())
        for a in rr:
            s = ref.get(a["symbol"])
            jr = int(a["rank_counted"])
            if anyp and a["a1"] == "1":
                tf_slots_in_pass_minutes += 1
            if (s["rank"] if s else -1) != jr:
                cmp["rank_diff"] += 1
                bad.append(("rank", ts, a["symbol"], s, jr))
            jg = int(a["gated"])
            if (s["gated"] if s else 0) != jg:
                cmp["gated_diff"] += 1
                bad.append(("gated", ts, a["symbol"]))
            jp = int(a["pass"])
            if (s["pass"] if s else 0) != jp:
                cmp["pass_diff"] += 1
                bad.append(("pass", ts, a["symbol"]))
            if jg and a["bookfull"] == "0" and s and s["q"] is not None:
                if f2b(s["q"]) != int(a["q_bits"]):
                    cmp["q_diff"] += 1
                    bad.append(("q", ts, a["symbol"], float(s["q"]), float(b2f(a["q_bits"]))))
            cmp["rows"] += 1
    # nap r: REF vs Java (appended.csv.gz)
    japp = collections.Counter()
    with gzip.open(run + "/appended.csv.gz", "rt") as fh:
        for a in csv.DictReader(fh):
            japp[(int(a["ts"]), int(a["r_bits"]))] += 1
    rapp = collections.Counter(ref_app)
    app_eq = japp == rapp
    # lenh: PASS REF (khong LEGACY) <=> outcome
    oc = collections.Counter()
    miss = []
    legacy_rows = {}
    with gzip.open(run + "/trace_dec.csv.gz", "rt") as fh:
        for a in csv.DictReader(fh):
            legacy_rows[(int(a["ts"]), a["symbol"])] = a
    for k in sorted(ref_pass):
        a = legacy_rows[k]
        if a["legacy"] == "1":
            oc["LEGACY(sau gate)"] += 1
            continue
        oc[a["outcome"]] += 1
        if a["outcome"] == "-":
            miss.append(k)
    res = {"rows": cmp["rows"], "diff": {k: v for k, v in cmp.items() if k != "rows"}, "bad_sample": [str(x) for x in bad[:20]],
           "q_hours": len(qcache), "ref_pass": len(ref_pass), "appended_equal": app_eq, "appended_ref": sum(rapp.values()),
           "appended_java": sum(japp.values()), "outcomes_of_ref_pass": dict(oc), "pass_without_leg_call": [str(x) for x in miss[:20]],
           "a1_slots_in_pass_minutes": tf_slots_in_pass_minutes}
    res["E1"] = (cmp["rank_diff"] == 0 and cmp["gated_diff"] == 0 and cmp["pass_diff"] == 0 and cmp["q_diff"] == 0 and app_eq
                 and not miss)
    json.dump(res, open(run + "/check_ref.json", "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
