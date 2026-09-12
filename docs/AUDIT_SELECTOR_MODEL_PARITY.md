# AUDIT — parity model symbolPred: LIVE selector vs SIM (baseline x1_c3_full)

READ-ONLY feasibility + do luong. KHONG build port, KHONG deploy, KHONG cham 242,
KHONG sua sim/baseline. Ra go/no-go cho viec dua live selector dung CUNG model
symbolPred voi sim.

Fold do: `20251001` (OOS 2025Q4, block [2025-09-30 17:00 .. 2025-12-31 17:00)),
4,517,610 dong ung vien, join key (ts,symId) 100%, p15 coverage 100%.
Script: `research/analysis/sel_model_parity_measure.py` (chay tren Oracle, offline).

## 1. HAI NGUON symbolPred — khac nhau o dau

| | LIVE 242 hien tai (HEAD, LiveProfileC3 TAT) | LIVE C3-shadow (LiveProfileC3 BAT) | SIM baseline (x1_c3_full) |
|---|---|---|---|
| model | `Funding_Classifier_Final.onnx` | `g015x26_f15_cut20251001.onnx` (net015) | net015 x26 (predwf_G015x26) |
| gia tri | `preds[0]=P(class0)` RAW per-coin | net015 P(win) -> quantile-map | `1-p0` predwf_map_s1a2_x1 (mapped) |
| xep hang | theo pNoPump | theo S1 (buildS1Pool) | theo S1 |
| map | KHONG | LiveBuildMap (theo S1 rank) | build_map (theo S1 rank) |
| dat lenh that | CO | KHONG (SHADOW_NO_PUSH hardcode) | n/a |

- Ca 3 la model **45-input** cung bo feature (40 Tool1 + 5 OI). `preds[0]` la
  probabilities[:,0] (FundingOnnxInferenceManager.predictBatch). net015 symbolPred
  = `1 - P(win)` = probabilities[:,0]. => **CUNG TRUC** (P(class0), thap = tot).
- Khac o **HIEU CHUAN + label train**: Funding_Classifier train nhan pump +6%/72h;
  net015 train nhan `retEnd_4h > 0.015`. => phan phoi lech (do o muc 2).
- LIVE C3-shadow DA dung DUNG model+map cua sim (Net015ValueLive + LiveBuildMap),
  co test byte-parity (LiveBuildMapTest, research/pipeline/l4/build_map_parity.py),
  nhung chi chay SHADOW (khong dat lenh). Tuc: **port da ton tai o muc code.**
- Code da tu ghi nhan Funding_Classifier lech: "ho maxFav, hieu chuan lech 2 lan
  -> admission x5.05" (docs/G4_RECIPE_C4.md 6.2; DetectEntrySignal2TradeNormal:357-362).

dyn_thr = `0.008 * max(0.26787, symbolPred/0.15 * 1.28760)` (SIM_MIN_MOMENTUM_15M,
CHI CO can duoi; profile x1_c3_full). pass = dyn_thr <= p15 (predReturn15M per-tick).

## 2. SO DO LECH (fold 20251001)

### 2.1 Phan phoi symbolPred (thap = tot)
| nguon | mean | std | p10 | p50 | p90 |
|---|---|---|---|---|---|
| live (FundingClf P0) | 0.7437 | 0.1942 | 0.4502 | 0.8045 | 0.9317 |
| sim (net015 mapped 1-p0) | 0.4971 | 0.1311 | 0.3367 | 0.4932 | 0.6640 |
| net_raw (net015 raw) | 0.4971 | 0.1311 | 0.3367 | 0.4932 | 0.6640 |

=> **KHAC THANG**: live cao hon sim ~+0.25 mean va co duoi thap hon nhieu
(dyn_thr min live 0.00214 vs sim 0.00304). sim(map) va net_raw cung phan phoi
(map bao toan multiset moi tick) nhung khac per-coin (spearman 0.883).

### 2.2 Monotonicity (spearman, ~300k mau)
- live vs sim(mapped): **0.815**
- live vs net_raw: **0.902**
- sim(map) vs net_raw: 0.883

### 2.3 dyn_thr (toan bo 4.5M dong)
| nguon | mean | p50 | p90 | min | max |
|---|---|---|---|---|---|
| live | 0.0511 | 0.0553 | 0.0640 | 0.00214 | 0.0681 |
| sim | 0.0341 | 0.0339 | 0.0456 | 0.00304 | 0.0672 |

### 2.4 QUYET DINH pass/reject tren TOP-8 (con so go/no-go)
Top-8 = 8 coin S1-rank tot nhat moi tick (= 8 gia tri mapped net015 lon nhat =
8 sim_sp nho nhat). 8,832 tick, 70,656 slot. Voi CUNG bo coin do, doi model gia tri
gate:
- pass_sim (net015) = **2.01%** slot (0.161 coin/tick)
- pass_live (FundingClf) = **20.49%** slot (1.639 coin/tick)
- **DECISION FLIP = 20.01% slot top-8** (14,138/70,656)
- **live admit gap ~10x** so voi net015 (khop code: "admission x5.05", con lon hon o fold nay)
- top-8 SET overlap (neu dung gia tri de xep hang, sim vs live): Jaccard mean 0.296

