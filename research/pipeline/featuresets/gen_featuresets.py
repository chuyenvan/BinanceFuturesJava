#!/usr/bin/env python3
"""gen_featuresets.py — sinh cac file JSON version hoa danh sach feature (selector S1/G015x26).

NGUON (khong doan):
  - `docs/analysis/EVAL_SELECTOR_FEATURES.md` §1 (bang 45 cot: ten · nguon · cong thuc, co file:line)
  - `docs/analysis/EVAL_SELECTOR_FEATURES.md` §6.3 (GIU 22 feature, share >= 1.30%)
  - `docs/diag/DIAG_RVOL15M.md` §D (rvol15m: chua du can cu cat offline -> version v1 = drop-one de test)
  - `docs/experiment/G015_RECIPE.md` §2 (cong thuc train: nhan, WFO, XGB hyperparam) + §5/§6 (model, bins)
  - `docs/runbooks/AGENT_RUNBOOK.md` (nhan THAT cua predwf_G015 = `retEnd_4h > 0.015`)

KHONG train, KHONG sim. Thuan sinh JSON. Chay lai: `python3 gen_featuresets.py`
"""
import json, os

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# (index, name, source, formula) — dung THU TU 0..44 nhu model (vi tri, khong co ten cot trong artifact)
FEATURES = [
    (0, "btcMomentum1H", "Tool1 f0", "close_BTC(t)/close_BTC(t-60m)-1, [t-60m,t]"),
    (1, "btcMomentum4H", "Tool1 f1", "close_BTC(t)/close_BTC(t-240m)-1"),
    (2, "btcMomentum24H", "Tool1 f2", "close_BTC(t)/close_BTC(t-1440m)-1"),
    (3, "btcDominance", "Tool1 f3", "vol_BTC(t)/sum vol(t), {t}; ⚠ survivorship diedSymbol"),
    (4, "marketBreadthStrength", "Tool1 f4", "#(close>open tai t)/#valid, {t}; ⚠ survivorship"),
    (5, "rateDown15MAvg", "Tool1 f5", "avg top-100 (close(t)/max15m-1), [t-14m,t]; ⚠ survivorship"),
    (6, "momentum1H", "Tool1 f6", "close(t)/close(t-60m)-1"),
    (7, "momentum4H", "Tool1 f7", "close(t)/close(t-240m)-1"),
    (8, "momentum24H", "Tool1 f8", "close(t)/close(t-1440m)-1"),
    (9, "rsi1H", "Tool1 f9", "RSI14 tren 14 nen 1m, [t-14m,t]"),
    (10, "distFromLow24H", "Tool1 f10", "(close(t)-low24)/low24"),
    (11, "volatilityShock", "Tool1 f11", "(high(t)-low(t))/avgRange20, {t}+[t-21m,t-1]"),
    (12, "basketMomentum15M", "Tool1 f12", "avg_basket getReturn(15)"),
    (13, "basketMomentum1H", "Tool1 f13", "avg_basket getReturn(60)"),
    (14, "basketMomentum24H", "Tool1 f14", "avg_basket getReturn(1440)"),
    (15, "basketRsi14", "Tool1 f15", "avg_basket RSI14"),
    (16, "basketVolSpike", "Tool1 f16", "avg_basket vol(t)/avgVol20"),
    (17, "coinFundingRate", "Tool1 f17", "funding settlement gan nhat <= t (floorEntry)"),
    (18, "basketFundingAvg", "Tool1 f18", "avg_basket cua f17"),
    (19, "fundingRateAvg24H", "Tool1 f19", "avg floorEntry tai t-0,4,8,12,16,20,24h"),
    (20, "fundingRateTrend", "Tool1 f20", "f17 - f19"),
    (21, "fundingPercentileCoin", "Tool1 f21", "percentile funding hien tai trong toan lich su <= t (expanding); ⚠ troi theo lich"),
    (22, "fundingZCoin", "Tool1 f22", "z-score tren cung tap expanding <= t; ⚠ troi theo lich"),
    (23, "fundingPersistence", "Tool1 f23", "so ky lien tiep cung dau, quet lui tu ky <= t; ⚠ proxy thoi gian"),
    (24, "fundingSum24h", "Tool1 f24", "sum funding settle trong (t-24h, t]"),
    (25, "fundingAbs", "Tool1 f25", "abs(funding ky <= t)"),
    (26, "volumeZCoin", "Tool1 f26", "(vol(t)-mean20_truoc)/std20_truoc (bo nen t khoi mean/std)"),
    (27, "volumeTrend", "Tool1 f27", "avgVol5/avgVol60 (deu bo nen t)"),
    (28, "distFromHigh24H", "Tool1 f28", "(high24-close(t))/high24"),
    (29, "rangePosition24H", "Tool1 f29", "(close(t)-low24)/(high24-low24)"),
    (30, "atrSqueeze", "Tool1 f30", "avgRange14/avgRange100 (bo nen t)"),
    (31, "relStrengthBtc24H", "Tool1 f31", "f8 - f2"),
    (32, "fundingRankCS", "Tool1 f32", "rank-percentile f17 giua cac coin cung moc t"),
    (33, "volumeZRankCS", "Tool1 f33", "rank-percentile f26 cung moc t"),
    (34, "momentumRankCS", "Tool1 f34", "rank-percentile f8 cung moc t"),
    (35, "ret15m", "Tool1 f35", "close(t)/close(t-15m)-1"),
    (36, "rvol15m", "Tool1 f36", "std cua return giua 15 nen gan nhat"),
    (37, "volumeZ5m", "Tool1 f37", "sumVol5/(avgVol20*5)"),
    (38, "closePosRange15m", "Tool1 f38", "(close(t)-low15)/(high15-low15)"),
    (39, "wickRatio15m", "Tool1 f39", "avg (high-max(open,close))/(high-low) tren 15 nen"),
    (40, "oi_delta24h", "OI tool #41", "oi(t)/oi(t-24h)-1; ExportFundingOiPerCoin.java:104-107"),
    (41, "oi_z", "OI tool #42", "OI z-score expanding no-leak; ExportFundingOiPerCoin.java:85"),
    (42, "ls_global", "OI tool #43", "long/short ratio global (Binance metrics)"),
    (43, "ls_toptrader", "OI tool #44", "long/short ratio top traders"),
    (44, "taker_buy", "OI tool #45", "takerBuyRatio r/(1+r); ExportFundingOiPerCoin.java:117-124"),
]

