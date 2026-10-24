"""LIQX_S1 V3 — INDEPENDENT minimal re-implementation (imports nothing from the pipeline).
From raw kline/metrics: universe (median 30d qv), per-(sym,day) create_time convention, I_mkt / r_mkt / cum60_mkt / n_valid,
MKT validity (7d trailing median), then ONSET/EXH with theta_MKT (number read from thresholds.json).
Compares with S1/mkt.parquet and S1/episodes.parquet only at the end. Usage: python3 v3_indep.py 2022-05-12 2022-06-13 ..."""
import json
import sys
import numpy as np
import pyarrow.parquet as pq
import pandas as pd

S1 = "/home/ubuntu/claude_master/liqx_wk/s1"
KLP = "/home/ubuntu/vz_e1/raw/kline1m-{}.parquet"
MTP = "/home/ubuntu/vz/out/metrics5m/{}/{}.parquet"
MIN, FIVE, DAYMS = 60000, 300000, 86400000
BAD = ["USDCUSDT", "BTCDOMUSDT", "DEFIUSDT", "FOOTBALLUSDT", "BLUEBIRDUSDT", "PAXGUSDT", "XAUUSDT"]


def utc(s):
    return int(np.datetime64(s, "ms").astype(np.int64))


def ym_list(a, b):
    out, t = [], np.datetime64(a, "ms").astype("datetime64[M]")
    while t.astype("datetime64[ms]").astype(np.int64) < b:
        out.append(str(t))
        t = t + 1
    return out


def load(path_fmt, cols, a, b, syms=None, metrics=False):
    parts = []
    for ym in ym_list(a, b):
        p = path_fmt.format(ym[:4], ym) if metrics else path_fmt.format(ym)
        f = pq.ParquetFile(p)
        for i in range(f.num_row_groups):
            t = f.read_row_group(i, columns=cols)
            ts = t.column("ts").to_numpy()
            if ts.max() < a or ts.min() >= b:
                continue
            d = t.to_pandas()
            d["sym"] = d["sym"].astype(str)
            d = d[(d.ts >= a) & (d.ts < b)]
            if syms is not None:
                d = d[d.sym.isin(syms)]
            parts.append(d)
    return pd.concat(parts, ignore_index=True)


