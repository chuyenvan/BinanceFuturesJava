#!/usr/bin/env python3
"""PARITY_V11_WINDOW luot D — chay harness OFFLINE (HARNESS_OFFLINE=1, stub Aerospike halt 97, SecurityManager halt 98,
duoi strace) cho ngay UTC D (PV_DAY). Thay cac lenh tay cua D1 (runs/d21) bang 1 script. Khong doc/ghi 242.

argv:
  r0                 : self-test chan mang (OfflineGuardSelfTest driver, nhu sh/r0_r1.sh phan R0) -> RUN/r0.json
  main               : cache Vision (VisionCacheBuilder) -> OFF-BT [T0,T1] + OFF-NEW2 theo tung doan restart that
                       (WORK/segs.json) -> ghep NEW2 -> CTL (cmp_runs) ; dem connect() trong strace
  drop <groups.json> : OFF-BT tren U_D \\ G cho tung nhom G (K3', PREREG ADDENDUM1) -> RUN_drop/g<k>/
"""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pv_cfg import cfg, MIN  # noqa: E402

C = cfg()
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))    # research/parity_v11
ROOT, RUN, WORK, TAG = C["ROOT"], C["RUN"], C["WORK"], C["tag"]
T0, T1 = C["T0"], C["T1"]
CPE = dict(l.strip().split("=", 1) for l in open(ROOT + "/build/cp.env") if "=" in l)
FUNDING = ROOT + "/univ/funding_le202609.csv.gz"
PKG = "com.binance.chuyennd.aerospike."


def mapper():
    return ROOT + "/univ/mapper_u_d21.csv" if C["layout"] == "legacy-d1" else ROOT + "/univ/mapper_%s.csv" % TAG


def env(extra=None):
    e = dict(os.environ)
    e.update(HARNESS_MAPPER_FILE=mapper(), LIVE_IS_SHADOW_HOST="true", LIVE_WRITE_242_ENABLED="false",
             HARNESS_OFFLINE="1", HARNESS_FUNDING_FILE=FUNDING)
    e.update(extra or {})
    return e


def mkrun(d):
    subprocess.run(["bash", R + "/sh/mkdir_run.sh", d], check=True, capture_output=True)


def strace_count(p):
    t = open(p, errors="ignore").read().splitlines()
    c = [x for x in t if "connect(" in x]
    return {"connect": len(c), "to_242": sum("103.157.218.242" in x for x in t),
            "af_inet": sum("AF_INET" in x for x in c), "af_inet_non_loopback": sum(("AF_INET" in x) and ("127.0.0.1" not in x) for x in c)}


def build_cache(d, uni, frm, to):
    name = "cache_%d_%d.ser.gz" % (frm, to)
    r = subprocess.run(["java", "-Xmx8g", "-cp", CPE["CP_OFF"], PKG + "VisionCacheBuilder", uni, C["VIS"], str(frm), str(to),
                        name, "holes.csv"], cwd=d, env=env(), capture_output=True, text=True)
    open(d + "/cache_build.log", "w").write(r.stdout + r.stderr)
    if r.returncode != 0:
        raise RuntimeError("VisionCacheBuilder rc=%d %s" % (r.returncode, r.stderr[-1500:]))
    return name


def harness(d, mode, restart, first, last, outname, extra=None):
    st = "strace_%s.txt" % outname
    cmd = ["strace", "-f", "--seccomp-bpf", "-e", "trace=connect", "-o", st, "java", "-Xmx6g", "-cp", CPE["CP_OFF"],
           PKG + "V11FeatHarness", mode, str(restart), str(first), str(last), "out_%s.csv.gz" % outname]
    r = subprocess.run(cmd, cwd=d, env=env(extra), capture_output=True, text=True)
    open(d + "/log_%s.txt" % outname, "w").write(r.stdout + r.stderr)
    bad = [x for x in (r.stdout + r.stderr).splitlines() if "VIOLATION" in x or "Loaded Symbol Mapper" in x
           or "Init funding fee" in x or "Exception" in x]
    return {"rc": r.returncode, "strace": strace_count(d + "/" + st), "suspicious_log_lines": bad[:5]}


def link_cache(d, src, frm, to):
    n = "cache_%d_%d.ser.gz" % (frm, to)
    if not os.path.exists(d + "/" + n):
        os.symlink(src, d + "/" + n)


def cmp(ref, new, kind, out, first=None, last=None):
    a = ["python3", R + "/py/cmp_runs.py", ref, new, kind, out]
    if first is not None:
        a += ["--first", str(first), "--last", str(last)]
    r = subprocess.run(a, capture_output=True, text=True)
    return r.stdout.strip()[-600:]


