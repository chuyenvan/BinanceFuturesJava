# featuresets — version hoa danh sach feature (selector S1 / G015x26)

Muc dich: **khong bao gio mat danh sach cot nao da tung train**, va moi ket qua/sim gan duoc voi
dung version feature da sinh ra no.

## Quy tac version (BAT BUOC)

1. **Them hoac bot cot => VERSION MOI.** Khong bao gio sua file JSON cua version da cong bo.
2. Sua **khong doi cot** (chinh typo trong `formula`, bo sung `model_paths`, `sim_runs`, `notes`)
   => **duoc sua tai cho** (khong tang version), vi tap cot khong doi.
3. Dat ten file: `fs_<version>_<n_features>.json` (vd `fs_v1_44.json` = v1, 44 cot).
   Version chua chot dung `fs_v<k>_reserved.json` (`status: reserved`, tap cot rong).
4. **Thu tu cot trong JSON la thu tu VI TRI cua model** (model/ONNX KHONG luu ten cot:
   `feature_names=None`, `metadata_props` rong) => khong duoc doi thu tu trong mot version da train.
   Nguon thu tu: Java `ExportFeaturesForPythonTool.convertFeaturesToArray` (f0..f39) + merge OI (40..44).
5. Sinh lai toan bo bang `python3 gen_featuresets.py` (nguon du lieu nam trong chinh script nay).
   Neu can sua noi dung cot: sua trong `FEATURES` cua `gen_featuresets.py` **va** cap version.

## Bang doi chieu version

| version | file | n_features | `status` | ket qua / sim gan voi version | nguon |
|---|---|---|---|---|---|
| v0 | `fs_v0_45.json` | 45 | trained | `predwf_G015` (= G015x26 = net015): 18 fold `model_f0..17_4h.json`, bins `predwf_G015x26`, sim `C3`, `X1_C3`, `FG_KEEPLEG0` (moc parity md5 `99e42b75`), `C4_parity`, `G5_parity_S1` | `docs/experiment/G015_RECIPE.md`, `docs/runbooks/AGENT_RUNBOOK.md` |
| v1 | `fs_v1_44.json` | 44 | planned | drop-one `rvol15m` — **chua train, chua sim**; du doan chot truoc: admit TANG, expectancy/top-8 win GIAM; do bang rank-IC cross-section + top-8 lift, KHONG dung gain | `docs/diag/DIAG_RVOL15M.md` §D |
| v2 | `fs_v2_21.json` | 21 | planned | tap GIU (§6.3, 22 cot) BO `rvol15m` => 21; **chua train, chua sim** | `docs/analysis/EVAL_SELECTOR_FEATURES.md` §6.3 |
| v3 | `fs_v3_reserved.json` | (rong) | reserved | khung cho vong ablation Stage 1 (bo nhom NGAT CHAC 5/45) | `docs/prereg/PREREG_FEAT_ABLATION.md` |
| v4 | `fs_v4_reserved.json` | (rong) | reserved | khung cho ket qua Stage 1 | — |
| v5 | `fs_v5_reserved.json` | (rong) | reserved | khung cho Stage 2 prep | — |

Moi file JSON deu co day du truong bat buoc: `version` · `n_features` · `features[{index,name,source,formula}]`
(co thu tu) · `label` (**`retEnd_4h > 0.015`**) · `folds` · `seed` · `hyperparams` ·
`train_code_git_commit` · `model_paths` · `bins_path` · `sim_runs` · `notes`.

## Nac thang NGAT CHAC / CAN NHAC / GIU (45 cot, §6.3)

- NGAT CHAC 5: `#9 rsi1H`, `#26 volumeZCoin`, `#33 volumeZRankCS`, `#37 volumeZ5m`, `#38 closePosRange15m`
- CAN NHAC 18: `#0,#1,#3,#4,#11,#12,#13,#15,#16,#19,#21,#22,#23,#25,#27,#34,#39,#43`
- GIU 22: `#2,#5,#6,#7,#8,#10,#14,#17,#18,#20,#24,#28,#29,#30,#31,#32,#35,#36,#40,#41,#42,#44`

`#36 rvol15m` nam trong GIU (share 34,09%) nhung rank-IC ~ 0 => la NGHIEM THU DUY NHAT cua vong
ablation v1 (`docs/diag/DIAG_RVOL15M.md`).

## Code train

Xem `research/pipeline/train/README.md`. Snapshot dong bang:
`research/pipeline/train/g015_net_train_v0_snapshot.py` (code sinh ra v0).

## ⚠️ Hai thu de lan (doc truoc khi doc so)

1. **"S1" trong repo la HAI thu khac nhau**: S1-**ranker** (9 feature, `research/pipeline/x1/x1_s1_rank.py`)
   sinh ra THU TU coin; **net015/G015x26** (45 feature, `research/pipeline/g015_net_train.py`) sinh ra GIA TRI
   P(win). Cac file `fs_v*.json` nay noi ve **net015 (45 cot)**.
2. **Bat danh so fold**: `model_f<i>_4h.json` lay `i` = vi tri trong `CUT_DATES` (da noi them 3 fold DEV2021 +
   `20251231`) => cutoff `20240101` = **fidx 11**, khong phai 8. So sanh phai khop theo CUTOFF.

Nguon: `docs/PREP_STAGE2_TRAIN.md` §0/§1.2.
