"""head_s2.py - do KICH THUOC file aggTrades Vision (CHI HTTP HEAD, khong tai noi dung) tren mau ngau nhien (sym, ngay) GAN DUNG
khung su kien COND_A c0.2 k2 (sym ~ so don vi khop S1 theo sym x nua; ngay ~ so don vi dat theo ngay). Chi ngay <= 2025-12-31.
Dung: python3 head_s2.py RUN2_DIR LIFECYCLE OUT_JSON N_PER_HALF (<= 140)."""
import sys, json, glob, time, logging, urllib.request, urllib.error
import numpy as np, pandas as pd
log = logging.getLogger("head_s2")
DS, DAY = 1619827200000, 86400000
SEAL = 1767225600000
U = "https://data.binance.vision/data/futures/um/daily/aggTrades/%s/%s-aggTrades-%s.zip"


def head(url):
    rq = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(rq, timeout=20) as r:
            return r.status, int(r.headers.get("Content-Length", -1))
    except urllib.error.HTTPError as e:
        return e.code, -1
    except Exception as e:  # noqa
        return -1, -1


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    run2, lpath, out, nph = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    assert nph <= 140
    ag = pd.concat([pd.read_parquet(f) for f in glob.glob(run2 + "/d*/reduced/agg.parquet")])
    sh = pd.concat([pd.read_parquet(f) for f in glob.glob(run2 + "/d*/reduced/shalf.parquet")])
    ag = ag[(ag.cell == 20) & (ag.model == "OPT")].groupby("day").place.sum()
    sh = sh[(sh.cell == 20) & (sh.model == "OPT")]
    life = pd.read_parquet(lpath)
    lf = {r.symbol: (pd.Timestamp(r.first_utc).value // 10**6, (pd.Timestamp(r.last_utc).value // 10**6) if not pd.isna(r.last_utc) else SEAL)
          for r in life.itertuples()}
    rng = np.random.default_rng(2026112201)
    res, nreq = [], 0
    for hv, (lo, hi) in ((0, (761, 761 + 914)), (1, (1675, 1675 + 731))):
        s = sh[sh.half == hv].groupby("sym").fill.sum()
        ws = s.values / s.values.sum()
        dd = ag[(ag.index >= lo) & (ag.index < hi)]
        wd = dd.values / dd.values.sum()
        got = 0
        tries = 0
        while got < nph and tries < 50 * nph:
            tries += 1
            sym = s.index[rng.choice(len(s), p=ws)]
            day = int(dd.index[rng.choice(len(dd), p=wd)])
            t = DS + day * DAY
            if sym not in lf or not (lf[sym][0] <= t - 30 * DAY and lf[sym][1] >= t + DAY) or t >= SEAL:
                continue
            ds = pd.Timestamp(t, unit="ms").strftime("%Y-%m-%d")
            assert ds < "2026-01-01"
            st, sz = head(U % (sym, sym, ds))
            nreq += 1
            res.append(dict(half="AB"[hv], sym=sym, date=ds, status=st, bytes=sz))
            got += 1
            time.sleep(0.05)
    json.dump(dict(n_requests=nreq, rows=res), open(out, "w"), indent=0)
    df = pd.DataFrame(res)
    for h, g in df.groupby("half"):
        ok = g[g.status == 200]
        log.info("half %s n %d ok %d miss %d mean_MB %.2f med %.2f p90 %.2f max %.1f", h, len(g), len(ok), (g.status != 200).sum(),
                 ok.bytes.mean() / 1e6, ok.bytes.median() / 1e6, ok.bytes.quantile(.9) / 1e6, ok.bytes.max() / 1e6)
    log.info("requests %d", nreq)


if __name__ == "__main__":
    main()
