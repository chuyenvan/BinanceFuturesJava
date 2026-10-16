import sys, glob, gzip, io, logging, numpy as np, pandas as pd
from grr_lib import load, ms, f
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("look")
def rd(p):
    try: return pd.read_csv(io.BytesIO(gzip.open(p).read()))
    except Exception:
        try:
            b = b""; g = gzip.open(p)
            while True:
                c = g.read(65536)
                if not c: break
                b += c
        except Exception: pass
        return pd.read_csv(io.BytesIO(b[:b.rfind(b"\n") + 1])) if b else pd.DataFrame()
S = pd.concat([rd(p) for p in sorted(glob.glob("sel/sel_dump_*.csv.gz"))], ignore_index=True)
S["m"] = S.ts // 60000; S.to_parquet("sel.parquet") if hasattr(S, "to_parquet") else None
log.info("sel rows %d minutes %d ranks max %d range %s..%s", len(S), S.m.nunique(), S["rank"].max(), f(S.ts.min()), f(S.ts.max()))
log.info("selectorScore quantiles: %s", np.quantile(S.selectorScore, [0, .05, .5, .95, 1]).round(4))
D = {n: load(n + ".bin")[:2] for n in ["bc3", "b242_k16", "bc3b", "b242"]}
for mm in ["10-03 10:05", "10-10 12:04", "10-08 22:20", "10-14 09:00", "10-16 15:30"]:
    m = ms(mm) // 60000
    for n, (t, r) in D.items():
        x = np.sort(r[t // 60000 == m])[::-1]
        log.info("%s %-8s n=%2d r: %s", mm, n, len(x), " ".join("%.5f" % v for v in x[:26]))
    s = S[S.m == m].sort_values("rank")
    if len(s):
        r_imp = s.p15 / s.gateValue
        log.info("%s sel n=%d p15=%.6f score[%s] gate[%s] p15/gate[%s]", mm, len(s), s.p15.iloc[0], " ".join("%.3f" % v for v in s.selectorScore.values[:24]), " ".join("%.4f" % v for v in s.gateValue.values[:24]), " ".join("%.4f" % v for v in r_imp.values[:24]))
