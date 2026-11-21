# RETRAIN_PILOT_RUN - luot 1 = buoc 2 (cong tai lap 3a) theo docs/prereg/PREREG_RETRAIN_PILOT.md (c796c7b3, sha256 7cf7e516...) - DUNG tai STOP-1
Ngay 2026-11-21 10:20-11:10 +07. Chi du lieu DEV (+ gate_dataset_full doan 2026H1 cho P15-A, U2). Khong train T1, khong artefact Vision 2026,
khong jar, khong 242, khong commit. Nhat ky tung buoc: RETRAIN_PILOT_RUN.progress. Out: ~/claude_master/w3/retrain/out/.

## Bang cong (muc 4 prereg)
| cong | do duoc | nguong | ket qua |
|---|---|---|---|
| P15-A (cut20260701 UTC, purge 15', xgb-env) | ONNX md5 86d0542a != b68563fe; MOI thuoc tinh TreeEnsemble TRUNG (attr diff rong), 150 cay / 4 592 node = ref; chi khac graph.name (uuid ngau nhien onnxmltools); ORT moi vs ORT b68563fe max|d| = 0,0 (20 000 dong DEV < S0); booster vs ONNX moi 7,45e-8; train 2 889 623 dong, ts_max 1782838800000 | md5 hoac (cay/node bang + max|d| <= 1e-6) | PASS (co dieu kien theo chu prereg; thuc chat noi dung model trung tuyet doi) |
| P15-B (fold_20: CUTOFF 20260401 purge 0) | ONNX md5 26c94045 (khac 24e99ef8 chi do uuid graph.name); attr TRUNG 100 % voi retrain HO5 p2 (fold20_retrain.onnx) => moi truong tat dinh; vs fold_20 8ec99757: nodes_values/target_weights khac; |d| q50 3,3e-9, q99 1,2e-8, q99,9 1,6e-8, MAX 6,75e-5 (1/20 000 dong > 1e-6; 0,02 sd pred) | ONNX fold_20 vs booster retrain max|d| <= 1e-6 tren >= 20 000 dong | FAIL (theo nguong) |
| S1-A (X1_CUT 20251001, ledger cand_dev_x1, keep9 Kaggle md5 1aa3b974, python3 he thong) | sha256 JSON cc0924f1e26f9fcc...997308 TRUNG; score_mem/json spearman 1, max|d| 0 (3 499 202 dong); top-8 6800/6800; fit 108 s; rc=3 do cong noi bo gop onnx 2,62e-6 (ky vong, nhu RESULT_S1REFRESH) | sha == cc0924f1 + json spearman 1 / <= 1e-6 | PASS |
| NET-A (kernel rt-net-a, ONNX cut20251001 ds ho4p1-code md5 a39dbe9a / sha256 7921ceaf...) | khoa 4 517 610 = 4 517 610 trung 100 %; spearman 0,9999999999999; max|d| 4,77e-7; mean 3,6e-8; NaN 0; ref bins sha256 e03f0e58 | khoa 100 %, spearman >= 0,999999, max|d| <= 1e-5 | PASS |
| NET-B (rt-net-b1, rt-net-b2, Kaggle CPU 4 core, xgb 3.2.0, Py 3.13) | train 26,1 / 23,8 phut wall; model_f18 sha256 ff591c49... TRUNG BYTE 2 lan; bin sha 2115eb7e trung; vs goc GPU: khoa trung, spearman 0,991128 (max|d| 0,228, mean 0,0123); n_train 34 904 563, pos 0,1891, p_mean 0,5048 | spearman >= 0,98 + 2 lan CPU trung sha | PASS |

## Ket luan cong
- 4/5 PASS (P15-A, S1-A, NET-A, NET-B). P15-B FAIL theo nguong prereg (1 dong / 20 000 lech 6,75e-5). Theo N2/D10: DUNG cong P15-B, bao MASTER.
  Chan doan (mo ta): retrain hom nay == retrain HO5 tung thuoc tinh (tat dinh); fold_20 goc train tu file wfo_feature_store.csv DA MAT (AUDIT_FOLD20_DATA),
  khong phai a1c78e2f; P15-A chung minh pipeline + file + moi truong tai lap DUNG model 10-02 (noi dung trung tuyet doi). P15-B khong lien quan T1
  (T1 khong dung fold_20; fold_20 chi la model live / Lane L). MASTER quyet: chap nhan P15-B la "da biet, khong chan" hay dung.
- Nhan xet md5 ONNX: onnxmltools gan graph.name = uuid ngau nhien moi lan convert => md5 ONNX KHONG bao gio tai lap; so sanh dung = thuoc tinh cay
  (hoac ORT max|d|). Ap cho moi cong md5 ONNX ve sau (P15-A, 3d).
- D4: CPU 23,8-26,1 phut cho fold 20251001 (34,9 M dong) << 9 h => CPU cho MOI model net015 (T1/T2), tat dinh (2 lan trung byte). Khong dung GPU.

## P14 (ban copy, KHONG sua repo)
- ~/claude_master/w3/retrain/work/p14/g015_net_train.py md5 3de89b98339d1c46b267f4e92d10314f (sha256 3a96281a...); diff 1 dong (:60):
  `"20251231", "20260101", "20260401"]` -> `"20251231", "20260101", "20260401", "20260701", "20261001"]` => 24 cut, idx 20251001=18, 20251231=19,
  20260701=22, 20261001=23. File diff: work/p14/P14.diff (sha256 3bef6131...). MASTER commit truoc khi train net015 T1.
- BAT THUONG MOI (ngoai P14, CAN MASTER): g015_net_train.load_labels (:144) loc cung `ten file nhan < "20260701"` => o T2 (cut20261001) file
  funding_label_20260701_to_20261001.pb bi BO im lang -> model T2 khong co nhan Q3 (train ~ nhu T1, khong loi). T1 khong bi anh huong (dung file <
  20260701). Muon T2 dung nhan Q3 phai doi them 1 dong (vd "20261001") = thay doi code ngoai "chi cutoff" => MASTER quyet truoc buoc 7.

## Script moi (sha256)
- work/rt_p15_train.py 388ec2815b00bb18...; work/rt_p15b_diag.py 82a8a7598552c9c1...; work/run_2a.sh 29dec883...; work/run_2b.sh 0774a9a4...;
  work/wait_net.sh b86ca115...; work/kaggle/rt-code/rt_net_kernel.py 9baa6da3d95e294e... (dataset private chuyendinh/rt-code, kem g015_net_train.py
  goc a32bb0f7); kernel run.py rt-net-a / rt-net-b1 / rt-net-b2 (xem sha trong progress). Kernel: private, internet BAT chi de pip pin
  xgboost 3.2.0 / ORT 1.23.2 / pandas 2.3.3 / numpy 2.2.6 (nhu chain HO4/HO5), CPU.
- File tam: work/data/feat_v2_x1_keep9.parquet (286 MB, giu cho S1 T1). Dia Oracle con 17 G (>= 15 G).

## Uoc thoi gian buoc 3-4 (cap nhat)
- 3a splice check + K3 ~1 h; 3b ledger L-a phan DEV + G-L ~1 h (Kaggle). 4a p15 T1 ~2 ph (fit 40 s). 4b net015 T1 CPU ~30-40 ph + ONNX/3c-3d ~30 ph.
  4c P-N1 + chain N ~2-3 h; 4d ledger Q3 ~1 h; 4e S1 T1 ~15 ph; 4f P-N2 + a3 ~30 ph. Tong buoc 3-4 ~6-8 h wall (net015 khong con la duong gang).

## BUOC 3-4 (luot 2-3, 2026-11-21 11:00-12:35 +07; prereg c796c7b3 + ADD1 c471c851 + ADD2 a6ab4186) - DUNG tai STOP-2 (mot phan)
Moi kernel/script doc 2026 log "HOLDOUT_UNSEAL_REF HOLDOUT_UNSEAL_2026_1121 e9095a02 (U2 RETRAIN)". Khong sim, khong 242, khong commit.
### Bang cong
| cong | do duoc | nguong | ket qua |
|---|---|---|---|
| K (rt-splice) Tool1 diem noi | DEV Q2 max 2026-06-30 23:45 UTC < Vision Q3 min 07-01 00:00 UTC, khong ho luoi 15' | ADD2 A2-1 | PASS (theo A2-1; theo chu prereg goc FAIL) |
| K1 Tool1 Vision Q3 | 25 102 khoa trung = 50 204 dong = 0,92 % Q3; DUNG 8 id mapper dung chung 843-850 (16 ten: BNC/SOXS 10 542, SNOW/ZHIPU 6 858, PANW/SKHY 6 446, MINIMAX/VRT 6 104, APP/SHAZ 5 928, FWDI/TZA 5 608, MUU/XBI 4 758, GEV/SOFI 3 960 dong); 2026-07-16..09-30 (77 ngay) | A2-2: bao cao; T2 loai | BAO CAO (T1 khong dung file nay). Luu y T2: 0,92 % < 1 %, nhung 16 TEN symbol (8 id) - nguong "> 12 symbol" can MASTER doc la id hay ten |
| K2 nhan | DEV Q2 max 06-30 16:45 UTC, Vision Q3 min 07-01 00:00 UTC => ho 7 h 15' | A2-3 chap nhan | CHAP NHAN (ghi chu) |
| K feat_v2 (S1) | K1 dup 0/0; DEV <S0 ket thuc S0-1h, Vision bat dau dung S0; luoi gio 0 thieu; K4 cot du; chong lan Vision lead-in 14 118 dong: 99,8 % o trung (ls_global 90,1 %, rk_oi_delta24h 0,2 %) | K1/K2/K4 | PASS |
| K gate Vision Q3 | 0 ts trung, ts tang, moi ngay Q3 1 440 phut, NaN 0, du cot | K1/K2/K4 | PASS |
| K3 (mo ta) | Tool1 DEV vs Vision 2026H1: 26,2 % o bang nhau, 0 % dong bang du; nhan Q1 retEnd_4h 99,98 %, 72h 97-98 %; gate 33 cot trung binh xem result (vd momentum1M 18 %, momentum1H 85,6 %, breadth ~2 %) | mo ta | - |
| G-L lan 1 | 6 928 308 = 6 928 308 dong; 11/12 cot trung; g1lite lech 1 289 373 dong (max 7,6e-8) | 12/12 | FAIL |
| G-L lan 2 (A2-4: ep float32) | g1lite VAN lech 140 932 dong. Nguyen nhan da xac minh: ban cu tinh g1lite bang SO HOC float32 (numpy 2 NEP50 tren Oracle: tinh lai tu maxFav/retEnd cua chinh ban cu ra 0 lech); ban moi tren Kaggle tinh float64 roi ep -> khac lam tron. Nhan S1 rel5 trung 100 % (0 / 6 928 308) | 12/12 | FAIL -> DUNG nhanh S1 (S1-A bang ledger moi CHUA chay) |
| NET-EQ | model_f22 sha256 d91fe74181cd2c0c... TRUNG BYTE giua P14 (rt-net-t1, 35,9 ph) va P14b (rt-net-t1b, 35,1 ph) | trung byte | PASS |
| 3c net015 T1 | n_train 48 429 620; max train ts 1782578700000 (06-27 16:45 UTC) < 1782579600000; pos 0,1853; OOS 17 034 rec = size/26; NaN 0; p trong (0,1) | muc 5 | PASS |
| 3d net015 T1 (rt-net-d3) | ONNX sha256 29d9a79d... (md5 a2547c33) vs booster: 319 821 dong DEV 2025Q4, spearman 0,9999999999988, max|d| 4,17e-7, top-8/50/200 100 %, top-8 theo tick 644/644 | >= 0,9999999 / 1e-5 / 100 % | PASS |
| p15 T1 (4a) + 3d | train 2 889 607 dong, max ts 1782837840000 < 1782837900000; booster vs ONNX 8,9e-8 (20 000 dong); NaN 0 | assert + 1e-6 | PASS |
| P-N1 | rt-chain-pn1 (fork, 2 model cu): pred26 64f66a15, net015 4d38b41f / 55c78806 / 53cdea81 = MANIFEST ho5-a3-chain26 4/4 | trung md5 | PASS |
| P-N2 | rt_a3n pn2: bins 20260701 sha256 9a914693... == Lane L | trung sha | PASS |
| chain N | rt-chain-n26: model p15 T1 3f840e4b + net015 T1 a2547c33 (kiem trong kernel ho5_models_ok); pred26 c1b00ba9 (393 120, NaN 0); RAW 20260101 f0558240, 20260401 8ec96255, 20260701 e72532c6 (5 382 633, NaN 0) | toan ven | PASS |
| 4d / 4e / 4f build | CHUA CHAY (bi chan boi G-L) | - | DUNG |
### Manifest model T1 (2 / 3 xong)
- p15 T1: out/p15_t1/Model_Regressor_Return15M.onnx sha256 c9f13fc00571266b... (md5 3f840e4b, cay/node 150/4 602), booster sha256 71e82572...; DATA gate_dataset_full.csv
  a1c78e2f (DEV, 0 % Vision); CUTOFF 20260701, GATE_PURGE_MS 26100000; 2 889 607 dong; max train ts 1782837840000; seed 42; xgb-env Py 3.10.12, xgboost 3.2.0,
  onnxmltools 1.16.0, ORT 1.23.2; script train_gate_fold.py b41c9159 qua rt_p15_train.py (v2 md5 a47dd10e).
- net015 T1: model_f22_4h.json sha256 d91fe74181cd2c0c9e49098c21c45e3b5b94a7b9aa00aacb0a9ccea2a0c57901; ONNX g015x26_f15_cut20260701.onnx sha256 29d9a79d5ad706fe...
  (md5 a2547c33); g015_net_train.py repo P14 3de89b98 (--fold 20260701, idx 22, CPU, seed 42, nest 400); 48 429 620 dong train; max ts 1782578700000; 0 % Vision
  (T1_DIR chi DEV, 22 file Tool1 + 22 file nhan DEV); Kaggle CPU Py 3.13.18, xgboost 3.2.0, numpy 2.2.6, pandas 2.3.3. Dataset private rt-net-t1-model (model + ONNX).
- S1 T1: CHUA (chan boi G-L). feat ghep san: out/s1/feat_rt26.parquet md5 32e879f6 (DEV 10 260 504 + Vision 3 888 245 dong; 27,5 % Vision).
### Mo ta pred T1 vs model live tren Q3 (KHONG PnL)
- p15 (132 480 phut): T1 p50 0,00909 / p99 0,01356 / max 0,145 vs fold_20 p50 0,00887 / p99 0,01306 / max 0,092; spearman 0,9878.
- net015 RAW fold 20260701 (5 382 633 dong): T1 p50 0,4198 / p99 0,6985 vs cut20251231 p50 0,4169 / p99 0,6876; spearman toan bo 0,9835, trung vi theo tick 0,9887.
### P14b (ban copy work/p14b, MASTER commit)
- md5 7d2b6e8a5780f5dddb8d406c8d3078b5 (sha256 96fcbfe6...); diff work/p14b/P14b.diff (sha256 d33ae54f...) 2 hunk:
  :144 `fs = [... split("_")[2] < "20260701"]` -> `cut_lb = int((pd.to_datetime(hi_ms + TZ, unit="ms") - pd.DateOffset(months=OOS_MONTHS)).value // 10 ** 6) - TZ`
  + `fs = [f for f in fs if ms(os.path.basename(f).split("_")[2]) < cut_lb]` (cut cua fold, tinh nguoc tu hi_ms - dung khi chay 1 fold / lan);
  :258 `assert int(ts_all[tp].max()) < c` -> `< tr_cut` (assert nhan train < cut - 72 h). NET-EQ: trung byte voi P14 tren fold 20260701.
### Dataset / artefact
- rt-n-data26: CHUA tao (can bins 20260701 tu S1 T1). Da co: pred_2026_N tu chain N (c1b00ba9); P-N2 chung minh duong a3 tai lap Lane L.
- Dataset private moi: rt-code (v6), rt-chain-code (v2: + net015 T1), rt-net-t1-model. Kernel: rt-splice, rt-ledger-dev(v2), rt-net-t1(v2), rt-net-t1b(v2),
  rt-net-d3(v2), rt-dup, rt-chain-pn1, rt-chain-n26 (rt-net-t1 v2 status ERROR chi do buoc 3d trong cung kernel thieu makedirs; train + 3c xong truoc do;
  3d lam lai o rt-net-d3).
### md5 cong cu fork / moi
rt_chain.py 163e69b4 (= ho5_chain 20dce08c + 2 cho ten file model tu cfg); rt_chainops.py e21fa0d4 (fork ho5_chainops aea28618: bien the pn1/n, ds rt-chain-code);
rt_a3n.py 8f6a2a3a (fork a3_26 753064a2: pn2 / build / upload, hard link bins L, dung a3lib HO5 06bdd753 chi doc); rt_t1_kernel.py a9971c01 (splice/ledger/net/dup/d3);
rt_fetch.py d9c2215d; wait2.sh 6b53b593; rt_gl.py d370d8f7; rt_cast32.py 92c83340; rt_feat_splice.py 167df4cf; rt_desc_q3.py 5b7eca7b; rt_p15_train.py a47dd10e.
run.py sha256: rt-splice 2e301384, rt-ledger-dev 596c9926, rt-net-t1 d8a97e07, rt-net-t1b 430ccaad, rt-net-d3 e6daadcc, rt-dup 7c048955, rt-chain-pn1 a672d955, rt-chain-n26 4226d17c.
### Dia + bat thuong
- Dia Oracle 16,15 GB trong (>= 15,5). File tam con: out/k/rt-chain-n26 (RAW_N 140 MB, pred26 6 MB), out/s1/feat_rt26.parquet 398 MB.
- Bat thuong: (1) g1lite phu thuoc kieu so hoc (float32 Oracle vs float64 Kaggle) - x1_ledger khong tat dinh qua moi truong; (2) gate_cfg HEAD khong doc duoc
  AIRejectFilter.java HEAD (L7 da refactor) - phai dung ban 2026-09-05 (chi anh huong cot dyn_thr/gate_dyn_ok, trung 100 %); (3) Tool1 DEV dung bien UTC,
  nhan DEV dung bien +07 (khac nhau giua 2 loai file DEV); (4) output kernel trang thai ERROR khong mount duoc lam kernel_source.
### De xuat cho MASTER (G-L)
- Phuong an a (khuyen nghi): ledger = cand_dev_x1 nguyen byte cho ts < S0 (DEV goc) + dong >= S0 tu ledger moi voi g1lite tinh lai bang SO HOC float32
  dung cong thuc x1_ledger (da kiem: cong thuc float32 tai lap 100 % ban cu); G-L tu dong dat cho phan < S0; them kiem S1-A tren ledger ghep.
- Phuong an b: chay x1_ledger tren Oracle (python3, numpy 2.2.6, ra float32 nhu ban cu) - can ~3,7 GB dia tam (khong du nguong 15 GB) => khong khuyen nghi.
### Uoc thoi gian con lai
- Sau quyet dinh G-L: ledger Q3 (Kaggle ~15 ph) + S1-A lai (~5 ph) + S1 T1 + 3c/3d (~20 ph) + a3 N build + upload rt-n-data26 (~20 ph) => ~1-1,5 h.
- Buoc 5 Lane N 8 sim (<= 5 song song, ~45-65 ph/kernel) ~2-2,5 h wall; buoc 6 cham ~1 h.

## BUOC 4d-4f + 5 (luot 4-5, 2026-11-21 12:35-..., ADD3 2d5458ad + ADD4 6b41632c) - DUNG tai STOP truoc khi cham
### Bang cong
| cong | do duoc | nguong | ket qua |
|---|---|---|---|
| 4d ledger Q3 (rt-ledger-q3) | cand_rt26q3 16 712 052 dong, (ts,sym) trung 0; Q3 3 924 883 dong / 6 911 tick; pool Q3 = pred26 chain N (c1b00ba9) >= S3, DEV wfo_gate_pred < S3 (2 760 442 + 132 480 dong, md5 877badea); nhan DEV + Vision Q3 | toan ven | PASS |
| G-L (A3-1: g1lite so hoc float32, rt_g1lite32.py) | 6 928 308 = 6 928 308 dong, 12/12 cot trung tuyet doi (ts < S0 - 72 h) | 12/12 | PASS |
| S1-A lai bang ledger moi (cand_rt26q3_32 + feat_rt26) | sha256 JSON cc0924f1...997308 | == cc0924f1 | PASS |
| 4e S1 T1 assert | train 12 787 169 dong, max train ts 1782440100000 (2026-06-26 02:15 UTC) < 1782579600000 (S3 - 72 h) | assert | PASS |
| 3c S1 T1 | NaN json/onnx 0/0 tren 3 924 883 dong OOS Q3; score (= -pred) mean/std T1 1,1675 / 0,5570 vs live 1,1983 / 0,5808 (mo ta) | NaN 0 | PASS |
| 3d S1 T1 | ONNX vs JSON: spearman 0,9999999999975, max|d| 2,15e-6, top-8 trung 6 911 / 6 911 tick | >= 0,99999, 100 %, >= 5 000 tick | PASS |
| 4f P-N2 (luot truoc) + build | bins 0101/0401 hard link Lane L (sha trung); pred_2026_N: 260 640 dong ts < S3 trung byte Lane L + 132 480 dong N; NaN 0 | trung | PASS |
### Manifest S1 T1
- out/s1_t1/s1a2x1_cut20260701.json sha256 8bb11092dc20db6b4e70aaac29d7aa6293bb272640912e9aea9f008f2316ac88; .onnx sha256 18ed11a0d15050e20b49c6bd07314edfabcebe543d229cea904e0d62cff57c63;
  manifest sha256 29993585...; script x1_s1_save_model.py 00695118 (khong sua), X1_CUT=20260701, seed 42, purge 72 h; ledger out/s1/cand_rt26q3_32.parquet (sha256 df19411d...);
  feat out/s1/feat_rt26.parquet (md5 32e879f6); python3 he thong 3.10.12, xgboost 3.2.0, onnxmltools 1.16.0, ORT 1.23.2, pandas 2.3.3, numpy 2.2.6.
- Ti le 2 nguon: 45,1 % dong train S1 T1 co ts >= S0 (2026H1: pool + nhan DEV, feature feat_v2 Vision); 54,9 % <= 2025 (DEV thuan). Cong noi bo script (so voi
  ref S1 live) gate_pass/topk8_pass False = MO TA (khong ap dung), rc=3 ky vong.
### Mo ta S1 T1 vs S1 live tren OOS Q3 (KHONG PnL; out/s1_t1/check.json)
- score p01/p50/p99: T1 -0,788 / 1,285 / 1,892 vs live -0,789 / 1,334 / 1,850; spearman 0,9774; top-8 trung binh trung 81,0 % (trung vi 87,5 %) moi tick.
### rt-n-data26 (private)
- pred_2026.bin md5 a574a2e9b9e3f561c4050b2ccb938bf5; predict_wf_20260101.bin sha256 b58099f4... (= L); 20260401 78e4e437... (= L); 20260701 bb64cde34cfc38a8...
  (S1 T1 8bb11092 + RAW_N e72532c6; demoted 16,3 %). Kiem chain: out/a3n/A3N_build.json, out/a3n/DATA26_N.json.
### Diff run.py Lane N vs Lane L (out/nsim/cfgdiff.json, out/nsim/diff_run_<seed>.txt)
- 8/8 seed: phan ngoai CFG cua run.py TRUNG tuyet doi. CFG khac o: tag (rt-n-l26-*), ho5.d26_ds (rt-n-data26), ho5.pred26_md5 (a574a2e9), ho5.bins26_sha
  [20260701] (bb64cde3) - 2 cai cuoi la ma bam ghim du lieu cua dataset moi (bat buoc) - va ho5.unseal_ref "(U2 RETRAIN)" thay "(U1 HO5)" (chuoi log tham chieu
  HOLDOUT_UNSEAL). kernel-metadata: id/title + dataset rt-n-data26 thay ho5-a3-data26. Jar sim-jar-tsx cc0f9d11 (stub, giong HO5), profile, overrides khong doi.
### rt_score_n.py (CHUA chay tren Lane N)
- work/score/rt_score_n.py sha256 907d2af865f7b6372183147b90aeec12e240cf1534578149ec20e6d2f1eae885 (dung rows/updates/metr cua l5/score_l5.py md5 1a082088, chi doc).
  Luat: D5 ROI_Q3 = SigmaPnL_Q3 / E_start_Q3; H-E0, H-NI (LB = mean - 2,3646 sd / sqrt 8 >= -1,0 pp), H-DD; mo ta: ROI MTM + H-NI MTM, bootstrap tuan CI80,
  lenh theo thang (start), n_pass gate tong (log sim chi in tong). Chay Lane N can co --allow-n.
- Selftest L-vs-L: d = 0 o 8/8 seed; tai lap RESULT_HO5 Q3 tung seed (SigmaPnL, E_start, E_end, ROI MTM 4,51 %, maxDD -1,48 %); ROI theo D5 = 3,12 %
  (ADD4 6b41632c dinh chinh). Ket qua: out/score/score_n_selftest_LvsL.json.
### Buoc 5 - 8 kernel sim Lane N (Kaggle CPU, private, jar sim-jar-tsx cc0f9d11, KHONG tai funding.bin) + kiem chung KHONG lo PnL
- Push: s123 12:56 (thu truoc, qua tu kiem) -> a1/s13/s2024/s21 13:01-13:05 -> s7 13:45, s777 13:49, s99 13:54 (orch_n.sh v2). Su co: orch v1 dem slot sai
  (used=0) -> 2 lan push s7/s777 luc 13:06/13:08 bi Kaggle TU CHOI (free_slots=0, KHONG tao kernel) -> khong vuot 5 kernel; da sua (dem kernel cua minh + kiem URL).
- 8/8 COMPLETE (java_rc=1 nhu r1-a3), tai chon loc (result.json, printDone.csv, sim.out.gz, config/prof, a3_funding.json; 0 funding.bin), out/nsim/rt-n-l26-<seed>/.
- rt_nchk.py (sha256 0cf6eb2d...; chi in dem / True-False): 8/8 PASS - ok, date_last >= 20260929, jar cc0f9d11, mapper 5c436e65/6143fa75, funding snapshot
  fb024c40/207e7c60, bins26 3 sha (b58099f4 / 78e4e437 / bb64cde3), unseal U2, pred n_2026 393 120 NaN 0, pred nguon <SEAL + n_dev = L, market = L, funding phan DEV
  = L, profile_hash + overrides + bins r1-a3 = L, header printDone = L, MOI dong printDone end < 2026-07-01 00:00 +07 TRUNG nguyen dong + thu tu voi L
  (a1 3866, s123 3828, s13 3706, s2024 3758, s21 3794, s7 3792, s777 3782, s99 3798 dong), khong NaN pnl/start/end, 273 dong Update ngay 2026 (= L),
  dong Update <= 20260630 trung L. Tong hop: out/nsim/check_summary.txt; tung seed out/nsim/rt-n-l26-<seed>/check_n.json.
- KHONG chay rt_score_n.py tren Lane N; KHONG mo / in dong end >= 2026-07-01 hay equity sau 06-30. DUNG, cho audit doc lap + MASTER.
### Duong dan cho auditor
- Code fork/moi: ~/claude_master/w3/retrain/work/{rt_p15_train.py, rt_fetch.py, rt_gl.py, rt_cast32.py, rt_feat_splice.py, rt_desc_q3.py, p14b/,
  kaggle/rt-code/ (rt_t1_kernel.py, g015_p14*.py, x1_ledger.py, gate_cfg.py, repo_*), kaggle/<kernel>/run.py, chain/ (rt_chain.py, rt_chainops.py, kaggle/),
  a3n/rt_a3n.py, s1/ (rt_g1lite32.py, rt_s1_ref.py, rt_s1_check.py, run_s1t1.sh), nsim/ (rt_nsim.py, rt_nchk.py, rt_cfgdiff.py, orch_n.sh, kern/), score/rt_score_n.py}.
- Manifest/log: out/p15_t1/manifest_rt.json + p15_t1.log; out/k/rt-net-t1*/result.json; out/k/rt-net-d3/result.json; out/k/rt-chain-{pn1,n26}/;
  out/k/rt-ledger-{dev,q3}/result.json + ledger_build.log; out/GL_*.json; out/s1a2/ (S1-A lai); out/s1_t1/ (+ check.json, s1_t1.log); out/a3n/A3N_*.json,
  DATA26_N.json; out/DESC_Q3.json; out/nsim/ (cfgdiff.json, diff_run_*, gen/push/fetch/chk logs); out/score/score_n_selftest_LvsL.json; out/k/rt-splice, rt-dup.
- Dia Oracle: 15,80 GB trong (>= 15,5).

## BUOC 6 (ADD5 cb5e2d07) - DUNG tai STOP-3
- A5-6 jar_sec_check (research/nup3/jar_sec_check.py md5 d59ab164) tren ~/claude_master/tsx/ds_sim-jar-tsx/sim.jar (sha256 cc0f9d11...): ok=True, PrivateConfig chi 2
  ten JVM (0 chuoi la, max run 44), com/binance 0 lop co chuoi 64 alnum, 8 lop gnu/crypto (hang so). KHONG co key. out/jar_sec_check_cc0f9d11.json.
- A5-1 rt_score_n.py v2 sha256 26c86069... (diff work/score/rt_score_n.v1_v2.diff): assert check_n 8/8 + check_l5 8/8, assert E_start = Update 20260701 ca 2 lane;
  selftest L-vs-L d = 0 8/8; thu pha (copy s13 bo Update 0701) -> AssertionError, rc 1 (out/score/brk/brk.log).
- Cham Lane N: H-E0 FAIL (mean SigmaPnL_Q3 -10 743,4; 0/8 seed > 0), H-NI FAIL (mean d -9,5640 pp, LB -9,5642), H-DD khong canh bao (maxDD TB -7,45 %).
  QUYET DINH: PILOT tiep tuc BI CHAN; DUNG; khong buoc 7. Ket qua: v12/RESULT_RETRAIN_T1.md (sha256 30ad943e...), out/score/score_n_laneN.json.
