#!/usr/bin/env python3
"""E2E_REPLAY_V12 - REF DOC LAP (numpy/python) viet tu DAC TA docs/c3live/E2E_REPLAY_V12_SPEC.md (prereg
PREREG_E2E_REPLAY_V12 §3). KHONG import / goi Java, KHONG doc output cua replay (chi doc fixture + env 242 + tham so luot).

Mo phong vong kin theo phut (cung dong ho voi rig, spec §R0): tang quyet dinh (selector top-K + gate ratio q theo gio +
skipFull) -> sizing (§R3) -> khop (§R4: FAKE = gia nhip luc quyet dinh = open nen b+1; DRY = close nen b) -> DCA grid
(§R5) -> thoat A3 theo nen 1m (§R6: arm 0,07 tren HIGH, trailing gap min(peak*ratio, 0,03) lam tron 0,005, ratchet
lien tuc, time-stop 168 h tinh tu phut quyet dinh leg dau, khop min(SL, open) / min(open, close)).

argv: --fx DIR --env FILE --out DIR --venue FAKE|DRY --capital C --flags on|off [--sdca-at MS --sdca-n N]
      [--fin-inj-at MS] [--end MS]
Ra: <out>/ref_legs.csv, ref_clusters.csv, ref_q.csv, ref_summary.json
"""
import argparse
import collections
import csv
import gzip
import json
import math
import os
import sys
from decimal import Decimal, ROUND_FLOOR

import numpy as np

sys.path.insert(0, os.path.expanduser("~/claude_master/1016/grr"))
import grr_lib  # noqa: E402  (doc file buffer gate_ratio_live.bin - python thuan, khong Java)

F = np.float32
MIN, H, DAY = 60000, 3600000, 86400000
# Hang so EntryGate (spec §R2; = docs/c3live/E2E_REPLAY.md / check_ref.py 11-05)
DYN_MIN, SCORE_BASE, DYN_MULT = F(0.26787), F(0.15), F(1.28760)
# Spec cung (prereg §3; khong co trong env 242 => gia tri dac ta)
U_MAX_DEF = 0.6
LEVELS = [F(-0.50), F(-0.75), F(-0.90)]
SIZE_CAP = 0.045
MIN_BUDGET = 5.0
SDCA_FACTORS = [0.40, 0.20, 0.07]
SDCA_PHASE = 10 * MIN
TF_UNDERLYING = {"EQUITY", "HK_EQUITY", "KR_EQUITY", "CN_EQUITY", "COMMODITY", "FX"}
TF_TAGS = {"TRADFI", "STOCK", "STOCKS", "EQUITY", "EQUITIES", "ETF", "FOREX", "FX", "COMMODITY", "COMMODITIES", "METAL", "METALS"}


def load_env(path):
    e = {}
    for ln in open(path):
        s = ln.strip()
        if s.startswith("export "):
            s = s[7:].strip()
        if "=" in s:
            k, v = s.split("=", 1)
            e[k.strip()] = v.strip()
    return e


def params(env, capital, flags):
    w = [float(x) for x in env.get("DCA_GRID_WEIGHTS", "1,1,1,1").split(",")]
    return dict(
        TOPK=int(env["SELECTOR_RANK_TOPK"]), PCT=float(F(float(env["LIVE_GATE_ROLLING_PCT"]))),
        DAYS=int(env.get("LIVE_GATE_ROLLING_DAYS", "90")), GS=F(float(env["SIM_GATE_DYN_SCALE"])),
        MOM=F(float(env["SIM_MIN_MOMENTUM_15M"])), F_BASE=F(float(env["SIM_F_BASE"])),
        U_MAX=F(float(env.get("SIM_U_MAX", U_MAX_DEF))), W=[F(x) for x in w], SCALE=F(float(env["DCA_GRID_SCALE"])),
        ARM=F(float(env["SIM_RATE_PROFIT_STOP_MARKET"])), RATIO=F(float(env["TS_GIVEBACK_RATIO"])),
        GAP=F(float(env["SIM_TS_MAX_GAP"])), GAP_WEAK=F(float(env["SIM_TS_MAX_GAP_WEAK"])),
        TSTOP_H=int(env["SIM_LOSER_TIME_STOP_HOURS"]), SKIPFULL=env.get("GATE_QUOTA_SKIP_WHEN_FULL", "") == "true",
        C=float(capital), APPLY=(flags == "on"), DCA=(flags == "on"))


