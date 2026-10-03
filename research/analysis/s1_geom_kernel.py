#!/usr/bin/env python3
"""S1_FEAT_GEOM — kernel Kaggle GPU: S1 ranker s1a2x1 recipe x1_s1_rank.py (= CTRL K42/S7 cua S1_RETRAIN_NOISE) CHI doi tap feature.
Pre-reg docs/prereg/PREREG_S1_FEAT_GEOM.md. Arm (device=cuda, xgboost 3.2.0):
  G  = KEEP9 + GEOM(9)          seed 42, 7  -> G42, G7
  GN = KEEP9 + GEOM(9) + noise  seed 42, 7  -> GN42, GN7  (doi chung khop nhieu)
Ghi pred_<arm>.parquet (ts, sym, score) + summary.json (edge5/fold, importance gain/total_gain/weight moi fold).
Usage (Oracle): python3 s1_geom_kernel.py build | push | status | fetch
"""
import glob, hashlib, json, logging, os, shutil, subprocess, sys, time
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("geom_k")
SLUG = "s1-geom-gpu"
USER = "chuyendinh"
DS = ["s1-featv2-x1-20260919", "s1-geom-x1-20261003"]
D = "/home/ubuntu/claude_master/1003/geom"
MD5 = {"feat_v2_x1_keep9.parquet": "1aa3b97490cb68d6ce654051184eae7c",
       "cand_dev_x1_lite.parquet": "2cc8381e0577b5289fa1e5714fd865fe",
       "geom_x1.parquet": "__GEOM_MD5__"}
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d", "ret_14d", "ls_global",
        "rk_oi_delta24h"]
GEOM = ["pos24", "pos7d", "dist_high24", "dist_low24", "atr_ratio", "range7d", "rk_pos24", "rk_dist_low24", "rk_atr_ratio"]
ARMS = [("G42", 42, KEEP + GEOM), ("GN42", 42, KEEP + GEOM + ["noise"]),
        ("G7", 7, KEEP + GEOM), ("GN7", 7, KEEP + GEOM + ["noise"])]
