#!/usr/bin/env python3
"""
run_cpcv_validation.py — DRIVER Pha 2 (FROZEN v1, recipe sha256 738772ff...).

Luồng: đọc VALIDATION window (configs/data_tiers.json) → build 8 block + gap → bốc 200 config từ
search space ĐÃ ĐÓNG BĂNG → ghi cells.jsonl → gọi CpcvBatchRunner (Java, 1 JVM nạp dataset 1 lần) →
đọc results.jsonl → ma trận Calmar_mtm(block×config) → CPCV 28 path (inner chọn / outer đo) +
trial_ledger + DSR + PBO → verdict. Người CHỈ nhận verdict, không thấy số per-config.

CHẠY: python3 run_cpcv_validation.py <tiers.json> <workdir> [--java-cmd "..."] [--n 200] [--seed 42]
Logging: module logging (không print).
"""
from __future__ import annotations
import argparse, json, logging, os, subprocess, sys
from datetime import datetime, timezone, timedelta
from itertools import combinations
import numpy as np
from cpcv_validation import deflated_sharpe_ratio, pbo_cscv
from trial_ledger import TrialLedger, spec_hash, canonical_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("cpcv_val")
TZ = timezone(timedelta(hours=7))  # data_tiers timezone
MS_DAY = 86_400_000

# ===== SEARCH SPACE FROZEN v1 (khớp docs/PHASE1_RECIPE_FROZEN_v1.md) =====
SPACE = {
    "MIN_MOMENTUM_15M": (0.005, 0.020), "PREDICT_SYMBOL_RATE_MAX_THRESHOLD": (0.10, 0.30),
    "AI_DYNAMIC_MULTIPLIER": (1.0, 3.0), "AI_DYNAMIC_MIN": (0.1, 1.0),
    "MS_DOWN_BIG_AVG": (-0.060, -0.025), "DCA_GRID_L1": (-0.75, -0.25),
    "DCA_GRID_STEP": (0.10, 0.30), "DCA_GRID_LEGS": [2, 3, 4],
    "DCA_GRID_W_RATIO": (1.0, 3.0), "RATE_PROFIT_STOP_MARKET": [0.05, 0.06, 0.07, 0.08],
    "TS_PROFIT_MULTIPLIER": [2, 3, 4, 5], "TS_MAX_GAP": (0.05, 0.20),
    "F_BASE": (0.01, 0.05), "U_MAX": (0.40, 0.80),
}
PASS = {"pbo": ("<", 0.20), "dsr": (">", 0.95), "pos_path_ratio": (">=", 0.80), "maxdd_mtm_cap": 0.85}
N_BLOCKS, K_TEST, GAP_DAYS = 8, 2, 14
SPEC_META = {"space": {k: (list(v) if isinstance(v, list) else list(v)) for k, v in SPACE.items()},
             "objective": "median(Calmar_mtm)-0.5*std", "pass": PASS,
             "cpcv": {"n": N_BLOCKS, "k": K_TEST, "gap_days": GAP_DAYS}}


def ymd_ms(s: str) -> int:
    return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=TZ).timestamp() * 1000)


def validation_window(tiers_path):
    t = json.load(open(tiers_path, encoding="utf-8"))["tiers"]["VALIDATION"]
    return ymd_ms(t["start"]), ymd_ms(t["end"]) + MS_DAY - 1  # end inclusive


def build_blocks(start, end, n, gap_ms):
    edges = np.linspace(start, end, n + 1).astype(np.int64)
    return [(int(edges[i]), int(edges[i + 1]) - gap_ms) for i in range(n)]


def sample_configs(space, n, seed):
    rng = np.random.default_rng(seed)
    keys = sorted(space)
    out = []
    for _ in range(n):
        cfg = {}
        for k in keys:
            v = space[k]
            if isinstance(v, list):
                cfg[k] = float(v[int(rng.integers(0, len(v)))])
            else:
                cfg[k] = round(float(rng.uniform(v[0], v[1])), 6)
        out.append(cfg)
    # dedupe giữ thứ tự
    seen, uniq = set(), []
    for c in out:
        key = canonical_json(c)
        if key not in seen:
            seen.add(key); uniq.append(c)
    return uniq