assert len(FEATURES) == 45 and [f[0] for f in FEATURES] == list(range(45))

# --- STAGE 2 (docs/prereg/PREREG_STAGE2_FEATVAR.md) — cot APPEND vao CUOI vector -------------
# Index 45..54 KHONG nam trong vector 45 cot cua Tool1/ONNX. Chung chi ton tai o duong OFFLINE
# Stage 2 (`g015_net_train_add.py --add-feats`), gan vao cac cot CUOI (append-only, xem
# docs/plan/PREP_STAGE2_TRAIN.md §2.2). 45 vi tri cu KHONG xE dich => model 45 cot con so duoc.
# 45..49 = 5 feature PASS cua Stage 0 (docs/result/RESULT_PRESCREEN_FEAT.md §3).
# 50..54 = 5 cot NHIEU sinh trong kernel, dung DUNG NaN-mask cua 45..49 (doi chung "them cot != them tin hieu").
APPENDED = [
    (45, "rvol7d", "prefeat (rvb_1m 1h bars)",
     "std(log-return 1h) tren 168 gio (7d), cua so DONG, min_periods=84"),
    (46, "mom30d", "prefeat (rvb_1m 15m bars)", "c15(t)/c15(t-30d)-1 (2880 nen 15m)"),
    (47, "mom7d", "prefeat (rvb_1m 15m bars)", "c15(t)/c15(t-7d)-1 (672 nen 15m)"),
    (48, "daysSinceHigh30D", "prefeat (rvb_1m 15m bars)",
     "(idx - argmax(h15 trong 2880 nen 15m))/96, don vi NGAY; sliding argmax min_periods=1440"),
    (49, "oi_delta7d", "prefeat (oi_percoin_full.bin cot 0)",
     "prod_{k=0..6}(1+oi_delta24h(t-24h*k))-1 tren luoi 5m roi lay tai tick 15m"),
    (50, "noise_rvol7d", "SINH TRONG KERNEL (numpy default_rng)",
     "gia tri ngau nhien N(0,1) tai moi dong, NaN dung DUNG mask cua cot 45"),
    (51, "noise_mom30d", "SINH TRONG KERNEL (numpy default_rng)",
     "gia tri ngau nhien N(0,1) tai moi dong, NaN dung DUNG mask cua cot 46"),
    (52, "noise_mom7d", "SINH TRONG KERNEL (numpy default_rng)",
     "gia tri ngau nhien N(0,1) tai moi dong, NaN dung DUNG mask cua cot 47"),
    (53, "noise_daysSinceHigh30D", "SINH TRONG KERNEL (numpy default_rng)",
     "gia tri ngau nhien N(0,1) tai moi dong, NaN dung DUNG mask cua cot 48"),
    (54, "noise_oi_delta7d", "SINH TRONG KERNEL (numpy default_rng)",
     "gia tri ngau nhien N(0,1) tai moi dong, NaN dung DUNG mask cua cot 49"),
]
assert [f[0] for f in APPENDED] == list(range(45, 55))
FEATURES_EXT = FEATURES + APPENDED