def budget(P, used, leg_idx):
    """§R3: b = C*F_BASE*(1-U/U_MAX)/sum(w) [* w[leg]*SCALE neu APPLY]; None = U >= U_MAX (float32 nhu sim)."""
    C = F(P["C"])
    u = F(F(used) / C)
    if u >= P["U_MAX"]:
        return None
    b = F(F(F(C * P["F_BASE"]) * F(F(1) - F(u / P["U_MAX"]))) / F(sum(P["W"])))
    if P["APPLY"]:
        if leg_idx >= len(P["W"]):
            return F(0)
        b = F(b * F(P["W"][leg_idx] * P["SCALE"]))
    cap = F(F(SIZE_CAP) * C)
    if b > cap:
        b = cap
    return b


def hand_values():
    """prereg §3: C=10000, 3 leg PREDICT lien tiep cung phut, bo lam tron qty, co BAT: 225,00 / 216,56 / 208,44."""
    P = dict(C=10000.0, F_BASE=F(0.015), U_MAX=F(0.6), W=[F(1)] * 4, SCALE=F(6.0), APPLY=True)
    used, out = 0.0, []
    for _ in range(3):
        b = float(budget(P, used, 0))
        out.append(b)
        used += b
    return out


def trail(P, rate):
    """§R6 trailRate: gap = min(rate*RATIO, GAP) (GAP_WEAK = GAP o env 242 => khong phu thuoc symbolPred);
    sl = round((rate-gap)/0.005)*0.005 (float32, Math.round = floor(x+0.5))."""
    gap = min(F(rate * P["RATIO"]), P["GAP"])
    r = F(rate - gap)
    step = F(0.005)
    return F(F(math.floor(float(F(r / step)) + 0.5)) * step)


def floor_to(x, step):
    if step <= 0:
        return Decimal(0)
    return (Decimal(repr(x)) / step).to_integral_value(rounding=ROUND_FLOOR) * step


def load_exinfo(path):
    d = json.load(open(path))
    meta = {}
    for s in d["symbols"]:
        f = {x["filterType"]: x for x in s.get("filters", [])}
        lot, mlot = f.get("LOT_SIZE", {}), f.get("MARKET_LOT_SIZE", {})
        step = Decimal(mlot.get("stepSize", "0") or "0")
        if step <= 0:
            step = Decimal(lot.get("stepSize", "0") or "0")
        minq = Decimal(mlot.get("minQty") or lot.get("minQty") or "0")
        mn = Decimal(f.get("MIN_NOTIONAL", {}).get("notional", "0") or "0")
        tick = Decimal(f.get("PRICE_FILTER", {}).get("tickSize", "0") or "0")
        ct = (s.get("contractType") or "").upper()
        ut = (s.get("underlyingType") or "").upper()
        # §R1 universe A1 (dinh nghia A1 cong bo: TRADFI = contractType chua TRADIFI/TRADFI hoac underlyingType thuoc
        #   TF_UNDERLYING; + INDEX + PREMARKET). Symbol khong co trong exinfo => loai neu phut > serverTime (fail-closed).
        a1x = ("TRADIFI" in ct or "TRADFI" in ct or ut in TF_UNDERLYING or ut in ("INDEX", "PREMARKET"))
        meta[s["symbol"]] = dict(step=step, minq=minq, mn=mn, tick=tick, status=s.get("status"), a1x=a1x)
    return meta, int(d.get("serverTime", 0))


