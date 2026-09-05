"""H1 — sinh p15 (predReturn15M) cho cua so HOLDOUT 2026 tu feature store + model ONNX da co.
KHONG replay Aerospike, KHONG train lai: dung dung hai model WFOGateRunner da sinh
  fold_19  train[.. 2026-01-01 GMT+7]  OOS [2026-01-01, 2026-04-01) GMT+7
  fold_20  train[.. 2026-04-01 GMT+7]  OOS [2026-04-01, 2026-07-01] GMT+7
=> chuoi walk-forward lien tuc, moi doan do model CHUA thay no du bao.

predRisk4H ghi 0: truong nay DA CHET trong duong quyet dinh (AIRejectFilter dong 103-104,
bo han 2026-08-08 — "khong con model dung sau"). Sim chi doc predReturn15M.

Ra file MOI, KHONG dong vao wfo_gate_pred.csv hien co.
usage: h1_p15_gen.py <out_csv>
"""
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/pipeline/h1")
from h1_p15_repro import V3FULL, load_window, predict  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("h1gen")

SEAL_MS = 1767225600000      # 2026-01-01 00:00 UTC — HoldoutSeal.SEAL_MS
Q2_MS = 1774976400000        # 2026-04-01 00:00 GMT+7
END_MS = 1782838800000       # 2026-07-01 00:00 GMT+7 = het feature store
SEGMENTS = [(19, SEAL_MS, Q2_MS), (20, Q2_MS, END_MS + 60_000)]


def main():
    out = sys.argv[1]
    frames = []
    for fold, lo, hi in SEGMENTS:
        d = load_window(lo, hi)
        p = predict(fold, d)
        LOG.info("fold %d: %d dong, ts %d .. %d", fold, len(d), d.timestamp.iloc[0], d.timestamp.iloc[-1])
        frames.append(pd.DataFrame({"timestamp": d.timestamp.to_numpy(np.int64),
                                    "predReturn15M": np.asarray(p, dtype=np.float64)}))
    df = pd.concat(frames, ignore_index=True).sort_values("timestamp").reset_index(drop=True)
    assert df.timestamp.is_unique, "trung timestamp giua hai fold"
    assert int(df.timestamp.min()) >= SEAL_MS, "co dong truoc SEAL_MS"
    with open(out, "w") as fh:
        fh.write("timestamp,predReturn15M,predRisk4H\n")
        for ts, v in zip(df.timestamp.to_numpy(), df.predReturn15M.to_numpy()):
            fh.write("%d,%.8f,%s\n" % (ts, v, "0.00000000"))
    LOG.info("GHI %d dong -> %s | ts %d .. %d", len(df), out,
             int(df.timestamp.min()), int(df.timestamp.max()))
    LOG.info("dong/thang: %s", df.assign(m=pd.to_datetime(df.timestamp, unit="ms").dt.strftime("%Y-%m"))
             .groupby("m").size().to_dict())


if __name__ == "__main__":
    main()
