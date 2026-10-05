#!/usr/bin/env python3
"""S1_FIRSTHIT_RANK — kernel Kaggle GPU: S1 ranker s1a2x1 (recipe x1_s1_rank.py) voi TARGET = nhan first-hit FLAT3.
Pre-reg docs/prereg/PREREG_S1_FIRSTHIT_RANK.md. Arm (seed 42, 7; device=cuda):
  FHP = recipe S1 y het (XGBRanker rank:ndcg, topk 8, 300/4/0,05 ...), relevance = y_FH in {0,1}.
  FHL = nhu FHP nhung truncation NDCG@16: lambdarank_num_pair_per_sample=16 (topk) + eval_metric ndcg@16.
Khac CTRL (K42/S7 cua S1_RETRAIN_NOISE): target (rel5 -> y_FH), purge 72h -> 169h, bo dong thieu nhan khoi train.
Usage (Oracle): python3 s1_fhrank_kernel.py build | push | status | fetch
"""
import glob, hashlib, json, logging, os, shutil, subprocess, sys, time
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("fhr_k")
SLUG = "s1-fhrank-gpu"
USER = "chuyendinh"
DS = ["s1-featv2-x1-20260919", "s1-fhrank-yfh-20261003"]
D = "/home/ubuntu/claude_master/1003/fhr"
MD5 = {"feat_v2_x1_keep9.parquet": "1aa3b97490cb68d6ce654051184eae7c",
       "cand_dev_x1_lite.parquet": "2cc8381e0577b5289fa1e5714fd865fe",
       "yfh_x1.parquet": "99c1e2ee70790083632caa53e30d877d"}
ARMS = [("FHP42", 42, 8), ("FHL42", 42, 16), ("FHP7", 7, 8), ("FHL7", 7, 16)]
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d", "ret_14d", "ls_global",
        "rk_oi_delta24h"]
CUTS16 = ("20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001 20240101 20240401 20240701 "
          "20241001 20250101 20250401 20250701 20251001").split()