class Cluster:
    def __init__(self, sym, b0, fill, qty, rank):
        self.sym, self.b0, self.first = sym, b0, fill
        self.qty, self.cost, self.legs = qty, qty * fill, 1
        self.sl, self.minp, self.armed = None, math.inf, False
        self.rank = rank
        self.exit = None   # (bar, reason, price, at_open)

    @property
    def vwap(self):
        return self.cost / self.qty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fx", required=True)
    ap.add_argument("--env", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--venue", default="FAKE")
    ap.add_argument("--capital", type=float, default=10000.0)
    ap.add_argument("--flags", default="on")
    ap.add_argument("--sdca-at", type=int, default=-1)
    ap.add_argument("--sdca-n", type=int, default=2)
    ap.add_argument("--fin-inj-at", type=int, default=-1)
    ap.add_argument("--end", type=int, default=-1)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    env = load_env(a.env)
    P = params(env, a.capital, a.flags)
    man = json.load(open(a.fx + "/manifest.json"))
    START, END = man["START"], man["END"] if a.end < 0 else a.end
    meta, server_time = load_exinfo(a.fx + "/exinfo.json")
    # sel: ts -> list rows (rank order of file)
    sel = collections.defaultdict(list)
    with gzip.open(a.fx + "/sel.csv.gz", "rt") as fh:
        r = csv.reader(fh)
        next(r)
        for x in r:
            sel[int(x[0])].append((x[1], F(float(x[2])), int(x[3]), F(float(x[4])), F(float(x[5]))))
    bars = collections.defaultdict(dict)
    with gzip.open(a.fx + "/klines.csv.gz", "rt") as fh:
        r = csv.reader(fh)
        next(r)
        for x in r:
            bars[x[0]][int(x[1])] = (float(x[2]), float(x[3]), float(x[4]), float(x[5]))
    bigdown = collections.defaultdict(list)
    with open(a.fx + "/bigdown.csv") as fh:
        r = csv.reader(fh)
        next(r)
        for x in r:
            bigdown[int(x[0])].append(x[1])
    bts, br, nbad = grr_lib.load(a.fx + "/gate_ratio_live.bin")
    assert nbad == 0
    bts = np.asarray(bts, np.int64)
    br = np.asarray(br, np.float32)
    m0 = bts < START
    o = np.argsort(bts[m0], kind="stable")
    rec_ts, rec_r = list(bts[m0][o]), list(br[m0][o])
    head = 0
    qcache = {}

    sdca_start = {}

    def fct(s, t):
        st = sdca_start.get(s)
        if st is None or t < st:
            return 1.0
        return SDCA_FACTORS[min(len(SDCA_FACTORS) - 1, (t - st) // SDCA_PHASE)]

    def bar(s, t):
        x = bars.get(s, {}).get(t)
        if x is None:
            return None
        f = fct(s, t)
        return x if f == 1.0 else tuple(v * f for v in x)

    def a1_excluded(s, b):
        m = meta.get(s)
        if m is None:
            return b > server_time
        return m["a1x"]

    book = collections.OrderedDict()   # sym -> Cluster (dang mo)
    done = []
    legs = []
    last_tick = {}
    pending_free = []   # cum thoat trong nen tm sau thoi diem quyet dinh (giai phong sau quyet dinh)
    fin_inj = {"symbol": None, "bar": None}
    qrows = []

    def used():
        return sum(c.cost for c in book.values())

    def process_bar(c, t):
        """§R6 mot nen t cho cum c (sim A3). Tra (reason, price, at_open) hoac None."""
        x = bar(c.sym, t)
        if x is None:
            return None
        O, Hh, L, Cc = x
        c.minp = min(c.minp, L)
        P_ = c.vwap
        if not c.armed and t - c.b0 > P["TSTOP_H"] * H:
            return ("TIME_STOP", min(O, Cc), True)
        if c.armed or Hh >= P_ * (1 + float(P["ARM"])):
            if not c.armed:
                rate = F((Hh - P_) / P_)
                if rate > P["ARM"]:
                    c.sl = P_ * (1 + float(trail(P, rate)))
                    c.armed = True
                    c.minp = Cc
                    return None
            else:
                if c.minp <= c.sl:
                    px = min(c.sl, O)
                    return ("TRAIL" if c.sl > P_ else "TRAIL_LOSS", px, O <= c.sl)
            rate = F((Hh - P_) / P_)
            if c.armed and rate >= P["ARM"]:
                nsl = P_ * (1 + float(trail(P, rate)))
                if nsl > c.sl and nsl > P_:
                    c.sl = nsl
                    c.minp = Cc
        return None

    def leg(b, s, level, leg_idx, rank, tm):
        """§R3 sizing + §R4 khop. Tra outcome."""
        x = bars.get(s, {}).get(b)
        if x is None or s not in last_tick:
            legs.append([b, s, level, "NO_BAR", leg_idx, "", "", "", "", ""])
            return "NO_BAR"
        ref = x[3] * fct(s, b)
        szpx = last_tick[s]
        u0 = used()
        bud = budget(P, u0, leg_idx)
        if bud is None:
            legs.append([b, s, level, "U_MAX", leg_idx, u0 / P["C"], "", "", szpx, ""])
            return "U_MAX"
        if float(bud) < MIN_BUDGET:
            legs.append([b, s, level, "BUDGET_SMALL", leg_idx, u0 / P["C"], float(bud), "", szpx, ""])
            return "BUDGET_SMALL"
        m = meta.get(s)
        qty = floor_to(float(bud) / szpx, m["step"]) if m else Decimal(0)
        notional = float(qty) * szpx
        if m is None or qty <= 0 or qty < m["minq"] or Decimal(repr(notional)) < m["mn"]:
            legs.append([b, s, level, "SIZING", leg_idx, u0 / P["C"], float(bud), str(qty), szpx, ""])
            return "SIZING"
        fill = szpx if a.venue == "FAKE" else ref
        q = float(qty)
        if leg_idx == 0:
            book[s] = Cluster(s, b, fill, q, rank)
            # nen tm (nen chua phut khop) duoc xu ly cho cum moi sau quyet dinh (khong co thoat-tai-open)
        else:
            c = book[s]
            c.qty += q
            c.cost += q * fill
            c.legs += 1
        legs.append([b, s, level, "SUBMITTED", leg_idx, u0 / P["C"], float(bud), str(qty), szpx, fill])
        return "SUBMITTED"

    for tm in range(START, END, MIN):
        # S-DCA chon cum (§R7) truoc khi xu ly nen tm
        if a.sdca_at >= 0 and not sdca_start and tm >= a.sdca_at:
            cand = [c for c in book.values() if c.legs == 1 and not c.armed]
            if len(cand) >= a.sdca_n:
                cand.sort(key=lambda c: (c.b0, c.sym))
                for c in cand[:a.sdca_n]:
                    sdca_start[c.sym] = tm
        # gia nhip luc quyet dinh = open nen tm (x he so)
        for s in bars:
            x = bar(s, tm)
            if x is not None:
                last_tick[s] = x[0]
        # nen tm cho cum dang mo: thoat tai-open giai phong TRUOC quyet dinh; con lai SAU quyet dinh
        pending_free = []
        for s in list(book.keys()):
            c = book[s]
            ex = process_bar(c, tm)
            if ex is None:
                continue
            c.exit = (tm,) + ex
            if ex[2]:
                done.append(book.pop(s))
            else:
                pending_free.append(s)
        new_syms = set()
        b = tm - MIN
        rows = sel.get(b, [])
        if b >= START and rows:
            p15 = rows[0][4]
            h = b // H * H
            pool = {}
            for row in sorted(rows, key=lambda z: z[2]):
                pool[int(np.array([row[1]], np.float32).view(np.int32)[0])] = row
            order = sorted(pool.values(), key=lambda z: z[1])
            rank = 0
            for (s, key, rk, gv, _p) in order:
                if a1_excluded(s, b):
                    continue
                if rank >= P["TOPK"]:
                    break
                rank += 1
                if s in book:   # held (so cua chinh REF)
                    continue
                full = P["SKIPFULL"] and budget(P, used(), 0) is None
                if full:
                    continue
                if h not in qcache:
                    cut = h - P["DAYS"] * DAY
                    while head < len(rec_ts) and rec_ts[head] < cut:
                        head += 1
                    arr = np.asarray(rec_r[head:], np.float32)
                    tsa = np.asarray(rec_ts[head:], np.int64)
                    arr = arr[tsa < h]
                    mm = len(arr)
                    k = min(mm - 1, max(0, int(math.floor(P["PCT"] * (mm - 1)))))
                    qcache[h] = F(np.partition(arr, k)[k])
                    qrows.append([h, float(qcache[h]), int(np.array([qcache[h]], np.float32).view(np.int32)[0])])
                q = qcache[h]
                fac = max(DYN_MIN, F(F(gv / SCORE_BASE) * DYN_MULT))
                rr = F(p15 / F(fac * P["GS"]))
                rec_ts.append(b)
                rec_r.append(rr)
                thr = F(F(q * fac) * P["GS"])
                if p15 < thr:
                    continue
                # PASS: LEGACY (C3_EXCLUDE_LEGACY_HELD=false => khong) -> fin -> leg
                if a.fin_inj_at >= 0 and fin_inj["symbol"] is None and b >= a.fin_inj_at:
                    fin_inj.update(symbol=s, bar=b)
                    legs.append([b, s, "PREDICT_SYMBOL_TRADE", "FIN_EXCL", 0, "", "", "", "", ""])
                    continue
                if bars.get(s, {}).get(b) is None:
                    legs.append([b, s, "PREDICT_SYMBOL_TRADE", "FIN_EXCL", 0, "", "", "", "", ""])
                    continue
                oc = leg(b, s, "PREDICT_SYMBOL_TRADE", 0, rank, tm)
                if oc == "SUBMITTED":
                    new_syms.add(s)
            # BIG_DOWN: bo gate (profile c3), khong A1, khong dang giu
            for s in bigdown.get(b, []):
                if a1_excluded(s, b):
                    continue
                if bars.get(s, {}).get(b) is None:
                    continue
                if s in book:
                    legs.append([b, s, "BIG_DOWN", "HOLDING", 0, "", "", "", "", ""])
                    continue
                if leg(b, s, "BIG_DOWN", 0, -1, tm) == "SUBMITTED":
                    new_syms.add(s)
            # DCA grid (§R5)
            if P["DCA"]:
                for s in sorted(book.keys()):
                    c = book[s]
                    if s in new_syms or c.exit is not None:
                        continue
                    x = bar(s, b)
                    if x is None:
                        continue
                    n = c.legs
                    if n < 1 or n > len(LEVELS):
                        continue
                    drop = F(F(F(x[3]) / F(c.first)) - F(1))
                    if drop > LEVELS[n - 1]:
                        continue
                    if p15 < P["MOM"]:   # gate DCA: thr = MIN_MOMENTUM_15M (sp null)
                        legs.append([b, s, "DCA_LEVEL1", "GATE_REJECT", n, "", "", "", "", ""])
                        continue
                    leg(b, s, "DCA_LEVEL1", n, -1, tm)
        # giai phong cum thoat trong nen tm (sau quyet dinh)
        for s in pending_free:
            if s in book and book[s].exit is not None:
                done.append(book.pop(s))
        # cum moi: xu ly phan con lai cua nen tm (khop tai open)
        for s in new_syms:
            c = book.get(s)
            if c is None or c.b0 != b:
                continue
            ex = process_bar(c, tm)
            if ex is not None and ex[0] != "TIME_STOP":
                c.exit = (tm,) + ex
                done.append(book.pop(s))
    # ket xuat
    with open(a.out + "/ref_legs.csv", "w") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["decision_ts", "symbol", "level", "outcome", "leg_idx", "u_before", "budget", "qty", "sizing_px", "fill_px"])
        w.writerows(legs)
    with open(a.out + "/ref_clusters.csv", "w") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["symbol", "b0", "first", "vwap", "legs", "qty", "exit_bar", "reason", "exit_px", "at_open", "sl"])
        for c in done + list(book.values()):
            e = c.exit or ("", "OPEN", "", "")
            w.writerow([c.sym, c.b0, c.first, c.vwap, c.legs, c.qty, e[0], e[1], e[2], e[3], c.sl if c.sl else ""])
    with open(a.out + "/ref_q.csv", "w") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["hour", "q", "q_bits"])
        w.writerows(qrows)
    summ = {"params": {k: (float(v) if isinstance(v, np.floating) else ([float(z) for z in v] if isinstance(v, list) else v))
                       for k, v in P.items()},
            "venue": a.venue, "START": START, "END": END, "legs": len(legs),
            "submitted": sum(1 for x in legs if x[3] == "SUBMITTED"),
            "clusters_exited": len(done), "clusters_open_end": len(book),
            "sdca_start": sdca_start, "fin_inj": fin_inj, "hand_values": hand_values()}
    json.dump(summ, open(a.out + "/ref_summary.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in summ.items() if k != "params"}, default=str))


if __name__ == "__main__":
    main()
