"""Rebuild S1 bins tu input ghim, 2 lan doc lap (r1,r2), CPU. So byte voi deploy.
Chay dung script featv2 da sinh deploy (sha khop e6112094/f5323b1f). Khong ghi de file bao ve.
Output bins: /home/ubuntu/predwf_s1_v2 (r1), /home/ubuntu/predwf_s1_v2_r2 (r2)."""
import subprocess, hashlib, glob, os, json, time, logging, sys
import numpy as np, pandas as pd
from scipy.stats import spearmanr
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
LOG = logging.getLogger(__name__)
FEATV2 = "/home/ubuntu/featv2"
DEPLOY = "/home/ubuntu/predwf_map_s1a2"
LED = "/home/ubuntu/ledger"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()


def run(cmd):
    LOG.info("RUN %s", " ".join(cmd))
    t = time.time()
    r = subprocess.run(cmd, cwd=FEATV2, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    LOG.info("rc=%d %.1fs | tail: %s", r.returncode, time.time() - t,
             " / ".join(r.stdout.strip().splitlines()[-2:]))
    if r.returncode != 0:
        LOG.error("FAIL:\n%s", r.stdout[-3000:]); sys.exit(1)
    return r.stdout


def do(suf, outdir):
    run([sys.executable, "-u", f"{FEATV2}/s1_rank.py", suf])
    run([sys.executable, "-u", f"{FEATV2}/build_map.py", "s1a" + suf, outdir])
    return {os.path.basename(x): sha(x) for x in sorted(glob.glob(f"{outdir}/predict_wf_*.bin"))}


t0 = time.time()
r1 = do("2r1", "/home/ubuntu/predwf_s1_v2")
r2 = do("2r2", "/home/ubuntu/predwf_s1_v2_r2")
dep = {os.path.basename(x): sha(x) for x in sorted(glob.glob(f"{DEPLOY}/predict_wf_*.bin"))}

# map ten fold: build_map giu ten predict_wf_<yyyymmdd>.bin theo file G015 nguon => trung ten deploy
folds = sorted(dep.keys())
LOG.info("\n== SO SANH BINS (sha256) ==")
n_r1r2 = n_r1dep = 0
rows = []
for f in folds:
    a, b, c = r1.get(f), r2.get(f), dep.get(f)
    ok12 = (a == b); ok1d = (a == c)
    n_r1r2 += ok12; n_r1dep += ok1d
    rows.append({"fold": f, "r1_sha": a, "r1==r2": ok12, "r1==deploy": ok1d})
    LOG.info("%s r1==r2=%s r1==deploy=%s", f, ok12, ok1d)
LOG.info("TONG: r1==r2 %d/10 | r1==deploy %d/10", n_r1r2, n_r1dep)

# sanity: edge5 + spearman vs deploy pred
D = pd.read_parquet(f"{LED}/cand_dev.parquet"); D = D[D.g1lite.notna()]
for nm in ("s1a2r1", "s1a2"):
    P = pd.read_parquet(f"{LED}/pred_{nm}.parquet")
    M = D.merge(P, on=["ts", "sym"], how="inner")
    M["rk"] = M.groupby("ts").score.rank(method="first")
    top = M[M.rk <= 5].groupby("ts").g1lite.mean(); pool = M.groupby("ts").g1lite.mean()
    e = (top - pool).dropna()
    LOG.info("edge5 %s = %+.4f%% (ticks %d)", nm, 100 * e.mean(), len(e))
Pa = pd.read_parquet(f"{LED}/pred_s1a2r1.parquet").rename(columns={"score": "s_r1"})
Pb = pd.read_parquet(f"{LED}/pred_s1a2.parquet").rename(columns={"score": "s_dep"})
mm = Pa.merge(Pb, on=["ts", "sym"], how="inner")
LOG.info("pred r1 vs deploy: rows chung %d | spearman(s_r1, s_dep) = %.8f",
         len(mm), spearmanr(mm.s_r1, mm.s_dep).correlation)
# dong nhat thu hang trong tick? (method=first)
mm["r_r1"] = mm.groupby("ts").s_r1.rank(method="first")
mm["r_dep"] = mm.groupby("ts").s_dep.rank(method="first")
LOG.info("so ban ghi lech thu hang trong tick: %d / %d", int((mm.r_r1 != mm.r_dep).sum()), len(mm))


# ghi MANIFEST.sha256 canh bins r1
man = f"/home/ubuntu/predwf_s1_v2/MANIFEST.sha256"
with open(man, "w") as fh:
    for f in folds:
        fh.write(f"{r1[f]}  {f}\n")
# aggregate sha (noi tiep theo ten sort) = dau van tay BinsProvenance
agg = hashlib.sha256()
for f in folds:
    with open(f"/home/ubuntu/predwf_s1_v2/{f}", "rb") as x:
        for c in iter(lambda: x.read(1 << 22), b""):
            agg.update(c)
LOG.info("aggregate bins.sha256 = %s", agg.hexdigest())
LOG.info("aggregate bins.sha256_16 = %s", agg.hexdigest()[:16])
json.dump({"r1": r1, "r2": r2, "deploy": dep, "n_r1_eq_r2": n_r1r2,
           "n_r1_eq_deploy": n_r1dep, "aggregate_sha256": agg.hexdigest()},
          open("/home/ubuntu/feataudit/s1prov_bins_compare.json", "w"), indent=1)
# don pred tam (khong de lai rac trong ledger)
for suf in ("2r1", "2r2"):
    p = f"{LED}/pred_s1a{suf}.parquet"
    if os.path.exists(p):
        os.remove(p); LOG.info("da xoa tam %s", p)
# khoi phuc pool_rankic.csv goc (bi s1_rank ghi de)
import shutil
shutil.copy("/home/ubuntu/feataudit/pool_rankic.orig.csv", f"{LED}/pool_rankic.csv")
LOG.info("da khoi phuc pool_rankic.csv goc")
LOG.info("DONE %.1f phut", (time.time() - t0) / 60)
