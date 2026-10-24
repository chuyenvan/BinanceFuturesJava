"""Orderbook sample checks: event types, snapshot at hour start, depth, update-id continuity, ToB rebuild vs trades."""
import sys
import numpy as np, pandas as pd, pyarrow.parquet as pq, pyarrow as pa, pyarrow.compute as pc
S = "/home/ubuntu/claude_master/chd_wk/sample"
for date, h, s in [(a, b, c) for a, b in (("2025-09-02", 12), ("2025-10-10", 21)) for c in (sys.argv[1:] or ["BTCUSDT", "MYXUSDT"])]:
    tb = pq.read_table(f"{S}/{date}_{h:02d}_{s}_orderbook.parquet")
    t0 = int(pd.Timestamp(f"{date} {h:02d}:00", tz="UTC").value // 10**6)
    et = tb.column("event_type").to_numpy(zero_copy_only=False)
    vc = pd.Series(et).value_counts().to_dict()
    print(f"== {date} {h} {s} rows={tb.num_rows} event_type={vc}")
    df = pd.DataFrame({"et": et, "E": tb.column("event_time").to_numpy(), "U": tb.column("first_update_id").to_pandas(), "u": tb.column("final_update_id").to_pandas(),
                       "pu": tb.column("prev_final_update_id").to_pandas(), "lu": tb.column("last_update_id").to_pandas(),
                       "side": tb.column("side").to_numpy(zero_copy_only=False), "p": tb.column("price").cast(pa.float64()).to_numpy(), "q": tb.column("quantity").cast(pa.float64()).to_numpy()})
    del tb
    snaps = df[df.et != "update"]
    if len(snaps):
        g = snaps.groupby(["et", "lu"]).agg(E=("E", "first"), n=("p", "size"), nb=("side", lambda x: (x == "bid").sum()))
        g["Es"] = (g.E - t0) / 1000
        print("  snapshots:", g.reset_index()[["et", "lu", "Es", "n", "nb"]].head(6).to_string(index=False).replace("\n", "\n    "), "count", len(g))
    up = df[df.et == "update"].drop_duplicates("u")[["U", "u", "pu", "E"]]
    br = (up.pu.values[1:] != up.u.values[:-1])
    print(f"  updates msgs={len(up)} pu-continuity breaks={int(br.sum())} first_break_at_s={((up.E.values[1:][br][:5]-t0)/1000).round(1).tolist()} max_gap_E_s={np.diff(up.E.values).max()/1000:.1f}")
    # rebuild: start from first snapshot, apply updates with u > snapshot lu, sample ToB each second
    if not len(snaps):
        print("  no snapshot in file -> rebuild from EMPTY book using updates only (warm-up 300 s excluded)")
        bids = {}; asks = {}; rest = df[df.et == "update"]
    else:
        lu0 = snaps.lu.iloc[0]; i0 = snaps.index[0]
        first = snaps[snaps.lu == lu0]
        bids = dict(zip(first.p[first.side == "bid"], first.q[first.side == "bid"])); asks = dict(zip(first.p[first.side == "ask"], first.q[first.side == "ask"]))
        rest = df.loc[i0:]
        rest = rest[(rest.et == "update") & (rest.u > lu0)]
    E = rest.E.values; P = rest.p.values; Q = rest.q.values; SD = rest.side.values
    nxt = t0 + 1000; tob = []; j = 0; n = len(E)
    while nxt <= t0 + 3600000:
        while j < n and E[j] < nxt:
            dct = bids if SD[j] == "bid" else asks
            if Q[j] == 0: dct.pop(P[j], None)
            else: dct[P[j]] = Q[j]
            j += 1
        bb = max(bids) if bids else np.nan; ba = min(asks) if asks else np.nan
        tob.append((nxt, bb, ba, len(bids), len(asks))); nxt += 1000
    tob = pd.DataFrame(tob, columns=["t", "bb", "ba", "nb", "na"])
    tob = tob[tob.t >= t0 + 300000]
    print(f"  ToB: crossed={(tob.bb >= tob.ba).mean():.4f} spread_bps median={((tob.ba-tob.bb)/tob.bb*1e4).median():.3f} levels bid/ask median={tob.nb.median():.0f}/{tob.na.median():.0f}")
    tr = pq.read_table(f"{S}/{date}_{h:02d}_{s}_trades.parquet", columns=["trade_time", "price"]).to_pandas(); tr["price"] = tr.price.astype(float)
    tr["t"] = (tr.trade_time // 1000 + 1) * 1000
    last = tr.groupby("t").price.last()
    m = tob.set_index("t").join(last, how="inner")
    inside = ((m.price >= m.bb * (1 - 2e-4)) & (m.price <= m.ba * (1 + 2e-4))).mean()
    print(f"  last trade of second within [bid,ask]+-2bp: {inside:.4f} (n={len(m)})")
