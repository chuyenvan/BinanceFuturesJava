#!/usr/bin/env python3
"""TSX (PREREG_PARITY_V11_WINDOW §4 dong TSX) cho ngay UTC D (PV_DAY): co [TS-EXT] flag day=D live == co tinh tu Vision
cung luat (code live AltEwIndex qua tsxoff.TsxLiveOffline cua jar v11c), universe = hop cac U_D da khai; |dS_D| bao cao.
Tham so hoa tu d1_tsx_build.py (5f8e7291).
- S_j (j >= 2026-10-20) tinh tu bin Vision (j-1, j) => S_j du 1440 phut (D1 dung bin bat dau dung ngay 10-20 nen
  S_10-20 chi 1439 phut: tao tac bien, ghi o D2). S_j < 10-20: lich su Vision da tinh (v11_tsx/off out/2026-09, outv/2026-10).
- Co ngay F dung S_{F-30..F-1}; Vision thieu ngay j => S_j khong co => co cac ngay can j = NA (KHONG DO DUOC).
argv: [--regress-d1]  (dung lai bin 10-20..10-21 + u_d21 nhu D1, so bit voi work/tsx_out_days64.csv cua D1)
"""
import gzip
import json
import os
import re
import subprocess
import sys
import zipfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pv_cfg import cfg, shift  # noqa: E402

C = cfg()
TSXD = C["ROOT"] + "/tsx"
OFF = os.path.expanduser("~/claude_master/v11_tsx/off")
JAR = os.path.expanduser("~/claude_master/v11_tsx/jar/binance-java-sdk-1.2.4.jar_v11c_eea5adec")
CP = OFF + "/classes3:" + JAR
HIST = [OFF + "/out/2026-09_days64.csv", OFF + "/outv/2026-10_days64.csv"]   # 09-01..10-19 (nhu D1)
FIRST_NEW = "2026-10-20"


def build_bin(days, uni, out_bin, out_syms):
    rows, miss, nsy = [], {}, {}
    for ds in days:
        n = 0
        for s in uni:
            p = "%s/%s/%s.zip" % (C["VIS"], ds, s)
            if not os.path.exists(p):
                miss[ds] = miss.get(ds, 0) + 1
                continue
            with zipfile.ZipFile(p) as z:
                raw = z.read(z.namelist()[0]).decode()
            lines = [ln for ln in raw.splitlines() if ln and ln[0].isdigit()]
            a = np.array([ln.split(",") for ln in lines])
            rows.append(pd.DataFrame({"ts": a[:, 0].astype(np.int64), "sym": s,
                                      "close": a[:, 4].astype(np.float64),
                                      "quote_volume": a[:, 7].astype(np.float64)}))
            n += 1
        nsy[ds] = n
    t = pd.concat(rows, ignore_index=True).drop_duplicates(["sym", "ts"], keep="last").sort_values(["sym", "ts"])
    syms = sorted(t.sym.unique())
    idx = {s: i for i, s in enumerate(syms)}
    o = np.lexsort((t.sym.map(idx).to_numpy(np.int32), t.ts.to_numpy(np.int64)))
    with open(out_bin, "wb") as f:
        np.array([len(t)], dtype="<i8").tofile(f)
        t.ts.to_numpy(np.int64)[o].astype("<i8").tofile(f)
        t.sym.map(idx).to_numpy(np.int32)[o].astype("<i4").tofile(f)
        t.close.to_numpy(np.float64)[o].astype("<f8").tofile(f)
        t.quote_volume.to_numpy(np.float64)[o].astype("<f8").tofile(f)
    open(out_syms, "w").write("\n".join(syms) + "\n")
    return {"rows": int(len(t)), "syms": len(syms), "files_per_day": nsy, "missing": miss}


def ew(bin_, syms, prefix):
    r = subprocess.run(["java", "-cp", CP, "tsxoff.TsxLiveOffline", "ew", bin_, syms, prefix], capture_output=True,
                       text=True, cwd=TSXD)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])
    return r.stdout.strip()[-300:]


def uni_all():
    u = set()
    for p in C["tsx_univ"]:
        u |= {x.strip() for x in open(p) if x.strip()}
    return sorted(u)


def s_day(j, uni):
    """S_j tu bin (j-1, j); cache TSXD/S_<j>.csv (days64 + days32)."""
    out = TSXD + "/S_%s.csv" % j
    if os.path.exists(out):
        return pd.read_csv(out)
    zj = sum(1 for s in uni if os.path.exists("%s/%s/%s.zip" % (C["VIS"], j, s)))
    zp = sum(1 for s in uni if os.path.exists("%s/%s/%s.zip" % (C["VIS"], shift(j, -1), s)))
    if zj == 0 or zj < 0.99 * zp:      # Vision ngay j chua phat hanh du => S_j KHONG DO DUOC (khong ghi cache)
        return None
    pre = TSXD + "/tmp_%s" % j
    info = build_bin([shift(j, -1), j], uni, pre + ".bin", pre + "_syms.txt")
    ew(pre + ".bin", pre + "_syms.txt", pre)
    d64 = pd.read_csv(pre + "_days64.csv")
    d32 = pd.read_csv(pre + "_days32.csv")
    r = d64[d64.date == j].merge(d32[d32.date == j][["date", "sum_ew", "n_min"]], on="date", suffixes=("", "_32"))
    r["n_syms_bin"] = info["syms"]
    r["files_day"] = info["files_per_day"].get(j, 0)
    r[["epoch_day", "date", "sum_ew", "n_min", "sum_ew_32", "n_min_32", "n_syms_bin", "files_day"]].to_csv(out, index=False)
    for ext in (".bin", "_syms.txt", "_days64.csv", "_days32.csv", "_ew32.bin", "_ew64.bin"):
        if os.path.exists(pre + ext):
            os.remove(pre + ext)
    return pd.read_csv(out)


