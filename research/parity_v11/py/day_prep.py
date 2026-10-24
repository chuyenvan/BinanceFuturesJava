#!/usr/bin/env python3
"""PARITY_V11_WINDOW luot D — chuan hoa du lieu live cua ngay UTC D tu ~/claude_master/pull242/<D>(+<D+1>) va kiem do phu.
KHONG doc/ghi 242 (chi doc ban keo ve Oracle). Timestamp int64 ms.

env PV_DAY=YYYY-MM-DD. argv:
  prep      : gop log (moi full.log@* cua pull242/<D> va <D+1>, khu trung theo snapshot-prefix + noi theo thoi gian),
              loc D 06:00 -> D+1 07:10 (+07) => live/log_window.gz; giai nen buffer moi nhat => live/gate_ratio_live.bin;
              giai ma psym ts in [T0,T1] bang Pa1020Feat => live/feat45_live.csv.gz; ucand_<tag>.txt; restarts.json;
              coverage_<tag>.json (khong nhin so parity).
  universe  : U_D = ucand ∩ {Vision ngay D co file}; kiem >= 99 % (khong dat => exit 3 = KHONG DO DUOC phan can Vision);
              mapper_<tag>.csv; segs.json (cac doan NEW2 theo restart that).
"""
import datetime as dt
import glob
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pv_cfg import cfg, globs, shift, day_ms, MIN, H  # noqa: E402

C = cfg()
assert C["layout"] == "pull242", "day_prep chi dung cho bo cuc pull242"
LIVE, WORK, RUN, TAG = C["LIVE"], C["WORK"], C["RUN"], C["tag"]
T0, T1 = C["T0"], C["T1"]
UNIV = C["ROOT"] + "/univ"
PAT = re.compile(rb"^(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)\.(\d+)")
TZ7 = dt.timezone(dt.timedelta(hours=7))
JAR = os.path.expanduser("~/claude_master/v11_tsx/jar/binance-java-sdk-1.2.4.jar_v11c_eea5adec")


def lt(b):
    m = PAT.match(b)
    if not m:
        return None
    d, mo, y, hh, mi, ss, _ = (int(x) for x in m.groups())
    return int(dt.datetime(y, mo, d, hh, mi, ss, tzinfo=TZ7).timestamp() * 1000)


def read_lines_gz(p):
    raw = b""
    try:
        with gzip.open(p, "rb") as f:
            while True:
                b = f.read(1 << 22)
                if not b:
                    break
                raw += b
    except (EOFError, OSError, zlib.error):
        pass
    ls = raw.split(b"\n")
    if ls and ls[-1] == b"":
        ls = ls[:-1]
    elif ls:
        ls = ls[:-1]   # dong cuoi co the dang ghi do
    return ls


def merge_logs(files):
    """Cac snapshot cua cung full.log (ten full.log@<mtime>_<size>.gz). Gop: neu snapshot truoc la PREFIX cua snapshot sau
    => lay snapshot sau; nguoc lai (log da xoay vong) => noi phan co timestamp > timestamp cuoi da co. Tra (lines, info)."""
    acc, info = [], []
    for p in sorted(files, key=lambda x: int(re.search(r"@(\d+)_", x).group(1)) if re.search(r"@(\d+)_", x) else 0):
        ls = read_lines_gz(p)
        if acc and len(ls) >= len(acc) and ls[:len(acc)] == acc:
            how = "prefix-extend"
            acc = ls
        elif not acc:
            how = "first"
            acc = ls
        else:
            last = None
            for x in reversed(acc):
                last = lt(x)
                if last:
                    break
            add = []
            on = False
            for x in ls:
                t = lt(x)
                if t is not None:
                    on = t > last
                if on:
                    add.append(x)
            how = "time-splice(+%d)" % len(add)
            acc = acc + add
        info.append({"file": p, "lines": len(ls), "how": how})
    return acc, info


