#!/usr/bin/env python3
"""
TASK-130b OPTUNA tuning (Kaggle GPU) — funding-train-optuna-24h.
PHƯƠNG PHÁP (pre-register trước khi chạy):
- Data + split + metric TÁI DÙNG NGUYÊN VẸN từ train_funding_selector.py (exec module, KHÔNG chạy main)
  → cùng purge=horizon, cùng evaluate() → số so được táo-táo với run full e205bb0.
- Optuna TPE 50 trials, objective = rankIC(P_win) trên VAL. TEST KHÔNG ĐƯỢC ĐỤNG trong vòng tuning.
- Early stopping 50 rounds trên VAL AUC (n_estimators trần 2000, số cây thực = best_iteration).
- Chốt: best params → train 3 seeds (42/43/44) → ensemble average P_win → đo TEST ĐÚNG 1 LẦN
  (+ per-quarter + so single-seed để thấy giá trị ensemble).
- Baseline so sánh: model full chưa tune (rankIC TEST 0.2918, LIFT 1.527, commit e205bb0).
"""
import os, glob, json, sys, traceback
import numpy as np

WORK = "/kaggle/working"

def find1(pat):
    m = sorted(glob.glob(pat, recursive=True))
    assert m, "KHONG tim thay: " + pat
    return m[0]

def main():
    import subprocess
    try:
        print(subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True).stdout, flush=True)
    except Exception:
        pass
    ff_all = sorted(glob.glob("/kaggle/input/**/ff_*.bin", recursive=True))
    os.environ.update({
        "TOOL1_GLOB": os.path.dirname(ff_all[0]) + "/ff_*.bin",
        "OI_FILE": find1("/kaggle/input/**/oi_percoin_full.bin"),
        "LABEL_CSV": find1("/kaggle/input/**/funding_label.csv"),
        "MAP_CSV": find1("/kaggle/input/**/symbol_map.csv"),
        "OUT_DIR": WORK, "HORIZON": "24h",
        "TEST_MONTHS": "6", "VAL_MONTHS": "6",
    })
    train_py = find1("/kaggle/input/**/train_funding_selector.py")
    mod = {"__name__": "funding_selector_module", "__file__": train_py}
    exec(compile(open(train_py).read(), train_py, "exec"), mod)
    build_dataset, time_split, evaluate = mod["build_dataset"], mod["time_split"], mod["evaluate"]

    ds, feat = build_dataset()
    tr, va, te = time_split(ds)
    print(f"split tr/va/te = {len(tr)}/{len(va)}/{len(te)}", flush=True)
    assert tr.ts.max() < va.ts.min() and va.ts.max() < te.ts.min(), "LEAK split"
    Xtr, ytr = tr[feat], tr.y
    Xva, yva = va[feat], va.y
    Xte, yte = te[feat], te.y
    pos = ytr.mean()
    spw = (1 - pos) / max(pos, 1e-6)

    import xgboost as xgb
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def make_clf(p, seed):
        return xgb.XGBClassifier(tree_method="hist", device="cuda", eval_metric="auc",
                                 n_jobs=-1, random_state=seed, scale_pos_weight=spw,
                                 n_estimators=2000, early_stopping_rounds=50, **p)

    def objective(trial):
        p = dict(
            max_depth=trial.suggest_int("max_depth", 3, 9),
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            subsample=trial.suggest_float("subsample", 0.5, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.5, 1.0),
            min_child_weight=trial.suggest_float("min_child_weight", 1.0, 100.0, log=True),
            reg_alpha=trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            reg_lambda=trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        )
        clf = make_clf(p, 42)
        clf.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
        r = evaluate("trial", clf.predict_proba(Xva)[:, 1], yva)
        trial.set_user_attr("best_iteration", int(clf.best_iteration))
        trial.set_user_attr("val_LIFT", r["LIFT"])
        return r["rankIC"]

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=int(os.environ.get("N_TRIALS", "50")), show_progress_bar=False)
    best = study.best_trial
    print(f"BEST trial#{best.number}: VAL rankIC={best.value:.4f} LIFT={best.user_attrs['val_LIFT']:.3f} "
          f"best_iter={best.user_attrs['best_iteration']} params={best.params}", flush=True)

    # ===== TEST một lần: 3-seed ensemble với best params =====
    preds, singles = [], []
    for seed in (42, 43, 44):
        clf = make_clf(best.params, seed)
        clf.fit(Xtr, ytr, eval_set=[(Xva, yva)], verbose=False)
        pw = clf.predict_proba(Xte)[:, 1]
        preds.append(pw)
        singles.append(evaluate(f"seed{seed}", pw, yte)["rankIC"])
        clf.save_model(f"{WORK}/model_24h_tuned_seed{seed}.ubj")
    ens = np.mean(preds, axis=0)
    A = evaluate("model_24h_tuned_ens3", ens, yte)
    import pandas as pd
    te2 = te.assign(_p=ens, _q=pd.to_datetime(te.ts, unit="ms").dt.to_period("Q").astype(str))
    A["per_quarter"] = {q: {"N": int(len(g)), "LIFT": round(evaluate(q, g._p.values, g.y.values)["LIFT"], 3),
                            "rankIC": round(evaluate(q, g._p.values, g.y.values)["rankIC"], 4)}
                        for q, g in te2.groupby("_q") if len(g) >= 200}
    A["single_seed_rankIC"] = [round(s, 4) for s in singles]
    A["best_params"] = best.params
    A["best_iteration"] = best.user_attrs["best_iteration"]
    A["val_rankIC_best"] = best.value
    A["baseline_untuned_e205bb0"] = {"rankIC": 0.2918, "LIFT": 1.527}
    A["n_trials"] = len(study.trials)
    json.dump(A, open(f"{WORK}/metrics_24h_tuned.json", "w"), indent=2)
    json.dump([{"n": t.number, "v": t.value, "p": t.params} for t in study.trials],
              open(f"{WORK}/optuna_trials.json", "w"), indent=2)
    print("=== TEST (1 lần, ensemble 3 seeds) ===", flush=True)
    for k in ("rankIC", "hit_top", "LIFT", "z", "single_seed_rankIC", "per_quarter"):
        print(f"  {k} = {A[k]}", flush=True)
    print("OPTUNA_DONE", flush=True)

if __name__ == "__main__":
    try:
        main(); sys.exit(0)
    except Exception:
        traceback.print_exc(); sys.exit(1)
