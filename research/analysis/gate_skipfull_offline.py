#!/usr/bin/env python3
"""gate_skipfull_offline.py -- GATE_QUOTA_SKIPFULL (Pha E) cong OFFLINE (pre-reg docs/prereg/PREREG_GATE_QUOTA_SKIPFULL.md §4).

Goi qua `python3 research/analysis/gate_offline.py skipfull` (hoac truc tiep). THUAN PYTHON, 0 Java/sim.
Gate G2 offline (gate_offline.run_g2) OFF vs ON (full=phut so day). U xap xi tu run OFF cua CHINH seed:
  U(t) = sum margin printDone (moi level, s <= t < e) / E(t); E(t) = b+unP dong 'Update yyyymmdd hh:mm' gan nhat <= t
  trong logs/sim.out; full <=> E <= 0 hoac U >= 0.60 (U_MAX mac dinh, profile khong override).
Cong (S21, S7): q_h trung binh T6-T9/2022 ON < OFF; pass symbol-phut T6-T9 ON/OFF >= 1.30. Khong chan sim.
"""
import json
import logging
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import gate_offline as g  # noqa: E402

log = logging.getLogger("gqsf_off")
UMAX = 0.60
CAP0 = 35000.0
JOUT = g.REPO + "/docs/audit/gate_skipfull_offline.json"
GATE_ARMS = ("S21", "S7")
RX = re.compile(r"Update (\d{8} \d\d:\d\d) => b:\s*(-?\d+).*?unP:\s*(-?\d+)")


def loc_ms(s):
    return int(pd.Timestamp(s).value // 10 ** 6) - g.TZ


W0, W1 = loc_ms("2022-06-01"), loc_ms("2022-10-01")
M0, M1 = loc_ms("2022-05-01"), loc_ms("2022-06-01")


def equity_snap(tag):
    rows = []
    with open(g.OUTK + tag + "/logs/sim.out", errors="ignore") as f:
        for ln in f:
            m = RX.search(ln)
            if m:
                rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "eq"]).drop_duplicates("d", keep="last")
    t = pd.to_datetime(e["d"], format="%Y%m%d %H:%M").values.astype("datetime64[ms]").astype(np.int64) - g.TZ
    o = np.argsort(t, kind="mergesort")
    return t[o], e["eq"].to_numpy(float)[o]


def full_mask(C, tag):
    d = C["d"]
    mg = pd.to_numeric(d["margin"], errors="coerce").fillna(0).to_numpy(float)
    s = d["s_ms"].to_numpy(np.int64)
    e = d["e_ms"].to_numpy(np.int64)
    ts = C["ts"]
    os_, oe = np.argsort(s, kind="mergesort"), np.argsort(e, kind="mergesort")
    cs = np.concatenate([[0.0], np.cumsum(mg[os_])])
    ce = np.concatenate([[0.0], np.cumsum(mg[oe])])
    mopen = cs[np.searchsorted(s[os_], ts, "right")] - ce[np.searchsorted(e[oe], ts, "right")]
    et, ev = equity_snap(tag)
    j = np.searchsorted(et, ts, "right") - 1
    eq = np.where(j >= 0, ev[np.maximum(j, 0)], CAP0)
    U = np.where(eq > 0, mopen / np.where(eq > 0, eq, 1.0), np.inf)
    return (eq <= 0) | (U >= UMAX), U, len(et)


def hour_q(C, G, sel):
    has = C["valid"].any(1) & sel & ~G["warm"]
    h = C["ts"][has] // g.H
    q = G["qm"][has]
    _, i = np.unique(h, return_index=True)
    return (float(np.mean(q[i])) if len(i) else None), int(len(i))


def one(arm, B, s2id):
    tag = g.SEEDS[arm][2]
    C = g.build(arm, B, s2id)
    full, U, n_snap = full_mask(C, tag)
    Goff = g.run_g2(C)
    _, _, E = g.d1d2(arm, C, Goff, g.simlog(tag))
    Gon = g.run_g2(C, full=full)
    ts, yr = C["ts"], C["yr"]
    win, may, y22 = (ts >= W0) & (ts < W1), (ts >= M0) & (ts < M1), yr == 2022
    waste = Goff["P"] & ~E
    fc = full[:, None]
    qoff, nhoff = hour_q(C, Goff, win)
    qon, nhon = hour_q(C, Gon, win & ~full)
    r = dict(tag=tag, pred_md5=C["pred_md5"], printdone_md5=C["pd_md5"], n_equity_snap=n_snap,
             full_min_2022=int((full & y22).sum()), full_min_may22=int((full & may).sum()),
             full_min_t69=int((full & win).sum()), cand_min_2022=int(y22.sum()),
             U_may22=g.qstat(U[may & np.isfinite(U)]),
             pass_t69_off=int(Goff["P"][win].sum()), pass_t69_on=int(Gon["P"][win].sum()),
             q_t69_off=qoff, q_t69_on=qon, n_hour_t69_off=nhoff, n_hour_t69_on=nhon,
             pass_may_off=int(Goff["P"][may].sum()), pass_may_on=int(Gon["P"][may].sum()),
             pass_2022_off=int(Goff["P"][y22].sum()), pass_2022_on=int(Gon["P"][y22].sum()),
             pass_all_off=int(Goff["P"].sum()), pass_all_on=int(Gon["P"].sum()),
             waste22_off=int(waste[y22].sum()), waste22_flag_full=int((waste & fc)[y22].sum()),
             entered22=int(E[y22].sum()), entered22_flag_full=int((E & fc)[y22].sum()),
             pass_year={int(y): [int(Goff["P"][yr == y].sum()), int(Gon["P"][yr == y].sum())] for y in g.YEARS},
             q_month22={})
    r["ratio_t69"] = r["pass_t69_on"] / max(1, r["pass_t69_off"])
    for mo in range(1, 13):
        a, b = loc_ms("2022-%02d-01" % mo), loc_ms("2023-01-01" if mo == 12 else "2022-%02d-01" % (mo + 1))
        sm = (ts >= a) & (ts < b)
        r["q_month22"][mo] = [hour_q(C, Goff, sm)[0], hour_q(C, Gon, sm & ~full)[0]]
    log.info("%s %s", arm, json.dumps(g.tojs({k: v for k, v in r.items() if k != "q_month22"})))
    log.info("%s q_month22 %s rss %.2f GB", arm, json.dumps(g.tojs(r["q_month22"])), g.rss())
    return r


