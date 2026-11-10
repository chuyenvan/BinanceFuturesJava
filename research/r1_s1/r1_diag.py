"""Chan doan G-FULL pool_matched < 99.9% (fold 20250701, 20251001)."""
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_build as A  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("diag")


def main():
    P = pd.read_parquet(A.PRED, columns=["ts", "sym", "score"])
    P["sym"] = P["sym"].astype("int64")
    log.info("P rows=%d ts=[%s,%s] score_nan=%d", len(P), P.ts.min(), P.ts.max(), int(P.score.isna().sum()))
    for fold in sys.argv[1:]:
        b = "predict_wf_%s.bin" % fold
        raw = np.fromfile(os.path.join(A.RAW, b), dtype=A.REC)
        D = pd.DataFrame({"ts": raw["ts"].astype("i8"), "sym": raw["sym"].astype("i8"), "p": raw["p0"].astype("f8")})
        fin = np.isfinite(D.p.values)
        lo, hi = D.ts[fin].min(), D.ts[fin].max()
        Pr = P[(P.ts >= lo) & (P.ts <= hi)]
        M = Pr.merge(D, on=["ts", "sym"], how="left", indicator=True)
        absent = M._merge == "left_only"
        nanp = (M._merge == "both") & M.p.isna()
        dup = int(Pr.duplicated(["ts", "sym"]).sum())
        tsset = set(D.ts.unique().tolist())
        ts_missing = ~M.ts.isin(tsset)
        log.info("fold=%s range=[%d,%d] ref=%d absent_key=%d (ts_absent=%d) nan_p=%d dup_ref=%d ref_score_nan_in_unmatched=%d",
                 fold, lo, hi, len(Pr), int(absent.sum()), int((absent & ts_missing).sum()), int(nanp.sum()), dup,
                 int(M.score[absent | nanp].isna().sum()))
        U = M[absent | nanp]
        if len(U):
            log.info("  unmatched: n_sym=%d top_sym=%s n_ts=%d ts_min=%d ts_max=%d",
                     U.sym.nunique(), U.sym.value_counts().head(8).to_dict(), U.ts.nunique(), U.ts.min(), U.ts.max())
            # coin co trong bin o tick khac khong?
            syms_in_bin = set(D.sym[fin].unique().tolist())
            log.info("  unmatched sym never in bin(fin): %d / %d", len(set(U.sym) - syms_in_bin), U.sym.nunique())


if __name__ == "__main__":
    main()