### 2.5 Co che (vi sao 10x)
p15 2025Q4 rat nho: mean 0.0091, p90 0.0111, p99 0.0140. dyn gate qua duoc chi khi
market momentum cao. Coin tot nhat cua live co dyn_thr ~0.0137 (p15 vuot 1.19% tick);
cua net015 ~0.0231 (p15 vuot 0.16% tick) => ty le 1.19/0.16 ~ khop 10x pass. Funding_
Classifier cho ra pNoPump rat thap (tu tin) cho vai coin => chui qua gate de; net015
KHONG bao gio xuong thap the => gate chat hon. => "dai thr live [0.0157..0.0235] trung
dev" la TIN HIEU YEU (chi phan anh khoang gia tri, KHONG phan anh admit rate).

## 3. FEASIBILITY port net015 -> live (gia tri gate)

**Luu y ten**: "x26" = 26 BYTE/record cua bins, KHONG phai 26 feature. Model dung
**45 feature** = f0..f39 (Tool1 T1C2) + 5 OI (oi_delta24h, oi_z, ls_global,
ls_toptrader, taker_buy), merge_asof(on=ts, by=symId, backward, tol=2h).

| yeu to | trang thai |
|---|---|
| 45 feature co san live? | **CO** — chinh la float[45] da dua vao Funding_Classifier (FundingOnnxInferenceManager.extractFeaturesToArray; DetectEntrySignal2TradeNormal:632 `selFeat45` reuse `featureArrays`). Swap gia tri gate KHONG can them feature nao. |
| ONNX net015 co san? | **CO** — `/home/ubuntu/g3x26/g015x26_f15_cut20251001.onnx` (+ban o `deploy_242_l3/models/`). Da verify ONNX-vs-JSON (g015x26_onnx_gate.py: spearman ~1, max\|d\| 1 ULP). Khong phai "chi con booster JSON". |
| code port da co? | **CO** — Net015ValueLive (nap onnx tren) + LiveBuildMap (quantile-map = build_map.py, byte-parity test). Gate sau `LiveProfileC3.on()`. Chi chay SHADOW (SHADOW_NO_PUSH hardcode). |
| BLOCKER | quantile-map (LiveBuildMap) can **S1 RANK** (buildS1Pool -> score S1, 9 feature hourly gom OI history). 242 chi giu ~2 thang OI => **blocker S1 (da biet)**. |

**Effort**:
- Swap gia tri gate Funding_Classifier -> net015 RAW (khong map, xep hang theo net015):
  **THAP**. Onnx + feature + code Net015ValueLive da co. Multiset gia tri moi tick =
  sim (map bao toan multiset) => dyn_thr distribution + admit rate KHOP sim ngay ca khi
  chua co S1. Chi khac per-coin identity (spearman mapped vs raw 0.883).
- Full parity (co S1 map) = giong het sim: **TRUNG-CAO**, vuong blocker OI 2-thang cua S1.

## 4. PHAN QUYET — GO (lech LON)

Hai nguon symbolPred **KHONG tuong duong**: khac thang (mean 0.744 vs 0.497,
spearman 0.815), va **20% quyet dinh gate top-8 doi chieu**, net015 admit **~10x it
hon** Funding_Classifier. Tin hieu "thr band trung dev" da che dau khoang cach admit
that su => dung ĐO, khong đoan.

=> Theo rubric (ii): **lech lon => dang port**. Diem thuan loi: port gia tri gate
gan nhu MIEN PHI (onnx + 45 feature + Net015ValueLive/LiveBuildMap da co, byte-parity
test), phan lon la bat co (LIVE_PROFILE / bat nhanh net015 tren duong dat lenh that).
Open item duy nhat cho FULL parity la S1 rank (blocker OI 2-thang) — nhung ngay ca
KHONG co S1, swap sang net015-raw da dong khoang cach admit 10x so voi hien tai.

**Khuyen nghi uu tien**: GIU uu tien item 2 (dang lam), path re nhat = swap gia tri
gate sang net015; S1-map de sau (cho blocker OI). KHONG deploy trong pham vi audit nay.

## 5. Sai lech / caveat cua phep do
- Do tren 1 fold (20251001 / 2025Q4). Cac fold khac chua do (co the lam sau).
- Universe = toan bo (ts,symId) co feature+OI (= dung universe predwf bins), KHONG loc
  EntrySignalFilter — dong bo voi cach net015 bins sinh ra, hop ly cho so sanh nguon.
- p15 lay tu wfo_gate_pred.csv (per-tick, dong nhat moi coin trong tick) — dung nguon
  sim dung. dyn gate la 1 trong nhieu gate; con so o day chi ve tang dyn.
- live_sp tinh lai tu Funding_Classifier onnx tren feature rebuild (khop key bins 100%),
  KHONG phai log 242 that; gia dinh extractor live = feature rebuild (cung cong thuc 45).