CUTS16 = ("20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001 20240101 20240401 20240701 "
          "20241001 20250101 20250401 20250701 20251001").split()


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def kaggle_main():
    W = "/kaggle/working"
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "xgboost==3.2.0"], check=True)
    import numpy as np
    import pandas as pd
    import xgboost as xgb
    assert xgb.__version__ == "3.2.0", ("xgboost version", xgb.__version__)
    import platform
    log.info("xgb %s pandas %s numpy %s py %s plat %s cpu %s", xgb.__version__, pd.__version__, np.__version__,
             sys.version.split()[0], platform.platform(), os.cpu_count())
    try:
        log.info("nvidia-smi: %s", subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True).stdout.strip())
    except Exception as e:  # noqa: BLE001
        log.info("nvidia-smi loi %s", e)
    path = {}
    for fn in MD5:
        g = glob.glob("/kaggle/input/**/" + fn, recursive=True)
        assert g, fn
        path[fn] = g[0]
        m = md5f(g[0])
        assert m == MD5[fn], (fn, m)
        log.info("dataset %s md5 OK %s", fn, m)
    H, TZ = 3600000, 7 * 3600000
    PURGE = 72 * H
    T2026 = int(pd.Timestamp("2026-01-01").value // 10 ** 6) - TZ
    t0 = time.time()
    # --- D y het x1_s1_rank.py / s1_retrain_noise_kernel.py (ledger loc g1lite, rel5 ngu phan vi trong tick, join theo gio) ---
    Dd = pd.read_parquet(path["cand_dev_x1_lite.parquet"])
    Dd = Dd[Dd.g1lite.notna()].copy()
    assert Dd.ts.max() < T2026, "du lieu 2026 trong ledger"
    Dd["med"] = Dd.groupby("ts").g1lite.transform("median")
    Dd["rel"] = Dd.g1lite - Dd.med
    Dd["rk"] = Dd.groupby("ts").rel.rank(pct=True, method="first")
    Dd["rel5"] = np.minimum((Dd.rk * 5).astype(int), 4)
    Dd["ts_h"] = (Dd.ts // H) * H
    F = pd.read_parquet(path["feat_v2_x1_keep9.parquet"])
    G = pd.read_parquet(path["geom_x1.parquet"])
    assert len(F) == len(G) and (F.ts.to_numpy() == G.ts.to_numpy()).all() and (F.sym.to_numpy() == G.sym.to_numpy()).all()
    F = pd.concat([F, G[GEOM + ["noise"]]], axis=1)
    del G
    n0 = len(Dd)
    Dd = Dd.merge(F.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
    assert len(Dd) == n0
    del F
    log.info("pool %s vol_7d %.4f pos24 %.4f atr_ratio %.4f noise %.4f load %.0fs", Dd.shape, Dd.vol_7d.notna().mean(),
             Dd.pos24.notna().mean(), Dd.atr_ratio.notna().mean(), Dd.noise.notna().mean(), time.time() - t0)
    cut = [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 10 ** 6) - TZ for c in CUTS16]
    summ = {"xgb": xgb.__version__, "platform": platform.platform(), "pool_rows": int(len(Dd)),
            "cov_pool": {k: float(Dd[k].notna().mean()) for k in KEEP + GEOM + ["noise"]}, "arms": {}}
    for arm, seed, FE in ARMS:
        ta = time.time()
        preds, edges, folds = [], [], []
        for i, c in enumerate(cut):
            hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 10 ** 6) - TZ
            tr = Dd[Dd.ts < c - PURGE].sort_values("ts")
            oos = Dd[(Dd.ts >= c) & (Dd.ts < hi)].sort_values("ts")
            assert len(tr) >= 5000 and len(oos) > 0, (arm, i)
            assert tr.ts.max() < c, "LEAK"
            m = xgb.XGBRanker(objective="rank:ndcg", n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8,
                              colsample_bytree=0.8, min_child_weight=50, n_jobs=4, tree_method="hist", random_state=seed,
                              lambdarank_pair_method="topk", lambdarank_num_pair_per_sample=8, device="cuda")
            m.fit(tr[FE], tr.rel5, qid=pd.factorize(tr.ts, sort=True)[0])
            p = m.predict(oos[FE])
            o = oos[["ts", "sym", "g1lite"]].assign(score=-p)
            o["rk"] = o.groupby("ts").score.rank(method="first")
            e = o[o.rk <= 5].groupby("ts").g1lite.mean() - o.groupby("ts").g1lite.mean()
            bst = m.get_booster()
            imp = {t: {k: float(v) for k, v in bst.get_score(importance_type=t).items()}
                   for t in ("gain", "total_gain", "weight")}
            folds.append(dict(fold=i, cut=CUTS16[i], n_train=int(len(tr)), n_oos=int(len(oos)),
                              edge5=float(100 * e.mean()), imp=imp))
            log.info("%s fold %d %s train %d oos %d edge5 %+.3f%%", arm, i, CUTS16[i], len(tr), len(oos), 100 * e.mean())
            preds.append(o[["ts", "sym", "score"]])
            edges.append(e)
        P = pd.concat(preds, ignore_index=True)
        P.to_parquet(f"{W}/pred_{arm}.parquet", index=False)
        E = pd.concat(edges)
        summ["arms"][arm] = dict(seed=seed, feats=FE, secs=round(time.time() - ta, 1), rows=int(len(P)),
                                 edge5_all=float(100 * E.mean()), folds=folds)
        log.info("ARM %s xong %.0fs rows %d edge5 %+.3f%%", arm, time.time() - ta, len(P), 100 * E.mean())
        json.dump(summ, open(f"{W}/summary.json", "w"), indent=1)
    log.info("DONE")


KAG = "/home/ubuntu/envs/xgb-env/bin/kaggle"


def run_cli(*a):
    r = subprocess.run([KAG] + list(a), capture_output=True, text=True)
    log.info("kaggle %s -> rc %d\n%s%s", " ".join(a), r.returncode, r.stdout[-3000:], r.stderr[-1500:])
    return r


def build():
    kd = D + "/k_train"
    os.makedirs(kd, exist_ok=True)
    gm = json.load(open(D + "/geom_meta.json"))["md5"]
    src = open(os.path.abspath(__file__)).read()
    ph = '"geom_x1.parquet": "' + "__GEOM" + '_MD5__"'
    assert src.count(ph) == 1
    open(kd + "/" + SLUG + ".py", "w").write(src.replace(ph, '"geom_x1.parquet": "%s"' % gm))
    meta = {"id": USER + "/" + SLUG, "title": SLUG, "code_file": SLUG + ".py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_tpu": False,
            "enable_internet": True, "dataset_sources": [USER + "/" + x for x in DS], "kernel_sources": [],
            "competition_sources": [], "model_sources": []}
    json.dump(meta, open(kd + "/kernel-metadata.json", "w"), indent=1)
    log.info("built %s geom md5 %s code md5 %s", kd, gm, md5f(kd + "/" + SLUG + ".py"))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "build":
        build()
    elif cmd == "push":
        run_cli("kernels", "push", "-p", D + "/k_train")
    elif cmd == "status":
        run_cli("kernels", "status", USER + "/" + SLUG)
    elif cmd == "fetch":
        os.makedirs(D + "/kout", exist_ok=True)
        run_cli("kernels", "output", USER + "/" + SLUG, "-p", D + "/kout")
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    if os.path.isdir("/kaggle/input"):
        kaggle_main()
    else:
        main()