def objective_O(calmars):
    a = np.asarray(list(calmars), float)
    if a.size == 0: return float("nan")
    if a.size == 1: return float(a[0])
    return float(np.median(a) - 0.5 * a.std(ddof=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tiers"); ap.add_argument("workdir")
    ap.add_argument("--java-cmd", default=os.environ.get("CPCV_JAVA_CMD", ""))
    ap.add_argument("--n", type=int, default=200); ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dataset-epoch", default="VALIDATION_2024_07_2025_12")
    ap.add_argument("--campaign", default="v1")
    a = ap.parse_args()
    os.makedirs(a.workdir, exist_ok=True)
    cells_p = os.path.join(a.workdir, "cells.jsonl")
    out_p = os.path.join(a.workdir, "results.jsonl")
    ledger = TrialLedger(os.path.join(a.workdir, "trial_ledger.jsonl"))
    sf = spec_hash(SPEC_META)

    start, end = validation_window(a.tiers)
    blocks = build_blocks(start, end, N_BLOCKS, GAP_DAYS * MS_DAY)
    configs = sample_configs(SPACE, a.n, a.seed)
    log.info("VALIDATION [%d..%d] | %d block gap=%dd | %d config -> %d cell | spec=%s",
             start, end, N_BLOCKS, GAP_DAYS, len(configs), len(configs) * N_BLOCKS, sf)

    # ghi cells.jsonl (ci = seq của config)
    with open(cells_p, "w", encoding="utf-8") as f:
        for ci, cfg in enumerate(configs):
            for bi, (s, e) in enumerate(blocks):
                f.write(canonical_json({"seq": ci, "knobs": cfg, "block": f"b{bi:02d}",
                                        "start": s, "end": e}) + "\n")

    # gọi Java (1 JVM nạp dataset 1 lần). java-cmd rỗng -> chỉ sinh cells (smoke/tách bước).
    if a.java_cmd:
        env = dict(os.environ, CPCV_CELLS=cells_p, CPCV_OUT=out_p)
        log.info("chạy Java: %s", a.java_cmd)
        rc = subprocess.call(a.java_cmd, shell=True, env=env)
        if rc != 0:
            log.error("Java rc=%d -> dừng", rc); sys.exit(2)
    if not os.path.exists(out_p):
        log.warning("chưa có %s (chưa chạy Java?) -> dừng sau khi ghi cells.", out_p); return

    # đọc results -> ma trận calmar[block, config]
    calmar = np.full((N_BLOCKS, len(configs)), np.nan)
    ok, msg = ledger.verify()
    if not ok: raise RuntimeError("ledger hỏng: " + msg)
    seen_cfg = set()
    for line in open(out_p, encoding="utf-8"):
        line = line.strip()
        if not line: continue
        r = json.loads(line)
        ci = int(r["seq"]); bi = int(r["block"][1:])
        calmar[bi, ci] = float(r["metrics"].get("calmar", 0.0))
        key = canonical_json(r["knobs"])
        if key not in seen_cfg:
            seen_cfg.add(key)
            ledger.append(campaign=a.campaign, phase="TEST", spec_fingerprint=sf,
                          dataset_epoch=a.dataset_epoch, knobs=r["knobs"], block="ALL",
                          metrics={"calmar_mtm": float(r["metrics"].get("calmar", 0.0))}, seq=ci)

    # CPCV 28 path: inner argmax O(train) / outer đo O(test)
    paths = []
    for test_idx in combinations(range(N_BLOCKS), K_TEST):
        train_idx = [i for i in range(N_BLOCKS) if i not in test_idx]
        o_train = np.array([objective_O(calmar[train_idx, c]) for c in range(len(configs))])
        w = int(np.nanargmax(o_train))
        paths.append(objective_O(calmar[list(test_idx), w]))
    o_tests = np.array(paths, float)
    pos_ratio = float(np.mean(o_tests > 0))

    s_blk = N_BLOCKS if N_BLOCKS % 2 == 0 else N_BLOCKS - 1
    pbo = pbo_cscv(calmar[:s_blk], s_blocks=s_blk).get("pbo", float("nan"))
    best = int(np.nanargmax([objective_O(calmar[:, c]) for c in range(len(configs))]))
    series = calmar[:, best]
    sr_std = float(np.std([objective_O(calmar[:, c]) for c in range(len(configs))], ddof=1)) or 1.0
    n_tr = ledger.n_trials(a.dataset_epoch)
    dsr = deflated_sharpe_ratio(np.asarray(series, float), n_trials=max(2, n_tr),
                                sharpe_std_across_trials=max(1e-6, sr_std)).get("dsr", float("nan"))

    verdict = (pbo < 0.20 and dsr > 0.95 and pos_ratio >= 0.80)
    log.info("=== VERDICT %s | O_test median=%.4f | %%path+=%.0f%% | PBO=%.2f DSR=%.3f (n_trials=%d) ===",
             "PASS" if verdict else "FAIL", float(np.median(o_tests)), pos_ratio * 100, pbo, dsr, n_tr)
    log.info(">>> LƯU Ý: VALIDATION 2024-2025 đã bị nhìn quá khứ → DSR là CẬN TRÊN. 2026 mới là trọng tài.")
    json.dump({"verdict": "PASS" if verdict else "FAIL", "O_test_median": float(np.median(o_tests)),
               "pos_path_ratio": pos_ratio, "pbo": pbo, "dsr": dsr, "n_trials": n_tr,
               "best_config": configs[best], "spec": sf},
              open(os.path.join(a.workdir, "verdict.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
