#!/usr/bin/env python3
"""short_v3_r2_slcheck.py — KIEM DINH FIDELITY (post-hoc, KHONG vao luat GO) cho R2 PROGRAM_SHORT_V3.

Cung lenh (D0, D1) cua short_v3_r2_listing.py, nhung SL +15% kiem tren HIGH 1m (Aerospike test.kline_1m_opt) nhu mot
stop-market that: fill = max(1,15*P0, open phut cham) + truot 0,2%; funding cat tai phut thoat. Khong SL => giong ban chinh.
Muc dich: do do lech cua quy uoc "SL kiem tren close 1h, fill tai muc" (khai o pre-reg §10 la lac quan). Out: them khoa
`posthoc_SL1m` vao docs/result/RESULT_SHORT_V3_R2.json; bang -> ~/claude_master/1002/r2_slcheck.md
"""
import json, logging, os, struct, sys, time
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import short_v3_r2_listing as R
from short_state_0sim import _rd_varint

log = logging.getLogger("r2sl")
MIN = 60000
NM = R.HOLD * 60


def extract(buf, pats):
    """pats: {sym: pattern} -> {sym: (open, high, low, close)} chi cho sym co mat trong record."""
    out = {}
    for s, p in pats.items():
        i = buf.find(p)
        if i < 0:
            continue
        j = i + len(p)
        vl, j = _rd_varint(buf, j); end = j + vl
        f = [np.nan] * 6
        while j < end:
            t, j = _rd_varint(buf, j); fn = t >> 3; w = t & 7
            if w == 5:
                if fn < 6:
                    f[fn] = struct.unpack("<f", buf[j:j + 4])[0]
                j += 4
            elif w == 0:
                _, j = _rd_varint(buf, j)
            elif w == 2:
                l2, j = _rd_varint(buf, j); j += l2
            elif w == 1:
                j += 8
            else:
                break
        out[s] = (f[1], f[2], f[3], f[4])
    return out