def r0():
    T = RUN + "/r0"
    shutil.rmtree(T, ignore_errors=True)
    os.makedirs(T)
    subprocess.run(["bash", R + "/sh/mkdir_run.sh", T + "/off"], check=True, capture_output=True)
    subprocess.run(["bash", R + "/sh/mkdir_run.sh", T + "/real", "real"], check=True, capture_output=True)
    # nhu sh/r0_r1.sh: mapper + co shadow export chung; driver tu bat HARNESS_OFFLINE cho tung ca con
    e = env({"HARNESS_FUNDING_EMPTY_OK": "1"})
    e.pop("HARNESS_OFFLINE", None)
    e.pop("HARNESS_FUNDING_FILE", None)
    r = subprocess.run(["java", "-cp", CPE["CP_OFF"], PKG + "OfflineGuardSelfTest", "driver", CPE["CP_OFF"], CPE["CP_NOSTUB"],
                        T + "/off", T + "/real"], cwd=T + "/off", env=e, capture_output=True, text=True)
    lines = [x for x in (r.stdout + r.stderr).splitlines() if "[R0]" in x]
    res = {"driver_rc": r.returncode, "lines": lines}
    shutil.rmtree(T + "/real", ignore_errors=True)
    json.dump(res, open(RUN + "/r0.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


def main():
    os.makedirs(RUN, exist_ok=True)
    plan = json.load(open(WORK + "/segs.json"))
    mkrun(RUN)
    frm, to = plan["cache_from"], plan["cache_to"]
    name = build_cache(RUN, C["U"], frm, to)
    src = RUN + "/" + name
    res = {"cache": name, "cache_log_tail": open(RUN + "/cache_build.log").read().splitlines()[-2:]}
    # OFF-BT: restart = T0 (chi anh huong khoang nap cache), first=T0, last=T1
    link_cache(RUN, src, T0 - 3880 * MIN, T1)
    res["BT"] = harness(RUN, "BT", T0, T0, T1, "BT")
    # OFF-NEW2 theo doan restart that
    parts_g, parts_f = [], []
    res["NEW2"] = []
    for i, s in enumerate(plan["segs"]):
        d = RUN + "/new2_s%d" % i
        os.makedirs(d, exist_ok=True)
        mkrun(d)
        seed_from = (s["restart"] - s["restart"] % MIN) - 2000 * MIN
        link_cache(d, src, min(seed_from, s["first"] - 2880 * MIN) - 1000 * MIN, s["last"])
        rr = harness(d, "NEW2", s["restart"], s["first"], s["last"], "NEW2", {"LIVE_FEAT_INPUT": "snapshot"})
        rr.update(seg=s)
        res["NEW2"].append(rr)
        parts_g.append((d + "/out_NEW2.csv.gz", s["keep_from"], s["last"]))
        parts_f.append((d + "/fund_NEW2.csv.gz", s["keep_from"], s["last"]))
    import pandas as pd
    for parts, outp in ((parts_g, RUN + "/out_NEW2.csv.gz"), (parts_f, RUN + "/fund_NEW2.csv.gz")):
        dfs = []
        for p, a, b in parts:
            x = pd.read_csv(p, dtype=str, keep_default_na=False)
            m = x["min"].astype("int64")
            dfs.append(x[(m >= a) & (m <= b)])
        pd.concat(dfs, ignore_index=True).to_csv(outp, index=False, compression="gzip")
    # CTL: OFF-NEW2 vs OFF-BT
    res["CTL_gate"] = cmp(RUN + "/out_BT.csv.gz", RUN + "/out_NEW2.csv.gz", "gate", RUN + "/cmp_ctl_gate.json")
    res["CTL_fund"] = cmp(RUN + "/fund_BT.csv.gz", RUN + "/fund_NEW2.csv.gz", "fund", RUN + "/cmp_ctl_fund.json")
    json.dump(res, open(RUN + "/harness_%s.json" % TAG, "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str)[:5000])


def drop(gfile):
    groups = json.load(open(gfile))["groups"]
    base = RUN + "_drop"
    os.makedirs(base, exist_ok=True)
    out = {}
    for g in groups:
        d = base + "/g%d" % g["k"]
        os.makedirs(d, exist_ok=True)
        mkrun(d)
        U = [x.strip() for x in open(C["U"]) if x.strip() and x.strip() not in set(g["drop"])]
        open(d + "/u_drop.txt", "w").write("\n".join(U) + "\n")
        frm = T0 - 3880 * MIN
        if not os.path.exists(d + "/out_BT.csv.gz"):
            build_cache(d, d + "/u_drop.txt", frm, T1)
            out[g["k"]] = harness(d, "BT", T0, T0, T1, "BT")
            os.remove(d + "/cache_%d_%d.ser.gz" % (frm, T1))
        out.setdefault(g["k"], {"rc": "da co (khong chay lai)"})["drop"] = g["drop"]
    json.dump(out, open(base + "/drop_runs.json", "w"), indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "r0":
        r0()
    elif a == "main":
        main()
    elif a == "drop":
        drop(sys.argv[2])