KEEPERS_22 = [20, 24, 5, 30, 6, 32, 14, 18, 42, 2, 17, 7, 41, 29, 8, 35, 31, 44, 10, 40, 28, 36]

SOURCES = {
    "feature_list": "docs/analysis/EVAL_SELECTOR_FEATURES.md §1 (45 cot, co file:line) + §0",
    "keepers": "docs/analysis/EVAL_SELECTOR_FEATURES.md §6.3 (GIU 22, share >= 1.30%)",
    "rvol15m": "docs/diag/DIAG_RVOL15M.md §D (KHONG du can cu cat tu offline; phai do bang rank-IC + lift@8)",
    "recipe": "docs/experiment/G015_RECIPE.md §2 (cong thuc) + §5 (dau vao ghim) + §6 (bins)",
    "train_duong": "docs/plan/PREP_STAGE2_TRAIN.md §1 (duong train THAT cua net015-45, script + fold + seed + tham so)",
    "label": "docs/runbooks/AGENT_RUNBOOK.md (nhan THAT cua predwf_G015x26 = retEnd_4h > 0.015; dinh chinh 2026-09-06)",
}

HYPERPARAMS = {
    "xgb": {
        "objective": "binary:logistic",
        "n_estimators": 400, "max_depth": 5, "learning_rate": 0.05,
        "subsample": 0.8, "colsample_bytree": 0.8, "min_child_weight": 20,
        "scale_pos_weight": "(1-pos)/pos, pos = ty le lop 1 CUA TUNG FOLD (khong phai toan cuc): fold0 = 2.70527601 ... fold17 = 4.35441685",
        "eval_metric": "auc", "n_jobs": -1, "tree_method": "hist",
        "random_state": 42, "device_goc": "cuda (Kaggle GPU)",
    },
    "xgboost_version": "3.2.0",
    "pipeline_version": "wfo-selector-v2-1m-canonical-20260804",
    "grid_min": 15,
    "max_train_rows": 60000000,
}

FOLD_INDEX_TRAP = (
    "model_f<i>_4h.json lay i = VI TRI trong CUT_DATES. CUT_DATES ban repo hien tai da noi them 3 fold DEV2021 "
    "(20210401/20210701/20211001) + 20251231 => cutoff 20240101 = fidx 11, KHONG phai 8 nhu ban deploy. "
    "Moi bang so sanh phai khop theo CUTOFF, khong theo so trong ten file (nguon docs/plan/PREP_STAGE2_TRAIN.md §1.2)."
)

FOLDS_V0 = {
    "scheme": "expanding WFO",
    "first_cutoff": "20220101", "last_cutoff": "20260401",
    "n_folds": 18, "oos_months": 3, "purge_steps": 288, "purge_hours": 72,
    "tz_offset_ms": 25200000, "tz": "GMT+7",
    "cutoffs": ["20220101", "20220401", "20220701", "20221001", "20230101", "20230401",
                "20230701", "20231001", "20240101", "20240401", "20240701", "20241001",
                "20250101", "20250401", "20250701", "20251001", "20260101", "20260401"],
    "canh_bao": "fold 20260101/20260401 nam TREN HoldoutSeal (2026-01-01): KHONG dua vao sim/verdict khi chua HOLDOUT_UNSEAL",
    "bat_danh_so_fold": FOLD_INDEX_TRAP,
}

