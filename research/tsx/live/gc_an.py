#!/usr/bin/env python3
"""Phan tich gc.log (Xlog:gc time,uptime) cac process v_t_m 242 (doc qua pipe, luu Oracle)."""
import glob, re, sys  # noqa: E401
import json

D = "/home/ubuntu/claude_master/v11_tsx/off/live242/gc/"
R = re.compile(r"^\[(\S+?)\]\[(\d+\.\d+)s\] GC\((\d+)\) (Pause .+?) (\d+)M->(\d+)M\((\d+)M\) (\d+\.\d+)ms")
out = {}
for f in sorted(glob.glob(D + "gc.log*")):
    ev = []
    t0 = None
    for ln in open(f, errors="replace"):
        if t0 is None and "Using G1" in ln:
            t0 = ln[1:24]
        m = R.match(ln)
        if m:
            ev.append(dict(t=m.group(1)[:19], up=float(m.group(2)), kind=m.group(4), before=int(m.group(5)),
                           after=int(m.group(6)), cap=int(m.group(7)), ms=float(m.group(8))))
    if not ev:
        continue
    full = [e for e in ev if e["kind"].startswith("Pause Full")]
    def at_hour(h):
        c = [e for e in ev if e["up"] <= h * 3600]
        if not c:
            return None
        win = [e for e in c if e["up"] > (h - 0.5) * 3600] or c[-5:]
        return dict(min_after=min(e["after"] for e in win), last_after=c[-1]["after"], cap=c[-1]["cap"])
    up_end = ev[-1]["up"] / 3600
    # old-gen proxy: min heap-after-GC theo tung gio
    hourly = []
    for h in range(1, int(up_end) + 1):
        w = [e for e in ev if (h - 1) * 3600 < e["up"] <= h * 3600]
        if w:
            hourly.append((h, min(e["after"] for e in w), max(e["cap"] for e in w), sum(e["kind"].startswith("Pause Full") for e in w)))
    out[f.split("/")[-1]] = dict(start=t0, end=ev[-1]["t"], hours=round(up_end, 2), n_gc=len(ev), n_full=len(full),
                                  full_first=full[0]["t"] if full else None, full_up_h=[round(e["up"] / 3600, 2) for e in full][:30],
                                  full_after=[e["after"] for e in full][:30], full_ms_max=max([e["ms"] for e in full], default=0),
                                  pause_max_ms=max(e["ms"] for e in ev), h1=at_hour(1), h6=at_hour(6), h11=at_hour(11),
                                  hourly_min_after=hourly)
for k in sorted(out, key=lambda k: out[k]["start"] or ""):
    v = out[k]
    print("==", k, v["start"], "->", v["end"], "h=", v["hours"], "gc=", v["n_gc"], "full=", v["n_full"], "fullmax_ms=", v["full_ms_max"], "pausemax_ms=", v["pause_max_ms"])
    print("   h1", v["h1"], "h6", v["h6"], "h11", v["h11"])
    print("   full at h", v["full_up_h"], "after", v["full_after"])
    print("   hourly(h,minAfterM,capM,nfull)", v["hourly_min_after"])
json.dump(out, open(D + "gc_summary.json", "w"), indent=1)
