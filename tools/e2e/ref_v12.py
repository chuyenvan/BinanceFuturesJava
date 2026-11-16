#!/usr/bin/env python3
"""E2E_REPLAY_V12 - REF DOC LAP (numpy/python) viet tu DAC TA docs/c3live/E2E_REPLAY_V12_SPEC.md (prereg
PREREG_E2E_REPLAY_V12 ?3 + ERRATA1). KHONG import / goi Java. Doc: fixture + env 242 + tham so luot; va (CHI khi --fills)
file khop cua SAN (fills.csv = su that san, ERRATA1 E1/N4: "REF tinh E doc lap tu fills + gia mark cua fixture") - khong
doc quyet dinh / sizing / outcome nao cua replay.

Mo phong vong kin theo phut (spec ?R0). Thu tu tang quyet dinh = production (DetectEntrySignal2TradeNormal:433-516 /
sim Simulator:340-420): BIG_DOWN -> DCA grid nhanh "level" (chi khi BIG_DOWN) -> DCA grid nhanh "dcaAlt" (chi khi isDcaAlt)
-> selector PREDICT. Dieu kien thi truong (?R8) tu nen 1m (mkt.csv.gz) theo cong thuc SIM. Sizing ?R3 voi
C_eff = min(C3_CAPITAL, E) (?R9). Thoat ?R6.

argv: --fx DIR --env FILE --out DIR --venue FAKE|DRY --capital C --flags on|off [--sdca-at MS --sdca-n N]
      [--fin-inj-at MS] [--end MS] [--fills FILE] [--flat-ext]
Ra: <out>/ref_legs.csv, ref_clusters.csv, ref_q.csv, ref_market.csv, ref_summary.json
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
# Hang so EntryGate (spec ?R2; = docs/c3live/E2E_REPLAY.md / check_ref.py 11-05)
DYN_MIN, SCORE_BASE, DYN_MULT = F(0.26787), F(0.15), F(1.28760)
# Spec cung (prereg ?3; khong co trong env 242 => gia tri dac ta)
U_MAX_DEF = 0.6
LEVELS = [F(-0.50), F(-0.75), F(-0.90)]
SIZE_CAP = 0.045
MIN_BUDGET = 5.0
SDCA_FACTORS = [0.40, 0.20, 0.07]
SDCA_PHASE = 10 * MIN
# [ERRATA1 E5] S-DCA tong hop DIEU KIEN THI TRUONG + p15 (spec ?R7b): tinh tren nen quyet dinh b, moc st = phut chon cum
SDCA_DIP_OFFS = (2, 3, 12, 22)   # phut b - st co "dip": moi symbol KHA DUNG o b: c' = o*0.98, l' = min(l, c') (CHI dau vao thi truong)
SDCA_P15_ZERO_OFF = 2            # phut b - st: p15 thi truong := 0 (duoi MIN_MOMENTUM_15M) cho CA phut
SDCA_DIP = 0.98
# ?R8 nguong thi truong: SIM_MS_DOWN_BIG_AVG / _DCA khong dat o 242 va profile A3 => mac dinh sim Configs:511,515
MS_DEF = -0.03157
TF_UNDERLYING = {"EQUITY", "HK_EQUITY", "KR_EQUITY", "CN_EQUITY", "COMMODITY", "FX"}


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
        MS=F(float(env.get("SIM_MS_DOWN_BIG_AVG") or MS_DEF)), MSD=F(float(env.get("SIM_MS_DOWN_BIG_AVG_DCA") or MS_DEF)),
        C=float(capital), C3=float(capital), APPLY=(flags == "on"), DCA=(flags == "on"))


def budget(P, used, leg_idx):
    """?R3: b = C*F_BASE*(1-U/U_MAX)/sum(w) [* w[leg]*SCALE neu APPLY]; None = U >= U_MAX (float32 nhu sim).
    C = C_eff = min(C3_CAPITAL, E) (ERRATA1 N4) - nguoi goi dat P["C"]."""
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
    """prereg ?3: C=10000, 3 leg PREDICT lien tiep cung phut, bo lam tron qty, co BAT: 225,00 / 216,56 / 208,44."""
    P = dict(C=10000.0, F_BASE=F(0.015), U_MAX=F(0.6), W=[F(1)] * 4, SCALE=F(6.0), APPLY=True)
    used, out = 0.0, []
    for _ in range(3):
        b = float(budget(P, used, 0))
        out.append(b)
        used += b
    return out


def trail(P, rate):
    """?R6 trailRate: gap = min(rate*RATIO, GAP) (GAP_WEAK = GAP o env 242 => khong phu thuoc symbolPred);
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
        # ?R1 universe A1 (dinh nghia A1 cong bo: TRADFI = contractType chua TRADIFI/TRADFI hoac underlyingType thuoc
        #   TF_UNDERLYING; + INDEX + PREMARKET). Symbol khong co trong exinfo => loai neu phut > serverTime (fail-closed).
        a1x = ("TRADIFI" in ct or "TRADFI" in ct or ut in TF_UNDERLYING or ut in ("INDEX", "PREMARKET"))
        meta[s["symbol"]] = dict(step=step, minq=minq, mn=mn, tick=tick, status=s.get("status"), a1x=a1x)
    return meta, int(d.get("serverTime", 0))