SIM_RUNS_V0 = [
    {"run": "C3", "mo_ta": "48 thang (30 thang cho C2b la so lich su)", "nguon": "docs/runbooks/AGENT_RUNBOOK.md"},
    {"run": "X1_C3 / X1_C3_FULL", "mo_ta": "48 thang, cham diem bang research/analysis/x1_rates.py", "nguon": "docs/runbooks/AGENT_RUNBOOK.md"},
    {"run": "FG_KEEPLEG0", "mo_ta": "MOC parity (kg0-g170, md5 99e42b75) — ton tai ca Oracle lan Kaggle", "nguon": "docs/runbooks/AGENT_RUNBOOK.md; commit 24e6bdc"},
    {"run": "C4_parity", "mo_ta": "map s1a2x1 tu bins predwf_G015x26, byte-identical 16/16", "nguon": "docs/experiment/G015_RECIPE.md §6"},
    {"run": "G5_parity_S1", "mo_ta": "doi THU TU x26, giu nguyen multiset P(win)", "nguon": "docs/experiment/G5_VALUE_LABELS.md"},
]

MODEL_PATHS_V0 = {
    "dir": "/home/ubuntu/claudedata/predwf_G015",
    "files": "model_f{0..17}_4h.json (18 fold, num_feature=45, feature_names=None)",
    "kernel_goc": "chuyendinh/selector-15mtr-pred15-net015-gpu (log: claudedata/predwf_G015/selector-15mtr-pred15-net015-gpu.log, mtime 2026-08-14)",
    "trainer_goc": "DA MAT (docs/experiment/G3_X26_RECOVERY.md §8) — ban trong repo la ban TAI DUNG, xac minh PASS o docs/experiment/G015_RECIPE.md §4 (fold 8)",
}
BINS_PATH_V0 = {
    "dir": "/home/ubuntu/claudedata/predwf_G015x26",
    "files": "predict_wf_{cutoff}.bin (16 bin) + MANIFEST.sha256",
    "dinh_dang": "26 B/rec, big-endian >q h 4f; slot p0 = 4h, ba slot con lai NaN",
    "sha256_fold8_goc": "e5a684f4132996ea47cc2341960cf0fd3a5dc0262c65368bac5cf63a4117f131",
}

TRAIN_CODE = {
    "git_commit_repo_head": "6695a8c",  # repo HEAD luc ghi (2026-09-24); file g015_net_train.py KHONG doi tu f442c0e
    "file": "research/pipeline/g015_net_train.py",
    "file_last_modified_commit": "f442c0e",
    "snapshot": "research/pipeline/train/g015_net_train_v0_snapshot.py (byte-identical, sha256 e8b6798f...)",
    "predict_file": "research/pipeline/g015x26_train.py (predict lai tu 18 model da luu; snapshot o research/pipeline/train/)",
    "lenh": "python3 g015_net_train.py --fold 20240101 --device cuda --save-model --out-dir <dir>",
}


def fs(version, name, keep_idx, status, notes, alias):
    feats = [{"index": i, "name": n, "source": s, "formula": f} for (i, n, s, f) in FEATURES_EXT if i in keep_idx]
    d = {
        "version": version,
        "alias": alias,
        "status": status,
        "n_features": len(feats),
        "features": feats,
        "label": "retEnd_4h > 0.015",
        "label_filter": "nBars_4h >= 16 va retEnd_4h notna",
        "label_mode": "net (LABEL_MODE=net, NET_THR=0.015)",
        "folds": FOLDS_V0,
        "seed": 42,
        "hyperparams": HYPERPARAMS,
        "train_code_git_commit": TRAIN_CODE["git_commit_repo_head"] if status == "trained" else None,
        "train_code": TRAIN_CODE,
        "model_paths": MODEL_PATHS_V0 if status == "trained" else None,
        "bins_path": BINS_PATH_V0 if status == "trained" else None,
        "sim_runs": SIM_RUNS_V0 if status == "trained" else [],
        "sources": SOURCES,
        "notes": notes,
    }
    return d


