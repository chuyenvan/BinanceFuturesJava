#!/usr/bin/env python3
"""reaudit_short_v3_r2b_raw.py — REAUDIT R2B tai lap tren du lieu tho (CHI DOC; DEV <= 2025-12-31).
(i) stale/ffill cuoi chuoi CLOSES_1H; (ii) listing_day D0 vs phut 1m dau tien trong Aerospike kline_1m_opt;
(iii) D0 net1m sau khi loai 16 symbol nhiem (dung arm_stats cua short_v3_r2b_listing1m.py tren trades JSON R2B).
"""
import json, logging, sys, time
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import short_v3_r2_listing as R
import short_v3_r2_slcheck as SC
import short_v3_r2b_listing1m as RB

log = logging.getLogger("reaudit_r2b")
H, DAY, MIN = R.H, R.DAY, 60000
STALE = ["FTMUSDT", "MATICUSDT", "EOSUSDT", "MKRUSDT", "BNXUSDT", "KLAYUSDT", "RNDRUSDT", "GALUSDT", "ALPACAUSDT"]
SAMP = ["JASMY", "HOOK", "AMB", "HFT", "MAV", "ORDI", "ILV", "LSK", "STRK", "BANANA", "SAFE", "VTHO", "BID", "SXT",
        "OBOL", "AIN", "EVAA", "BLUAI", "MMT", "WET"]
REN = ['RENDERUSDT', 'POLUSDT', 'KAIAUSDT', 'SUSDT', 'AUSDT', 'SKYUSDT', 'GUSDT', 'FORMUSDT']
IDX = ['FOOTBALLUSDT', 'BLUEBIRDUSDT', 'PAXGUSDT', 'XAUUSDT']
REL = ['1000LUNCUSDT', 'USTCUSDT', 'BSVUSDT', 'RAYSOLUSDT']
OUT = "/home/ubuntu/claude_master/1002/reaudit_r2b_raw.json"


def ts_s(ms):
    return None if ms is None else str(pd.Timestamp(int(ms), unit="ms"))


def part_i(C, names, t_start):
    out = {}
    n2j = {n: j for j, n in enumerate(names)}
    file_last = t_start + (C.shape[0] - 1) * H
    for s in STALE:
        if s not in n2j:
            out[s] = "absent"; continue
        c = C[:, n2j[s]].astype(np.float64); f = np.where(np.isfinite(c))[0]
        k0, k1 = int(f[0]), int(f[-1]); last = c[k1]
        k = k1  # duoi phang: bo qua NaN, dung khi gap gia tri huu han khac last
        while k - 1 >= k0 and (not np.isfinite(c[k - 1]) or c[k - 1] == last):
            k -= 1
        while not np.isfinite(c[k]):
            k += 1
        flat_tail = k1 - k  # so gio tu gio dau tien cua doan phang cuoi toi gio cuoi
        cf = c[f]; same = np.concatenate([[False], cf[1:] == cf[:-1]])
        best, bs, rs = 0, 0, 0
        for q in range(1, len(cf)):
            if same[q]:
                if not same[q - 1]: rs = q - 1
                if q - rs > best: best, bs = q - rs, rs
        mfr = dict(len_obs=int(best), start=ts_s(t_start + int(f[bs]) * H), end=ts_s(t_start + int(f[bs + best]) * H))
        d = np.diff(c[k0:k1 + 1]); fd = d[np.isfinite(d)]
        runs, r = [], 0
        for v in fd:
            r = r + 1 if v == 0 else 0; runs.append(r)
        out[s] = dict(first_ts=ts_s(t_start + k0 * H), last_ts=ts_s(t_start + k1 * H), n_hours=int(len(f)),
                      n_nan_inside=int((k1 - k0 + 1) - len(f)), last_close=float(last), flat_tail_h=int(flat_tail),
                      flat_tail_start=ts_s(t_start + k * H), max_flat_run_h=int(max(runs) if runs else 0), max_flat_run=mfr,
                      frac_zero_ret=float((fd == 0).mean()) if len(fd) else None,
                      last_is_file_end=bool(k1 == C.shape[0] - 1))
        log.info("(i) %s %s", s, out[s])
    return out, ts_s(file_last)


