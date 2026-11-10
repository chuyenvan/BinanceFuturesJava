#!/usr/bin/env python3
"""[ADD18] BIG_DOWN-SEL: top-n leg BIG_DOWN live ([BIG_DOWN-SEL]) == tap tinh lai offline theo logic S1-map cua SIM
(SimulatorMarketLevelTicker1MStopLoss:368-380 = MarketBigChangeDetector.getTopSymbolArray tren bins S1-map).
Offline: symbolPred = gv_off (GV-I harness, p2_pairs: coin c3 dang giu da bo theo ADD1), xep (gv_off tang) nhu TreeMap<Float,.> cua sim,
lay n dau. [ADD19 errata r4u3] tap loai tru GIONG SIM: CHI coin c3 dang giu, KHONG loai coin LEGACY (C3_EXCLUDE_LEGACY_HELD=false). Hoa diem o bien hang n/n+1 (|dv| <= 1e-6*max|v|),
hoac 2 coin trung gia tri (sim mat 1) => XAM. Thieu du lieu => KHONG DO DUOC (=> XAM ngay, ADD18 §1).
Ngay khong co su kien => "KHONG AP DUNG (0 su kien)". Chi cham khi jar ngay co BIG_DOWN-SEL (r4u*); jar cu chi dem su kien.
Ham thuan evaluate() de test. Doc WORK/p2_pairs.csv.gz + LIVE/log_window.gz. Khong doc 242."""
import datetime as dt
import gzip
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RX_LEVEL = re.compile(r"Market level change: (\d{8} \d\d:\d\d) level: (\S+)")
RX_SEL = re.compile(r"\[BIG_DOWN-SEL\] (\d{8} \d\d:\d\d) level=(\S+) n=(\d+)(?: pool=(\d+) top=(\S+))?")
RX_LEG = re.compile(r"^(\d\d/\d\d/\d{4} \d\d:\d\d:\d\d)\.\d+ .*\[LEGACY\] managed \d+: (\S*)")
EVENT_LEVELS = ("BIG_DOWN",)
TIE = 1e-6


def ms7(s):
    """'yyyyMMdd HH:mm' (+07) -> ms UTC."""
    return int((dt.datetime.strptime(s, "%Y%m%d %H:%M") - dt.timedelta(hours=7) - dt.datetime(1970, 1, 1)).total_seconds() * 1000)


def parse_log(lines):
    ev, sel, leg = {}, {}, []
    for s in lines:
        m = RX_LEVEL.search(s)
        if m and m.group(2) in EVENT_LEVELS:
            ev[m.group(1)] = m.group(2)
        m = RX_SEL.search(s)
        if m:
            top = []
            if m.group(5) and m.group(5) != "-":
                top = [x.split("=")[0] for x in m.group(5).split(",")]
            sel[m.group(1)] = {"level": m.group(2), "n": int(m.group(3)), "top": top, "no_map": m.group(5) is None}
        m = RX_LEG.search(s)
        if m:
            t = int((dt.datetime.strptime(m.group(1), "%d/%m/%Y %H:%M:%S") - dt.timedelta(hours=7) - dt.datetime(1970, 1, 1)).total_seconds() * 1000)
            leg.append((t, set(x for x in m.group(2).split(",") if x)))
    return ev, sel, leg


def offline_top(rows, n, locked):
    """rows: [(symbol, gv_off)] cua 1 phut. Tra (top, ly_do_xam|None)."""
    r = sorted([(float(v), s) for s, v in rows if v == v], key=lambda x: x[0])   # sim: TreeMap<Float> tang dan
    vals = [v for v, _ in r]
    dup = len(vals) != len(set(vals))
    top, i = [], 0
    for v, s in r:
        i += 1
        if s in locked:
            continue
        top.append(s)
        if len(top) >= n:
            break
    why = None
    if len(top) == n and i < len(r):
        vmax = max(abs(x) for x in vals) or 1.0
        if abs(r[i][0] - r[i - 1][0]) <= TIE * vmax:
            why = "hoa diem bien hang %d/%d" % (n, n + 1)
    if dup and why is None:
        cut = r[i - 1][0] if top else None
        if cut is not None and sum(1 for v in vals if v <= cut) != len(set(v for v in vals if v <= cut)):
            why = "trung gia tri trong top (sim TreeMap mat 1)"
    return top, why


def evaluate(ev, sel, p2_by_ts, legacy_at):
    """ev: {min: level}; sel: {min: {...}}; p2_by_ts: {ts: [(sym, gv_off)]}; legacy_at(ts) -> set."""
    out = []
    for mn in sorted(set(ev) | set(k for k, v in sel.items() if v["level"] in EVENT_LEVELS)):
        r = {"min": mn, "level": ev.get(mn) or sel[mn]["level"]}
        s = sel.get(mn)
        if s is None:
            r.update(status="TRUOT", why="co su kien BIG_DOWN nhung khong co dong [BIG_DOWN-SEL]")
            out.append(r)
            continue
        r["live_top"] = s["top"]
        ts = ms7(mn)
        rows = None
        for off in (0, 60000, -60000):
            if ts + off in p2_by_ts:
                rows, r["p2_offset_ms"] = p2_by_ts[ts + off], off
                break
        if s["no_map"]:
            r.update(status="KHONG DO DUOC", why="live: chua co S1-map (0 leg)")
        elif rows is None:
            r.update(status="KHONG DO DUOC", why="khong co gv_off offline tai phut")
        else:
            top, why = offline_top(rows, s["n"], legacy_at(ts))
            r["off_top"] = top
            if len(top) < s["n"]:
                r.update(status="KHONG DO DUOC", why="tap offline khong du n (p2 chi co ung vien selector)")
            elif set(top) == set(s["top"]):
                r["status"] = "DAT"
            else:
                r.update(status="XAM" if why else "TRUOT", why=why or "tap top khac (khong do hoa diem)")
        out.append(r)
    sts = [x["status"] for x in out]
    if not out:
        tot = "KHONG AP DUNG (0 su kien)"
    elif "TRUOT" in sts:
        tot = "TRUOT"
    elif "XAM" in sts or "KHONG DO DUOC" in sts:
        tot = "XAM"
    else:
        tot = "DAT"
    return {"n_events": len(out), "events": out, "status": tot}


def main():
    from pv_cfg import cfg
    import pandas as pd
    C = cfg()
    W = C["WORK"]
    L = gzip.open(C["LIVE"] + "/log_window.gz", "rt", errors="ignore").read().splitlines()
    ev, sel, leg = parse_log(L)
    leg.sort()

    def legacy_at(ts):   # [ADD19 errata r4u3] sim khong loai LEGACY => tap loai tru them = rong (coin c3 giu da bo o p2)
        return set()
    applies = str(C.get("JAR", "")).startswith("r4u")
    p2 = {}
    pf = W + "/p2_pairs.csv.gz"
    if os.path.exists(pf) and (ev or sel):
        P = pd.read_csv(pf, usecols=["ts", "symbol", "tag", "gv_off"])
        P = P[P.tag == "live"]
        for ts, g in P.groupby("ts"):
            p2[int(ts)] = list(zip(g.symbol, g.gv_off))
    res = evaluate(ev, sel, p2, legacy_at)
    res["jar"], res["ap_dung"] = C.get("JAR"), applies
    if not applies:
        res["status_jar_cu"] = res["status"]
        res["status"] = "KHONG AP DUNG (jar %s, khong co BIG_DOWN-SEL)" % C.get("JAR") if res["n_events"] else "KHONG AP DUNG (0 su kien)"
    json.dump(res, open(W + "/bigdown_%s.json" % C["tag"], "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "events"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