def avg_keys(keys):
    """MarketBigChangeDetector.calRateChangeAvg(TreeMap, 100) (sim, BD_FRACTION=0): khoa DUY NHAT tang dan; period=100,
    tran size*4/5 (chia nguyen); cong float32 tuan tu toi khi counter >= period (period 0 => 1 phan tu); rong => 0."""
    n = len(keys)
    if n == 0:
        return F(0)
    period = 100
    if period > n * 4 // 5:
        period = n * 4 // 5
    cnt = min(n, max(1, period))
    tot = np.cumsum(np.asarray(keys[:cnt], np.float32), dtype=np.float32)[-1]
    return F(F(tot) / F(cnt))


class Market:
    """?R8 dieu kien thi truong theo phut, cong thuc SIM (ExportMarketData2File:96-147 + MarketBigChangeDetector:48-95,
    149-201): rate = (c-o)/o float32 moi symbol CO NEN o b (tru died); bo (btc>-0.004 & rate<-0.15) va rate>0.3;
    rateDownAvg = avg(khoa rate); rateDown15MAvg = avg(khoa (c - max15)/max15) voi max15 = max HIGH 15 nen KHA DUNG gan
    nhat (Utils.isTickerAvailable: h != l hoac qv != 0) va chi symbol KHA DUNG o b. BIG_DOWN <=> down < MS;
    isDcaAlt <=> down15 < MSD hoac down < MSD/3 (float32). Bien the 'a1' (REF chinh) = them loc universe A1 (?R1, live
    UniverseA1Filter); bien the 'all' (= sim A3 khong loc A1, AUDIT_GOLIVE_1116_D #23) chi bao cao."""

    def __init__(self, path, died, meta, server_time, ms, msd):
        import pandas as pd
        df = pd.read_csv(path, dtype={"symbol": str}, float_precision="round_trip")
        self.syms = sorted(df.symbol.unique())
        self.idx = {s: i for i, s in enumerate(self.syms)}
        self.T0 = int(df.t.min())
        self.n = int((int(df.t.max()) - self.T0) // MIN + 1)
        ns = len(self.syms)
        si = df.symbol.map(self.idx).to_numpy()
        ti = ((df.t.to_numpy(np.int64) - self.T0) // MIN).astype(np.int64)
        A = {}
        for k, col in (("o", "o"), ("h", "h"), ("l", "l"), ("c", "c"), ("q", "qv")):
            a = np.full((ns, self.n), np.nan, np.float32)
            a[si, ti] = df[col].to_numpy(np.float64).astype(np.float32)
            A[k] = a
        self.O, self.Hh, self.L, self.C, self.Q = A["o"], A["h"], A["l"], A["c"], A["q"]
        self.present = ~np.isnan(self.C)
        self.avail = self.present & ((self.Hh != self.L) | (self.Q != F(0)))
        self.max15 = np.full_like(self.C, np.nan)
        for r in range(ns):
            ix = np.nonzero(self.avail[r])[0]
            if len(ix) == 0:
                continue
            hs = self.Hh[r, ix]
            m = hs.copy()
            for k in range(1, 15):
                m[k:] = np.maximum(m[k:], hs[:-k])
            self.max15[r, ix] = m
        self.died = np.array([s in died for s in self.syms])
        self.a1x = np.array([bool(meta[s]["a1x"]) if s in meta else False for s in self.syms])
        self.inx = np.array([s in meta for s in self.syms])
        self.server_time = server_time
        self.btc = self.idx.get("BTCUSDT", -1)
        self.MS, self.MSD = F(ms), F(msd)
        self.MSD3 = F(self.MSD / F(3))

    def state(self, b, sdca, fct, dip):
        """sdca: {sym: st} (cum S-DCA bi ep gia), fct(s, t) -> he so; dip: phut b la phut dip S-DCA (?R7b)."""
        j = (b - self.T0) // MIN
        if j < 0 or j >= self.n:
            return None
        o, h, l, c = self.O[:, j].copy(), self.Hh[:, j].copy(), self.L[:, j].copy(), self.C[:, j].copy()
        mx = self.max15[:, j].copy()
        for s in sdca:
            r = self.idx.get(s)
            if r is None:
                continue
            f = fct(s, b)
            if f != 1.0 and self.present[r, j]:
                o[r], h[r], l[r], c[r] = (F(float(v) * f) for v in (o[r], h[r], l[r], c[r]))
            if self.avail[r, j]:
                ix = np.nonzero(self.avail[r, :j + 1])[0][-15:]
                mx[r] = max(F(float(self.Hh[r, k]) * fct(s, self.T0 + int(k) * MIN)) for k in ix)
        av = self.avail[:, j]
        if dip:
            c2 = (o.astype(np.float64) * SDCA_DIP).astype(np.float32)
            c = np.where(av, c2, c)
            l = np.where(av, np.minimum(l, c2), l)
        with np.errstate(all="ignore"):
            rate = ((c - o) / o).astype(np.float32)
            r15 = ((c - mx) / mx).astype(np.float32)
        btcr = float(rate[self.btc]) if self.btc >= 0 and self.present[self.btc, j] else 0.0
        r64 = rate.astype(np.float64)
        univ = self.present[:, j] & ~self.died
        a1m = ~(self.a1x | (~self.inx & (b > self.server_time)))
        out = {}
        for name, um in (("a1", univ & a1m), ("all", univ)):
            keep = um & ~((btcr > -0.004) & (r64 < -0.15)) & ~(r64 > 0.3)
            dk = np.unique(rate[keep])
            sel15 = keep & av & ~np.isnan(mx)
            k15 = np.unique(r15[sel15])
            down, down15 = avg_keys(dk), avg_keys(k15)
            out[name] = dict(down=down, down15=down15, big=bool(down < self.MS),
                             alt=bool(down15 < self.MSD or down < self.MSD3), n=int(keep.sum()), n15=int(sel15.sum()))
        return out


def load_fills(path):
    rows = []
    with open(path) as fh:
        for x in csv.DictReader(fh):
            rows.append(dict(ms=int(x["ms"]), symbol=x["symbol"], side=x["side"], qty=float(x["qty"]), price=float(x["price"]),
                             fee=float(x["fee"] or 0), cid=x["cid"]))
    rows.sort(key=lambda z: z["ms"])   # stable: giu thu tu file trong cung ms
    return rows


def equity_at(fills, t, mark, C3):
    """?R9 E(t) = C3_CAPITAL + sum rp - sum phi + UPL(mark) tu khop SAN co ms <= t (rp TU TINH = q*(px - gia vao TB);
    phi = cot fee cua san; gia vao TB = VWAP lenh MUA tu luc vi the 0; mark = gia nhip cua fixture tai t - mark(s, t)).
    = C3MainEquity.c3Equity:122-152 (funding = 0: san gia khong co funding)."""
    pos, cost = collections.defaultdict(float), collections.defaultdict(float)
    rp = fee = 0.0
    for f in fills:
        if f["ms"] > t:
            break
        s, q, px = f["symbol"], f["qty"], f["price"]
        fee += f["fee"]
        if f["side"] == "BUY":
            pos[s] += q
            cost[s] += q * px
        elif pos[s] > 0:
            avg = cost[s] / pos[s]
            rp += q * (px - avg)
            cost[s] -= q * avg
            pos[s] -= q
            if pos[s] <= 1e-12:
                pos[s], cost[s] = 0.0, 0.0
    upl = 0.0
    for s, q in pos.items():
        if q > 1e-12:
            upl += q * (mark(s, t) - cost[s] / q)
    return C3 + rp - fee + upl


def make_mark(raw_bar, fct):
    """?R9 mark(s, t) = gia nhip cua fixture tai t (= rig applyPrices: k=0 O; nen giam k1 H k2 L; nen tang k1 L k2 H; k=3 C;
    k = (t - phut)//15 s) x he so S-DCA; khong co nen o phut t => close cua nen gan nhat truoc do."""
    def mark(s, t):
        tm = t // MIN * MIN
        k = min(3, (t - tm) // 15000)
        back = 0
        x = None
        for back in range(0, 3 * 1440):
            x = raw_bar(s, tm - back * MIN)
            if x is not None:
                break
        if x is None:
            return float("nan")
        if back > 0:
            k = 3
        down = F(x[3]) < F(x[0])
        i = 0 if k == 0 else (3 if k == 3 else ((1 if down else 2) if k == 1 else (2 if down else 1)))
        return float(Decimal(repr(x[i])) * Decimal(repr(fct(s, tm - back * MIN))))
    return mark


def load_bars(fx):
    bars = collections.defaultdict(dict)
    with gzip.open(fx + "/klines.csv.gz", "rt") as fh:
        r = csv.reader(fh)
        next(r)
        for x in r:
            bars[x[0]][int(x[1])] = (float(x[2]), float(x[3]), float(x[4]), float(x[5]))
    return bars


def sdca_fct(sdca_start):
    def fct(s, t):
        st = sdca_start.get(s)
        if st is None or t < st:
            return 1.0
        return SDCA_FACTORS[min(len(SDCA_FACTORS) - 1, (t - st) // SDCA_PHASE)]
    return fct


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
    ap.add_argument("--fills", default="", help="khop SAN cua luot (E, ERRATA1 N4); trong => C_eff = C3_CAPITAL")
    ap.add_argument("--flat-ext", action="store_true", help="S-TS: sau END fixture gia dung yen = close cuoi")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    env = load_env(a.env)
    P = params(env, a.capital, a.flags)
    man = json.load(open(a.fx + "/manifest.json"))
    START, END_FX = man["START"], man["END"]
    END = END_FX if a.end < 0 else a.end
    meta, server_time = load_exinfo(a.fx + "/exinfo.json")
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
    lastc = {s: m[max(t for t in m if t < END_FX)][3] for s, m in bars.items() if any(t < END_FX for t in m)}
    bigdown = collections.defaultdict(list)
    with open(a.fx + "/bigdown.csv") as fh:
        r = csv.reader(fh)
        next(r)
        for x in r:
            bigdown[int(x[0])].append(x[1])
    if not os.path.isfile(a.fx + "/mkt.csv.gz"):
        raise SystemExit("TU CHOI: fixture thieu mkt.csv.gz (ERRATA1 N6) - dung prep_fixture --extend-from")
    mkt = Market(a.fx + "/mkt.csv.gz", set(man["mkt"]["died_symbols_sim"]), meta, server_time, P["MS"], P["MSD"])
    fills = load_fills(a.fills) if a.fills else None
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

    def raw_bar(s, t):
        x = bars.get(s, {}).get(t)
        if x is None and a.flat_ext and t >= END_FX and s in lastc:
            v = lastc[s]
            x = (v, v, v, v)
        return x

    def bar(s, t):
        x = raw_bar(s, t)
        if x is None:
            return None
        f = fct(s, t)
        return x if f == 1.0 else tuple(v * f for v in x)

    mark = make_mark(raw_bar, fct)

    def a1_excluded(s, b):
        m = meta.get(s)
        if m is None:
            return b > server_time
        return m["a1x"]

    book = collections.OrderedDict()   # sym -> Cluster (dang mo)
    done = []
    legs = []
    last_tick = {}
    fin_inj = {"symbol": None, "bar": None}
    qrows, mrows = [], []
    sd = {"st": None, "dip": [], "p15_zero": []}

    def used():
        return sum(c.cost for c in book.values())

    def process_bar(c, t):
        """?R6 mot nen t cho cum c (sim A3). Tra (reason, price, at_open) hoac None."""
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

    def leg(b, s, level, leg_idx, rank, Pm, tag=""):
        """?R3 sizing (C = C_eff cua phut) + ?R4 khop. Tra outcome."""
        x = bars.get(s, {}).get(b)
        ce, er = Pm["C"], Pm.get("E", "")
        if x is None or s not in last_tick:
            legs.append([b, s, level, "NO_BAR", leg_idx, "", "", "", "", "", ce, er, tag])
            return "NO_BAR"
        ref = x[3] * fct(s, b)
        szpx = last_tick[s]
        u0 = used()
        bud = budget(Pm, u0, leg_idx)
        if bud is None:
            legs.append([b, s, level, "U_MAX", leg_idx, u0 / ce, "", "", szpx, "", ce, er, tag])
            return "U_MAX"
        if float(bud) < MIN_BUDGET:
            legs.append([b, s, level, "BUDGET_SMALL", leg_idx, u0 / ce, float(bud), "", szpx, "", ce, er, tag])
            return "BUDGET_SMALL"
        m = meta.get(s)
        qty = floor_to(float(bud) / szpx, m["step"]) if m else Decimal(0)
        notional = float(qty) * szpx
        if m is None or qty <= 0 or qty < m["minq"] or Decimal(repr(notional)) < m["mn"]:
            legs.append([b, s, level, "SIZING", leg_idx, u0 / ce, float(bud), str(qty), szpx, "", ce, er, tag])
            return "SIZING"
        fill = szpx if a.venue == "FAKE" else ref
        q = float(qty)
        if leg_idx == 0:
            book[s] = Cluster(s, b, fill, q, rank)
        else:
            c = book[s]
            c.qty += q
            c.cost += q * fill
            c.legs += 1
        legs.append([b, s, level, "SUBMITTED", leg_idx, u0 / ce, float(bud), str(qty), szpx, fill, ce, er, tag])
        return "SUBMITTED"

    def dca_pass(b, p15, tag, new_syms, Pm):
        """?R5 DCA grid (sim DcaProcessor.getDCA nhanh DCA_GRID_ENABLED) + cong p15 phang (N2): chi goi o phut co dieu kien."""
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
            if p15 < P["MOM"]:   # gate DCA: thr = MIN_MOMENTUM_15M (sp null) - sim createOrder:2286-2301
                legs.append([b, s, "DCA_LEVEL1", "GATE_REJECT", n, "", "", "", "", "", Pm["C"], Pm.get("E", ""), tag])
                continue
            leg(b, s, "DCA_LEVEL1", n, -1, Pm, tag)

    for tm in range(START, END, MIN):
        # S-DCA chon cum (?R7) truoc khi xu ly nen tm
        if a.sdca_at >= 0 and not sdca_start and tm >= a.sdca_at:
            cand = [c for c in book.values() if c.legs == 1 and not c.armed]
            if len(cand) >= a.sdca_n:
                cand.sort(key=lambda c: (c.b0, c.sym))
                for c in cand[:a.sdca_n]:
                    sdca_start[c.sym] = tm
                sd["st"] = tm
        for s in bars:
            x = bar(s, tm)
            if x is not None:
                last_tick[s] = x[0]
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
            st = sd["st"]
            off = (b - st) // MIN if st is not None and b >= st else None
            if off == SDCA_P15_ZERO_OFF:
                p15 = F(0)
                sd["p15_zero"].append(b)
            dip = off in SDCA_DIP_OFFS
            if dip:
                sd["dip"].append(b)
            ms = mkt.state(b, sdca_start, fct, dip)
            mA = ms["a1"] if ms else None
            Pm = dict(P)
            if fills is not None:
                E = equity_at(fills, tm, mark, P["C3"])
                Pm["E"] = E
                Pm["C"] = min(P["C3"], E)
            mrows.append([b, float(p15), int(dip)] + ([float(mA["down"]), float(mA["down15"]), int(mA["big"]), int(mA["alt"]),
                                                        mA["n"], float(ms["all"]["down"]), float(ms["all"]["down15"]),
                                                        int(ms["all"]["big"]), int(ms["all"]["alt"]), ms["all"]["n"]]
                                                       if mA else [""] * 10))
            # 1. BIG_DOWN (shadow log): bo gate (profile c3), khong A1, khong dang giu
            for s in bigdown.get(b, []):
                if a1_excluded(s, b):
                    continue
                if bars.get(s, {}).get(b) is None:
                    continue
                if s in book:
                    legs.append([b, s, "BIG_DOWN", "HOLDING", 0, "", "", "", "", "", Pm["C"], Pm.get("E", ""), ""])
                    continue
                if leg(b, s, "BIG_DOWN", 0, -1, Pm) == "SUBMITTED":
                    new_syms.add(s)
            # 2-3. DCA grid CHI o phut co dieu kien thi truong (N6): nhanh level (BIG_DOWN) roi nhanh dcaAlt
            if P["DCA"] and mA:
                if mA["big"]:
                    dca_pass(b, p15, "level", new_syms, Pm)
                if mA["alt"]:
                    dca_pass(b, p15, "dcaAlt", new_syms, Pm)
            # 4. selector PREDICT
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
                full = P["SKIPFULL"] and budget(Pm, used(), 0) is None
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
                if a.fin_inj_at >= 0 and fin_inj["symbol"] is None and b >= a.fin_inj_at:
                    fin_inj.update(symbol=s, bar=b)
                    legs.append([b, s, "PREDICT_SYMBOL_TRADE", "FIN_EXCL", 0, "", "", "", "", "", Pm["C"], Pm.get("E", ""), ""])
                    continue
                if bars.get(s, {}).get(b) is None:
                    legs.append([b, s, "PREDICT_SYMBOL_TRADE", "FIN_EXCL", 0, "", "", "", "", "", Pm["C"], Pm.get("E", ""), ""])
                    continue
                oc = leg(b, s, "PREDICT_SYMBOL_TRADE", 0, rank, Pm)
                if oc == "SUBMITTED":
                    new_syms.add(s)
        for s in pending_free:
            if s in book and book[s].exit is not None:
                done.append(book.pop(s))
        for s in new_syms:
            c = book.get(s)
            if c is None or c.b0 != b:
                continue
            ex = process_bar(c, tm)
            if ex is not None and ex[0] != "TIME_STOP":
                c.exit = (tm,) + ex
                done.append(book.pop(s))
    with open(a.out + "/ref_legs.csv", "w") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["decision_ts", "symbol", "level", "outcome", "leg_idx", "u_before", "budget", "qty", "sizing_px", "fill_px",
                    "c_eff", "e_ref", "dca_tag"])
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
    with open(a.out + "/ref_market.csv", "w") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["b", "p15", "dip", "down_a1", "down15_a1", "big_a1", "alt_a1", "n_a1", "down_all", "down15_all", "big_all",
                    "alt_all", "n_all"])
        w.writerows(mrows)
    mk = [r for r in mrows if r[3] != ""]
    summ = {"params": {k: (float(v) if isinstance(v, np.floating) else ([float(z) for z in v] if isinstance(v, list) else v))
                       for k, v in P.items()},
            "venue": a.venue, "START": START, "END": END, "legs": len(legs),
            "submitted": sum(1 for x in legs if x[3] == "SUBMITTED"),
            "dca_submitted": sum(1 for x in legs if x[3] == "SUBMITTED" and x[2] == "DCA_LEVEL1"),
            "clusters_exited": len(done), "clusters_open_end": len(book),
            "sdca_start": sdca_start, "sdca_synth": sd, "fin_inj": fin_inj, "hand_values": hand_values(),
            "market": {"minutes": len(mk), "big_a1": sum(r[5] for r in mk), "alt_a1": sum(r[6] for r in mk),
                       "big_all": sum(r[10] for r in mk), "alt_all": sum(r[11] for r in mk),
                       "flag_a1_ne_all": sum(1 for r in mk if (r[5], r[6]) != (r[10], r[11]))},
            "fills_used": a.fills or None, "flat_ext": a.flat_ext,
            "c_eff_min": min((x[10] for x in legs if x[3] == "SUBMITTED"), default=None)}
    json.dump(summ, open(a.out + "/ref_summary.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in summ.items() if k != "params"}, default=str))


if __name__ == "__main__":
    main()