def main():
    g.wait_lock()
    g.disk_ok("skipfull")
    B = dict(np.load(g.CACHE + "/cand_base.npz"))
    mp = pd.read_csv(g.MAPF)
    s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
    out = dict(meta=dict(script="research/analysis/gate_skipfull_offline.py", prereg="docs/prereg/PREREG_GATE_QUOTA_SKIPFULL.md",
                         umax=UMAX, window_t69="2022-06-01..2022-09-30 GMT+7", gate_arms=list(GATE_ARMS),
                         approx=["U = margin printDone (luc dong, gom leg DCA) / E ngay b+unP cua run OFF",
                                 "so lenh = so OFF (khong phan hoi bac 2)", "held tu printDone OFF"]),
               arms={})
    order = list(GATE_ARMS) + [a for a in g.SEEDS if a not in GATE_ARMS]
    for arm in order:
        out["arms"][arm] = one(arm, B, s2id)
    gate = {}
    for a in GATE_ARMS:
        x = out["arms"][a]
        gate[a] = dict(q_down=bool(x["q_t69_on"] < x["q_t69_off"]), pass_up30=bool(x["ratio_t69"] >= 1.30),
                       q_off=x["q_t69_off"], q_on=x["q_t69_on"], pass_off=x["pass_t69_off"], pass_on=x["pass_t69_on"],
                       ratio=x["ratio_t69"])
    out["gate"] = dict(arms=gate, q_down_all=all(v["q_down"] for v in gate.values()),
                       pass_up30_all=all(v["pass_up30"] for v in gate.values()))
    log.info("CONG OFFLINE %s", json.dumps(g.tojs(out["gate"])))
    g.disk_ok("truoc ghi json")
    with open(JOUT, "w") as f:
        json.dump(g.tojs(out), f, indent=1, ensure_ascii=False)
    log.info("ghi %s md5 %s rss %.2f GB", JOUT, g.md5f(JOUT), g.rss())


def posthoc():
    """HAU KIEM (KHONG phai cong, viet SAU khi thay cong §4 = 0 phut full): xap xi U §4 gan 0 phut full
    (U max thang 5 < 0.60) => thay bang PROXY: phut 'full' = phut co >= 1 pass OFF KHONG vao lenh (lang phi D2,
    tuc pass bi chan sau gate - D2 cho thay 100% do managerBudget null). Chi do huong co che q_t, khong do loi ich."""
    g.disk_ok("posthoc")
    B = dict(np.load(g.CACHE + "/cand_base.npz"))
    mp = pd.read_csv(g.MAPF)
    s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
    js = json.load(open(JOUT))
    ph = {}
    for arm in list(GATE_ARMS) + [a for a in g.SEEDS if a not in GATE_ARMS]:
        tag = g.SEEDS[arm][2]
        C = g.build(arm, B, s2id)
        Goff = g.run_g2(C)
        _, _, E = g.d1d2(arm, C, Goff, g.simlog(tag))
        full = (Goff["P"] & ~E).any(1)
        Gon = g.run_g2(C, full=full)
        ts = C["ts"]
        win = (ts >= W0) & (ts < W1)
        qoff, _ = hour_q(C, Goff, win)
        qon, _ = hour_q(C, Gon, win & ~full)
        r = dict(full_min=int(full.sum()), full_min_2022=int((full & (C["yr"] == 2022)).sum()),
                 pass_t69_off=int(Goff["P"][win].sum()), pass_t69_on=int(Gon["P"][win].sum()),
                 q_t69_off=qoff, q_t69_on=qon,
                 pass_year={int(y): [int(Goff["P"][C["yr"] == y].sum()), int(Gon["P"][C["yr"] == y].sum())] for y in g.YEARS},
                 q_month22={})
        r["ratio_t69"] = r["pass_t69_on"] / max(1, r["pass_t69_off"])
        for mo in range(5, 13):
            a, b = loc_ms("2022-%02d-01" % mo), loc_ms("2023-01-01" if mo == 12 else "2022-%02d-01" % (mo + 1))
            sm = (ts >= a) & (ts < b)
            r["q_month22"][mo] = [hour_q(C, Goff, sm)[0], hour_q(C, Gon, sm & ~full)[0]]
        log.info("POSTHOC %s %s", arm, json.dumps(g.tojs(r)))
        ph[arm] = r
        del C, Goff, Gon, E
    js["posthoc_waste_proxy"] = dict(note=posthoc.__doc__, arms=ph)
    g.disk_ok("truoc ghi json posthoc")
    with open(JOUT, "w") as f:
        json.dump(g.tojs(js), f, indent=1, ensure_ascii=False)
    log.info("ghi %s md5 %s rss %.2f GB", JOUT, g.md5f(JOUT), g.rss())


if __name__ == "__main__":
    posthoc() if sys.argv[1:] == ["posthoc"] else main()
