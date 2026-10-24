"""LIQX_S1 V6 (extra, not in prereg): independent recompute of basket returns (ON/EXH r1440, r240, mae24) and
EXH control rank for the 5 deepest MKT main episodes. Uses v3_indep (no pipeline import) for raw loading/universe."""
import json
import numpy as np
import pandas as pd
from v3_indep import load, top100, KLP, utc, DAYMS, MIN

S1 = "/home/ubuntu/claude_master/liqx_wk/s1"


def main():
    E = pd.read_parquet(S1 + "/episodes.parquet")
    R = pd.read_parquet(S1 + "/ret_entries.parquet")
    RC = np.load(S1 + "/ret_ctrl.npy")
    J = np.load(S1 + "/ctrl_j.npy")
    em = E[(E.level == "MKT") & (E.variant == "main")].sort_values("depth").head(5)
    out = []
    for _, e in em.iterrows():
        ym = pd.Timestamp(e.T_on, unit="ms").strftime("%Y-%m")
        U = top100(utc(ym + "-01"))
        bk = [s for s in U if s not in ("BTCUSDT", "ETHUSDT")][:24]
        k = load(KLP, ["ts", "sym", "close"], e.T_on - 10 * MIN, e.T_on + 3 * DAYMS, set(bk))
        piv = k.pivot(index="ts", columns="sym", values="close").sort_index()
        full = np.arange(e.T_on - 10 * MIN, e.T_on + 3 * DAYMS, MIN, dtype=np.int64)
        piv = piv.reindex(full).ffill()
        have = k.groupby("sym").ts.apply(set)

        def ret(te, h):
            mem = [s for s in bk if s in have.index and te in have[s]]
            p0 = piv.loc[te, mem]
            return float(np.log((piv.loc[te + h * MIN, mem] / p0).mean()))

        def mae(te):
            mem = [s for s in bk if s in have.index and te in have[s]]
            v = (piv.loc[te + MIN: te + 1440 * MIN, mem] / piv.loc[te, mem]).mean(axis=1)
            return float(np.log(v).min())
        d = dict(T_on=pd.Timestamp(e.T_on, unit="ms").isoformat())
        for kind, te in (("ON", e.T_on), ("EXH", e.T_exh)):
            r = R[(R.ep == e.ep) & (R.kind == kind)].iloc[0]
            d[kind] = dict(r1440=ret(te, 1440), pipe_r1440=float(r.r1440), r240=ret(te, 240), pipe_r240=float(r.r240),
                           mae24=mae(te), pipe_mae24=float(r.mae24))
        tc = e.T_on + J[e.ep].astype(np.int64) * MIN
        rc = np.array([ret(int(t), 1440) for t in tc])
        x = d["EXH"]["r1440"]
        rk = ((rc < x).sum() + 0.5 * (rc == x).sum()) / len(rc)
        d["ctrl_maxabs"] = float(np.nanmax(np.abs(rc - RC[e.ep])))
        d["rank_exh_indep"] = float(rk)
        d["maxabs_all"] = float(max(abs(d[k][a] - d[k]["pipe_" + a]) for k in ("ON", "EXH") for a in ("r1440", "r240", "mae24")))
        out.append(d)
        print(json.dumps(d), flush=True)
    json.dump(out, open(S1 + "/v6.json", "w"), indent=1)


if __name__ == "__main__":
    main()