def aero_hits(cli, sym, t_list):
    """t_list: UTC ms phut; key Aerospike = gio UTC+7 (nhu SC.fetch). Tra list t co sym trong record."""
    pats = {sym: b"\x0a" + bytes([len(sym)]) + sym.encode() + b"\x12"}
    hits, miss = [], 0
    for b in range(0, len(t_list), 1000):
        ch = t_list[b:b + 1000]
        keys = [("test", "kline_1m_opt", (pd.Timestamp(t, unit="ms") + pd.Timedelta(hours=7)).strftime("%Y%m%d-%H%M"))
                for t in ch]
        for t, rr in zip(ch, cli.batch_read(keys).batch_records):
            if rr.result != 0 or rr.record is None or not rr.record[2] or "data" not in rr.record[2]:
                miss += 1; continue
            ex = SC.extract(bytes(SC_dec(rr.record[2]["data"])), pats)
            if sym in ex:
                hits.append((t, ex[sym]))
    return hits, miss


def SC_dec(x):
    import cramjam
    return cramjam.snappy.decompress_raw(x)


def part_ii(T, C, names, t_start):
    import aerospike
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    n2j = {n: j for j, n in enumerate(names)}
    out = {}
    for b in SAMP:
        cand = sorted({s for s in T.sym if s == b + "USDT"} or {s for s in T.sym if s.endswith(b + "USDT")})
        if not cand:
            out[b] = "khong co trong trades D0/D1"; continue
        s = cand[0]; D0 = int(pd.Timestamp(str(T[T.sym == s].D0.iloc[0])).value // 10**6 // DAY)
        j = n2j[s]; f = np.where(np.isfinite(C[:, j]))[0]
        first1h = t_start + int(f[0]) * H
        lo = (D0 - 45) * DAY; hi = (D0 + 3) * DAY
        coarse = list(range(lo, hi, 10 * MIN))
        hits, miss = aero_hits(cli, s, coarse)
        rec = dict(sym=s, D0=R.dstr(D0), first_1h_closes=ts_s(first1h), coarse_miss_rec=miss, n_coarse_hits=len(hits))
        if hits:
            tc = hits[0][0]
            fine, _ = aero_hits(cli, s, list(range(tc - 10 * MIN, tc + MIN, MIN)))
            t1 = fine[0][0] if fine else tc
            rec.update(first_1m=ts_s(t1), first_1m_ohlc=[float(x) for x in (fine[0][1] if fine else hits[0][1])[:4]],
                       lag_min_vs_D0=int((t1 - D0 * DAY) // MIN), first_1m_day=R.dstr(t1 // DAY),
                       hit_at_window_start=bool(hits[0][0] == lo), day_match=bool(t1 // DAY == D0), hits_before_D0=int(sum(1 for t, _ in hits if t < D0 * DAY)))
        out[b] = rec
        log.info("(ii) %s", rec)
    return out


def part_iii(r):
    out = {}
    for arm in ("D0", "D1"):
        d = pd.DataFrame(r["trades"][arm]); dt = pd.to_datetime(d.t0, unit="ms"); d["mi"] = (dt.dt.year - 2022) * 12 + dt.dt.month - 1
        for tag, ex in (("all", []), ("-REN8", REN), ("-REN8-IDX4", REN + IDX), ("-16", REN + IDX + REL)):
            g = d[~d.sym.isin(ex)].reset_index(drop=True)
            a = RB.arm_stats(g, "net1m", "sl1m", "fund1m")
            out["%s %s" % (arm, tag)] = dict(n=int(len(g)), n_removed=int(len(d) - len(g)), mean=a["all"]["mean"],
                                              ci_raw=a["all"]["ci_raw"], ci_infl=a["all"]["ci_infl"],
                                              years_pos=a["GO"]["G2_years_pos"], drop10=a["GO"]["G5_drop10_mean"],
                                              excess=a["all"]["excess_mean"], sl_rate=a["all"]["sl_rate"],
                                              GO=a["GO"]["PASS"])
            log.info("(iii) %s %s", "%s %s" % (arm, tag), out["%s %s" % (arm, tag)])
        out[arm + " present16"] = sorted(set(d.sym) & set(REN + IDX + REL))
    return out


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    t0 = time.time()
    r = json.load(open(RB.OUT_JSON))
    T = pd.concat([pd.DataFrame(r["trades"][a]) for a in ("D0", "D1")], ignore_index=True)
    res = dict(src=RB.OUT_JSON, json_D0_mean=r["strategy"]["D0"]["all"]["mean"])
    res["iii"] = part_iii(r)
    C, names, t_start, info = R.load_hourly()
    res["i"], res["i_file_last_row"] = part_i(C, names, t_start)
    res["ii"] = part_ii(T, C, names, t_start)
    json.dump(res, open(OUT, "w"), indent=1, default=str)
    log.info("WROTE %s %.0fs", OUT, time.time() - t0)


if __name__ == "__main__":
    main()