ALL45 = set(range(45))
IDX_V1 = ALL45 - {36}                       # 45 - rvol15m
IDX_V2 = set(KEEPERS_22) - {36}             # GIU 22 - rvol15m = 21
assert len(IDX_V1) == 44 and len(IDX_V2) == 21

FILES = {
    "fs_v0_45.json": fs("v0", "45-col goc", ALL45, "trained",
        "Ban GOC 45 cot. Model dang chay = predwf_G015 (= G015x26 = net015). "
        "Model/ONNX KHONG luu ten cot (feature_names=None, metadata_props rong) => thu tu nay la "
        "nguon duy nhat de map index -> ten (khop FEAT40_LOOKAHEAD.md C1 va SelectorOnnxInferenceManager.extractFeatures45). "
        "rvol15m (#36) chiem 34,09% gain nhung rank-IC ~ 0 => xem fs_v1_44.json.",
        "predwf_G015 / G015x26 / net015 (45 cot)"),
    "fs_v1_44.json": fs("v1", "45 - rvol15m", IDX_V1, "planned",
        "Drop-one #36 rvol15m (NGHIEM THU DUY NHAT cua vong ablation). "
        "Can cu: docs/diag/DIAG_RVOL15M.md §D — tieu chi cat chot TRUOC khong thoa offline (lift@8 = 4,12 [3,93;4,33]), "
        "nen phai quyet dinh bang drop-one retrain + sim. DU DOAN chot truoc: admit TANG, expectancy/top-8 win GIAM "
        "(rvol15m do BIEN DO/fat-tail). Cham bang rank-IC cross-section + top-8 lift (KHONG dung gain). "
        "CHUA train/chua sim — dien model_paths/bins_path/sim_runs o Stage 1/2.",
        "drop-one rvol15m (44 cot) — CHUA train"),
    "fs_v2_21.json": fs("v2", "GIU 22 - rvol15m = 21 keeper", IDX_V2, "planned",
        "Tap GIU theo §6.3 (share >= 1,30%) BO rvol15m => 21 cot. Luu y: §6.3 ghi GIU = 22 (gOM #36 rvol15m); "
        "v2 co tinh chon loc lai sau khi #36 duoc phan xu o v1, nen = 21. "
        "Neu ablation cho thay GIU ca #36 thi dung fs_v0_45.json / fs_v1_44.json, KHONG sua file nay. "
        "CHUA train/chua sim — dien o Stage 1/2.",
        "21 keeper (GIU 22 - rvol15m)"),
}

def reserved(version, purpose):
    """Khung TRONG cho version chua chot (dien o Stage 1/2). Giu DU truong bat buoc, gia tri rong/null."""
    return {
        "version": version, "alias": "RESERVED — chua chot", "status": "reserved",
        "n_features": 0, "features": [], "label": "retEnd_4h > 0.015", "folds": None,
        "seed": None, "hyperparams": None, "train_code_git_commit": None,
        "model_paths": None, "bins_path": None, "sim_runs": [], "sources": SOURCES,
        "notes": "KHUNG TRONG — " + purpose + ". Di theo luat docs: them/bot cot => VERSION MOI, KHONG sua version cu (xem README.md).",
    }


FILES["fs_v3_reserved.json"] = reserved("v3", "cho vong ablation Stage 1 (bo nhom NGAT CHAC 5/45, xem commit 26cdf5e / docs/PREREG_FEAT_ABLATION*)")
# fs_v4_reserved.json / fs_v5_reserved.json da BI GO (git rm, 2026-09-24): 2 khung trong do da
# duoc dung that boi 6 bien the Stage 2 (v4..v9). Khong co thong tin nao mat (chung rong).

# --- STAGE 2: 6 bien the train (docs/prereg/PREREG_STAGE2_FEATVAR.md muc 1) --------------------
KEEPERS21 = set(KEEPERS_22) - {36}                       # 21 moc (fs_v2_21)
ADD_REAL = {45, 46, 47, 48, 49}                          # 5 feature PASS
ADD_NOISE = {50, 51, 52, 53, 54}                         # 5 cot nhieu
DROP_ARG = sorted(ALL45 - KEEPERS21)                     # 24 cot bo (--drop-cols), DUNG CHUNG moi bien the
assert len(DROP_ARG) == 24


