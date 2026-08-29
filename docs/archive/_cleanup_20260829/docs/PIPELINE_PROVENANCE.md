# PIPELINE PROVENANCE - Luong du lieu & mo hinh, vet truy nguyen

> ⚠️ SNAPSHOT 2026-07-01, đã CŨ (trước canonical fold-0-fix + lưới 1-phút 2026-08-03/04). Xem [WFO_DATA_PIPELINE_MASTER](WFO_DATA_PIPELINE_MASTER.md) cho trạng thái pipeline SỐNG hiện tại.

> Muc dich: mot nguon su that ve luong end-to-end: du lieu tho -> feature -> label -> train model -> sinh prediction -> nap Aerospike -> export WFO dataset -> chay WFO/HPO. Ghi ro CODE nao sinh ARTIFACT nao, tu INPUT nao, NGAY nao, provenance co sach khong. Viet 2026-07-01 (phien ra soat dem) dua tren bang chung doc code + artifact thuc tren server (do khong doan). Cho nao chua xac lap du -> ghi "CHUA XAC LAP".

> CANH BAO TOI QUAN TRONG: STRATEGY WFO hien tai (StrategyWfoTask) dang tieu thu prediction RO RI (in-sample) cho hau het window OOS. Xem muc 4. Moi con so WFO truoc ~2025-06 KHONG phai OOS hop le. Day la ly do ton tai tai lieu nay.

## 1. Hai tang "hoc duoc" - dung lan

- Tang A - MODEL du doan (XGBoost sinh con so: funding selector, gate/market return15m/risk4h). "Train" = khop cay vao feature+label. WFO KHONG toi uu tang nay - no dung prediction CO SAN.
- Tang B - THAM SO chien luoc (18 gene: nguong vao lenh, DCA, trailing, budget...). "Train" = random-search chon bo tot nhat tren IS. WFO CO toi uu tang nay.

WFO la phuong phap KIEM DINH chong overfit cho tang B. No KHONG train tang A. Tang A phai duoc train + sinh prediction LEAK-FREE o buoc rieng TRUOC WFO. Neu tang A ro ri -> moi kiem dinh tang B vo nghia.

## 2. Luong end-to-end (thuc te, theo code)

- [kline_1m_opt @226] du lieu gia tho (ticker 1m)
- FEATURE EXPORT (Java):
  - Funding v2: ai_ml/features/export/fundingv2/ExportFeaturesForPythonTool.java -> ff_*.bin ; ExportFundingOiPerCoin.java (OI) ; ExportTool1Master/Worker.java
  - Gate/market: ai_ml/features/export/gate/ExportGate15mV2.java (+ WFOGateRunner per-fold CSV) ; ExportGateReturn.java ; ExportGateFeaturesGroupA/B.java
- LABEL EXPORT (Java):
  - Funding label: ai_ml/features/export/ExportFundingLabel.java -> funding_label.csv. Path per-coin, horizon H={4h,12h,24h,72h}, LOOK-AHEAD toi da 72h; dung lifecycle (gom coin chet -> KHONG survivorship bias o label).
- TRAIN MODEL (Python @Oracle):
  - Funding selector: claudedata/train_funding_selector.py. Time-split, no-shuffle, purge=horizon, assert chong leak; TEST = 12 THANG CUOI -> models_v2/model_{4h,12h,24h,72h}.ubj+.onnx + train_meta_*.json + metrics_*.json.
  - Gate per-fold: java/simulator/train_gate_fold.py (expanding cutoff, goi boi WFOGateRunner) -> wfo_models/fold_0..13/Model_Regressor_Return15M.onnx  [LEAK-FREE].
  - Gate don: gate_model_v2/Model_Regressor_Return15M.onnx + train_meta.json.
- SINH PREDICTION FULL-HISTORY (Python @226):
  - Funding: nap 4 booster models_v2 -> predict MOI thang 2021->2026 -> predict_1m/predict_YYYYMM.bin (log funding-generate-1m.log). [DIEM RO RI: 1 model train<=2024-12 predict ca history].
