"""LIQX_S0 V2: independent minimal recomputation of M1(P1, sample A). No pipeline import; raw files only; own rank."""
import pyarrow as pa, pyarrow.parquet as pq, pyarrow.compute as pc, numpy as np, csv, gzip, math, os, json, datetime as dt
KL = "/home/ubuntu/vz_e1/raw/kline1m-%04d-%02d.parquet"
MET = "/home/ubuntu/vz/out/metrics5m/%04d/%04d-%02d.parquet"
TAR = os.path.expanduser("~/claude_master/liqx_wk/tardis/liquidations_%04d-%02d-01_PERPETUALS.csv.gz")
MIN = 60000


def epoch_ms(y, m, d=1):
    return int(dt.datetime(y, m, d, tzinfo=dt.timezone.utc).timestamp()) * 1000


def avg_rank(a):
    a = np.asarray(a, dtype=np.float64); o = np.argsort(a, kind="mergesort"); s = a[o]
    r = np.empty(len(a)); i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        r[o[i:j + 1]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return r


xs, ys = [], []
for y in (2022, 2023):
    for m in range(1, 13):
        D = epoch_ms(y, m); py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
        # RUN 2 fix (V2 own bug): window [D-30d, D) can reach 2 months back (e.g. 2022-03-01 -> 2022-01-30); read 3 files.
        qv = {}; close = {}
        p2y, p2m = (py, pm - 1) if pm > 1 else (py - 1, 12)
        for (yy, mm) in ((p2y, p2m), (py, pm), (y, m)):
            if not os.path.exists(KL % (yy, mm)):
                continue
            t = pq.read_table(KL % (yy, mm), columns=["ts", "sym", "quote_volume", "close"])
            t = t.set_column(1, "sym", pc.cast(t.column("sym"), pa.string())); ts = t.column("ts")
            w = pc.and_(pc.greater_equal(ts, D - 30 * 86400000), pc.less(ts, D))
            agg = t.filter(w).select(["sym", "quote_volume"]).group_by("sym").aggregate([("quote_volume", "sum")]).to_pydict()
            for s_, v in zip(agg["sym"], agg["quote_volume_sum"]):
                qv[s_] = qv.get(s_, 0.0) + v
            w2 = pc.and_(pc.greater_equal(ts, D - 6 * MIN), pc.less(ts, D + 86400000))
            tt = t.filter(w2).to_pydict()
            for s_, a, b in zip(tt["sym"], tt["ts"], tt["close"]):
                close[(s_, int(a))] = b
        uni = [s for s, _ in sorted(qv.items(), key=lambda kv: -kv[1])[:100]]
        mt = pq.read_table(MET % (y, y, m), columns=["ts", "sym", "oi_value"])
        mts = mt.column("ts").to_numpy(); msym = np.asarray(mt.column("sym").to_pylist(), dtype=object); mv = mt.column("oi_value").to_numpy()
        w = (mts >= D) & (mts <= D + 86400000)
        oiv = {(s_, int(a)): b for s_, a, b in zip(msym[w], mts[w], mv[w]) if b == b}
        liq = {}
        with gzip.open(TAR % (y, m), "rt") as f:
            for row in csv.DictReader(f):
                if row["side"] != "sell":
                    continue
                tms = int(row["timestamp"]) // 1000
                T = tms - tms % 300000 + 300000
                key = (row["symbol"], T)
                liq[key] = liq.get(key, 0.0) + float(row["price"]) * float(row["amount"])
        us = set(uni)
        for s_ in uni:
            for k in range(1, 289):
                T = D + 300000 * k
                need = [(s_, T - j * MIN) for j in range(1, 7)]
                if not all(n in close for n in need) or (s_, T) not in oiv or (s_, T - 300000) not in oiv:
                    continue
                r5 = math.log(close[(s_, T - MIN)] / close[(s_, T - 6 * MIN)])
                if not r5 < -0.01:
                    continue
                p1 = max(0.0, oiv[(s_, T - 300000)] - oiv[(s_, T)])  # r5<0 holds
                xs.append(p1); ys.append(liq.get((s_, T), 0.0))
        print(y, m, len(xs), flush=True)
rx, ry = avg_rank(xs), avg_rank(ys)
rx -= rx.mean(); ry -= ry.mean()
rho = float((rx * ry).sum() / math.sqrt((rx * rx).sum() * (ry * ry).sum()))
sc = json.load(open(os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/liqx_s0/scores.json")))
pipe = sc["A"]["P1"]["M1"]; nA = sc["A"]["n_M1"]
out = {"V2_M1_P1_A_indep": rho, "pipeline": pipe, "delta": abs(rho - pipe), "n_indep": len(xs), "n_pipeline": nA, "PASS": abs(rho - pipe) < 1e-9 and len(xs) == nA}
print(out)
json.dump(out, open(os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/liqx_s0/v2.json"), "w"), indent=1)
