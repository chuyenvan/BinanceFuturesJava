#!/usr/bin/env python3
"""TS_MKT_EXT live offline: (a) EW phut + co ngay cua code LIVE (Java AltEwIndex) vs index sim; (c) replay decide() vs trade list sim."""
import json, logging, sys  # noqa: E401

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("cmp")
W = "/home/ubuntu/claude_master/v11_tsx/off/"
O = W + "out/"
M26 = ["2025-12"] + ["2026-%02d" % i for i in range(1, 10)]
M22 = ["2021-12"] + ["2022-%02d" % i for i in range(1, 13)]
res = {}


def ms(s):
    return int(pd.Timestamp(s).value // 10**6)


def load_ew(months, kind):
    t, v = [], []
    for m in months:
        a = np.fromfile(O + m + "_ew%s.bin" % kind, dtype=[("t", ">i8"), ("v", ">f8")])
        t.append(a["t"].astype(np.int64))
        v.append(a["v"].astype(np.float64))
    return np.concatenate(t), np.concatenate(v)


def ew_cmp(name, ref, months, lo, hi):
    rt, rr = ref["ew_ts"].astype(np.int64), ref["ew_r"].astype(np.float64)
    m = (rt >= ms(lo)) & (rt < ms(hi))
    t, v = load_ew(months, "64")
    t32, v32 = load_ew(months, "32")
    same = bool(np.array_equal(rt[m], t))
    out = dict(n_ref=int(m.sum()), n_live=int(len(t)), same_ts=same,
               max_abs=float(np.max(np.abs(rr[m] - v))) if same else None,
               f32_same_ts=bool(np.array_equal(t32, t)),
               f32_max_abs_vs64=float(np.max(np.abs(v32 - v))) if np.array_equal(t32, t) else None)
    out["ok"] = bool(same and out["max_abs"] <= 1e-9)
    log.info("EW %s %s", name, out)
    res["ew_" + name] = out
    return out


def ref_dd(ref, lo_day, hi_day):
    """dd sim (cumsum + rolling 31 hang) tu index tham chieu."""
    L = pd.Series(np.cumsum(ref["ew_r"].astype(np.float64)), index=pd.to_datetime(ref["ew_ts"].astype(np.int64), unit="ms"))
    eod = L.groupby(L.index.floor("D")).last()
    dd = np.exp(eod - eod.rolling(31, min_periods=1).max()) - 1
    s = pd.Series(dd.values, index=dd.index + pd.Timedelta(days=1))  # theo NGAY CO
    return s[(s.index >= lo_day) & (s.index <= hi_day)]


def ranges(days):
    days = sorted(days)
    out, st, pv = [], None, None
    for d in days:
        if st is None:
            st = pv = d
        elif d == pv + pd.Timedelta(days=1):
            pv = d
        else:
            out.append((st, pv))
            st = pv = d
    if st is not None:
        out.append((st, pv))
    return ",".join("%s-%s" % (a.strftime("%Y%m%d"), b.strftime("%Y%m%d")) if a != b else a.strftime("%Y%m%d") + "-" + b.strftime("%Y%m%d")
                    for a, b in out)


def flag_cmp(name, fcsv, f32csv, ref, lo, hi, want_days):
    f = pd.read_csv(fcsv)
    g = pd.read_csv(f32csv)
    f["date"] = pd.to_datetime(f["date"])
    on = list(f.loc[f.state == "ON", "date"])
    on32 = list(pd.to_datetime(g.loc[g.state == "ON", "date"]))
    rd = ref_dd(ref, pd.Timestamp(lo), pd.Timestamp(hi))
    fd = f.set_index("date")["dd"]
    j = pd.concat([fd, rd.rename("ref")], axis=1).dropna()
    out = dict(n_on=len(on), ranges=ranges(on), n_na=int((f.state == "NA").sum()),
               want_n=len(want_days), same_as_sim=sorted(on) == sorted(want_days),
               dd_max_abs_vs_sim=float((j["dd"] - j["ref"]).abs().max()), dd_n=len(j),
               min_margin_to_thr=float((f["dd"] + 0.30).abs().min()),
               f32_n_on=len(on32), f32_same=sorted(on32) == sorted(on),
               f32_dd_max_abs=float((f["dd"] - g["dd"]).abs().max()))
    log.info("FLAGS %s %s", name, out)
    res["flags_" + name] = out


b = np.load("/home/ubuntu/claude_master/tsx/ho/ew_out/ew_2026.npz")
a = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
ew_cmp("2026", b, M26, "2025-12-01", "2026-10-01")
ew_cmp("2022", a, M22, "2021-12-01", "2023-01-01")

hf = json.load(open("/home/ubuntu/claude_master/tsx/ho/ho_flags.json"))
want26 = []
for r in hf["ranges"].split(","):
    x, y = r.split("-")
    want26 += list(pd.date_range(x, y, freq="D"))
dev = json.load(open("/home/ubuntu/claude_master/tsx/flags.json"))
want22 = []
for r in dev["ranges"].split(","):
    x, y = r.split("-")
    want22 += [d for d in pd.date_range(x, y, freq="D") if d.year == 2022]
flag_cmp("2026", O + "flags26_64.csv", O + "flags26_32.csv", b, "2026-01-01", "2026-09-30", want26)
flag_cmp("2022", O + "flags22_64.csv", O + "flags22_32.csv", a, "2022-01-01", "2022-12-31", want22)
res["want22_n"] = len(want22)

# (c) replay — moi seed
def replay(sd):
    rp = pd.read_csv(O + "replay_s%d.csv" % sd)
    rp["dur_h"] = (rp.exit_ms - rp.anchor_ms) / 3.6e6
    due = rp[rp.exit_ms >= rp.first_due_ms]
    sl = due[due.status == "STOP_LOSS_DONE"]
    sm = due[due.status != "STOP_LOSS_DONE"]
    sl_ok = sl.cut_ms == sl.exit_ms
    deferred = due[due.first_dec == "DEFER"]
    c = dict(n_trades=len(rp), n_due=len(due), n_sl_due=len(sl), sl_cut_match=int(sl_ok.sum()),
             sl_mismatch=sl.loc[~sl_ok, ["sym", "anchor_ms", "exit_ms", "first_dec", "cut_ms", "dur_h"]].to_dict("records"),
             n_sm_due=len(sm), sm_first_defer=int((sm.first_dec == "DEFER").sum()),
             sm_due_list=sm[["sym", "dur_h", "first_dec", "cut_ms", "exit_ms"]].to_dict("records"),
             deferred_clusters=len(deferred),
             cut_after_defer=int(((deferred.status == "STOP_LOSS_DONE") & (deferred.cut_ms == deferred.exit_ms)).sum()))
    tsx = json.load(open("/home/ubuntu/claude_master/tsx/ho/res_tsx-ho-x14-s%d.json" % sd))["tsx"]
    c["sim_tsx_line"] = tsx
    c["ok"] = bool(c["sl_cut_match"] == c["n_sl_due"] and c["sm_first_defer"] == c["n_sm_due"]
                   and c["deferred_clusters"] == tsx[3] and c["cut_after_defer"] == tsx[4])
    log.info("REPLAY s%d %s", sd, {k: v for k, v in c.items() if k not in ("sm_due_list",)})
    return c


for sd in (42, 7, 13, 21, 99, 123, 777, 2024):
    res["replay_s%d" % sd] = replay(sd)
c = res["replay_s42"]
c_all = all(res["replay_s%d" % sd]["ok"] for sd in (42, 7, 13, 21, 99, 123, 777, 2024))
res["replay_all_ok"] = c_all
json.dump(res, open(W + "compare_ac.json", "w"), indent=1, default=str)
log.info("ALL ok_ew26=%s ok_ew22=%s flags26=%s flags22=%s replay_s42=%s replay_all=%s", res["ew_2026"]["ok"], res["ew_2022"]["ok"],
         res["flags_2026"]["same_as_sim"], res["flags_2022"]["same_as_sim"], c["ok"], c_all)
