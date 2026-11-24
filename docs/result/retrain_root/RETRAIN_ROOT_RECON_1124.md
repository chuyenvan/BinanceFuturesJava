# RETRAIN_ROOT_RECON_1124 - khao sat CHI DOC: nguyen nhan goc "retrain venh" + du lieu cho prereg moi (agent RECON-RETRAIN, 2026-11-24)
Khong train / sim / kernel / mvn / java, khong 242, khong du lieu >= 2026-10-01, khong PnL moi. So 2026 chi chep tu RESULT da cong bo.
Script tinh tam (giu de A1 kiem): ~/claude_master/v12/retrain_root_recon_tmp/{tail_q.py, tail_q.json, gate_seed.py, gate_seed.json}.
Ky hieu: [X] = da doc code/tai lieu xac nhan (file:dong); [SD] = suy doan cua agent; [KTT] = khong tim thay.

## 0. Dinh chinh boi canh (quan trong)
- [X] p15 live fold_20 KHONG train toi cuoi 2025: CUTOFF=20260401 (00:00 UTC), 2 759 040 dong 2021-01-01 -> 2026-03-31, purge 0
  (docs/result/AUDIT_FOLD20_DATA.md muc 1). => p15 T1 (cut 20260701 +07) chi hon live MOT quy du lieu (2026Q2, DEV). Live fold_20 doan Q3 la
  du doan "2 quy toi" (3-6 thang sau cut), T1 la "1 quy toi". S1 live + net015 live: cut 20251231.
- [X] Trong DEV moi quy la OOS cua MOT fold khac (p15: fold k = cut 2021-04-01 + 3k thang, 19 fold 0..18 -> pred.bin A1 md5 5dd6bb4c;
  net015 / S1: bins predict_wf_<cut> theo quy). => moi ranh gioi quy DEV DA la mot lan "doi model + bo dem gate 90 ngay tron model cu/moi".
  Backtest DEV (+878 / A3) da chua san 18 lan chuyen fold nhu vay.