- NAP PREDICTION -> AEROSPIKE (Java @226):
  - Funding: research/ExportSelectorPred1mToAerospike.java -> set funding_selector_pred_1m_v2 (chunk-ngay).
  - Gate/market: features/export/gate/GenerateGate15mV2Predictions.java -> set ai_pred_market_gate_v2 (MOI, default 2025-06->2026-06). Set CU ai_pred_market_full_basket_v2 = nguon predRisk4H giu nguyen; STRATEGY-WFO dang dung set CU nay.
- EXPORT WFO DATASET (Java, 1 lan tren node co Aerospike 226):
  - ai_ml/wfo/framework/ExportWfoDataset.java -> WfoDataset.export(). Doc 3 set: market_data + ai_pred_market_full_basket_v2 + funding_selector_pred_1m_v2 -> wfo_dataset/{market.bin, pred.bin, funding.bin, manifest.txt}.
- CHAY WFO / HPO (Java, tang B):
  - ai_ml/wfo/framework/tasks/StrategyWfoTask.java + WfoCoordinator + WfoJobStore + WfoWorker. Fitness: ai_ml/hpo/HPOFitnessCalculatorV4.java (calmar + gate cung). Dataset: env WFO_DATA_DIR (load offline, verify md5).

## 3. Registry artifact hien co (bang chung tren server)

