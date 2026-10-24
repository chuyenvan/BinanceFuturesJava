"""MM_Q1 driver: python3 mm_run.py <D|K> SYM [SYM ...]  (resumable; one JSON per candidate symbol-hour)."""
import sys, os, json, time, traceback
import numpy as np, pandas as pd, pyarrow as pa
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/mm_q1")
import mm_core as C

HMS = 3600000; H6 = 6 * HMS
RES = "/home/ubuntu/claude_master/mm_wk/res2"   # ADDENDUM1 rerun (run 1 kept in mm_wk/res)
PER = sys.argv[1]; SYMS = sys.argv[2:]
NEED = 60
if PER == "D":
    h_a, h_b, seed = 1751328000000, 1767225600000, 202507   # [2025-07-01, 2026-01-01)
else:
    h_a, h_b, seed = 1767225600000, 1790812800000, 202601   # [2026-01-01, 2026-10-01)
hours = np.arange(h_a, h_b, HMS, dtype=np.int64)
assert len(hours) == (4416 if PER == "D" else 6552), len(hours)
order = np.random.default_rng(seed).permutation(hours)
EP = None
if PER == "D":
    e = pd.read_parquet("/home/ubuntu/claude_master/liqx_wk/s1/episodes.parquet")
    e = e[(e.level == "MKT") & (e.variant == "main")]
    assert e.T_on.dtype == np.int64 and e.T_end.dtype == np.int64
    EP = (e.T_on.to_numpy() - H6, e.T_end.to_numpy() + H6)
LOG = f"/home/ubuntu/claude_master/mm_wk/log2_{PER}_{SYMS[0]}.txt"
def log(m):
    with open(LOG, "a") as f:
        f.write(time.strftime("%H:%M:%S ") + m + "\n")

BTC = {}
def btc_r(h0):
    # ADDENDUM1 bug 2: r from valid trades (chd kline rows are not closed bars)
    if h0 not in BTC:
        r = C.trades_r("BTCUSDT", h0)
        BTC[h0] = (r, "trades" if r is not None else "none")
    return BTC[h0]

for sym in SYMS:
    os.makedirs(f"{RES}/{sym}", exist_ok=True)
    done = {}
    for fn in os.listdir(f"{RES}/{sym}"):
        if fn.startswith(PER + "_") and fn.endswith(".json"):
            with open(f"{RES}/{sym}/{fn}") as f:
                done[int(fn[2:-5])] = json.load(f)["status"]
    acc = sum(1 for v in done.values() if v == "ok")
    log(f"{sym} start acc={acc} done={len(done)}")
    for H in order.tolist():
        if acc >= NEED:
            break
        if H in done:
            continue
        rec = {"sym": sym, "H": H, "period": PER, "status": None}
        t0 = time.time()
        try:
            if EP is not None and bool(np.any((H <= EP[1]) & (H + HMS > EP[0]))):
                rec["status"] = "rej_episode"
            else:
                rb, bsrc = btc_r(H); rec["r_btc"] = rb; rec["r_btc_src"] = bsrc
                if rb is None:
                    rec["status"] = "rej_btc_r_missing"
                elif abs(rb) >= 0.01:
                    rec["status"] = "rej_btc_ret"
                else:
                    rs = C.trades_r(sym, H); rec["r_sym_src"] = "trades" if rs is not None else "none"
                    rec["r_sym"] = rs
                    if rs is None:
                        rec["status"] = "rej_no_data_or_r"
                    elif abs(rs) >= 0.02:
                        rec["status"] = "rej_sym_ret"
                    else:
                        Dd = C.load_d(sym, H)
                        if Dd["ob"] is None or Dd["tr"] is None:
                            rec["status"] = "rej_no_data"
                        else:
                            rec["wire_bytes"] = int(Dd["nob"] + Dd["ntr"])
                            info, S = C.replay(Dd)
                            q = C.quality(H, info, S)
                            rec["info"] = info; rec["q"] = q
                            if info["n_nonupdate_rows"] > 0:
                                rec["status"] = "rej_snapshot"   # ADDENDUM1 point 3
                            elif info["pu_breaks"] > 0 or info["u_nonmono"] > 0 or info["E_nonmono"] > 0:
                                rec["status"] = "rej_pu"
                            elif q["crossed_frac"] > 0.01:
                                rec["status"] = "rej_crossed"
                            else:
                                res, dump = C.simulate(H, info, S, dump=(acc == 0))
                                rec["res"] = res
                                if dump:
                                    rec["dump"] = dump
                                rec["status"] = "ok"; acc += 1
                            del S
        except Exception as ex:
            rec["status"] = "error"; rec["err"] = traceback.format_exc()[-800:]
        rec["sec"] = round(time.time() - t0, 2)
        with open(f"{RES}/{sym}/{PER}_{H}.json.tmp", "w") as f:
            json.dump(rec, f)
        os.replace(f"{RES}/{sym}/{PER}_{H}.json.tmp", f"{RES}/{sym}/{PER}_{H}.json")
        done[H] = rec["status"]
        if rec["status"] in ("ok", "error") or rec["status"].startswith("rej_pu") or rec["status"] == "rej_crossed":
            log(f"{sym} {PER} H={H} {rec['status']} acc={acc} sec={rec['sec']}")
    log(f"{sym} {PER} END acc={acc} tried={len(done)}")