def fetch(trades):
    """trades: list (sym, t0). Tra O, Hh, Cc: (ntr, NM) float32; phut m <-> open = t0 + m*MIN."""
    import aerospike, cramjam
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    dec = cramjam.snappy.decompress_raw
    ntr = len(trades)
    O = np.full((ntr, NM), np.nan, np.float32); Hh = O.copy(); Cc = O.copy()
    byday = {}
    for ti, (s, t0) in enumerate(trades):
        for d in range(t0 // R.DAY, (t0 + NM * MIN - 1) // R.DAY + 1):
            byday.setdefault(d, []).append(ti)
    log.info("trades=%d unique days=%d", ntr, len(byday))
    t00 = time.time(); nrec_miss = 0
    for n, d in enumerate(sorted(byday)):
        tis = byday[d]
        pats = {trades[ti][0]: b"\x0a" + bytes([len(trades[ti][0])]) + trades[ti][0].encode() + b"\x12" for ti in tis}
        base = pd.Timestamp(d * R.DAY, unit="ms") + pd.Timedelta(hours=7)
        keys = [("test", "kline_1m_opt", (base + pd.Timedelta(minutes=k)).strftime("%Y%m%d-%H%M")) for k in range(1440)]
        for k, rr in enumerate(cli.batch_read(keys).batch_records):
            if rr.result != 0 or rr.record is None or not rr.record[2] or "data" not in rr.record[2]:
                nrec_miss += 1; continue
            ex = extract(bytes(dec(rr.record[2]["data"])), pats)
            tm = d * R.DAY + k * MIN
            for ti in tis:
                s, t0 = trades[ti]
                m = (tm - t0) // MIN
                if 0 <= m < NM and s in ex:
                    o, h, l, c = ex[s]; O[ti, m] = o; Hh[ti, m] = h; Cc[ti, m] = c
        if n % 100 == 0:
            log.info("day %d/%d %s %.0fs miss=%d", n, len(byday), R.dstr(d), time.time() - t00, nrec_miss)
    return O, Hh, Cc, nrec_miss


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    C, names, t_start, _ = R.load_hourly()
    fund = R.Fund()
    L, gap, S1, ucols, fl, lastc = R.find_listings(C, names, t_start, {})
    D, excl = R.build_arms(C, names, t_start, L, ucols, fund)
    n2j = {n: j for j, n in enumerate(names)}
    uniq = sorted({(r.sym, int(r.t0)) for arm in D for r in D[arm].itertuples()}, key=lambda x: x[1])
    O, Hh, Cc, miss = fetch(uniq)
    idx = {u: i for i, u in enumerate(uniq)}
    # sanity: close 1m phut cuoi moi gio vs CLOSES_1H ; high >= max(open, close)
    rel = []; viol = 0; tot = 0
    for (s, t0), i in idx.items():
        k0 = (t0 - t_start) // R.H; j = n2j[s]
        c1 = Cc[i, 59::60].astype(float); ch = C[k0 + 1:k0 + R.HOLD + 1, j].astype(float)
        ok = np.isfinite(c1) & np.isfinite(ch)
        rel.append(np.abs(c1[ok] / ch[ok] - 1))
        f = np.isfinite(Hh[i]) & np.isfinite(O[i]) & np.isfinite(Cc[i])
        viol += int((Hh[i][f] < np.maximum(O[i][f], Cc[i][f]) - 1e-9).sum()); tot += int(f.sum())
    rel = np.concatenate(rel)
    san = dict(n_uniq=len(uniq), rec_miss=miss, frac_min_nan=float(np.isnan(Hh).mean()), n_hour_pairs=int(len(rel)),
               close_rel_med=float(np.median(rel)), close_frac_gt_1e4=float((rel > 1e-4).mean()),
               high_viol_frac=float(viol / max(tot, 1)))
    log.info("sanity %s", san)
    assert san["close_frac_gt_1e4"] < 0.01 and san["high_viol_frac"] < 0.001, "1m parse sai field"
    out = dict(note="POST-HOC fidelity check, KHONG vao luat GO; SL +15% tren HIGH 1m, fill max(muc, open)+0,2%", sanity=san)

    md = ["| nhánh | n | SL-rate 1h | SL-rate 1m | net mean 1h (chính) | net mean 1m | net med 1m | CI raw 1m | CI infl 1m | năm dương 1m | lỗ SL TB 1m |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm, df in D.items():
        p1m, sl1m, loss = [], [], []
        ninc = 0
        for r in df.itertuples():
            i = idx[(r.sym, int(r.t0))]
            lvl = (1 + R.SL_X) * r.P0
            hit = np.where(np.nan_to_num(Hh[i], nan=-1.0) >= lvl)[0]
            if len(hit) == 0:
                if r.sl:
                    ninc += 1
                p1m.append(r.pnl); sl1m.append(bool(r.sl)); continue
            m = int(hit[0]); o = float(O[i, m])
            fill = max(lvl, o) if np.isfinite(o) else lvl
            ls = fill / r.P0 - 1 + R.SLIP
            _, _, f, _, _ = fund.window(r.sym, int(r.t0), int(r.t0) + (m + 1) * MIN)
            p1m.append(-ls - R.FEE + f); sl1m.append(True); loss.append(ls)
        g = df.copy(); g["pnl1m"] = p1m; g["sl1m"] = sl1m
        ci_r, ci_i = R.ci_block(g.pnl1m.to_numpy(float), g.mi.to_numpy(), 48)
        yrs = {str(y): float(g[g.year == y].pnl1m.mean()) for y in R.YEARS}
        a = dict(n=len(g), sl_rate_1h=float(g.sl.mean()), sl_rate_1m=float(g.sl1m.mean()), mean_1h=float(g.pnl.mean()),
                 mean_1m=float(g.pnl1m.mean()), med_1m=float(g.pnl1m.median()), ci_raw_1m=ci_r, ci_infl_1m=ci_i, by_year_1m=yrs,
                 years_pos_1m=int(sum(v > 0 for v in yrs.values())), sl_loss_mean_1m=float(np.mean(loss)) if loss else None,
                 sl_loss_p90_1m=float(np.percentile(loss, 90)) if loss else None, n_sl1h_no1mhit=ninc)
        out[arm] = a
        md.append("| %s | %d | %.1f | %.1f | %s | **%s** | %s | %s | %s | %d/4 | %s |" % (
            arm, a["n"], 100 * a["sl_rate_1h"], 100 * a["sl_rate_1m"], R.pc(a["mean_1h"]), R.pc(a["mean_1m"]), R.pc(a["med_1m"]),
            R.ci_s(ci_r), R.ci_s(ci_i), a["years_pos_1m"], R.pc(a["sl_loss_mean_1m"])))
        md.append("|  | theo năm 1m: %s |" % " · ".join("%s %s" % (y, R.pc(v)) for y, v in yrs.items()))
    res = json.load(open(R.OUT_JSON))
    res["posthoc_SL1m"] = out
    json.dump(res, open(R.OUT_JSON, "w"), indent=1, ensure_ascii=False)
    open("/home/ubuntu/claude_master/1002/r2_slcheck.md", "w").write("\n".join(md))
    log.info("posthoc %s", json.dumps(out))
    print("\n".join(md))


if __name__ == "__main__":
    main()