| Artifact | O dau | Ngay | Sinh boi (code) | Tu input | Provenance |
|---|---|---|---|---|---|
| funding_label.csv | (tam) | - | ExportFundingLabel.java | kline_1m_opt | OK (look-ahead dung thiet ke) |
| ff_m1/, ff_verify/ | Oracle claudedata | 2026-06-24 | ExportFeaturesForPythonTool | kline+OI | OK |
| gate15m_v2_full.csv | Oracle | 2026-06-23 | ExportGate15mV2/WFOGateRunner | kline+market | OK |
| models_v2/ (funding 4h/12h/24h/72h) | Oracle | 2026-06-25 | train_funding_selector.py | ff+label | train<=2024-12-12, test>=2025-06-11 |
| wfo_models/fold_0..13 (gate) | Oracle | 2026-06-23 | train_gate_fold.py | gate CSV per-fold | LEAK-FREE (expanding cutoff) |
| gate_model_v2/ (gate don) | Oracle | 2026-06-23 | train gate don | gate CSV | train_meta.json (can doc xac nhan cutoff) |
| predict_1m/predict_*.bin (funding full) | 226 | 2026-06-22 | Python inference nap models_v2 | models_v2 + ff full | RO RI: 1 model predict ca 2021->2026 |
| set funding_selector_pred_1m_v2 | Aerospike 226 | 2026-06-22 | ExportSelectorPred1mToAerospike.java | predict_1m/*.bin | RO RI truoc ~2025-06 |
| set ai_pred_market_full_basket_v2 | Aerospike 226 | (cu) | CHUA XAC LAP | CHUA XAC LAP | CHUA XAC LAP (nhieu kha nang full-history don -> ro ri) |
| set ai_pred_market_gate_v2 | Aerospike 226 | 2026-06 | GenerateGate15mV2Predictions.java | gate_model_v2 | default 2025-06->2026-06 (sach); strategy-WFO KHONG dung |
| wfo_dataset/ (strategy) | Oracle | 2026-06-29 | ExportWfoDataset.java | 3 set tren | thua huong ro ri cua funding + full_basket |
| coin_tier_full.bin | Oracle/226 | 2026-06-30 | ExportCoinTierStatic.java | kline | OK (static tier) |

Model funding train_meta (thuc do): 24h n_train 2,290,880 / n_test 1,051,094 | train_max 2024-12-12 | test 2025-06-11 -> 2026-06-06 (4h/12h/72h cung cau truc). Metrics OOS 2025-06->2026-06: 24h LIFT 1.54 rankIC 0.29 PASS; 72h LIFT 1.27 rankIC 0.20 PASS -- edge THAT nhung chi nhinh hon baseline 1-feature chut it (24h 1.543 vs 1.525).

## 4. Phat hien LEAKAGE (chi tiet + pham vi)

Co che: funding selector v2 train tren du lieu <= 2024-12, nhung prediction sinh cho TOAN BO 2021->2026 bang chinh model do. -> prediction o khoang model da train (2021->~2025-06) la in-sample: model "da thay" tuong lai khi sinh so. Strategy-WFO dung prediction nay lam tin hieu vao lenh o moi window.

Pham vi (map voi window strategy-WFO): model sach tu 2025-06-11. Window OOS >= 2025-07 -> sach (~3 window). Window OOS < 2025-06 -> in-sample (~13/15). 3 window sach van duong (pnl +435, +13348, +3849) nhung mau qua mong de ket luan edge.

SAC THAI DUNG (doi chieu insights/WFO_LEAKS_TODO.md muc L0 — Uni da neu 2026-06-28): Strategy-WFO la "loai 1" (model DUNG YEN, chi van 18 gene). Theo doctrine L0, pred co dinh la INPUT BAT BIEN HOP LE cho cau hoi HEP "tham so chien luoc co generalize qua window khong" — va o nghia do dataset hien tai la DUNG. DONG GOP MOI cua audit nay (do duoc, bo sung L0): vi pred co dinh do duoc sinh IN-SAMPLE (model train<=2024-12 predict ca history), CHAT LUONG tin hieu o giai doan <2025-06 la lac quan gia -> con so OOS TUYET DOI (pnl, %duong, calmar) o ~13/15 window bi THOI PHONG, KHONG dai dien live. Ket luan chinh xac: (a) claim "tham so chien luoc generalize" van song; (b) claim "he thong CO EDGE that" thi KHONG — chi ~3 window sach (2025-07+) la phep thu joint (model+chien luoc) hop le, mau qua mong.

LIEN QUAN cac leak da ghi: L1 (embargo quanh cutoff = label look-ahead, funding horizon toi 72h) va L4 (provenance predRisk4H ghep tu set cu) — deu can xu ly khi lam ban leak-free.

Bang chung: models_v2/train_meta_*.json (moc split) + funding-generate-1m.log @226 ("loaded 4 booster" -> predict moi thang) + WfoDataset.SET_FUNDING.

## 5. Provenance GAPS (phai bu de luong "tron")

1. [CHINH] Funding KHONG co ban per-fold leak-free. Can: train funding selector per-fold (expanding cutoff = bien IS moi window WFO, purge=horizon) -> sinh prediction ghep leak-free -> set moi co version -> strategy-WFO dung set do.
2. Market pred cua strategy-WFO dung set cu ai_pred_market_full_basket_v2 (provenance mo). Trong khi ban per-fold gate (wfo_models/fold_*, leak-free) VA gate_v2 moi deu ton tai nhung khong noi vao strategy-WFO. Can: xac lap provenance set cu; chuyen strategy-WFO sang gate per-fold leak-free.
3. Khong co manifest lien ket code<->data<->model<->prediction<->dataset<->run. wfo_dataset/manifest.txt co md5 + ten set + ngay NHUNG thieu: git SHA code, version model (train_meta) sinh moi set, moc leak-free-from moi set. Xem muc 6 + Phase-D.
4. Code inference sinh predict_*.bin (Python) chua xac dinh vi tri/versioning (train script co o Oracle; inference/generate script can dinh vi + dua vao git).
5. Ten set tron version (v2/v5/v6/full_basket/gate_v2/selector_1m) khong co bang anh xa version->(model, ngay, cutoff, leak-free-from). Muc 6 dua registry chuan.

## 6. QUY UOC VERSION & DANH DAU DU LIEU (di toi)

Nguyen tac: moi artifact tu mang vet truy nguyen. Khong artifact nao "mo coi".

6.1 Manifest bat buoc cho moi prediction set / dataset (sidecar <name>.provenance.json HOAC field trong manifest):
- artifact: ten set
- producedByCodeSha: git sha luc sinh
- producerClass: class Java + script Python@sha
- modelProvenance: {trainMaxTs, testMinTs, split: per-fold-expanding|single}
- inputSets: [ff_v2@sha, funding_label@sha]
- leakFreeFrom: ts | "per-fold (moi window sach)"
- generatedAt, rows

6.2 Quy uoc ten: <domain>_<kind>_<granularity>_v<N>[wf]. Hau to "wf" = walk-forward/per-fold (leak-free moi window). Khong "wf" = single-model (chi sach sau leakFreeFrom).

6.3 Danh dau du lieu train: moi model dir GIU train_meta.json (da co cho funding) + tham chieu git SHA code train + md5 input CSV. Model = code+data sinh ra no; mat mot trong ba -> coi nhu mat provenance.

6.4 wfo_dataset manifest them: codeGitSha, predSetProvenance, fundingSetProvenance (copy tu sidecar set nguon), leakFreeFrom.

## 7. KE HOACH WFO LEAK-FREE (thiet ke de thuc thi)

Muc tieu: strategy-WFO ma moi window OOS dung prediction chua tung thay trong luc train model.

Buoc:
1. Funding per-fold (bu gap chinh): sua train_funding_selector.py nhan TRAIN_CUTOFF (thay vi test=12thg-cuoi cung) -> train toi cutoff = bien IS cua tung window WFO (giong train_gate_fold.py). Moi fold: train <= cutoff-purge -> predict doan OOS fold do. Ghep moi fold -> prediction leak-free phu [first-OOS .. end].
2. Gate per-fold: da co (wfo_models/fold_*); sinh prediction gate leak-free ghep tuong tu (WFOGateRunner co khung).
3. Nap 2 chuoi prediction leak-free vao set version moi: funding_selector_pred_1m_v3wf, ai_pred_market_gate_v3wf (kem sidecar provenance muc 6).
4. Export wfo_dataset_wf/ tu 2 set moi + market_data (manifest co provenance 6.4).
5. Chay strategy-WFO tren dataset do, CUNG nguong pre-registered (WFE>=0.5, %OOS-duong>=70%, maxDD<=50%). So verdict voi ban ro ri.

Diem can Uni quyet (KHONG tu quyet - PnL/phuong phap):
- Tham so model per-fold funding (dung y het ban single hien tai la mac dinh an toan).
- Co chap nhan verdict leak-free lam chuan thay ban ro ri khong.
- Purge/embargo giua IS<->OOS moi fold = horizon dai nhat (72h) mac dinh an toan, nhung xac nhan.

## 8. Quan he voi tai lieu khac (KHONG trung lap)
- PIPELINE.md = doc CADENCE VAN HANH 3 thang (9 buoc + 2 cong gac) -- BO TRO, khong bi thay the. Doc nay (PIPELINE_PROVENANCE) tra loi "artifact nao tu code/data nao"; PIPELINE.md tra loi "quy trinh dinh ky lam gi".
- insights/WFO_LEAKS_TODO.md = danh sach leak L0-L5 (ghi 2026-06-28). Doc nay bo sung BANG CHUNG DO DUOC cho L0/L1/L4 (xem muc 4 + addendum trong file do).
- insights/WFO_FRAMEWORK_DESIGN.md = thiet ke framework + phan biet WFO loai 1/loai 2 (doc cung muc 7).
- ROADMAP.md / REBUILD_ROADMAP.md = lo trinh; FINDINGS.md = nguon su that ket luan da do.

## 9. Lich su tai lieu
- 2026-07-01: tao moi (phien ra dem autonomous). Nguon: audit code + artifact server (do khong doan).