PURGE_H = 169   # >= 168h (horizon nhan) + 15' lech can chinh nhan


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
    log.info("xgb %s pandas %s numpy %s plat %s", xgb.__version__, pd.__version__, np.__version__, platform.platform())
    try:
        log.info("nvidia-smi: %s", subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True).stdout.strip())
    except Exception as e:  # noqa: BLE001
        log.info("nvidia-smi loi %s", e)
    path = {}
    for fn in MD5:
        g = glob.glob("/kaggle/input/**/" + fn, recursive=True)
        assert g, fn
        path[fn] = g[0]
        assert md5f(g[0]) == MD5[fn], fn
        log.info("dataset %s md5 OK", fn)
    H, TZ = 3600000, 7 * 3600000
    PURGE = PURGE_H * H
    T2026 = int(pd.Timestamp("2026-01-01").value // 10 ** 6) - TZ
    Dd = pd.read_parquet(path["cand_dev_x1_lite.parquet"])
    Dd = Dd[Dd.g1lite.notna()].copy()
    assert Dd.ts.max() < T2026
    Y = pd.read_parquet(path["yfh_x1.parquet"])
    n0 = len(Dd)
    Dd = Dd.merge(Y, on=["ts", "sym"], how="left")
    assert len(Dd) == n0 and Dd.yfh.notna().all(), "yfh khong phu dung tap ledger"
    Dd["ts_h"] = (Dd.ts // H) * H
    F = pd.read_parquet(path["feat_v2_x1_keep9.parquet"])
    Dd = Dd.merge(F.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
    del F
    log.info("pool %s co yfh %.4f vol_7d %.3f", Dd.shape, (Dd.yfh >= 0).mean(), Dd.vol_7d.notna().mean())
    cut = [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 10 ** 6) - TZ for c in CUTS16]
    summ = {"xgb": xgb.__version__, "platform": platform.platform(), "purge_h": PURGE_H, "arms": {}}
    for arm, seed, topk in ARMS:
        ta = time.time()
        preds, folds = [], []
        for i, c in enumerate(cut):
            hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 10 ** 6) - TZ
            tr_all = Dd[Dd.ts < c - PURGE]
            tr = tr_all[tr_all.yfh >= 0].sort_values("ts")
            oos = Dd[(Dd.ts >= c) & (Dd.ts < hi)].sort_values("ts")
            assert len(tr) >= 5000 and len(oos) > 0, (arm, i)
            assert tr.ts.max() < c - 168 * H, "LEAK"
            kw = dict(objective="rank:ndcg", n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8,
                      colsample_bytree=0.8, min_child_weight=50, n_jobs=4, tree_method="hist", random_state=seed,
                      lambdarank_pair_method="topk", lambdarank_num_pair_per_sample=topk, device="cuda")
            if topk == 16:
                kw["eval_metric"] = "ndcg@16"
            m = xgb.XGBRanker(**kw)
            m.fit(tr[KEEP], tr.yfh.astype(int), qid=pd.factorize(tr.ts, sort=True)[0])
            o = oos[["ts", "sym", "yfh"]].assign(score=-m.predict(oos[KEEP]))
            o["rk"] = o.groupby("ts").score.rank(method="first")
            ok = o[o.yfh >= 0]
            lift = ok[ok.rk <= 16].groupby("ts").yfh.mean() - ok[(ok.rk > 16) & (ok.rk <= 50)].groupby("ts").yfh.mean()
            folds.append(dict(fold=i, cut=CUTS16[i], n_train=int(len(tr)), n_train_drop=int(len(tr_all) - len(tr)),
                              n_oos=int(len(oos)), lift16=float(lift.mean())))
            log.info("%s fold %d %s train %d (bo %d) oos %d lift16 %+.4f", arm, i, CUTS16[i], len(tr),
                     len(tr_all) - len(tr), len(oos), lift.mean())
            preds.append(o[["ts", "sym", "score"]])
        P = pd.concat(preds, ignore_index=True)
        P.to_parquet(f"{W}/pred_{arm}.parquet", index=False)
        summ["arms"][arm] = dict(seed=seed, topk=topk, secs=round(time.time() - ta, 1), rows=int(len(P)), folds=folds)
        log.info("ARM %s xong %.0fs rows %d", arm, time.time() - ta, len(P))
        json.dump(summ, open(f"{W}/summary.json", "w"), indent=1)
    log.info("DONE")


KAG = "/home/ubuntu/envs/xgb-env/bin/kaggle"


def run_cli(*a):
    r = subprocess.run([KAG] + list(a), capture_output=True, text=True)
    log.info("kaggle %s -> rc %d\n%s%s", " ".join(a), r.returncode, r.stdout[-3000:], r.stderr[-1500:])
    return r


def dsup():
    kd = D + "/kds"
    assert md5f(kd + "/yfh_x1.parquet") == MD5["yfh_x1.parquet"]
    json.dump({"title": DS[1], "id": USER + "/" + DS[1], "licenses": [{"name": "CC0-1.0"}]},
              open(kd + "/dataset-metadata.json", "w"))
    run_cli("datasets", "create", "-p", kd)


def build():
    kd = D + "/k_train"
    os.makedirs(kd, exist_ok=True)
    shutil.copy2(os.path.abspath(__file__), kd + "/" + SLUG + ".py")
    meta = {"id": USER + "/" + SLUG, "title": SLUG, "code_file": SLUG + ".py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_tpu": False,
            "enable_internet": True, "dataset_sources": [USER + "/" + x for x in DS], "kernel_sources": [],
            "competition_sources": [], "model_sources": []}
    json.dump(meta, open(kd + "/kernel-metadata.json", "w"), indent=1)
    log.info("built %s md5 code %s", kd, md5f(kd + "/" + SLUG + ".py"))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dsup":
        dsup()
    elif cmd == "build":
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