def top100(M):
    a, b, parts = M - 30 * DAYMS, M, []
    for ym in ym_list(a, b):
        f = pq.ParquetFile(KLP.format(ym))
        for i in range(f.num_row_groups):
            d = f.read_row_group(i, columns=["ts", "sym", "quote_volume"]).to_pandas()
            d = d[(d.ts >= a) & (d.ts < b)]
            if len(d):
                d["sym"] = d["sym"].astype(str)
                d["d"] = d.ts // DAYMS
                parts.append(d.groupby(["sym", "d"]).quote_volume.sum())
    q = pd.concat(parts).groupby(level=[0, 1]).sum()
    dd = np.arange(M // DAYMS - 30, M // DAYMS)
    sc = {}
    for s, g in q.groupby(level=0):
        if s in BAD:
            continue
        v = g.droplevel(0).reindex(dd).fillna(0.0).values
        sc[s] = float(np.median(v))
    return [s for s, _ in sorted(sc.items(), key=lambda kv: (-kv[1], kv[0]))[:100]]


def per_sym(k, m, a, nbk):
    """k: kline rows of one sym, m: metrics rows of one sym. Grid minutes from a. Returns dict of bucket arrays."""
    nmin = nbk * 5 + 24 * 60 * 3
    G = {c: np.full(nmin, np.nan) for c in ("close", "volume", "taker_buy_base", "quote_volume", "taker_buy_quote")}
    ix = ((k.ts.values - a) // MIN).astype(np.int64)
    ok = (ix >= 0) & (ix < nmin)
    for c in G:
        G[c][ix[ok]] = k[c].values[ok]
    # 5m taker ratio by window start (index in minutes)
    def win(arr, j):  # sums of 5 minutes starting at minute j (array), NaN if any missing
        idx = j[:, None] + np.arange(5)[None, :]
        good = (idx >= 0).all(1) & (idx < nmin).all(1)
        out = np.full(len(j), np.nan)
        v = arr[np.clip(idx, 0, nmin - 1)]
        s = v.sum(1)
        out[good & np.isfinite(s)] = s[good & np.isfinite(s)]
        return out
    # V3b: create_time off the 5' grid (BNXUSDT 2022-06..2023-01, TLMUSDT 2022-06; 0.08% rows) cannot be matched to a
    # 5' window or bucket -> excluded (spec detail made explicit after V3 run 1 mismatch, see result §V3)
    # a day that has rows but none on-grid is still a classified day (-> AMBIG), not a missing day
    all_days = np.unique(m.ts.values // DAYMS)
    m = m[m.ts.values % FIVE == 0]
    c = m.ts.values
    jc = ((c - a) // MIN).astype(np.int64)
    x = m.taker_ls_vol.values
    conv_day = {}
    days = c // DAYMS
    for dd in all_days:
        sel = days == dd
        tbo, vo = win(G["taker_buy_base"], jc[sel] - 5), win(G["volume"], jc[sel] - 5)
        tbn, vn = win(G["taker_buy_base"], jc[sel]), win(G["volume"], jc[sel])
        with np.errstate(invalid="ignore", divide="ignore"):
            eo = np.abs(x[sel] / (tbo / (vo - tbo)) - 1)
            en = np.abs(x[sel] / (tbn / (vn - tbn)) - 1)
        both = (np.isfinite(eo) & np.isfinite(en) & (x[sel] > 0) & (tbo > 0) & (vo - tbo > 0) & (tbn > 0) & (vn - tbn > 0))
        verdict = "AMBIG"
        if both.sum() >= 12:
            mo, mn = np.median(eo[both]), np.median(en[both])
            if mn < mo / 10:
                verdict = "NEW"
            elif mo < mn / 10:
                verdict = "OLD"
        if verdict == "AMBIG":
            p = m.oi_value.values[sel] / m.oi.values[sel]
            jo, jn = jc[sel] - 1, jc[sel] + 4
            co = np.where((jo >= 0) & (jo < nmin), G["close"][np.clip(jo, 0, nmin - 1)], np.nan)
            cn = np.where((jn >= 0) & (jn < nmin), G["close"][np.clip(jn, 0, nmin - 1)], np.nan)
            okp = np.isfinite(p) & (m.oi.values[sel] > 0) & np.isfinite(co) & np.isfinite(cn)
            if okp.sum() >= 144:
                po, pn = np.median(np.abs(p[okp] / co[okp] - 1)), np.median(np.abs(p[okp] / cn[okp] - 1))
                if pn < po / 3:
                    verdict = "NEW"
                elif po < pn / 3:
                    verdict = "OLD"
        conv_day[int(dd)] = verdict
    # effective ts
    eff = {}
    dup = set()
    for ci, ov, d in zip(c, m.oi_value.values, days):
        cur, prev = conv_day.get(int(d), "MISSING"), conv_day.get(int(d) - 1, "MISSING")
        u = cur
        if ci % DAYMS == 0:
            if prev == "OLD":
                if cur == "NEW":
                    continue
                u = "OLD"
            elif prev == "AMBIG":
                continue
        if u not in ("OLD", "NEW"):
            continue
        te = int(ci + (FIVE if u == "NEW" else 0))
        if te in eff:
            dup.add(te)
        eff[te] = ov
    for te in dup:
        eff.pop(te, None)
    return G, eff, conv_day


def main():
    targets = sys.argv[1:]
    th = json.load(open(S1 + "/thresholds.json"))["mkt"]["99.0"]
    K = pd.read_parquet(S1 + "/mkt.parquet").set_index("T")
    E = pd.read_parquet(S1 + "/episodes.parquet")
    E = E[(E.level == "MKT") & (E.variant == "main")]
    report = []
    for day in targets:
        D = utc(day)
        a = D - 8 * DAYMS            # grid start (7d history for validity + 1d detection)
        b = D + 2 * DAYMS
        nbk = (b - a) // FIVE
        Tg = a + FIVE * np.arange(1, nbk + 1, dtype=np.int64)
        months = sorted({str(np.datetime64(t, "ms").astype("datetime64[M]")) for t in (a, b - 1)})
        acc = {k: np.zeros(nbk) for k in ("sP2", "sOIV0", "nv", "sr", "nr", "sc", "nc")}
        for ym in months:
            M = utc(ym + "-01")
            Mn = int((np.datetime64(ym, "M") + 1).astype("datetime64[ms]").astype(np.int64))
            U = top100(M)
            k = load(KLP, ["ts", "sym", "close", "volume", "taker_buy_base", "quote_volume", "taker_buy_quote"], a, b + 3 * DAYMS, set(U))
            mt = load(MTP, ["ts", "sym", "oi", "oi_value", "taker_ls_vol"], a - DAYMS, b + DAYMS, set(U), metrics=True)
            mt = mt.sort_values(["sym", "ts"]).drop_duplicates(["sym", "ts"], keep="last")
            inm = (Tg - 1) // DAYMS * DAYMS
            inm = (inm >= M) & (inm < Mn)
            for s in U:
                ks, ms_ = k[k.sym == s], mt[mt.sym == s]
                if not len(ks) or not len(ms_):
                    continue
                G, eff, _ = per_sym(ks.sort_values("ts"), ms_, a, nbk)
                for i in np.flatnonzero(inm):
                    T = int(Tg[i])
                    j = (T - a) // MIN
                    o0, o1 = eff.get(T - FIVE), eff.get(T)
                    c1, c0, c60 = G["close"][j - 1], G["close"][j - 6], G["close"][j - 61] if j - 61 >= 0 else np.nan
                    qv, tq = G["quote_volume"][j - 5:j], G["taker_buy_quote"][j - 5:j]
                    if o0 is None or o1 is None or not (o0 > 0) or not np.isfinite(o1) or not np.isfinite(c1) or not np.isfinite(c0) \
                            or not np.isfinite(qv).all() or not np.isfinite(tq).all() or j - 6 < 0:
                        continue
                    r5 = np.log(c1 / c0)
                    p2 = min(max(0.0, o0 - o1), max(0.0, qv.sum() - 2 * tq.sum())) if r5 < 0 else 0.0
                    acc["sP2"][i] += p2
                    acc["sOIV0"][i] += o0
                    acc["nv"][i] += 1
                    if s not in ("BTCUSDT", "ETHUSDT"):
                        acc["sr"][i] += r5
                        acc["nr"][i] += 1
                        if np.isfinite(c60):
                            acc["sc"][i] += np.log(c1 / c60)
                            acc["nc"][i] += 1
        nv = acc["nv"]
        med = pd.Series(nv).rolling(2016, min_periods=1).median().values
        okm = (nv >= 0.85 * med) & (nv > 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            I = np.where(okm, acc["sP2"] / acc["sOIV0"], np.nan)
            rm = np.where(okm & (acc["nr"] > 0), acc["sr"] / acc["nr"], np.nan)
            cm = np.where(okm & (acc["nc"] > 0), acc["sc"] / acc["nc"], np.nan)
        # compare on [D-1d, D+2d) (full 7d history)
        sel = Tg > D - DAYMS
        Kp = K.reindex(Tg[sel])
        dI = np.nanmax(np.abs(Kp.I_mkt.values - I[sel]))
        dr = np.nanmax(np.abs(Kp.r_mkt.values - rm[sel]))
        dc = np.nanmax(np.abs(Kp.cum60_mkt.values - cm[sel]))
        nanmis = int((np.isnan(Kp.I_mkt.values) != np.isnan(I[sel])).sum())
        dn = int(np.max(np.abs(Kp.n_valid.values - nv[sel])))
        # independent episode scan from D-1d
        eps, i, idx = [], 0, np.flatnonzero(sel)
        Ts, Is, Rs, Cs = Tg[sel], I[sel], rm[sel], cm[sel]
        while i < len(Ts):
            if np.isfinite(Is[i]) and Is[i] >= th and np.isfinite(Cs[i]) and Cs[i] <= np.log(0.97):
                s = i
                end = None
                for bb in range(s + 3, len(Ts)):
                    if Ts[bb] >= Ts[s] + 6 * 3600000:
                        end = bb
                        break
                    if all(np.isfinite(Is[bb - q]) and Is[bb - q] < th / 4 for q in (0, 1, 2)):
                        end = bb
                        break
                Mx, jm, ex = Is[s], s, -1
                for bb in range(s + 1, len(Ts)):
                    if Ts[bb] > Ts[s] + 6 * 3600000:
                        break
                    if np.isfinite(Is[bb]) and Is[bb] > Mx:
                        Mx, jm = Is[bb], bb
                    if bb - 1 > jm and np.isfinite(Is[bb]) and np.isfinite(Is[bb - 1]) and Is[bb] < Mx / 4 and Is[bb - 1] < Mx / 4 \
                            and np.isfinite(Rs[bb]) and Rs[bb] >= -0.005:
                        ex = bb
                        break
                eps.append((int(Ts[s]), int(Ts[ex]) if ex >= 0 else -1))
                i = (end if end is not None else len(Ts)) + 1
            else:
                i += 1
        pipe = E[(E.T_on > D - DAYMS) & (E.T_on < D + 2 * DAYMS)][["T_on", "T_exh"]].values.tolist()
        iset = {tuple(x) for x in eps}
        first_match = bool(len(pipe) and all(tuple(int(v) for v in p) in iset for p in pipe))
        r = dict(day=day, max_abs_dI=float(dI), max_abs_dr=float(dr), max_abs_dcum60=float(dc), nan_mismatch=nanmis,
                 max_abs_dn_valid=dn, indep_eps=[(pd.Timestamp(x, unit="ms").isoformat(), pd.Timestamp(y, unit="ms").isoformat() if y > 0 else None) for x, y in eps],
                 pipe_eps=[(pd.Timestamp(x, unit="ms").isoformat(), pd.Timestamp(y, unit="ms").isoformat() if y > 0 else None) for x, y in pipe],
                 first_onset_exh_match=first_match, PASS=bool(dI < 1e-9 and nanmis == 0 and dn == 0 and first_match))
        print(json.dumps(r), flush=True)
        report.append(r)
    json.dump(report, open(S1 + "/v3.json", "w"), indent=1)


if __name__ == "__main__":
    main()
