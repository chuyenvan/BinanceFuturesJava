#!/usr/bin/env python3
"""S1_FIRSTHIT_RANK — prep nhan: join nhan first-hit FLAT3 (LABEL_FIRSTHIT, fh_all.parquet) vao pool S1 (ledger
cand_dev_x1_lite = dung tap dong kernel S1 doc). Pre-reg docs/prereg/PREREG_S1_FIRSTHIT_RANK.md.
Can chinh: y_FH cua dong ledger (ts, sym) = nhan FH tai tick (ts + 15', sym) (OFF = +900000 ms) — probe feasibility:
dong y SL<=72h(FH) vs maxAdv_72h<=-10% (ledger) cao nhat o lech nay (2023Q1: 0,962 vs 0,941 o lech 0).
Usage: python3 s1_fhrank_prep.py build
Ra: /home/ubuntu/claude_master/1003/fhr/kds/yfh_x1.parquet (ts,sym,yfh int8 [-1 thieu],hit int8 [-1 thieu]) + coverage.json
"""
import hashlib, json, logging, os, sys
import numpy as np
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("fhr_prep")
D = "/home/ubuntu/claude_master/1003/fhr"
LITE = "/home/ubuntu/s1hpo/kaggle_ds/cand_dev_x1_lite.parquet"
LITE_MD5 = "2cc8381e0577b5289fa1e5714fd865fe"
FH = "/home/ubuntu/claude_master/1003/fh/fh_all.parquet"
OFF = 900000
TZ = 7 * 3600000
T2022 = int(pd.Timestamp("2022-01-01").value // 10 ** 6) - TZ


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def load(off):
    assert md5f(LITE) == LITE_MD5, "lite ledger da doi"
    L = pd.read_parquet(LITE)
    log.info("lite cols %s rows %d", list(L.columns), len(L))
    L = L[L.g1lite.notna()][["ts", "sym"]].copy()
    F = pd.read_parquet(FH, columns=["ts", "symId", "y", "hit"]).rename(columns={"symId": "sym"})
    F = F.astype({"sym": np.int64})
    F["ts"] = F.ts - off   # nhan tai (ts+off) gan vao dong ledger ts
    M = L.merge(F, on=["ts", "sym"], how="left")
    assert len(M) == len(L)
    return M


def build():
    M = load(OFF)
    cov = M.y.notna()
    yr = pd.to_datetime(M.ts, unit="ms").dt.year
    out = dict(off_ms=OFF, rows=int(len(M)), coverage=float(cov.mean()),
               coverage_by_year={int(k): float(v) for k, v in cov.groupby(yr).mean().items()},
               coverage_oos2022=float(cov[M.ts >= T2022].mean()),
               coverage_train_pre2022=float(cov[M.ts < T2022].mean()),
               yfh_by_year={int(k): float(v) for k, v in M.y.groupby(yr).mean().items()},
               hit_dist={int(k): float(v) for k, v in M.hit.value_counts(normalize=True).items()})
    M0 = load(0)
    out["coverage_off0"] = float(M0.y.notna().mean())
    os.makedirs(D + "/kds", exist_ok=True)
    o = pd.DataFrame({"ts": M.ts.astype(np.int64), "sym": M.sym.astype(np.int64),
                      "yfh": M.y.fillna(-1).astype(np.int8), "hit": M.hit.fillna(-1).astype(np.int8)})
    p = D + "/kds/yfh_x1.parquet"
    o.to_parquet(p, index=False)
    out["md5_yfh_x1"] = md5f(p)
    json.dump(out, open(D + "/coverage.json", "w"), indent=1)
    log.info("COVERAGE %s", json.dumps(out))


if __name__ == "__main__":
    if sys.argv[1:] == ["build"]:
        build()
    else:
        raise SystemExit(__doc__)