def fs_var(version, alias, keep_idx, drop_cols, notes, purpose):
    """File version cho 1 bien the Stage 2: 21 moc (+ cot append o cuoi), ghi ro --drop-cols."""
    d = fs(version, alias, keep_idx, "planned", notes, alias)
    d["variant"] = version
    d["stage2"] = {
        "purpose": purpose,
        "base_keepers": sorted(KEEPERS21),
        "appended_real": sorted(ADD_REAL & keep_idx),
        "appended_noise": sorted(ADD_NOISE & keep_idx),
        "drop_cols_arg": ",".join(str(i) for i in sorted(drop_cols)),
        "keep_idx": sorted(keep_idx),
        "so_cot": len(keep_idx),
        "trainer": "research/pipeline/g015_net_train_add.py",
        "lenh": "python3 g015_net_train_add.py --add-feats <prefeat.parquet> --drop-cols \"%s\" --out-dir <dir>"
                 % ",".join(str(i) for i in sorted(drop_cols)),
        "pre_reg": "docs/prereg/PREREG_STAGE2_FEATVAR.md",
        "luu_y": "10 cot index 45..54 la append-only cho duong OFFLINE; KHONG cham ONNX/NUM_FEATURES=45/LIVE.",
    }
    return d


V_ARMS = {
    "fs_v4_21.json": ("V0", "21 keeper (MOC, control)", KEEPERS21,
                      set(DROP_ARG) | ADD_REAL | ADD_NOISE,
                      "Moc doi chung: dung 21 keeper, KHONG cot append nao."),
    "fs_v5_26.json": ("V1", "21 + ca 5 feature PASS", KEEPERS21 | ADD_REAL,
                      set(DROP_ARG) | ADD_NOISE, "De xuat chinh: them ca 5 feature Stage 0 PASS."),
    "fs_v6_23.json": ("V2", "21 + {mom7d, mom30d}", KEEPERS21 | {46, 47},
                      set(DROP_ARG) | {45, 48, 49} | ADD_NOISE,
                      "Nhom momentum dai han thuan (2 khung)."),
    "fs_v7_22.json": ("V3", "21 + {rvol7d}", KEEPERS21 | {45},
                      set(DROP_ARG) | {46, 47, 48, 49} | ADD_NOISE,
                      "Nguoi thay truc tiep cua rvol15m vua bi bo (#36)."),
    "fs_v8_23.json": ("V4", "21 + {daysSinceHigh30D, oi_delta7d}", KEEPERS21 | {48, 49},
                      set(DROP_ARG) | {45, 46, 47} | ADD_NOISE,
                      "2 feature it trung nhat voi ho hien co (rho 0,320 / 0,259)."),
    "fs_v9_31.json": ("V5", "21 + 5 + 5 cot NHIEU (mask khop)", KEEPERS21 | ADD_REAL | ADD_NOISE,
                      set(DROP_ARG), "Doi chung nhieu: cung so cot/mask nhu V1, noi dung ngau nhien."),
}

for _fn, (_v, _alias, _keep, _drop, _purpose) in V_ARMS.items():
    assert not (set(_keep) & set(_drop)), _fn
    assert sorted(set(_keep) | set(_drop)) == list(range(55)), _fn
    _n_ap = len((ADD_REAL | ADD_NOISE) & _keep)
    FILES[_fn] = fs_var(_v, _alias, _keep, _drop,
                        "Bien the train Stage 2 (%s). Base = 21 keeper (fs_v2_21) + cot APPEND o CUOI "
                        "(%d cot append). Dat ten theo dung luat them/bot cot => VERSION MOI; fs_v2_21.json "
                        "KHONG bi sua. Xem docs/prereg/PREREG_STAGE2_FEATVAR.md." % (_v, _n_ap), _purpose)


if __name__ == "__main__":
    for fn, data in FILES.items():
        p = os.path.join(OUT_DIR, fn)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print("wrote", fn, data["n_features"], "features")