def live_lines():
    L = gzip.open(C["logs"][-1], "rt", errors="ignore").read().splitlines() if C["layout"] == "pull242" else \
        sum((gzip.open(p, "rt", errors="ignore").read().splitlines() for p in C["logs"]), [])
    fl, dy = {}, {}
    for s in L:
        m = re.search(r"\[TS-EXT\] flag day=(\S+) flag=(\S+) dd=(\S+) .* minN=(\d+) src=(\S+) final=(\S+)", s)
        if m:
            fl.setdefault(m.group(1), []).append({"flag": m.group(2), "dd": float(m.group(3)), "minN": int(m.group(4)),
                                                  "src": m.group(5), "final": m.group(6)})
        m = re.search(r"\[TS-EXT\] day (\S+) sum_ew=(\S+) n_min=(\d+)", s)
        if m:
            dy[m.group(1)] = {"sum_ew": float(m.group(2)), "n_min": int(m.group(3))}
    return fl, dy


def main():
    os.makedirs(TSXD, exist_ok=True)
    D = C["day"]
    if "--regress-d1" in sys.argv:
        uni = [x.strip() for x in open(C["ROOT"] + "/univ/u_d21.txt") if x.strip()]
        pre = TSXD + "/regr_d1"
        build_bin(["2026-10-20", "2026-10-21"], uni, pre + ".bin", pre + "_syms.txt")
        ew(pre + ".bin", pre + "_syms.txt", pre)
        a = open(pre + "_days64.csv").read()
        b = open(C["ROOT"] + "/work/tsx_out_days64.csv").read()
        a32 = open(pre + "_days32.csv").read()
        b32 = open(C["ROOT"] + "/work/tsx_out_days32.csv").read()
        print(json.dumps({"days64_identical": a == b, "days32_identical": a32 == b32, "new": a, "d1": b}))
        for ext in (".bin", "_syms.txt", "_ew32.bin", "_ew64.bin"):
            os.remove(pre + ext)
        return
    uni = uni_all()
    days, j = [], FIRST_NEW
    while j <= D:
        days.append(j)
        j = shift(j, 1)
    Sd = {}
    for j in days:
        r = s_day(j, uni)
        if r is not None:
            Sd[j] = r
    files = list(HIST)
    for j in days:
        if j in Sd:
            files.append(TSXD + "/S_%s.csv" % j)
    fout = TSXD + "/flags_%s.csv" % C["tag"]
    r = subprocess.run(["java", "-cp", CP, "tsxoff.TsxLiveOffline", "flags", fout, "2026-09-20", shift(D, 1)] + files,
                       capture_output=True, text=True, cwd=TSXD)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])
    FL = pd.read_csv(fout)
    fl_live, dy_live = live_lines()
    res = {"day": D, "universe_union": len(uni), "S_files": files, "flags_cmd_out": r.stdout.strip()[-200:]}
    for F in (D, shift(D, 1)):
        v = FL[FL.date == F]
        lv = fl_live.get(F, [])
        res["flag_" + F] = {"vision": v.iloc[0].to_dict() if len(v) else None,
                            "live_lines": lv,
                            "live_final_states": sorted(set(x["flag"] for x in lv if x["final"] == "true"))}
    vf = res["flag_" + D]["vision"]
    lstates = res["flag_" + D]["live_final_states"]
    if vf is None or vf["state"] == "NA" or not lstates:
        res["flag_match"] = None
        res["flag_status"] = "KHONG DO DUOC (vision=%s, live=%s)" % (vf["state"] if vf else None, lstates)
    else:
        res["flag_match"] = bool(lstates == [vf["state"]])
        res["flag_status"] = "DAT" if res["flag_match"] else "TRUOT"
    sv = Sd.get(D)
    if sv is not None and len(sv) == 0:
        sv = None
    lvd = dy_live.get(D)
    res["S_D"] = {"vision64": float(sv.sum_ew.iloc[0]) if sv is not None else None,
                  "vision32": float(sv.sum_ew_32.iloc[0]) if sv is not None else None,
                  "n_min_vision": int(sv.n_min.iloc[0]) if sv is not None else None,
                  "live": lvd["sum_ew"] if lvd else None, "n_min_live": lvd["n_min"] if lvd else None}
    if sv is not None and lvd:
        res["S_D"]["absdiff64"] = abs(res["S_D"]["vision64"] - lvd["sum_ew"])
        res["S_D"]["absdiff32"] = abs(res["S_D"]["vision32"] - lvd["sum_ew"])
    res["S_hist_new"] = {j: {"vision64": float(Sd[j].sum_ew.iloc[0]), "n_min": int(Sd[j].n_min.iloc[0]),
                             "live": dy_live.get(j, {}).get("sum_ew"), "n_min_live": dy_live.get(j, {}).get("n_min")}
                         for j in Sd}
    os.makedirs(C["WORK"], exist_ok=True)
    json.dump(res, open(C["WORK"] + "/tsx_%s.json" % C["tag"], "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str)[:4000])


if __name__ == "__main__":
    main()
