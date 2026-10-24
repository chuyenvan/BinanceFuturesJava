"""LIQX_S1 step 4: post-entry returns (prereg §9) for ON/EXH + 200 controls per episode (ret_1440 only).
Out: S1/ret_entries.parquet (ep, kind, r60, r240, r1440, r4320, mfe24, mae24, btc_r1440, n_basket), S1/ret_ctrl.npy."""
import json
import numpy as np
import pandas as pd
from common import S1, DAY, M1, KL_LAST, MAJ, ms, months, nxt, read_kline, maxrss_mb

HOR = (60, 240, 1440, 4320)


class Px:
    def __init__(self, k):
        self.d = {}
        for s, g in k.groupby("sym", sort=False):
            self.d[s] = (g.ts.values, g.close.values)

    def at(self, s, t):
        """ffill close of bar open <= t (t array). NaN if before first bar or beyond KL_LAST."""
        if s not in self.d:
            return np.full(np.shape(t), np.nan)
        ts, c = self.d[s]
        i = np.searchsorted(ts, t, "right") - 1
        out = np.where(i >= 0, c[np.clip(i, 0, None)], np.nan)
        return np.where(np.asarray(t) <= KL_LAST, out, np.nan)

    def exact(self, s, t):
        if s not in self.d:
            return np.full(np.shape(t), np.nan)
        ts, c = self.d[s]
        i = np.searchsorted(ts, t, "left")
        ii = np.clip(i, 0, len(ts) - 1)
        return np.where((i < len(ts)) & (ts[ii] == t), c[ii], np.nan)


def lnret(px, members, te, offs):
    """te: array (n,), offs: array (k,) minutes. Basket EW buy-and-hold over members (list) -> ln V, shape (n,k)."""
    te = np.asarray(te, dtype=np.int64)
    num = np.zeros((len(te), len(offs)))
    cnt = np.zeros(len(te))
    tt = te[:, None] + np.asarray(offs, dtype=np.int64)[None, :] * M1
    for s in members:
        p0 = px.exact(s, te)
        ok = np.isfinite(p0)
        p = px.at(s, tt)
        num[ok] += p[ok] / p0[ok, None]
        cnt += ok
    with np.errstate(invalid="ignore", divide="ignore"):
        v = num / cnt[:, None]
        v[~np.isfinite(v)] = np.nan
        v[(tt > KL_LAST)] = np.nan
        return np.log(v), cnt


def main():
    E = pd.read_parquet(S1 + "/episodes.parquet")
    J = np.load(S1 + "/ctrl_j.npy")
    assert len(J) == len(E)
    E["mon"] = [pd.Timestamp(t, unit="ms").strftime("%Y-%m") for t in E.T_on]
    path = np.arange(1, 1441)
    res, RC = [], np.full(J.shape, np.nan)
    for y, m in months():
        tag = "%04d-%02d" % (y, m)
        e = E[E.mon == tag]
        if not len(e):
            continue
        uni = json.load(open(S1 + "/uni/%s.json" % tag))["uni"]
        basket = [s for s in uni if s not in MAJ][:24]
        need = set(e[e.level == "COIN"].sym)
        if (e.level == "MKT").any():
            need |= set(basket) | {"BTCUSDT"}
        M = ms(y, m)
        k = read_kline(need, M, ms(*nxt(y, m)) + 4 * DAY, cols=["ts", "sym", "close"])
        px = Px(k)
        del k
        for (lvl, sym), g in e.groupby(["level", "sym"]):
            mem = basket if lvl == "MKT" else [sym]
            for kind in ("ON", "EXH"):
                te = (g.T_on if kind == "ON" else g.T_exh).values
                sel = te >= 0
                if not sel.any():
                    continue
                gg = g[sel]
                t = te[sel]
                rh, cnt = lnret(px, mem, t, np.array(HOR))
                rp, _ = lnret(px, mem, t, path)
                d = pd.DataFrame({"ep": gg.ep.values, "kind": kind, "r60": rh[:, 0], "r240": rh[:, 1], "r1440": rh[:, 2],
                                  "r4320": rh[:, 3], "mfe24": np.max(rp, axis=1), "mae24": np.min(rp, axis=1),
                                  "n_basket": cnt})
                if lvl == "MKT":
                    rb, _ = lnret(px, ["BTCUSDT"], t, np.array(HOR))
                    d["btc_r1440"] = rb[:, 2]
                    d["btc_r240"] = rb[:, 1]
                res.append(d)
            tc = g.T_on.values[:, None] + J[g.ep.values].astype(np.int64) * M1
            rc, _ = lnret(px, mem, tc.ravel(), np.array([1440]))
            RC[g.ep.values] = rc[:, 0].reshape(tc.shape)
        print(tag, len(e), round(maxrss_mb()), flush=True)
    R = pd.concat(res, ignore_index=True)
    R.to_parquet(S1 + "/ret_entries.parquet", index=False)
    np.save(S1 + "/ret_ctrl.npy", RC)
    print("done", len(R), "maxrss", round(maxrss_mb()))


if __name__ == "__main__":
    main()