def prep():
    os.makedirs(LIVE, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    cov = {"day": C["day"], "T0": T0, "T1": T1, "pull_dirs": {}}
    for k in ("PULLD", "PULLN"):
        d = C[k]
        cov["pull_dirs"][d] = {"exists": os.path.isdir(d), "COMPLETE": os.path.exists(d + "/COMPLETE")}
    if not cov["pull_dirs"][C["PULLD"]]["COMPLETE"]:
        print("pull242/%s chua COMPLETE" % C["day"])
        sys.exit(2)
    # ---- log
    files = glob.glob(C["PULLD"] + "/logs/full.log@*") + glob.glob(C["PULLN"] + "/logs/full.log@*")
    allines, info = merge_logs(files)
    win, keep = [], False
    rs_all = []
    for x in allines:
        t = lt(x)
        if t is not None:
            keep = C["log_from"] <= t <= C["log_to"]
            if b"MainClass:" in x:
                rs_all.append(t)
        if keep:
            win.append(x)
    with gzip.open(LIVE + "/log_window.gz", "wb") as f:
        f.write(b"\n".join(win) + b"\n")
    ts_win = [t for t in (lt(x) for x in win) if t]
    cov["log"] = {"files": info, "merged_lines": len(allines), "window_lines": len(win),
                  "first": dt.datetime.fromtimestamp(min(ts_win) / 1000, TZ7).isoformat() if ts_win else None,
                  "last": dt.datetime.fromtimestamp(max(ts_win) / 1000, TZ7).isoformat() if ts_win else None,
                  "covers_from": bool(ts_win and min(ts_win) <= C["log_from"] + MIN),
                  "covers_to": bool(ts_win and max(ts_win) >= C["log_to"] - MIN)}
    mins = set(t // MIN for t in ts_win if T0 + MIN <= t < T1 + 2 * MIN)
    cov["log"]["minutes_with_lines_in_window"] = len(mins)
    cnt = {}
    for key in (b"[GATE] ", b"[GATE-RATIO] q_t=", b"[MAP] tick=", b"[LIVE-KLINE]", b"[FEAT-PIPE] ticks=", b"[TS-EXT] day ",
                b"[TS-EXT] flag day=", b"MainClass:", b"[LEGACY] managed"):
        cnt[key.decode()] = sum(1 for x in win if key in x)
    cov["log"]["markers"] = cnt
    gate_ticks = set()
    for x in win:
        if b"[GATE] " in x and b"n_pass=" in x:
            t = lt(x)
            tk = (t // MIN) * MIN - MIN
            if T0 <= tk <= T1:
                gate_ticks.add(tk)
    cov["log"]["gate_ticks_in_window"] = len(gate_ticks)
    gr_hours = set()
    for x in win:
        if b"[GATE-RATIO] q_t=" in x:
            h = (lt(x) // H) * H - H
            if (T0 // H) * H <= h <= (T1 // H) * H:
                gr_hours.add(h)
    cov["log"]["gate_ratio_hours_in_window"] = len(gr_hours)
    # restart: lan cuoi truoc T0 (log day du) + trong [T0, T1]
    rs_all = sorted(set(rs_all))
    before = [t for t in rs_all if t < T0]
    inday = [t for t in rs_all if T0 <= t <= T1 + MIN]
    rs = {"last_before_T0": before[-1] if before else None, "in_day": inday,
          "p07": [dt.datetime.fromtimestamp(t / 1000, TZ7).isoformat() for t in (before[-1:] + inday)]}
    json.dump(rs, open(WORK + "/restarts.json", "w"), indent=1)
    cov["restarts"] = rs
    # ---- buffer: snapshot moi nhat trong D, D+1
    bufs = sorted(glob.glob(C["PULLD"] + "/run/gate_ratio_live.bin*") + glob.glob(C["PULLN"] + "/run/gate_ratio_live.bin*"),
                  key=os.path.getmtime)
    b = bufs[-1]
    with (gzip.open(b, "rb") if b.endswith(".gz") else open(b, "rb")) as f, open(C["buffer"], "wb") as g:
        shutil.copyfileobj(f, g)
    cov["buffer"] = {"src": b, "bytes": os.path.getsize(C["buffer"])}
    # ---- psym -> feat45
    ps = {}
    for p in glob.glob(C["PULLD"] + "/psym/*/*.features.gz") + glob.glob(C["PULLN"] + "/psym/*/*.features.gz"):
        ts = int(os.path.basename(p).split(".")[0])
        if T0 <= ts <= T1:
            ps[ts] = p
    tmp = tempfile.mkdtemp(prefix="pv_psym_", dir=os.path.expanduser("~/claude_master/parity_v11w"))
    try:
        fl = []
        for ts in sorted(ps):
            o = "%s/%d.features" % (tmp, ts)
            with gzip.open(ps[ts], "rb") as f, open(o, "wb") as g:
                shutil.copyfileobj(f, g)
            fl.append(o)
        cp = "%s/build/stubcls:%s/build/clspa:%s" % (C["ROOT"], C["ROOT"], JAR)
        r = subprocess.run(["java", "-cp", cp, "Pa1020Feat", LIVE + "/feat45_live.csv.gz"] + fl,
                           capture_output=True, text=True)
        cov["psym"] = {"files_in_window": len(ps), "expected": (T1 - T0) // MIN + 1, "decode_stdout": r.stdout.strip(),
                       "decode_stderr_tail": r.stderr.strip()[-500:], "rc": r.returncode}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    import pandas as pd
    F = pd.read_csv(LIVE + "/feat45_live.csv.gz", usecols=["ts", "symbol"])
    cov["psym"]["rows"] = int(len(F))
    cov["psym"]["minutes_decoded"] = int(F.ts.nunique())
    cov["psym"]["rows_per_min_min"] = int(F.groupby("ts").size().min())
    # ---- dumps
    def dump_minutes(pats, col="ts"):
        n, mn = 0, set()
        for p in globs(pats):
            try:
                d = pd.read_csv(p, usecols=[col])
            except Exception:  # noqa: BLE001 - file dang ghi do / rong
                n += 1
                continue
            mn |= set(int(x) // MIN * MIN for x in d[col].values if T0 <= x < T1 + MIN)
        return len(mn), n, mn
    nf, bf, _ = dump_minutes(C["feat_globs"])
    ns, bs, _ = dump_minutes(C["sel_globs"])
    n1, b1, m1 = dump_minutes(C["s1_globs"])
    cov["dumps"] = {"feat_minutes": nf, "feat_bad_files": bf, "sel_minutes": ns, "sel_bad_files": bs,
                    "s1_minutes": n1, "s1_bad_files": b1}
    # ---- universe ung vien: u_cache1017 ∪ symbol live (sel/s1/psym) cua ngay D
    u = {x.strip() for x in open(UNIV + "/u_cache1017.txt") if x.strip()}
    live_syms = set(F.symbol.unique())
    for p in globs(C["sel_globs"] + C["s1_globs"]):
        try:
            d = pd.read_csv(p, usecols=["ts", "symbol"])
            live_syms |= set(d.symbol[(d.ts >= T0) & (d.ts <= T1)].unique())
        except Exception:  # noqa: BLE001
            pass
    cand = sorted(u | live_syms)
    open(UNIV + "/ucand_%s.txt" % TAG, "w").write("\n".join(cand) + "\n")
    open(UNIV + "/ulive_%s.txt" % TAG, "w").write("\n".join(sorted(live_syms)) + "\n")
    cov["ucand"] = {"n": len(cand), "u_cache1017": len(u), "live_syms": len(live_syms), "live_not_in_cache": sorted(live_syms - u)}
    json.dump(cov, open(WORK + "/coverage_%s.json" % TAG, "w"), indent=1, default=str)
    print(json.dumps(cov, indent=1, default=str)[:6000])


def universe():
    cand = [x.strip() for x in open(UNIV + "/ucand_%s.txt" % TAG) if x.strip()]
    vd = C["VIS"] + "/" + C["day"]
    have = [s for s in cand if os.path.exists(vd + "/" + s + ".zip")]
    frac = len(have) / max(1, len(cand))
    open(C["U"], "w").write("\n".join(have) + "\n")
    with open(UNIV + "/mapper_%s.csv" % TAG, "w") as f:
        for i, s in enumerate(have, 1):
            f.write("%s,%d\n" % (s, i))
    # nsym live (ky vong |U_D|): symbol live trong ngay ma Vision khong co => lech universe
    rs = json.load(open(WORK + "/restarts.json"))
    pts = [rs["last_before_T0"]] + rs["in_day"] if rs["last_before_T0"] else rs["in_day"]
    segs = []
    for i, r in enumerate(pts):
        first = -(-(r - 66000) // MIN) * MIN       # tick nho nhat M voi M+66s >= r (tick dau do process moi quyet dinh)
        nxt = pts[i + 1] if i + 1 < len(pts) else None
        last = T1 if nxt is None else min(T1, -(-(nxt - 66000) // MIN) * MIN - MIN)
        if last < T0:
            continue
        segs.append({"restart": r, "first": first, "last": last, "keep_from": max(T0, first)})
    cache_from = min([T0] + [s["first"] for s in segs]) - 3880 * MIN
    nd = (day_ms(C["day"]) - (cache_from // 86400000) * 86400000) // 86400000
    plan = {"segs": segs, "cache_from": cache_from, "cache_to": T1,
            "vision_days_cache": [shift(C["day"], -k) for k in range(nd, -1, -1)]}
    json.dump(plan, open(WORK + "/segs.json", "w"), indent=1)
    lv = [x.strip() for x in open(UNIV + "/ulive_%s.txt" % TAG) if x.strip()]
    frac_live = sum(1 for s in lv if os.path.exists(vd + "/" + s + ".zip")) / max(1, len(lv))
    res = {"cand": len(cand), "U_D": len(have), "frac_cand": frac, "live_syms": len(lv), "frac_live_with_vision": frac_live,
           "missing_cand": sorted(set(cand) - set(have))[:80],
           "missing_live": sorted(s for s in lv if not os.path.exists(vd + "/" + s + ".zip")), "plan": plan}
    json.dump(res, open(WORK + "/universe_%s.json" % TAG, "w"), indent=1)
    print(json.dumps(res, indent=1))
    if frac_live < 0.99:
        print("VISION_NGAY_D_DUOI_99PCT => KHONG DO DUOC phan can Vision")
        sys.exit(3)


if __name__ == "__main__":
    {"prep": prep, "universe": universe}[sys.argv[1]]()