## 1. PIPELINE TRAIN: live vs T1 (chi cac dong KHAC, xep theo muc dang ngo)
| # | model | muc | live | T1 | nguon |
|---|---|---|---|---|---|
| 1 | net015 | thiet bi train | GPU (kernel g015x26-cut20251231-gpu) - KHONG tat dinh | CPU Kaggle (tat dinh) | RESULT_NET015_CUT20251231 :11-13 (qua RECON_1119 C2); RETRAIN_PILOT_RUN NET-B: CPU vs GPU cung cut spearman 0,991128, max|d| 0,228, mean|d| 0,0123, p_mean 0,5048 vs 0,5043 |
| 2 | net015 | cua so train | expanding 2021 -> 2025-12-31 - 72 h, 39 354 754 dong | -> 2026-07-01 - 72 h, 48 429 620 dong (+2 quy DEV) | net_train_summary.json (kg015x26); ADD5 A5-2 |
| 3 | net015 | hieu chuan tuyet doi | scale_pos_weight = (1-pos)/pos tinh lai moi fold (~4,29) => P(win) KHONG hieu chuan, p_mean OOS doi theo fold (f18 0,504; f19 0,466) | nhu nhau theo thiet ke, nhung muc lech moi | g015_net_train.py :265-268 (RECON A3); summary f18/f19 |
| 4 | p15 | cua so / mep / purge | cut 20260401 00:00 UTC, purge 0 | cut 20260701 00:00 +07 (GATE_PURGE_MS=26100000 = 7h15'), purge hieu dung 15' | AUDIT_FOLD20_DATA muc 1; PREREG_RETRAIN_PILOT :44-45, :145 |
| 5 | S1 | nguon feature + universe | ledger cand_dev_x1 toi 2025-12-31, feat_v2 DEV | +2026H1: 45,1 % dong ts >= S0 hoc bang feature Vision (feat_rt26 27,5 % dong Vision); 12 787 169 dong (vs 6 911 775 o nguong A5-2) - universe 2026 mo rong | RESULT_RETRAIN_T1 manifest; ADD5 A5-2, A5-5; RETRAIN_PILOT_RUN :70 |
| 6 | S1 | ledger | x1_ledger Oracle (float32) | rt-ledger Kaggle, g1lite tinh lai float32 (G-L 12/12 PASS < S0; S1-A lai sha cc0924f1 PASS) | ADD2 A2-4, ADD3 A3-1; RUN :108 |
| 7 | p15 | file train | ~/claudedata/wfo_feature_store.csv (08-06, DA MAT) | gate_dataset_full.csv a1c78e2f (08-08) | AUDIT_FOLD20_DATA muc 1; ADD1 A1-1 |
| 8 | net015 | code | g015_net_train (CUT_DATES toi 20260401) | P14/P14b (them cut, loc file nhan theo cut, assert) - NET-EQ trung byte | RUN P14/P14b |
| 9 | p15 | runner | WFOGateRunner (Java) -> train_gate_fold.py | rt_p15_train.py (wrapper runpy) -> train_gate_fold.py b41c9159 | RUN :64-66 |
GIONG NHAU (da doc): hyperparam co dinh, khong HPO, khong tap valid / early stopping (p15 n_est 150; net015 400; S1 300), seed 42, danh sach + thu tu
feature (33 V3FULL / 45 / 9 keep), xgboost 3.2.0, onnxmltools 1.16.0, ORT 1.23.2, suy luan ONNX float32; p15 T1 + net015 T1 = 0 % Vision.
T1 KHONG phai ban viet lai: cung script goc (p15 qua wrapper, net015 sua 1-2 dong, S1 cung x1_s1_save_model.py); chi ledger S1 chay lai bang kernel.
### Phep thu TAI LAP (co)
- [X] p15: P15-A PASS (cut20260701 UTC lai = b68563fe tung cay, ORT max|d| 0); P15-B (fold_20) FAIL theo nguong nhung |d| q99,9 1,6e-8, max 6,75e-5
  (file goc mat); G0 (gate_ablation_driver, retrain ca 19 fold WFO seed 42 purge 15'): 19/19 pearson min 0,9919 / median 0,9970, spearman min 0,9805
  (docs/result/RESULT_GATE_ABLATION.md :19; ~/claude_master/1004/gabl/retrain_G0.json). => pipeline p15 tai lap duoc ca chuoi WFO.
- [X] S1: S1-A sha256 JSON cc0924f1 trung byte (2 lan). allfold 16 JSON tai lap spearman 1.
- [X] net015: NET-A (ONNX cut20251001 vs bins) PASS; NET-B CPU vs GPU goc 0,991. LO HONG: chua ai tai lap CHINH model live f19 (cut20251231 GPU) tren CPU
  va do muc lech duoi P(win); bins DEV goc deu tu GPU => mot lane "CPU retrain" luon co nhieu thiet bi ~ spearman 0,99.

## 2. BAN DO NGUONG (sim a8690d46 = live c3_hotfix 76134a52 o EntryGate; profile Lane L = Lane N: ho5-a3-l26-*/prof_run.properties)
Diem p15 o day la cap THI TRUONG (1 gia tri/phut: predictionMap.get(ticker.startTime), Sim :1352); sp = 1 - P(win) net015 (WfoDataset.java:248),
A3 bins giu multiset p0 cua net015, S1 chi doi coin nao nhan gia tri nao (a3lib.py :62-67 G-SAN).
| nguong | gia tri | file:dong | nhanh | loai | nguon goc | nhay voi p15 x a / pwin + d |
|---|---|---|---|---|---|---|
| MIN_MOMENTUM_15M | 0.008 (profile; code mac dinh 0.02284) | Configs.java:428,834; AIRejectFilter.java:90-98; EntryGate.threshold(sp=null) | DCA_LEVEL1, leg market-signal (khong BIG_DOWN); fallback warm-up 7 ngay cua PREDICT | TUYET DOI | gate R4 tuyet doi truoc ratio (PREREG_GDV2_EVEN.md:31-34; RESULT_GATESCALE, GD92) - fit tren pred DEV WFO seed 42 [chi tiet fit: KTT] | p15 x a: ti le phut qua = P(p15 >= 0,008/a), nguong nam GIUA than phan phoi (p50 DEV 0,0034-0,009) => rat nhay, VINH VIEN; pwin: khong |
| BIG_DOWN | khong qua gate p15 | Sim :1352 | BIG_DOWN | - | - | khong |
| SIM_GATE_ROLLING_PCT / DAYS | 0.999950829 / 90 ngay, warm-up 7 ngay | profile; GateRollingRatio.java threshold(); GateRatioBuffer | PREDICT (sp != null) | TUONG DOI (quantile cuon cua r) | GDV2 (PREREG_GDV2_EVEN) | p15 x a => r x a; pass tang trong luc bo dem con r cu (<= 90 ngay), sau do bat bien; duoi day => ti so pass ~ ti so duoi |
| DYN_MIN 0.26787, DYN_MULT 1.28760, SCORE_BASE 0.15 | hang | EntryGate.java:44-48 (cu Configs.java:349-350 "Cu 0.14568/1.40234" = HPO) | he so r | trieu tieu trong ratio mode (r va nguong cung he so) TRU san DYN_MIN: chi bind khi sp < 0,0312 (P(win) > 0,969) | HPO cu | pwin + d => r x (1-pwin)/(1-pwin-d): Q3 T1 p99 pwin 0,6985 vs 0,6876 => r +3,6 % o dau duoi |
| SIM_GATE_DYN_SCALE | 1.55 | profile; EntryGate GATE_DYN_SCALE | PREDICT | trieu tieu trong ratio | PREREG_GATESCALE | khong |
| SELECTOR_RANK_TOPK | 24 | profile; Sim selectCands :729 | chon ung vien PREDICT | TUONG DOI (rank/tick) | - | S1/net015 chi qua thu tu |
| CoinTier TIER_3 chan DCA; TIER_FLAT=1 | - | Sim :1428-1433; CoinRankManager :117 | DCA | khong dung diem model [SD, chua kiem CoinRankManager] | - | - |
| Trailing stop | p15 truyen vao nhung KHONG dung | TradeUtils calRateMinWithPredReturn15MForTradingStop ("gia tri predReturn15M khong con tac dong") | - | - | FROZEN v1 | khong |
| P15_Q (GATE-RECAL) | 0 = TAT | EntryGate.java (P15_Q) | moi nhanh khi bat; chi SIET (max(base, roll)) | tuong doi | PREREG_GATE_RECAL | khong dung duoc de noi long DCA |
- [X] LIVE: LiveGateRollingRatio co persist run/gate_ratio_live.bin + seedHistory/applySeedFile (c3_hotfix LiveGateRollingRatio.java:30-40,113-140)
  => khi doi model tren live, bo dem 90 ngay van la r cua model CU (tron nhu Lane N); co san co che SEED FILE de gieo bo dem. SIM KHONG co knob gieo
  bo dem (GateRollingRatio khong co seed) => muon thu "gieo bo dem" trong sim phai sua Java (can prereg).
- [KTT] gia tri LIVE_GATE_ROLLING_* tren 242 (khong doc 242 / env).

## 3. KHO LICH SU
Fold WFO (DEV): p15 19 fold OOS 2021Q2..2025Q4 (fold k: cut 2021-04-01 + 3k thang UTC, OOS 89-91 ngay, expanding tu 2021-01-01) + fold_20 (2026Q2);
net015 / S1: 16 fold bins cut 20220101..20251001 (+ 3 fold 2021 trong manifest wfo_ds_x1_2021: 20210701, 20211001); OOS = 1 quy moi fold.
| artefact | o dau | trang thai |
|---|---|---|
| p15 pred WFO A1 (ts,p15,risk) 2021-04-01..2026-01-01 | ~/wfo_ds_x1_2021/pred.bin (40 MB, md5 5dd6bb4c) + market.bin + funding.bin 4,4 GB + manifest | CON |
| p15 pred cac seed/lan retrain cung fold | ~/claude_master/1004/gsb/pred_S{123,13,2024,21,777,99}, 1004/gabl/p15_G0.npy, p15_SEED7.npy | CON |
| p15 booster tung fold | ~/claudedata/wfo_models chi con fold_20 ONNX | MAT (0..19) - nhung retrain 17-30 s/fold tai lap (G0) |
| p15 feature + nhan | ~/claude_master/gvz/store/gate_dataset_full.csv (1,06 GB, a1c78e2f, 2021-01 -> 2026-06-30) ; Kaggle gate-dataset-full | CON |
| net015 bins RAW DEV 16 quy | ~/claude_master/res1109/r1_s1/g015x26 (888 MB); Kaggle predwf-g015x26-gate | CON |
| net015 booster goc (GPU) | predwf_G015 MAT; ~/kg015x26_cut20251231 co model_f18 (ban RETRAIN GPU) + model_f19 (live) ; ~/sel_models_net015 model_f0..f13 (45 feat, 400 cay, kernel 08-12 du lieu funding-unf15-data) | quan he cua sel_models_net015 voi bins DEV: CHUA XAC MINH |
| net015 feature/nhan | Kaggle funding-tool1-15m, funding-label-15m, funding-oi-percoin (Oracle MAT) | CON tren Kaggle |
| S1 model 16 fold | ~/s1_model_allfold (16 JSON cut 20220101..20251001, 9,5 MB) | CON |
| S1 ledger / feat | ~/ledger/cand_dev_x1.parquet (209 MB) ; feat keep9 Kaggle s1-featv2-x1-20260919 (286 MB) | CON (feat chi Kaggle) |
| A3 bins DEV | ~/claude_master/res1109/r1_s1/a3_bins (16 file, 888 MB) | CON |
| log sim DEV 8 seed (GATE-RATIO theo quy) | ~/kaggle_sim/out/r1-a3-<seed>/logs/sim.out | CON |
(a) model fold k-1 suy luan tiep sang quy k: p15 CO (retrain G0 recipe tren gate_dataset_full, re); net015 CO nhung phai retrain CPU tren Kaggle
    (booster goc mat; ban CPU != GPU goc ~0,99) + can bien OOS 6 thang (OOS_MONTHS la hang trong code => doi code, can prereg); S1 CO ngay
    (16 JSON + ledger + feat), khong train - nhung pool S1 phu thuoc p15.
(b) KHONG co doan chong lan giua fold lien ke trong DEV (moi predict_wf_<cut> / khoi pred chi phu OOS cua chinh no, manifest span 89-91 ngay, khong giao).
    Chi co: cung-fold-khac-seed (gsb/gabl) va 2026 (fold_20 vs T1).
(c) CO: sim nhan pred.bin (ts,p15,risk) + thu muc bins theo quy => ghep tuy y theo quy (tien le rt_lane.py / rt_lsim.py / rt_lchk.py, hard link + sha).
    KHONG co knob gieo bo dem gate trong sim (xem muc 2).
(d) Uoc luong [SD, tu so lieu log cu]:
| viec | noi | chi phi |
|---|---|---|
| p15: train 19 fold + suy luan 1-quy-toi va 2-quy-toi (N = 17-18 ranh gioi) | Oracle 1 tien trinh, RAM ~4-5 GB (doc CSV 1 GB) => CAN oracle_heavy.lock | 20-40 phut |
| p15 bong cat som 90 ngay (N fold) | Oracle, cung tien trinh | +10-15 phut |
| net015 train CPU 16 fold + du doan 2 quy | Kaggle CPU, 10-26 phut/fold (5 M -> 35 M dong) | ~4-5 kernel-gio, ~1-1,5 h wall (4 song song, chia quota 5 kernel voi viec khac) |
| net015 bong cat som 90 ngay | Kaggle CPU | them ~4-5 kernel-gio |
| S1 suy luan keo dai (16 JSON) | Oracle python3 (co pyarrow) + tai keep9 286 MB | 10-20 phut |
| ledger/pool S1 + bins A3 cho moi lane p15 moi | Kaggle rt-ledger ~15 ph + a3 build Oracle | ~0,5-1 h / lane |
| Sim: 1 sim DEV phu MOI ranh gioi cung luc; 35-65 ph/kernel | Kaggle CPU | lane WFO = co san (r1-a3 8 seed, 0 chi phi); moi lane moi x 8 seed ~5-8 kernel-gio, 2-3 h wall; seed DEV chi doi p15 => 2 seed gan 1 mau cho net015/S1 |
| Replay gate offline (khong sim) | Oracle numpy | vai phut / lane |

## 4. MO TA DUOI p15 THEO QUY (DEV <= 2025-12-31; tail_q.py, 11 s, RSS 0,76 GB). KHONG PnL.
Quy +07; fold p15 = fold sinh quy do (moi quy la quy NGAY SAU mot ranh gioi fold). r-proxy = p15/(max(0.26787,sp/0.15*1.2876)*1.55), sp = 1 - max P(win)
tick 15' (a3 bins, chi tu 2022Q1). alt = ti so q cua 8 ban retrain cung fold (G0, SEED7, S123, S13, S2024, S21, S777, S99) / A1 tren CUNG quy.
| quy | fold | p50 | frac p15>=0,008 | q99,99 | q99,995 | max | q99,99 / quy truoc | r q99,995 | alt q99,99 min/med/max | alt q99,995 min/med/max |
|---|---|---|---|---|---|---|---|---|---|---|
| 2021Q2 | 0 | 0,0072 | 0,348 | 0,1007 | 0,1051 | 0,109 | - | - | 0,97/0,99/1,02 | 0,97/1,00/1,02 |
| 2021Q3 | 1 | 0,0053 | 0,052 | 0,0593 | 0,0665 | 0,092 | 0,59 | - | 0,88/0,97/1,04 | 0,91/0,99/1,06 |
| 2021Q4 | 2 | 0,0055 | 0,049 | 0,0985 | 0,1050 | 0,123 | 1,66 | - | 0,95/1,03/1,08 | 0,96/1,07/1,15 |
| 2022Q1 | 3 | 0,0062 | 0,104 | 0,0268 | 0,0292 | 0,039 | 0,27 | 0,0286 | 0,96/0,98/1,04 | 0,95/1,04/1,09 |
| 2022Q2 | 4 | 0,0055 | 0,147 | 0,0535 | 0,0558 | 0,073 | 1,99 | 0,0389 | 0,97/1,07/1,15 | 0,99/1,08/1,20 |
| 2022Q3 | 5 | 0,0050 | 0,026 | 0,0330 | 0,0351 | 0,049 | 0,62 | 0,0105 | 0,90/0,96/1,06 | 0,95/0,98/1,07 |
| 2022Q4 | 6 | 0,0038 | 0,050 | 0,0493 | 0,0536 | 0,072 | 1,50 | 0,0330 | 0,95/1,01/1,03 | 0,95/1,01/1,08 |
| 2023Q1 | 7 | 0,0046 | 0,026 | 0,0278 | 0,0314 | 0,038 | 0,56 | 0,0065 | 0,94/0,97/1,03 | 0,93/0,95/0,97 |
| 2023Q2 | 8 | 0,0039 | 0,008 | 0,0337 | 0,0369 | 0,073 | 1,21 | 0,0099 | 0,90/0,97/1,02 | 0,98/1,01/1,05 |
| 2023Q3 | 9 | 0,0034 | 0,005 | 0,0490 | 0,0577 | 0,086 | 1,46 | 0,0335 | 0,86/0,94/1,05 | 0,87/0,98/1,01 |
| 2023Q4 | 10 | 0,0048 | 0,015 | 0,0257 | 0,0294 | 0,075 | 0,52 | 0,0152 | 0,95/1,04/1,12 | 0,93/1,07/1,16 |
| 2024Q1 | 11 | 0,0057 | 0,088 | 0,0634 | 0,0678 | 0,090 | 2,46 | 0,0239 | 0,82/0,91/0,97 | 0,89/0,92/0,99 |
| 2024Q2 | 12 | 0,0050 | 0,037 | 0,0469 | 0,0491 | 0,074 | 0,74 | 0,0394 | 0,91/0,98/1,03 | 0,94/1,00/1,04 |
| 2024Q3 | 13 | 0,0047 | 0,031 | 0,0403 | 0,0441 | 0,075 | 0,86 | 0,0883 | 0,96/1,02/1,11 | 0,99/1,04/1,08 |
| 2024Q4 | 14 | 0,0057 | 0,086 | 0,0250 | 0,0270 | 0,047 | 0,62 | 0,0133 | 0,97/1,00/1,04 | 0,96/1,00/1,03 |
| 2025Q1 | 15 | 0,0062 | 0,123 | 0,0331 | 0,0424 | 0,049 | 1,32 | 0,0461 | 0,99/1,02/1,05 | 0,86/1,00/1,04 |
| 2025Q2 | 16 | 0,0066 | 0,159 | 0,0229 | 0,0246 | 0,026 | 0,69 | 0,0112 | 0,97/1,01/1,02 | 0,97/1,02/1,06 |
| 2025Q3 | 17 | 0,0069 | 0,219 | 0,0201 | 0,0238 | 0,056 | 0,88 | 0,0093 | 0,97/1,00/1,04 | 0,95/1,00/1,05 |
| 2025Q4 | 18 | 0,0090 | 0,758 | 0,0983 | 0,1099 | 0,120 | 4,89 | 0,1589 | 0,83/0,94/1,07 | 0,82/0,92/1,10 |
Doc (mo ta): (i) ti so quy/quy truoc 0,27-4,89 = che do thi truong lan voi doi fold - khong tach duoc tu du lieu nay. (ii) "nhieu retrain cung du lieu"
(8 ban, 18 quy) cho ti so duoi CUNG quy trong [0,82; 1,20] (median ~1,0): T1/live Q3 q99,99 1,19 = sat bien tren, q99,995 1,51 = NGOAI bien => lech
duoi T1 lon hon nhieu seed/moi truong; nhung T1 khac live o DU LIEU (+1 quy) + "tuoi" model, cai chua co doi chung DEV (phep do M1 muc 5).
(iii) frac p15 >= 0,008 (nguong DCA tuyet doi) dao dong 0,5 % -> 75,8 % theo quy; p50 DEV 0,0034-0,0090, Q3-2026 p50 0,0089-0,0091 (RUN :72) =>
nguong DCA dang nam SAT trung vi => moi dich muc p15 vai % doi manh so phut DCA du dieu kien.
GATE-RATIO pass theo quy, 8 seed DEV (gate_seed.py; seed DEV chi doi pred p15):
| quy | a1 | min-max 8 seed | max/min | | quy | a1 | min-max | max/min |
|---|---|---|---|---|---|---|---|---|
| 2021Q3 | 383 | 345-390 | 1,13 | | 2023Q4 | 259 | 258-285 | 1,10 |
| 2021Q4 | 182 | 171-190 | 1,11 | | 2024Q1 | 291 | 236-291 | 1,23 |
| 2022Q1 | 103 | 97-103 | 1,06 | | 2024Q2 | 162 | 155-166 | 1,07 |
| 2022Q2 | 249 | 240-274 | 1,14 | | 2024Q3 | 116 | 104-127 | 1,22 |
| 2022Q3 | 53 | 53-77 | 1,45 | | 2024Q4 | 259 | 222-298 | 1,34 |
| 2022Q4 | 100 | 93-111 | 1,19 | | 2025Q1 | 296 | 223-296 | 1,33 |
| 2023Q1 | 166 | 137-166 | 1,21 | | 2025Q2 | 68 | 34-68 | 2,00 |
| 2023Q2 | 173 | 148-184 | 1,24 | | 2025Q3 | 80 | 75-89 | 1,19 |
| 2023Q3 | 96 | 87-107 | 1,23 | | 2025Q4 | 275 | 260-275 | 1,06 |
So sanh (chep RESULT_RETRAIN_DIAG): Q3-2026 pass L 94, P 127 (x1,35), M 108, N 142 (x1,51). Doi seed p15 thuan tuy (cung du lieu) o DEV da tao
max/min 1,06-2,00 (median ~1,2; quy it pass 53-77 / 34-68 lech 1,45-2,0). => buoc nhay pass x1,35-1,51 KHONG vuot hien tuong da thay o DEV.
Gioi han: so dem gom ca hieu ung duong di (book full / skipFull) - khong phai chi do p15.

## 5. Y KIEN CHUYEN MON (Y KIEN - khong phai ket luan)
Xep hang kha di (cao -> thap) cho "Lane N thua Lane L 9,6 pp tren Q3":
1. H-noise (+ duong di) - UNG HO: 71 % lo tu 3 lenh / 2 tap; 1 duong di; o DEV doi seed p15 thuan tuy da doi pass/quy toi x2. CHONG: dich duoi q99,995 x1,51
   vuot bien seed [0,82; 1,20] => T1 co dich thang that, khong chi ngau nhien. => co che co that, CO LON PnL co the la nhieu.
2. H-abs (DCA_LEVEL1 >= 0,008 tuyet doi, ap p15 thi truong) - UNG HO: nguong nam giua than phan phoi, frac DEV 0,5-76 %; DCA L -0,65k vs N/PM -4,8k;
   khong bao gio tu chuan hoa lai. CHONG: 4 vs 10 lenh; so DCA con phu thuoc so vi the mo boi PREDICT (lan voi H-gate).
3. H-gate (tron bo dem 90 ngay) - UNG HO: co che dung, pass P x1,35. CHONG MANH: DEV da co 18 lan chuyen fold kieu nay trong moi backtest duoc dung de
   validate; lech thang con o thang 9 (DIAG D-D2) => khong chi la qua do.
4. H-pipeline - p15: gan nhu LOAI (P15-A trung cay, P15-B 6,75e-5, G0 19/19 >= 0,99); S1: byte; net015: GPU->CPU 0,991 khong bias (p_mean +0,0005) nhung
   la nguon nhieu that chua do o duoi; chua tai lap live f19 tren CPU.
5. H-src - THAP: p15 T1 + net015 T1 = 0 % Vision (2 model gay phan lon delta: Shapley P -5,84, M -4,48); chi S1 tron nguon va S1 gop +0,76 pp.
Them (agent): H-age - live fold_20 doan Q3 la "2 quy toi", T1 "1 quy toi"; khac biet duoi co the do "tuoi model" chu khong phai retrain sai. Va
H-spw - P(win) net015 khong hieu chuan (scale_pos_weight) => muc tuyet doi doi moi fold theo thiet ke.
### Phep do tach (chi DEV 2022-2025; N = so ranh gioi)
- M1 (re, khong PnL; ~30-40 ph Oracle + lock): train lai 19 fold p15 theo recipe G0, du doan moi quy bang fold "1 quy toi" (=WFO) VA "2 quy toi".
  Ti so duoi (q99,99 / q99,995 / max), dich p50, dich frac >= 0,008, ti so r-proxy (sp co dinh) tren CUNG quy, N = 17 quy. Neu 1,19 / 1,51 cua Q3 nam
  trong phan phoi nay => H-noise/H-age; neu he thong (vd >= 13/17 quy cung dau, sign test p < 0,05) => dich thang co tinh he thong khi them du lieu.
- M2 (re, khong PnL): replay gate offline tren dong ung vien (p15 phut x sp top-24 tick 15') cho lane WFO / LAG1 / WFO + bo dem gieo tu model bong;
  KIEM truoc: replay lane WFO a1 khop GATE-RATIO log theo quy (vd +-10 %). Tach qua do (pass vuot trong 30-90 ngay dau sau ranh gioi, roi tat) vs vinh vien.
- M3 (re): dich so phut p15 >= 0,008 giua fold k va k-1 tren cung quy (tu M1) = muc phoi nhiem H-abs; them net015 p_mean / p99 fold k vs k-1 (can Kaggle).
- M4 (PnL, prereg moi): sim lane LAG1 (moi quy dung fold k-1) vs WFO (co san), giai thua p15-only / net015-only; d theo quy, N = 16-18 quy (2 seed ~ 1 mau).
  Paired t n = 17: luc 80 % chi bat duoc hieu ung >= ~0,7 sd cua d theo quy [SD]. Nhanh "DCA tuong doi" can sua Java.
- M5 (dung sim co san, nhung la PnL DEV => MASTER duyet): phan tan ROI theo quy giua 8 seed r1-a3 = phan phoi rong cho "doi model cung recipe";
  dat d = -9,56 pp cua Q3 vao phan phoi do.
### Phuong an quy trinh retrain (da nhac + bo sung)
| phuong an | can gi de kiem | rui ro overfit |
|---|---|---|
| (a) gieo bo dem gate bang r OOS cua model bong cat som 90 ngay | M1 + M2; sim can knob preload bo dem (Java); live da co seed file | thap (khong tham so moi) - nhung model bong != model san xuat (it hon 90 ngay du lieu) |
| (b) hieu chuan lai nguong tuyet doi theo quantile (0,008 -> quantile tuong ung cua model moi tren cua so tham chieu) | M1/M3 cho do lech; chon cua so tham chieu TRUOC | trung binh (bac tu do = cua so, quantile) |
| (c) train mot nguon | rebuild Vision 2021-2025 hoac DEV-only cho S1 | thap; loi ich ky vong thap (H-src thap) |
| (d) khong retrain toi khi thuoc xep hang bao suy giam | thuoc IC/AUC/lift cuon tren DEV + nguong suy giam ghi truoc | thap-trung binh (nguong) ; NHUNG chu y: DEV validate = retrain MOI quy, khong retrain cung la lech khoi quy trinh da validate |
| (e) THEM: quantile-map dau ra model moi ve phan phoi OOS cua model cu (bien doi don dieu dong bang luc doi) - mot phep cho ca gate, DCA, sp | M1/M2 tren 17 ranh gioi | trung binh |
| (f) THEM: retrain dung nhu DEV (moi quy, cung mep/purge) thay vi de model "gia" 2 quy | M4 lane WFO vs LAG1 tra loi truc tiep | thap |
| (g) THEM: doi tung model mot (p15 hoac net015), khong doi ca 3; canary/shadow so bo dem | M4 giai thua | thap |
| (h) THEM: trung binh fold k-1 va k mot quy chuyen tiep | M1 + M4 | trung binh (them mot lua chon) |

## 6. KHONG khao sat duoc / gioi han
- Gia tri LIVE_GATE_ROLLING_* va profile live 242 (cam doc 242/env). Khong doc RESULT_PREDBIN_REPRO truc tiep (chi qua RESULT_GATE_ABLATION :19).
- Nguon goc fit cu the cua 0,008 / 0,26787 / 1,2876 / 1,55 (chi co ghi chu "HPO / GATESCALE / GD92", chua doc chi tiet).
- Quan he ~/sel_models_net015 (14 booster 45 feat) voi bins DEV g015x26: CHUA XAC MINH. CoinRankManager tier co dung diem model khong: chua kiem.
- Pass gate theo THANG / sau ranh gioi trong DEV: log chi co tong theo quy. r-proxy 2021 thieu (a3 bins tu 2022Q1).
- Mep quy: fold p15 cat theo UTC, quy dem theo +07 (lech 7 h) - bo qua trong bang muc 4.
- Khong goi API Kaggle (danh sach dataset lay tu RETRAIN_PILOT_DEV / RECON_1119).
