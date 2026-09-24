# train — snapshot code train (khong de mat code)

Muc dich: **giu code train da sinh ra model dang chay**, doc lap voi viec file goc trong repo
bi sua o cac phien sau. Snapshot la **ban sao byte-identical** lay tu git (khong sua 1 ky tu).

## Version v0 — `predwf_G015` (= `G015x26` = `net015`, 45 cot)

| thu | gia tri |
|---|---|
| Trainer goc (Kaggle) | kernel `chuyendinh/selector-15mtr-pred15-net015-gpu` — **notebook goc DA MAT** (`docs/experiment/G3_X26_RECOVERY.md` §8) |
| Code train trong repo | `research/pipeline/g015_net_train.py` (ban **TAI DUNG**, xac minh PASS o `docs/experiment/G015_RECIPE.md` §4, fold 8) |
| Snapshot dong bang | `g015_net_train_v0_snapshot.py` — sha256 `e8b6798fdb8e3f497e976fb45f5ad801040258902fcea0e8d4e6f6c0fc85aafc` |
| Snapshot code predict | `g015x26_train_v0_snapshot.py` — sha256 `56844a3e2534914186d9e629d2d6269282885dd1be06be48c128b6edf067cb2a` |
| `train_code_git_commit` | `6695a8c` (repo HEAD luc ghi, 2026-09-24); file `g015_net_train.py` **khong doi tu `f442c0e`** |

`g015_net_train.py` = TRAIN THAT (WFO 18 fold). `g015x26_train.py` = CHI PREDICT lai tu 18 model da luu
(dung khi chi can sinh lai bins). Model: `/home/ubuntu/claudedata/predwf_G015/model_f{0..17}_4h.json`.

## Tham so train v0 (nguon `docs/experiment/G015_RECIPE.md` §2)

| muc | gia tri |
|---|---|
| nhan | `LABEL_MODE=net`, `NET_THR=0.015` -> **`y = (retEnd_4h > 0.015)`** (base rate 0.1849) |
| loc nhan | `nBars_4h >= 16` va `retEnd_4h` notna |
| WFO | expanding, `FIRST_CUTOFF=20220101`, `OOS_MONTHS=3`, 18 cutoff `20220101..20260401` |
| purge | `PURGE_STEPS=288` buoc x 15m = **72h**; TZ = **GMT+7** |
| feature | **45** = `f0..f39` (Tool1) + 5 cot OI merge `merge_asof(on=ts, by=symId, backward, tolerance=2h)` |
| XGB | `XGBClassifier(n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, min_child_weight=20, scale_pos_weight=(1-pos)/pos, eval_metric="auc", n_jobs=-1, tree_method="hist", random_state=42, device=cuda)` |
| seed | **42** (`--seed`, `random_state`) |
| `scale_pos_weight` | tinh **theo TUNG FOLD**: fold 0 = `2.70527601` ... fold 17 = `4.35441685` (khong phai toan cuc) |
| xgboost | 3.2.0 · `MAX_TRAIN_ROWS=60.000.000` (khong bao gio cham) |

Cong thuc day du + dau vao ghim (sha256 Tool1/label/OI) o `docs/experiment/G015_RECIPE.md` §2/§5/§6.
Duong train THAT (script · luong · fold · seed · tham so) o `docs/plan/PREP_STAGE2_TRAIN.md` §1.

## 🔴 BAT DANH SO FOLD (phai doc truoc khi so bang)

`model_f<i>_4h.json` lay `i` = **vi tri trong `CUT_DATES`**. `CUT_DATES` ban repo hien tai da noi them
3 fold DEV2021 (`20210401/20210701/20211001`) + `20251231` => **cutoff `20240101` = fidx 11, khong phai 8**
nhu ban deploy. Moi bang so sanh phai khop theo **CUTOFF**, khong theo so trong ten file
(nguon `docs/plan/PREP_STAGE2_TRAIN.md` §1.2).

Tien ich trong script: `--drop-cols` (bo cot, da co san) · `--add-cols`/`--add-names` (them cot, phai
sua ca 3 tang: train · bins/predict · ONNX input) — xem `docs/plan/PREP_STAGE2_TRAIN.md` §2.

## Chay lai (NEU can — khong chay tren Oracle khi shadow LIVE)

```bash
python3 research/pipeline/g015_net_train.py --fold 20240101 --device cuda --save-model --out-dir <dir>
```

⚠️ `--device cuda` la device GOC; CPU cho mau khac (`docs/experiment/G015_RECIPE.md` §4/§7).
⚠️ Fold `20260101`/`20260401` nam TREN `HoldoutSeal` — khong dua vao sim/verdict khi chua `HOLDOUT_UNSEAL`.
