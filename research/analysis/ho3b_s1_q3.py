#!/usr/bin/env python3
"""HO3b B3: S1 Q3 = feat_v2 cua so (CONG THUC ho1_featv2_window) tren closes = ghim DEV + CLOSES_1H_2026v2 (H1) + Q3 (Vision 1h,
closes1h_build nhu HO1) va OI gio ghep (ghim < 2026-07-01 00:00 +07, dung lai Vision sau) -> kiem toan ven: hang ts in
[2026-06-15, 2026-06-30 17:00) UTC phai == feat_v2_ho26v2.parquet (9 KEEP, rel <= 1e-6) -> pool Q3 (tick gate p15 s42 Q3 mo,
nBars_72h >= 288, chi doc ton-tai nhan) -> S1 predict-only af706dc6. Usage: ho3b_s1_q3.py <closes_q3.bin> <pred_s42_q3.bin> <label_q3.pb> <out.parquet>"""
import glob, json, logging, os, struct, sys
import numpy as np
import pandas as pd
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R + "/research/analysis"); sys.path.insert(0, "/home/ubuntu/claude_master/1003/ho3b")
import ho1_featv2_window as FW  # noqa: E402
import ho1_s1_2026 as S1  # noqa: E402
import ho3b_gate3 as G3  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho3b_s1q3")
H = 3600000
SEALQ3 = 1782838800000
C26 = "/home/ubuntu/claude_master/1003/ho1/s1/CLOSES_1H_2026v2.bin"
F26 = "/home/ubuntu/claude_master/1003/ho1/s1/feat_v2_ho26v2.parquet"
CHK0 = int(pd.Timestamp("2026-06-15").value // 10**6)


def closes3(cq3):
    a = np.fromfile(FW.CLO, dtype=FW.DT)
    FW.DEV_UNI.update(int(x) for x in np.unique(a["sym"]))
    parts = [a]
    mx = int(a["ts"].astype(np.int64).max())
    for p in (C26, cq3):
        b = np.fromfile(p, dtype=FW.DT)
        b = b[b["ts"].astype(np.int64) > mx]
        parts.append(b)
        mx = max(mx, int(b["ts"].astype(np.int64).max()))
    df = pd.concat([pd.DataFrame({"ts": x["ts"].astype(np.int64), "sym": x["sym"].astype(np.int32),
                                  "c": x["c"].astype(np.float64)}) for x in parts])
    df = df[(df.ts >= FW.T_START) & (df.ts <= FW.T_END)]
    P = df.pivot(index="ts", columns="sym", values="c").sort_index()
    return P.reindex(pd.Index(np.arange(P.index.min(), P.index.max() + H, H)))


def main():
    cq3, pq3, lq3, out = sys.argv[1:5]
    FW.T_START = int(pd.Timestamp("2026-05-01").value // 10**6)
    FW.T_END = int(pd.Timestamp("2026-10-01").value // 10**6)
    FW.KEEP_FROM = CHK0
    G3.SEAL7 = SEALQ3
    G3.MODE = "rebuilt"
    hp = os.path.dirname(out) + "/oi_hourly_q3.bin"
    G3.comb_hourly_file(hp)
    FW.OI = hp
    P = closes3(cq3)
    long = FW.features(P)
    os.remove(hp)
    ref = pd.read_parquet(F26, columns=["ts", "sym"] + FW.KEEP)
    ref = ref[(ref.ts >= CHK0) & (ref.ts < SEALQ3)]
    nq = long[(long.ts >= CHK0) & (long.ts < SEALQ3)]
    M = ref.merge(nq, on=["ts", "sym"], how="outer", suffixes=("_d", "_n"), indicator=True)
    B = M[M._merge == "both"]
    bad = int((M._merge != "both").sum()) * len(FW.KEEP)
    for nm in FW.KEEP:
        a, b = B[nm + "_n"].to_numpy(np.float64), B[nm + "_d"].to_numpy(np.float64)
        nanx = np.isnan(a) != np.isnan(b)
        both = ~np.isnan(a) & ~np.isnan(b)
        rel = np.zeros(len(a)); rel[both] = np.abs(a[both] - b[both]) / np.maximum(np.abs(b[both]), 1e-12)
        bad += int(nanx.sum() + (rel > 1e-6).sum())
    chk = dict(rows_ref=int(len(ref)), rows_new=int(len(nq)), cells=int(len(M) * len(FW.KEEP)), bad=bad)
    chk["pass"] = chk["bad"] <= 0.001 * chk["cells"]
    log.info("KIEM June %s", chk)
    assert chk["pass"], "feat_v2 doan June != HO26 -> DUNG"
    F = long[long.ts >= SEALQ3 - 2 * H][["ts", "sym"] + S1.KEEP].copy()
    F["sym"] = F.sym.astype(np.int64)
    raw = open(pq3, "rb").read()
    n = struct.unpack(">i", raw[:4])[0]
    a = np.frombuffer(raw[4:4 + 16 * n], dtype=np.dtype([("ts", ">i8"), ("p15", ">f4"), ("r", ">f4")]))
    ts = a["ts"].astype(np.int64)
    m = (ts >= SEALQ3) & (ts < 1790787600000) & (ts % S1.Q == 0)
    open_ts = ts[m][a["p15"][m].astype(np.float32) >= np.float32(0.008)]
    files = [sorted(glob.glob(S1.LBDIR + "/funding_label_20260401*.pb"))[0], lq3]
    A = S1.avail_pool(open_ts, files)
    assert S1.sha256f(S1.M1231) == S1.M1231_SHA
    S, cov = S1.score(S1.M1231, A, F)
    S[["ts", "sym", "score"]].to_parquet(out, index=False)
    meta = dict(check_june=chk, n_open_ticks=int(len(open_ts)), pool_rows=int(len(A)), s1_rows=int(len(S)), feat_cov=cov,
                ts_min=int(S.ts.min()), ts_max=int(S.ts.max()), nan_score=int(S.score.isna().sum()), out_sha256=G3.sha256f(out))
    json.dump(meta, open(out + ".json", "w"), indent=1)
    log.info("S1 Q3 %s", meta)


if __name__ == "__main__":
    main()
