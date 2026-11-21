# PREREG_RETRAIN_PILOT_FINAL - train lai p15 / S1 / net015 truoc PILOT (ban CUOI, viet 2026-11-21, agent thiet ke; MASTER commit TRUOC khi chay)

Tu chua: doc file nay la du de chay. Duong dan tuong doi = repo ~/claude_master/vz_e1_wt (HEAD luc viet e9095a02).
Can cu bat buoc (doc, KHONG thay the file nay):
- Quyet dinh MASTER: ~/claude_master/w3/retrain/RETRAIN_MASTER_DECISIONS_1121.md (sha256 1c3fe28d37ba89a2...) = D1..D11.
- Mo seal: docs/prereg/HOLDOUT_UNSEAL_2026_1121.md (commit e9095a02), pham vi U2 (retrain) + U3 (2026-10-01 -> nay, kiem mo ta).
- Do dac nen: ~/claude_master/v12/RETRAIN_RECON_1119.md; ban nhap ~/claude_master/w3/retrain/PREREG_RETRAIN_DRAFT.md (file nay THAY ban nhap).
- Kiem ke luot nay: ~/claude_master/v12/RETRAIN_PILOT_DEV.md (con / mat / phai dung lai).
- Lane L = HO5: docs/prereg/PREREG_HO5_A3_2026.md (bf3f90a1) + ADD1 (5803ca82) + ADD2 (2725f216) + ADD3 (499700bd);
  dinh nghia cham ~/claude_master/w3/ho5/l5/SCORE_DEFS_L5.md (sha256 03a9345362d38e7a...), scorer l5/score_l5.py (md5 luc viet 1a2ea082).
Moi kernel / script doc du lieu >= 2026-01-01 PHAI log dong "HOLDOUT_UNSEAL_REF HOLDOUT_UNSEAL_2026_1121.md e9095a02 (U2 RETRAIN)" (D1).

## 0. Cau hoi, pham vi, nguyen tac
Cau hoi: bo 3 model train lai DUNG recipe cu voi cutoff moi (tang KIEM CHUNG cut 2026-07-01) co (a) khong am tren 2026Q3 (H-E0) va
(b) khong kem bo 3 model dang live qua bien -1,0 diem % ROI quy (H-NI) khi chay DUNG cau hinh sim r1-a3 nhu HO5 khong? Neu co, train
tang SAN XUAT cut 2026-10-01 cung recipe, qua cong toan ven + shadow 7 ngay, roi dua owner goi doi model 1 lenh.
Day la VAN HANH model (refresh theo nhip WFO), KHONG phai tim alpha.
Nguyen tac (ap nguyen van, khong ngoai le):
- N1 Khong HPO. Khong doi feature, nhan, hyperparam, seed train, thu tu feature, objective. Thay doi DUY NHAT duoc phep = cutoff (va
  du lieu moi toi cutoff do theo D2). Seed train = recipe: p15 random_state=42, S1 random_state=42, net015 SEED=42 (D10).
- N2 Moi cong FAIL -> DUNG, bao MASTER, khong va, khong chay buoc sau (D10). "Chay lai" chi khi loi ha tang da xac minh (kernel ERROR
  truoc khi ghi output, het dia, mat mang) - toi da 1 lan / buoc, ghi ro ly do; KHONG chay lai vi so xau.
- N3 Khong sua file nay sau khi co bat ky so nao cua Lane N / tang san xuat. Sua loi CODE ha tang sau commit chi duoc neu khong doi
  dinh nghia (ghi vao bao cao ket qua).
- N4 Khong cham 242 (production LIVE). Khong git push. Jar len Kaggle phai la jar STUB khong key: kiem bang research/nup3/jar_sec_check.py
  (md5 luc viet d59ab164) truoc moi dataset jar moi (D11). Khong in key / token.
- N5 Pham vi du lieu 2026 = U2/U3 cua HOLDOUT_UNSEAL. Khong grid, khong alpha moi, khong tinh chinh tham so chien luoc tren 2026.
- N6 Oracle dia: truoc moi buoc ghi > 200 MB tren Oracle: `df --output=avail -BG /` phai >= 16 G sau khi tru dung luong se ghi; duoi
  15 G => DUNG (khong xoa du lieu nguoi khac). Du lieu nang chi tren Kaggle. Khoa flock ~/claude_master/locks/oracle_heavy.lock cho moi
  buoc Python nang tren Oracle (> 2 GB RAM).
- N7 Kaggle: tong kernel CPU dang chay toan tai khoan <= 5 (KAGGLE_RULES muc 1), tinh ca HO5 dang chay; GPU <= 2 (chi neu D4 buoc GPU).
  Khong ks.fetch output co funding.bin (4,4 GB) ve Oracle; tai CHON LOC (result.json, printDone.csv, log, manifest).

## 1. Ba model - recipe CHINH XAC (khoa cung; md5 script luc viet - neu khac luc chay => DUNG)
### 1.1 p15 (gate, XGBRegressor, 1 so / phut, market-level)
- Script: ml/gate/train_gate_fold.py md5 b41c9159597ceecb254240b789429a98 (sha256 1819e9533d9452c5...). = ban WFOGateRunner goi
  (AUDIT_FOLD20_DATA.md muc 1). Env: DATA (csv), CUTOFF (yyyymmdd, :43 `pd.Timestamp(naive)` = 00:00 UTC), OUT_DIR, GATE_PURGE_MS (:35).
- Hyperparam (:60-62): XGBRegressor(objective=reg:squarederror, max_depth=4, n_estimators=150, learning_rate=0.05, subsample=0.8,
  colsample_bytree=0.8, min_child_weight=10, random_state=42, n_jobs=4). Khong valid, khong early stop.
- Feature (:24-33): 33 cot V3FULL dung thu tu khoa cung; float32 (:57); KHONG scaler. Nhan: label_oldbasket (:36, GATE_LABEL mac dinh).
- ONNX (:68): onnxmltools convert_xgboost, input ("float_input", FloatTensorType([None,33])); ten file Model_Regressor_Return15M.onnx.
- Train: Oracle, ~/envs/xgb-env/bin/python (Python 3.10.12; xgboost 3.2.0, onnxmltools 1.16.0, onnxruntime 1.23.2, skl2onnx 1.20.0,
  onnx 1.22.0, numpy 2.2.6, pandas 2.3.3, scipy 1.15.3, scikit-learn 1.7.2). Thoi gian fit ~17 s (export_cut20260701.log).
- Mep +07 (D3) KHONG sua code: CUTOFF=<yyyymmdd cua ngay cat> va GATE_PURGE_MS=26100000 (= 7 h + 15 phut) => tr_cut = 00:00 UTC - 7h15'
  = 00:00 +07 - 15'. Script assert (:52) tr.timestamp.max() < tr_cut. Manifest PHAI ghi "purge hieu dung = 15 phut sau mep +07".
- Booster: script KHONG luu booster. Wrapper moi rt_p15_train.py (viet o luot chay): kiem md5 script, dat env, `runpy.run_path(script,
  run_name="__main__")` (chay DUNG byte script), lay `model`/`tr` tu globals tra ve -> save_model JSON + manifest (rows, ts_min/max,
  sha256 DATA, sha256/md5 ONNX, xgb params doc tu model.get_params()) + parity muc 5.
### 1.2 S1 (selector, XGBRanker rank:ndcg)
- Script: research/pipeline/x1/x1_s1_save_model.py md5 00695118ee1276d70e4fba6b5493b770 (sha256 8f234eda09f963b6...).
  Env: X1_CUT, X1_LNAME (ledger ~/ledger/<LNAME>.parquet, thu muc LED khoa cung :42), X1_FEAT, X1_PRED (ref cong noi bo); argv[1] = out_dir.
- Hyperparam (:80-83): XGBRanker(objective=rank:ndcg, n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8,
  colsample_bytree=0.8, min_child_weight=50, n_jobs=4, tree_method=hist, random_state=42, lambdarank_pair_method=topk,
  lambdarank_num_pair_per_sample=8). qid = factorize(ts).
- Feature KEEP (:43-44, 9): vol_7d, dd_7d, rk_dd_7d, hrs_since_high_7d, ret_3d, rk_ret_3d, ret_14d, ls_global, rk_oi_delta24h
  (feat_v2 theo gio, join ts_h = floor gio). Nhan (:57-63): rel5 = min(int(rank_pct(g1lite - median_tick(g1lite))*5), 4), rank method first.
- Cutoff (:73): c = 00:00 +07 cua X1_CUT; train = ledger ts < c - 72 h (:75); OOS noi bo = [c, c+3 thang).
- Dau ra: <out>/s1a2x1_cut<CUT>.json + .onnx (convert_sklearn, opset {"":15,"ai.onnx.ml":2}, input "input" [None,9]) + .manifest.json.
- BAY (do doc code luot nay): neu OOS noi bo rong HOAC ref X1_PRED khong giao OOS thi script CRASH sau khi da luu JSON/ONNX va TRUOC manifest
  (np.concatenate([]) :137; d.max() tren mang rong :145). => Moi lan chay PHAI co (i) ledger co dong trong [c, c+3 thang) va (ii) X1_PRED
  giao cac dong do (xem muc 2.3). "CONG MODEL"/"CONG TOP-K" noi bo cua script = so voi ref cu => KHONG AP DUNG lam go/no-go
  (RETRAIN_RECON C1, RESULT_S1REFRESH.md:22); exit 3 do FAIL noi bo la ky vong, ghi lai.
- Chay: Oracle, python3 he thong (co pyarrow 25.0.1; xgb-env THIEU pyarrow) - cung phien ban xgboost 3.2.0 / onnxmltools 1.16.0 / ORT 1.23.2.
  Kaggle CPU == Oracle CPU byte-for-byte cho S1 (AGENT_RUNBOOK bay 7) => duoc chay Kaggle CPU neu dia Oracle khong du. GPU CAM.
- Ledger: research/pipeline/x1/x1_ledger.py md5 c9aa44f95e7a0fcb7b09b91445925622 (build: pool(tick 15') = coin co nhan tai tick ma
  p15 >= 0,008 doc tu /home/ubuntu/claudedata/wfo_gate_pred.csv; g1lite tu maxFav_72h/retEnd_72h, nBars_72h >= 288). Env: X1_T1, X1_CUTS,
  X1_LNAME, X1_LBGLOB, X1_LB_DIR. Duong khoa cung: /home/ubuntu/featv2 (gate_cfg), /home/ubuntu/sel1m_code, selector_pred_out/symbol_map.csv,
  claudedata/predwf_G015x26 (chi de left-merge p_g015, khong vao S1).
### 1.3 net015 (gia tri, XGBClassifier, y = retEnd_4h > 0,015)
- Script: research/pipeline/g015_net_train.py md5 hien tai a32bb0f759a884b2cb3cdff7aa1e9297. THAY DOI DUY NHAT (D10, nhu
  PREREG_NET015_CUT20251231 muc 2): them "20260701", "20261001" vao CUOI CUT_DATES (:57-60) => idx 22, 23; idx cu khong doi. Diff phai
  dung 1 dong; md5 moi ghi vao manifest + bao cao. Khong sua gi khac.
- Hyperparam (:61, :265-268): n_estimators 400, max_depth 5, learning_rate 0.05, subsample 0.8, colsample_bytree 0.8, min_child_weight 20,
  scale_pos_weight=(1-pos)/pos, eval_metric auc, tree_method hist, random_state 42, n_jobs=--njobs (mac dinh -1). 45 feature (Tool1 40 + OI 5),
  --drop-cols "" (= cong thuc x26). PURGE 288 x 15' = 72 h (:49-50); cutoff 00:00 +07 (ms() :63-66); OOS 3 thang (:51).
- Lenh: python3 g015_net_train.py --fold <cut> --device cpu --save-model --drop-cols "" --out-dir <d>  (env T1_DIR, LB_DIR, OI_FILE,
  MAP_CSV, SEL1M_CODE). Dau ra model_f<idx>_4h.json, predict_wf_<cut>.bin (OOS, 26 B/ban ghi), net_train_summary.json.
- BAY: (a) build_matrix doc glob T1_DIR/features_<nam>* va KHONG loc theo nam => 2 file cung khoang thoi gian trong T1_DIR = dong trung;
  (b) assert OOS khong rong (:261) => T1_DIR phai co dong >= c; (c) OI_FILE la 1 file duy nhat.
- Noi chay: Kaggle (Oracle OOM o duong nang - RECON A3). Thiet bi theo D4: CPU uu tien; do thoi gian o cong 3a(B); <= 9 h => CPU cho moi
  model; > 9 h hoac khong chay duoc => GPU kem cong 2 lan doc lap spearman >= 0,98 tren OOS, dung lan 1. Kernel pip pin xgboost==3.2.0.
- ONNX: script export cu (research/analysis/g015x26_onnx_gate.py, sha256 c0478e97...) khoa cung fold 15 + duong Oracle da mat => viet
  rt_net015_onnx.py CHI chep khoi convert: convert_xgboost(clf, initial_types=[("input", FloatTensorType([None,45]))], target_opset=15),
  p = prob[:,1]; ten g015x26_f15_cut<CUT>.onnx; + parity muc 5.

## 2. Du lieu (D2: hai nguon - DEV toi het du lieu DEV co san, 2026 phan con lai tu artefact Vision HO4-P1)
Ky hieu moc (ms UTC): S0 = 2025-12-31 17:00 UTC (= 2026-01-01 00:00 +07, SEAL); S3 = 2026-06-30 17:00 UTC (= 07-01 +07);
S4 = 2026-09-30 17:00 UTC (= 10-01 +07); S5 = 2026-10-31 17:00 UTC (= 11-01 +07).
### 2.1 Bang nguon (ton tai kiem 2026-11-21 bang ls / kaggle list, CHUA doc noi dung 2026)
| model | DEV (nguon cu) | khoang DEV | Vision HO4-P1 (exporter tat dinh P3-DET) | dung cho |
|---|---|---|---|---|
| p15 | Oracle ~/claude_master/gvz/store/gate_dataset_full.csv md5 a1c78e2f..., sha256 4094424d...; = Kaggle gate-dataset-full v1 | 2021-01-01 -> ts cuoi 2026-06-30 17:00 UTC (2 889 623 dong) | kernel ho4p1-x26-q3 out gate.csv.gz (Q3, 132 480 dong); ho4p1-dupfx gateA/gateB (Q3 ban sua mapper) | T1: DEV; T2: DEV < S3 + Vision [S3,S4) |
| net015 Tool1 | Kaggle funding-tool1-15m (features_..._20260401_to_20260701.t1c, het quy 2026Q2) | toi het file 20260701 | ho4p1-x26-q3 out features_20260701_to_20261001.t1c.gz | T1: DEV (+ file Vision Q3 CHI de OOS khong rong); T2: DEV + Vision Q3 |
| net015 nhan | Kaggle funding-label-15m (toi funding_label_20260401_to_20260701.pb) | toi 2026-07 | ho4p1-x26-q3 funding_label_20260701_to_20261001.pb | T1: DEV; T2: DEV + Vision Q3 |
| net015 OI | Kaggle funding-oi-percoin oi_percoin_full.bin (4,23 GB) | toi ~2026-07-01 | kernel ho4p1-oi-a oi_rebuilt.bin.gz ([2025-06-01, 2026-10-04) UTC) | T1: DEV; T2: file ghep DEV < S3 + Vision >= S3 |
| S1 pool p15 | Kaggle funding-gate-wfo-pred wfo_gate_pred.csv (WFO Java seed 42; 2026Q1 = fold_19, Q2 = fold_20) | 2021-04-01 -> 2026-06-30 | Q3: pred26 cua p15 T1 moi tren gate Vision Q3 (kernel chain Lane N) | T1+T2 |
| S1 nhan g1lite | funding-label-15m (nhu tren) | toi 2026-07 | ho4p1-x26-q3 funding_label_20260701_to_20261001.pb; Q4: gs-x26-q4 funding_label_20261001_to_20270101.pb | T1: DEV (+Q3 Vision chi OOS); T2: + Q3 train, Q4 OOS |
| S1 feat_v2 | Kaggle s1-featv2-x1-20260919 feat_v2_x1_keep9.parquet (286 MB) | toi het CLOSES_1H DEV (~2026-01-01) | ho4p1-chain-y26 out feat_v2_26.parquet (2026, 3 907 571 dong); Q4: gs-chain-q4 feat_v2_26.parquet | T1+T2 |
- Lane N (sim) dung DUNG artefact Vision ma HO5 Lane L dung (ho4p1-x26-q1..q3, ho4p1-oi-a, ho4p1-chain-y26, ticker ho4p1-tk26, funding
  snapshot v3, mapper snapshot) - ghi md5/sha theo result.json cua kernel HO5 tuong ung, so tung cai.
- Kiem ton tai lai ngay luc chay (kaggle kernels status / files, ten): ho4p1-x26-q1/q2/q3, ho4p1-oi-a, ho4p1-chain-y26, ho4p1-dupfx,
  gs-x26-q4, gs-oi-c, gs-chain-q4 (2026-11-21: tat ca COMPLETE, co file). Thieu => DUNG.
### 2.2 Diem noi (D2) + kiem lien tuc - BAT BUOC truoc moi train dung >= 2 nguon (script rt_splice_check.py; Kaggle neu file > 1 GB)
- Quy tac chung: DEV lay ts < S, Vision lay ts >= S, voi S = S0 (feat_v2), S3 (p15 / Tool1 / nhan / OI / pool o T2). Khong dung "mep file".
- K1 (ts): sau ghep, theo tung nguon: ts tang (gate) hoac (ts,sym) duy nhat (Tool1/nhan/OI/ledger/feat). Trung (ts,sym) => DUNG.
- K2 (ho): luoi deu (gate 1', Tool1/nhan/pool 15', feat 1 h, OI theo nguon). Bao cao so moc thieu theo thang tung phia + quanh S
  (+-2 ngay). Gate: moi ngay Q3 Vision 1 440 phut (HO4_P1 S4: q3 132 480 = 92 x 1 440). Neu DEV ket thuc truoc S - 1 buoc luoi hoac Vision
  bat dau sau S => "HO" => DUNG, bao MASTER (khong tu lap).
- K3 (chong lan): neu ca hai nguon co dong trong [S - 30 ngay, S + 30 ngay) hoac 2026H1 (p15: DEV store vs gate.csv.gz q1/q2; Tool1
  DEV 2026 vs Vision q1/q2; nhan; feat_v2 neu Vision co lead-in): bang lech DEV-vs-Vision MO TA theo cot: % o |d| <= 1e-6 (gate/feat),
  1 buoc luong tu (Tool1), % dong trung du; so voi HO4_P1 P3-DEV (gate 61,2 %, Tool1 strict 56-57 %, nhan 96,5 %, feat_v2 61,5 %). Khong luat.
- K4 (dinh dang): Vision file doc duoc bang DUNG reader DEV (tool1_col.read_tool1, funding_label_pb.read_label, pd.read_csv gate) va cung
  ten/thu tu cot. Khac => DUNG.
- Lech mapper (HO4_P1 ADD7): gate Vision Q3 lech tu ~2026-07-09 (16/41 cot, 99,2 % phut tu 07-10; nhan 52 % phut) do 8 id mapper dung
  chung. T2 dung ban nao: xem muc 15 (P7) - mac dinh A = ho4p1-x26-q3 gate.csv.gz (= du lieu HO5/Lane N dung).
### 2.3 Dung tung tap
- p15 T1 (cut20260701): DATA = gate_dataset_full.csv (DEV, khong ghep). T2 (cut20261001): DATA = rt_gate_t2.csv.gz = DEV ts < S3 + Vision
  Q3 [S3, S4) (cung 33 cot + label_oldbasket, cung thu tu cot DEV). Ghi md5.
- net015 T1: T1_DIR = 7 file DEV features_* 2021..20260701 (symlink) + file Vision features_20260701_to_20261001 (chi de OOS >= S3 khong
  rong; truoc khi dung: kiem max ts file DEV 2026Q2 < S3 <= min ts file Vision; neu chong lan => DUNG, KHONG tu cat). LB_DIR = DEV.
  OI_FILE = DEV. T2: T1_DIR/LB_DIR them Vision Q3 + Q4 (gs-x26-q4 features_20261001_to_20270101, CHI de OOS); OI_FILE = rt_oi_t2.bin
  (DEV ts < S3 + Vision ts >= S3, cung dtype [ts >i8, sym >i2, oi >f4 x5], kiem dtype/symbol_map giong).
- S1 ledger (Kaggle kernel rt-ledger, chay x1_ledger.py KHONG sua, tao symlink cac duong /home/ubuntu/... toi /kaggle/input):
  L-a cand_rt26: X1_T1=2026-10-01, X1_CUTS = 16 cut DEV (nhu run_x1.sh), X1_LBGLOB='202[1-6]', X1_LB_DIR = nhan DEV + Vision Q3;
      wfo_gate_pred.csv = DEV (< S3) noi them pred p15 T1 tren gate Vision Q3 (>= S3, cot timestamp,predReturn15M).
  L-b cand_rt26q4 (chi cho T2): nhu L-a + nhan gs-x26-q4 + pred p15 T2 tren gate gs-x26-q4 (>= S4) => co dong Q4 lam OOS cho S1 T2.
  Cong ledger G-L: (i) cac dong ts < S0 - 72 h cua cand_rt26 == ~/ledger/cand_dev_x1.parquet (sha256 41fb8269..., md5 f0b2ef2e) sau sort
  (ts,sym): pandas equals moi cot chung; (ii) (ts,sym) duy nhat; (iii) bao cao so dong / tick theo quy 2026. (i) FAIL => DUNG.
- S1 feat: rt_feat_t.parquet = keep9 DEV (ts < S0) + feat_v2_26 Vision ho4p1-chain-y26 (ts >= S0) [+ gs-chain-q4 cho ts >= S4 khi T2];
  cot = ts, sym, 9 KEEP; K1-K4 nhu tren.
- X1_PRED (ref cho cong noi bo, de script khong crash): rt_s1_ref_<cut>.parquet = (ts, sym, score = -pred) cua model S1 LIVE
  s1a2x1_cut20251231.json (sha256 af706dc6...) tren cac dong OOS cua ledger. Cong noi bo = "moi vs cu" (MO TA nhu RESULT_S1REFRESH muc 4).
### 2.4 Du lieu 2026-10-01 -> nay (U3, kiem mo ta D7)
- Da co (artefact GST, PREREG_PARITY_V12_DRY ADD3-7): gs-x26-q4 (exporter Vision, bien the "nt" = loai danh sach tradfi, jar khac, ngay
  2026-10-28 lap bang REST fapi klines), gs-oi-c, gs-chain-q4 (pred.bin, bins, feat_v2 Q4, market.bin), sim-gs-x14-s42 (k24, chay toi
  10-31 de lay gate seed). Pham vi [S4, S5) = 2026-10-01 -> 2026-10-31 (+07).
- Thieu cho sim D7: funding fee sau 2026-10-01 (snapshot v3 het tai 2026-10-01 00:00 UTC) -> crawl bo sung bang DUNG cong cu ADD3 C1
  (fcrawl FundingCrawlerFile, cong chong lan 2025 lap lai) toi S5; ticker Q4 (xac nhan nguon ticker cua sim-gs-x14-s42 + gst-kline-1028).
- "Toi nay" (> 2026-10-31): can export Vision moi (exporter ho4p1 ~1,5-2,5 h/kernel + OI ~1 h + chain ~1-2 h + REST cho ngay Vision thieu),
  ~0,5-1 ngay lich. Mac dinh prereg: D7 = [S4, S5); mo rong => MASTER (muc 15 P8).

## 3. Cutoff + mep + purge (D3) - assert cu the (ghi vao manifest tung model)
| tang | model | tham so | assert train (ms UTC) | OOS (+07) |
|---|---|---|---|---|
| T1 kiem chung cut20260701 | p15 | CUTOFF=20260701, GATE_PURGE_MS=26100000 | max(ts) < 1782837900000 (2026-06-30 16:45 UTC) | Q3 = [S3, S4) |
| T1 | S1 | X1_CUT=20260701 | max(ts) < S3 - 72 h = 1782579600000 (2026-06-27 17:00 UTC) | Q3 |
| T1 | net015 | --fold 20260701 (idx 22) | max(ts) < 1782579600000 | Q3 |
| T2 san xuat cut20261001 | p15 | CUTOFF=20261001, GATE_PURGE_MS=26100000 | max(ts) < 1790786700000 (2026-09-30 16:45 UTC) | Q4 |
| T2 | S1 | X1_CUT=20261001 | max(ts) < S4 - 72 h = 1790528400000 (2026-09-27 17:00 UTC) | Q4 |
| T2 | net015 | --fold 20261001 (idx 23) | max(ts) < 1790528400000 | Q4 |
- S3 = 1782838800000, S4 = 1790787600000 (khop hang so run_ho5: A2, END). Moi wrapper assert them: so dong train >= so dong cua model
  cut ngay truoc (p15 b68563fe: 2 889 623; S1 cut20251231: 6 911 775; net015 cut20251231: 39 354 754) VA khong co dong ts >= cutoff +07.
- p15 cut20260701 cu (md5 b68563fe, mep UTC, co 1 phut cua Q3 +07) CHI dung cho cong 3a, khong dung cho T1 (D3).

## 4. Cong tai lap (3a) - chay TRUOC moi train moi; mot cong FAIL => DUNG
- P15-A (cung): train_gate_fold.py, DATA=gate_dataset_full.csv (a1c78e2f), CUTOFF=20260701, GATE_PURGE_MS=900000, xgb-env
  => md5 ONNX == b68563febe2a5b7e1bc4505340dfb841 (model_cut20260701, manifest 10-02, train 2 889 623 dong). Neu khac byte: PASS co dieu kien
  khi so cay/node bang nhau VA ORT(ONNX moi) vs ORT(b68563fe) max|d| <= 1e-6 tren >= 20 000 dong DEV ts < S0 (mau rng 20261121); nguoc lai
  FAIL. (b68563fe sinh tu ~/claudedata/gate_dataset_full.csv.gz - file nay DA MAT; cung so dong 2 889 623.)
- P15-B (da biet truoc - KHONG doi md5 8ec99757): HO5 ADD2 B2 + w3/ho5/p2/p2_fold20.json da do: retrain fold_20 (CUTOFF=20260401, purge 0)
  ra md5 24e99ef88d90cdb746b6738aca75b1a2 != 8ec99757 (nguong tach lech <= 5,3e-7). Cong: retrain bang wrapper => md5 == 24e99ef8 (tat dinh
  moi truong) VA ORT(fold_20 8ec99757) vs booster retrain max|d| <= 1e-6 tren >= 20 000 dong DEV ts < S0 (HO5 do 1,96e-8 / 1 000 dong).
- S1-A: X1_CUT=20251001, X1_LNAME=cand_dev_x1 (Oracle, sha256 41fb8269...), X1_FEAT=feat_v2_x1_keep9.parquet (Kaggle s1-featv2-x1-20260919),
  X1_PRED mac dinh ~/ledger/pred_s1a2x1.parquet (sha256 2618fe1a...) => sha256 JSON == cc0924f1e26f9fcc199e33ef161916e293f48f4b4a0b3f8ca14ade0127997308
  (RESULT_S1REFRESH.md:16) VA score_json spearman = 1, max|d| <= 1e-6 (manifest). Khac => FAIL. (score_onnx 2,62e-6 la ky vong, khong tinh.)
- S1-L (ledger): cong G-L muc 2.3 (dong ts < S0 - 72 h trung cand_dev_x1).
- NET-A (predict-faithful, THAY ban nhap: booster goc predwf_G015/model_f15_4h.json DA MAT): ONNX g015x26_f15_cut20251001.onnx (trong
  dataset ho4p1-code; ghi md5 + sha256, ky vong sha256 7921ceaf24... theo AGENT_RUNBOOK muc 3) predict OOS 2025Q4 tu Tool1 + OI DEV (duong
  memory-light giong g015_net_train) -> so predict_wf_20251001.bin goc (Kaggle predwf-g015x26-gate): khoa (ts,sym) trung 100 %, spearman
  >= 0,999999, max|d| <= 1e-5. Khac => FAIL.
- NET-B (retrain, do thoi gian D4): g015_net_train.py --fold 20251001 --device cpu (Kaggle CPU 4 core) => so predict_wf_20251001.bin moi vs
  goc: khoa trung 100 %, spearman >= 0,98 (nguong FAIL cu cua PREREG_NET015_CUT20251231 :19-24; ban goc sinh tren GPU). Them: chay 2 lan CPU
  doc lap => sha256 model_f18_4h.json bang nhau (tat dinh). Ghi phut train (log "DONE x phut"). < 0,98 hoac 2 lan khac nhau => FAIL, DUNG,
  bao MASTER (KHONG tu chuyen GPU). Thoi gian > 9 h hoac kernel chet 12 h => D4 nhanh GPU: lam lai NET-B tren GPU (band >= 0,98) roi moi
  model net015 train 2 lan GPU doc lap, spearman OOS >= 0,98, dung lan 1.
- Xu ly khac byte chung: chi cac truong hop ghi o tren; moi khac biet khac => FAIL.

## 5. Kiem toan ven dataset / model / ONNX (3b-3d) - moi model, moi tang
- 3b dataset: so dong, ts min/max, K1-K4 (muc 2.2), NaN/inf: gate 33 cot + nhan = 0 o (HO4_P1 S4 NaN 0); Tool1/OI/feat: ty le NaN theo cot
  khong tang qua 2 x ty le cua DEV 2025 cung cot (mo ta neu thap hon; vuot => DUNG); md5 moi file dau vao vao manifest; assert muc 3.
- 3c model moi: pred tren mau >= 100 000 dong (OOS cua chinh no): NaN/inf 0; p15: phan vi p1/p50/p99 vs model cu tren CUNG dong (mo ta);
  net015: so ban ghi OOS = filesize/26, p0 trong (0,1), pos train trong [0,17; 0,21] (DEV 0,189); S1: mean/std score vs cu (mo ta, nhu
  RESULT_S1REFRESH muc 3). Bat ky NaN/inf hoac vi pham khoang cung => FAIL.
- 3d ONNX vs booster (cung dong, cung dtype float32): p15 max|d| <= 1e-6 tren >= 20 000 dong (DEPLOY242_READY :73); S1 top-8 trung 100 %
  tick (>= 5 000 tick co >= 8 ung vien) va spearman >= 0,99999; net015 spearman >= 0,9999999, max|d| <= 1e-5, top-8/50/200 100 % tren
  >= 300 000 dong (RESULT_NET015 muc 0). FAIL => DUNG.

## 6. Holdout tang kiem chung: sim Lane N vs Lane L tren 2026Q3
### 6.1 Cau hinh (DUNG r1-a3 nhu HO5 luot 5 - khong doi gi ngoai 3 model o Q3)
- Kernel sim = ban sao ~/claude_master/w3/ho5/ho5_sim.py (md5 luc viet 0f9d5826; ghi md5 ban HO5 THUC SU da chay luot 5) chi doi:
  tag "rt-n-l26-<seed>" va dataset du lieu 2026 "rt-n-data26" thay "ho5-a3-data26". Profile r4_kg0_k16_f015_g155 (PROFILE hash
  0738cca9159a78a5), jar sim-jar-tsx sha256 cc0f9d11..., overrides r1-a3 (B.OV_BASE + X14: SIM_LOSER_TS_EXT_HOURS=336, DAYS = tsx flags
  2021-2025 + ho_flags 2026), bins A3 DEV sha concat 0d6e3781, funding.bin DEV md5 50c4bc8d, mapper snapshot 5c436e65 + overlay 6143fa75,
  funding snapshot v3 gz fb024c40 + overlay 207e7c60, ticker tk26 (ho4p1-tk26), SIM_END_DATE 20261001, von 35 000, chay lien tuc tu 2021-07-01
  (khoi dong gate = lich su, nhu HO4/HO5; khong warm-up rieng). Diff run.py Lane N vs run.py Lane L cung seed phai CHI o tag + ten dataset 2026.
- 8 tag seed: a1, s123, s13, s2024, s21, s7, s777, s99 (pred p15 DEV <= 2025 theo seed: A1 = pred goc 5dd6bb4c, con lai gate-sb-<seed>).
### 6.2 "Seed" cua Lane N - CHOT: 1 model moi (seed train 42 theo recipe) + 8 lich su
- Lane N p15 tren 2026: [S0, S3) = pred26 cua fold_20 (byte giong Lane L); [S3, S4) = pred cua p15 T1 moi (1 model) - cung 1 gia tri cho ca
  8 seed. Doan <= 2025 = pred DEV cua tung seed (nhu Lane L). bins 2026: file 20260101, 20260401 = byte giong Lane L (sha so voi ho5-a3-data26);
  file 20260701 = a3lib.assign voi S1 T1 + net015 RAW Q3 cua net015 T1 (bins Lane L Q3 dung S1/net015 cut20251231).
- Ly do: (1) Lane L (HO5 ADD1 A3) la 1 p15 dong bang, 8 seed chi khac lich su <= 2025 => muon so cap seed (D5) thi Lane N phai cung cau
  truc, chi khac DUNG 3 model o Q3 => d(seed) do hieu ung model, khong lan nhieu re-seed; (2) D10 "seed train giu nhu recipe" + model san
  xuat se la 1 model seed 42 - danh gia dung thu se deploy; (3) HO4 dung 8 model p15 seed (gate-sb) vi do CAU HINH duoi bat dinh model, khac
  cau hoi nay; tron nhieu re-seed vao rieng Lane N se bat doi xung voi Lane L. Han che: 8 seed KHONG doc lap (cung model, cung thi truong
  Q3) => CI paired-t chi phan anh do nhay duong di, KHONG phan anh bat dinh mau thi truong (muc 13).
### 6.3 Dung du lieu Lane N (thu tu bat buoc)
- C-N1 chain: fork ho5_chainops.py/ho5_chain.py (mode ho5) chi doi: ten file model lay tu cfg (run_ho5 dang khoa ten
  g015x26_f15_cut20251231.onnx :482) + tag rt-n-chain26. Cong P-N1 (truoc khi dung model moi): chay fork voi 2 model CU
  (8ec99757, e65e683b) => md5 pred_2026.bin + 3 file net015 RAW TRUNG MANIFEST cua ho5-a3-chain26 (HO5 luot 5). Khong trung => DUNG.
  Roi chay fork voi p15 T1 + net015 T1 (kiem md5/sha trong cfg) -> pred26_N, net015 RAW_N.
- C-N2 a3: fork a3/a3_26.py: pred_2026_N = pred Lane L (ts < S3) + pred26_N (ts >= S3); bins 20260101/20260401 = copy Lane L (sha bang);
  bins 20260701 = a3lib.assign(S1 T1 JSON, net015 RAW_N fold 20260701, feat_v2_26, A1 exchangeInfo 20261027, bo id loai nhu run_y26).
  Cong P-N2: fork voi S1 cut20251231 + RAW Lane L => bins 20260701 sha == bins Lane L. Khong trung => DUNG. Upload dataset rt-n-data26.
- C-N3 sim: 8 kernel CPU (<= 5 song song tong tai khoan), ~45-65 phut/kernel, tai CHON LOC.
### 6.4 Lane L = HO5 luot 5 (khong chay lai)
- Lay printDone + log Update cua 8 kernel ho5-a3-l26-<seed> (da qua kiem chung SCORE_DEFS_L5 "Kiem chung truoc khi doc so"). HO5 Lane L
  khong co (R5) hoac thieu seed => H-NI KHONG danh gia duoc => DUNG o buoc 6, bao MASTER.

## 7. Tieu chi nhan (ghi truoc, ap nguyen van)
Dinh nghia (= SCORE_DEFS_L5, cung score_l5.py; chi them cua so Q3 = 2026-07-01 00:00 -> 2026-09-30 23:59 +07):
SigmaPnL_Q3(s) = tong pnl cac dong printDone co end trong Q3; E_start_Q3(s) = E cua dong Update ngay 2026-07-01 (07:00 +07, b + unP) cua
CHINH run do; maxDD_Q3 = min E/peak - 1 tren chuoi E ngay [E_start .. E_end] (peak dat lai 07-01); ROI_Q3(s) = SigmaPnL_Q3(s) / E_start_Q3(s) (D5).
- Kiem chung TRUOC khi doc so Lane N (fail => khong bao cao seed do; < 8 seed hop le => DUNG): moi muc kiem cua SCORE_DEFS_L5 + (i) printDone
  Lane N: moi dong co end < 2026-07-01 00:00 +07 TRUNG nguyen dong voi Lane L cung seed, cung so dong; (ii) dong Update ngay <= 20260630 trung
  Lane L; (iii) result.json ghi md5 pred_2026_N, sha bins 3 file, sha 3 model.
- H-E0 (Lane N, Q3): mean_s SigmaPnL_Q3 > 0 VA #{s: SigmaPnL_Q3(s) > 0} >= 6/8 => PASS.
- H-NI: d(s) = 100 x (ROI_Q3,N(s) - ROI_Q3,L(s)) (diem %), s = 8 seed; LB = mean(d) - 2,3646 x sd(d, ddof=1) / sqrt(8) (t 0,975 df 7).
  PASS neu LB >= -1,0. (sd = 0 => LB = mean.)
- H-DD (canh bao, khong chan): mean_s maxDD_Q3,N < -22,72 % => CANH BAO, trinh owner (so MTM ngay 07:00, nong hon MTM phut - ghi chu).
- Mo ta (khong luat): bang 8 seed x {n, SigmaPnL, ROI, ROI MTM E_end/E_start - 1, maxDD, Sharpe, % ngay co lenh} cho N va L; E0b-kieu bootstrap
  tuan (10 000, rng 20261121) cho chuoi d trung binh 8 seed, CI80; so lenh trung (sym, start) N vs L trong Q3.
| H-E0 | H-NI | quyet dinh |
|---|---|---|
| PASS | PASS | sang muc 8 (T2). H-DD canh bao (neu co) ghi kem, trinh owner truoc shadow. |
| FAIL | bat ky | PILOT tiep tuc BI CHAN (R2 HO5). DUNG. Khong tune, khong doi cutoff/seed/tham so, khong chay lai. Bao cao ca 2 lane. |
| PASS | FAIL | nhu tren (model moi kem live qua bien). |
- D7 kiem SACH (mo ta, KHONG vao bang tren): xem muc 8.3.

## 8. Tang san xuat cut20261001 (chi khi muc 7 PASS)
- 8.1 Train 3 model voi DUNG recipe muc 1, du lieu muc 2.3 T2, assert muc 3, cong 3b-3d muc 5. KHONG chay lai cong 3a (da qua), KHONG
  danh gia lai bang Q3 (Q3 nam trong train). Thu tu: p15 T2 -> pred p15 T2 tren gate gs-x26-q4 (Q4, de pool S1 OOS) -> ledger L-b -> S1 T2;
  net015 T2 song song.
- 8.2 Cong rieng T2: assert so dong train T2 > T1 cung model; ty le dong 2 nguon (Vision / tong) ghi ro tung model.
- 8.3 D7 (mo ta, U3): cua so [S4, S5) (2026-10-01 -> 2026-10-31 +07, mac dinh; xem P8). Hai lane sim tiep noi (8 seed, cau hinh 6.1):
  (i) "N7" = Lane N keo dai (model T1 tren Q4); (ii) "P7" = Lane N toi S4 + model T2 tu S4. Dung du lieu Q4 gs-* (bien the nt) + funding
  crawl bo sung (2.4). ROI_D7(s) = SigmaPnL_D7 / E_start_D7 (dinh nghia nhu muc 7 voi cua so D7). Neu mean_s ROI_D7 cua P7 < -3 % =>
  CANH BAO, trinh owner TRUOC khi shadow (khong tu dong chan). Khong lam duoc D7 (thieu du lieu/funding) => ghi "KHONG CO D7", trinh MASTER
  (khong chan shadow tru khi MASTER noi chan).

## 9. Parity + shadow song song 7 ngay (D6) - chi sau muc 8
- 9.1 Parity offline TRUOC shadow: p15 ORT(feat dump) vs Java p15_out (shadow, sau restart) max|d| <= 1e-6 (DEPLOY242_READY :74);
  S1 ONNX vs JSON top-8 100 %; net015 ONNX vs JSON spearman >= 0,9999999 / top-8 100 % tren feature 45 cot dump tu shadow.
- 9.2 Nap model vao shadow_c3 (Oracle, Redis RIENG 127.0.0.1:7301; TUYET DOI khong tro Redis 242). Bien cau hinh (chi ten):
  FILE_AI_PREDICTIONS (thu muc chua Model_Regressor_Return15M.onnx - p15 doi bang thu muc moi, khong ghi de file cu), S1_MODEL_ONNX,
  NET015_MODEL_ONNX; giu nguyen LIVE_GATE_ROLLING_MODE / _PCT / _DAYS, LIVE_PROFILE, SELECTOR_TIER1_NET015, TRAIL_HINGE_NET015, TS_PRED_GAP,
  SIM_GATE_DYN_SCALE nhu ban live. Trang thai 2026-11-21: shadow-c3.service = failed (KHONG chay) va cau hinh shadow LECH live (S1
  cut20251001, net015 cut20251001) => truoc shadow phai dung lai shadow = jar live (md5 01cfbb43 hotfix-ks) + env live (owner cung cap ban sao
  KHONG chua key) + 3 model moi; so voi live 242 (model cu). Phuong an A/B 2 shadow: xem P9.
- 9.3 Chi so (moi ngay): log nap model (duong dan + md5 3 file) 1 lan/restart; so exception/ERROR tren duong suy luan (p15, S1, net015) = 0;
  % phut co p15 / % tick co score S1 va net015 cho moi ung vien = 100 % thoi gian shadow UP; so phut gate PASS shadow va live; mo ta: p15
  p50/p99 moi vs cu, tap (phut, symbol) gate PASS giao nhau, top-8 S1 trung moi tick, symbolPred p10/50/90 muc lenh.
- 9.4 "Khong loi lech code" = (a) 3 md5 dung; (b) 0 exception suy luan; (c) parity 9.1 lap lai tren dump ngay 7 (Java == ORT offline cua
  chinh feature shadow); (d) 100 % phu (9.3). Khong co tieu chi hieu nang trong shadow.
- 9.5 Thoi luong: 7 ngay VA >= 1 phut gate PASS o ca shadow lan live trong cua so; khong co => keo dai toi khi co, toi da 14 ngay, roi trinh
  owner. Moi tuan shadow = 1 tuan forward bi "nhin" (AGENT_RUNBOOK luat 8c) - ghi nhan, khong mo seal moi.

## 10. Goi doi model cho owner (D9 buoc 9) - SCRIPT MOT LENH, agent KHONG deploy
Mau: ~/claude_master/w3/c3_hotfix/ops/c3live/golive_swap_jar.sh (md5 9ac84750) + golive_lib.sh. Script moi golive_swap_models.sh, yeu cau:
- R1 Mot lenh, chay tren Oracle: `DRY=1 bash golive_swap_models.sh` (chi kiem, 242 CHI DOC, in ke hoach) | `bash ...` (go YES trong khung
  gio cho phep) | `MODE=rollback bash ...` (quay ve 3 model cu, cung quy trinh chieu nguoc). Ma thoat 0 XONG/DA XONG/DRY PASS, 1 TU CHOI hoac
  da rollback DAT, 2 KHAN (giu KILL_SWITCH + Telegram).
- R2 Ghim md5 6 file (3 moi T2 + 3 cu dang live: p15 8ec99757, S1 511add62, net015 e65e683b) + md5 jar dang chay; kiem m1 (HEAD thu muc ops co
  trong A1_APPROVED_OPS.commit, khong co sua chua commit) + gl_manifest_check nhu mau.
- R3 Kiem truoc (sai => TU CHOI, khong doi gi): 1 process bot; jar dang chay = jar ghim; adapter/profile live; latch NONE; KHONG co
  run/KILL_SWITCH; KHONG PAUSE watchdog; khong canary/soak; RAM/dia 242; 3 model nguon tren Oracle dung md5; 3 model dang nap tren 242 = 3 cu
  (hoac = 3 moi => "DA XONG", exit 0).
- R4 Chep 3 file moi len 242 vao duong MOI (ten kem _rt_<TS>, quyen nhu file cu, kiem md5 tren 242) TRUOC khi dung bot.
- R5 Khong dung toi lenh dang mo: KILL_SWITCH token rieng (khong ghi de cua nguoi khac) -> cho het lenh DANG DAT/dang gui (khong co request
  cho Redis/queue va khong co order PENDING, cho toi da N giay, qua => TU CHOI + go KILL_SWITCH cua minh) -> PAUSE watchdog (token, tu go sau
  WD_PAUSE_MAX_S) -> stop -> backup (.bak_<NM>_<TS> + .md5 cho file p15 + conf/env.sh) -> doi FILE_AI_PREDICTIONS/S1_MODEL_ONNX/NET015_MODEL_ONNX
  (sed tren ban sao, diff dung 3 dong, roi mv) -> start. Vi the dang mo KHONG bi dong.
- R6 Hau kiem: 1 process; log JVM moi co dong nap 3 model voi duong dan/md5 MOI; p15_out phut dau trong khoang [p1, p99] cua phan phoi model
  moi tren DEV (ghi truoc trong manifest); 0 exception suy luan 10 phut; latch NONE; LEGACY khong doi; stream + recon OK; KILL_SWITCH cua minh
  con -> go -> cho PUSH ON -> go PAUSE. Truot sau khi dung bot => ROLLBACK TU DONG ve 3 model cu (backup) + hau kiem lai.
- R7 Idempotent + marker pha + bo qua SIGHUP (sau YES bo qua INT/TERM) nhu mau; log day du vao LOGDIR.
- R8 Gate rolling 90 ngay: KHONG reseed khi doi model (mac dinh, giong chuyen fold WFO trong sim - P10).
- R9 Audit DOC LAP (agent A1 khac, nhu A1_* truoc day) truoc khi dua owner: doc code + chay DRY tren fake242 (neu harness con) + test MODE=rollback;
  bao cao v12/A1_RETRAIN_SWAP.md; MASTER duyet + them HEAD vao A1_APPROVED_OPS.commit. Owner tu chay; agent khong ssh 242.

## 11. Lich dinh ky hang quy (mo ta, KHONG thuoc lan chay nay)
- Cutoff = 00:00 +07 ngay dau quy; bat dau ~ngay 5 (nhan 72 h + export Vision quy truoc xong); DEV pipeline da chet (Aerospike Oracle
  market_data_object / funding_data dung 07-08/2026) => moi quy moi chi con nguon Vision (exporter ho4p1 + OI + funding crawl) => ty le Vision
  trong tap train tang dan; can do drift.
- Buoc: export Vision quy (3 kernel) -> ghep (2.2) -> train 3 model (muc 1) -> cong 3b-3d -> D7-kieu mo ta tren quy moi nhat (khong luat) ->
  shadow 7 ngay -> script doi model (muc 10) -> deploy ~ngay 15-20. Tuoi model khi trade <= ~3,5 thang.
- Can prereg rieng cho luat nhan dinh ky (khong co holdout sach nua; chi forward + micro/pilot). Tu dong hoa (pipeline CE) = owner duyet.

## 12. So trial / do do
- Moi tang: DUNG 1 model / loai (1 lan train, seed 42). Khong chon giua nhieu model, khong chon cutoff, khong chon nguon du lieu sau khi
  thay so (nguon chot o muc 2 truoc khi chay; diem mo duy nhat P7/P8 phai MASTER chot TRUOC buoc 3).
- Lane N la 1 so sanh; ket qua am van bao cao (null co thong tin). Khong co nhanh "neu FAIL thi thu cut khac / seed khac / bo bot du lieu
  Vision". FAIL => dung, prereg moi neu muon lam lai.
- Equity khong phai tieu chi tim kiem o day: H-E0/H-NI la cong VAN HANH cho 1 ung vien duy nhat (khong co phep chon nhieu lan) =>
  khong can hieu chinh so trial.

## 13. Gioi han da biet + rui ro
1. Hai nguon du lieu: Vision lech DEV o muc thanh phan (gate 61 %, Tool1 56-57 %, nhan 96,5 %, feat_v2 61,5 %, rk_* ~0-6 %; net015 13,9 % o,
   HO4_P1:6). T1: chi feat_v2 2026H1 (S1) la Vision trong train; T2: ca 3 model them Q3 Vision (~5 % dong p15/net015, ~ nhieu hon cho S1).
   Model moi hoc tren dinh nghia feature tron => co the KEM model cu du cung recipe.
2. Q3 da bi nhin qua HO4 (k24, E0 FAIL Q3 - DIAG_NOTRADE_1117_B) va Lane L HO5 se duoc nhin truoc Lane N; chap nhan (D7), luat chot truoc.
3. Mot quy, 8 seed khong doc lap: CI paired-t hep gia tao; PASS H-NI khong chung minh khong kem o tuong lai; FAIL co the do 1 quy bat loi.
4. net015 GPU khong tat dinh (retrain cung seed spearman 0,991); CPU tat dinh nhung lech GPU goc => NET-B co the FAIL du khong co loi.
5. Gate Vision Q3 lech tu 07-09 do mapper 8 id dung chung (ADD7) - vao train T2 p15 (va nhan 52 % phut).
6. Funding fee snapshot het 2026-10-01 => D7 can crawl bo sung; ngay 2026-10-28 Vision thieu (GST lap bang REST).
7. Gate live = rolling ratio 90 ngay => sau doi model, 90 ngay dau nguong tron p15 cu/moi (sim WFO cung vay o moi moc quy).
8. Oracle dia 17 G trong (2026-11-21 sau HO5), nguong 15 G; HO5 dang chay song song. Kaggle CPU chia voi HO5 (<= 5).
9. Shadow hien KHONG chay va lech cau hinh live; so voi live can kenh doc log 242 (owner/MASTER).
10. Booster goc net015 (model_f15) + predwf_G015/ + wfo_gate_pred.csv + oi_percoin_full.bin + feat_v2_x1 da bi xoa khoi Oracle => phu thuoc
    dataset Kaggle (ghim md5 trong kernel; version thay doi => DUNG).
11. fold_20 khong tai lap byte (24e99ef8) - da biet; "file train goc" wfo_feature_store.csv da mat.
12. x1_s1_save_model crash voi OOS rong => S1 phu thuoc dong Q3/Q4 trong ledger (Q4 tu bien the nt gs-*).
13. Model moi co the te hon model cu vi it du lieu Vision / regime 2026; T2 KHONG co cong hieu nang (chi D7 mo ta 1 thang).
14. purge 72 h < holding 168 h (AGENT_RUNBOOK muc 5) - giu nguyen recipe.

## 14. Ke hoach chay (D9) - noi chay, lenh/script, thoi gian uoc, dia, diem dung MASTER
| buoc | viec | noi | script (viet o luot chay tru khi ghi "co san") | uoc | dia Oracle |
|---|---|---|---|---|---|
| 1 | MASTER commit prereg (+ chot P1-P15) | - | - | - | 0 |
| 2a | P15-A, P15-B | Oracle xgb-env, flock | rt_p15_train.py (wrapper runpy) | 15 ph | < 50 MB |
| 2b | S1-A | Oracle python3 | tai keep9 (286 MB) ; x1_s1_save_model.py (co san) | 20 ph | 0,3 G |
| 2c | NET-A | Kaggle CPU | kernel rt-net-a (ONNX cut20251001 tu ho4p1-code; Tool1/OI DEV) | 45 ph | 0 |
| 2d | NET-B x2 (do thoi gian D4) | Kaggle CPU x2 | kernel rt-net-b1/b2 (g015_net_train + datasets DEV) | 1-4 h (chua do) | 0 |
| STOP-1 | MASTER xem bao cao cong 3a | | | | |
| 3a | splice check K1-K4 + bang lech K3 | Kaggle CPU | rt_splice_check.py | 1 h | 0 |
| 3b | ledger L-a phan DEV + cong G-L | Kaggle CPU | kernel rt-ledger (x1_ledger.py co san + symlink) | 1 h | 0,25 G (tai ve) |
| 4a | p15 T1 | Oracle | rt_p15_train.py | 5 ph | < 50 MB |
| 4b | net015 T1 + ONNX + 3c/3d | Kaggle CPU (hoac GPU theo D4) | rt-net-t1 + rt_net015_onnx.py | 1-4 h | 0 |
| 4c | P-N1 (chain fork voi model cu) roi chain N | Kaggle CPU | fork ho5_chainops/ho5_chain | 2 x 1-1,5 h | < 0,5 G |
| 4d | ledger L-a them Q3 (pool tu pred26_N) | Kaggle CPU | rt-ledger | 1 h | 0,25 G |
| 4e | S1 T1 (+ ref X1_PRED) + 3c/3d | Oracle python3 | rt_feat_splice.py, rt_s1_ref.py, x1_s1_save_model.py | 30 ph | 0,8 G |
| 4f | P-N2 + a3 N + dataset rt-n-data26 | Oracle flock | fork a3_26.py | 30 ph | 0,6 G |
| STOP-2 | MASTER xem cong 3b-3d T1 | | | | |
| 5 | Lane N 8 sim | Kaggle CPU (<= 5) | fork ho5_sim.py | 2-3 h wall | < 0,2 G |
| 6 | cham H-E0/H-NI/H-DD | Oracle | score_l5.py (co san) + rt_score_n.py | 1 h | 0 |
| STOP-3 | MASTER: PASS -> 7 ; FAIL -> dung | | | | |
| 7a | T2: p15 (ghep gate DEV+Vision Q3 .gz), net015, S1 (ledger L-b) + 3b-3d | Oracle + Kaggle | nhu tren | 0,5 ngay | 1,5 G tam (xoa sau) |
| 7b | D7: funding crawl Q4 + 16 sim (N7, P7) | Oracle + Kaggle | fcrawl (co san) + fork ho5_sim | 0,5 ngay | < 0,3 G |
| STOP-4 | MASTER/owner xem D7 (canh bao -3 %) | | | | |
| 8 | shadow 7-14 ngay + parity | Oracle shadow_c3 | dung lai shadow theo 9.2 | 7-14 ngay | log 150 MB |
| 9 | golive_swap_models.sh + audit A1 | Oracle | moi | 1 ngay (song song 8) | 0 |
Tong: ~2,5-3,5 ngay lich toi model T2 qua cong + 7-14 ngay shadow => doi model som nhat ~2026-12-03.

## 15. Diem lech so voi D1-D11 / ban nhap + diem MASTER can chot (khuyen nghi in dam = mac dinh neu MASTER khong noi khac)
- P1 (lech ban nhap) Cong p15 fold_20 "md5 == 8ec99757" KHONG kha thi (HO5 ADD2 B2 da do 24e99ef8). Thay bang P15-A (b68563fe, cung) + P15-B
  (tai lap 24e99ef8 + parity 1e-6). **Chap nhan.**
- P2 D3 cai dat bang GATE_PURGE_MS=26100000 (7h15') thay vi sua code => manifest ghi ro. **Chap nhan.**
- P3 S1 can OOS khong rong + ref giao OOS (bay crash). T1: ledger co Q3 (pool = pred p15 T1 tren gate Vision Q3); T2: ledger co Q4 (gs-x26-q4,
  bien the nt) chi lam OOS. X1_PRED = diem model S1 live. Cong noi bo = mo ta. **Chap nhan.** (Phuong an khac: wrapper bat loi sau khi da luu
  JSON/ONNX - khong khuyen nghi.)
- P4 (lech chu D2) Pool + nhan S1 2026H1 lay tu DEV (wfo_gate_pred.csv fold_19/fold_20 + funding-label-15m) vi DEV CO SAN toi 2026-06-30;
  D2 noi "2026 tu HO4-P1". Chi feat_v2 2026 dung Vision. Q3 pool = p15 T1 (dung nghia WFO), khong dung pool HO4-P1 (p15 cut20260101).
  **Khuyen nghi DEV cho H1** (dung chu "DEV toi het du lieu DEV co san").
- P5 NET-A doi tu "booster goc model_f15" (da mat) sang "ONNX cut20251001 vs bins goc", nguong 1e-5. **Chap nhan.**
- P6 NET-B tren CPU so voi ban goc GPU (band >= 0,98) + 2 lan CPU trung sha. Neu < 0,98 => FAIL theo D10, MASTER quyet (khong tu doi GPU).
- P7 Gate Q3 cho p15 T2: A = ho4p1-x26-q3 (loi mapper tu 07-09, = du lieu HO5/Lane N/live truoc sua) | B = ho4p1-dupfx gateB (ban sua;
  can xac minh cfg_ho4p1-dupfx.json). **Khuyen nghi A** (nhat quan nguon, MASTER da chap nhan sai lech o ADD7); ghi gioi han.
- P8 D7 cua so: [10-01, 10-31] bang gs-* (bien the nt, jar khac) + funding crawl - **khuyen nghi**; hoac export moi toi ~11-19 (+0,5-1 ngay).
- P9 Shadow: (a) 1 shadow model moi vs live 242 (can kenh doc log 242) | (b) **2 shadow tren Oracle A = model cu, B = model moi, cung jar/env
  live, Redis rieng tung cai (RAM 2 x ~3,2 G, Oracle con ~19 G)** + doi chieu live 242 neu co kenh. Khuyen nghi (b).
- P10 Khong reseed gate rolling khi doi model (giong sim WFO). Phuong an khac: reseed tu sim P7 - khong khuyen nghi (doi them 1 thanh phan).
- P11 H-DD dung MTM ngay 07:00 (SCORE_DEFS_L5), nguong -22,72 % (MTM phut DEV) - giu, ghi chu.
- P12 Lane L phu thuoc HO5 luot 5 hoan tat + qua kiem chung; neu khong => dung o buoc 6.
- P13 Script ONNX net015 moi (rt_net015_onnx.py) vi script cu khoa cung fold 15 + duong da mat. **Chap nhan.**
- P14 g015_net_train.py: them 2 cutoff o CUOI CUT_DATES (idx 22/23) - diff 1 dong, MASTER commit cung prereg hoac ngay sau (md5 moi ghi lai).
- P15 Fork cong cu HO5 (chain/a3/sim) cho Lane N co cong P-N1/P-N2 (tai lap byte Lane L) truoc khi dung model moi. **Chap nhan.**

## 16. MASTER duyet (2026-11-21) - muc nay THANG khi mau thuan voi cac muc tren
Ban nay = PREREG_RETRAIN_PILOT_FINAL.md cua agent thiet ke (sha256 2ed43e9e...) + muc 16. Can cu: RETRAIN_MASTER_DECISIONS_1121.md (D1-D11),
HOLDOUT_UNSEAL_2026_1121 (e9095a02, pham vi U2/U3). Chua train, chua doc du lieu 2026 cho muc dich retrain truoc commit nay.
(a) Chot P1-P15 = phuong an KHUYEN NGHI / "Chap nhan" cua muc 15: P1 cong P15-A/P15-B; P2 GATE_PURGE_MS=26100000; P3 S1 can OOS khong
    rong; P4 pool + nhan S1 2026H1 tu DEV, feat_v2 2026 tu Vision; P5 NET-A bang ONNX cut20251001; P6 NET-B CPU band >= 0,98, FAIL -> DUNG
    bao MASTER; P7 gate Q3 phuong an A (ho4p1-x26-q3; gioi han mapper 8 id tu 07-09 ghi ro); P8 D7 = 2026-10-01..10-31 bang gs-* + funding
    crawl; P9 shadow phuong an (b) NHUNG xem (c); P10 khong reseed gate rolling; P11 H-DD MTM ngay; P13 script ONNX net015 moi; P14 them
    2 cutoff vao CUT_DATES (diff 1 dong - agent ap, bao md5, MASTER commit TRUOC khi train net015 T1); P15 fork cong cu HO5 voi cong P-N1 / P-N2.
(b) Lane L da co (P12): docs/result/ho5_a3_2026/RESULT_HO5_A3_2026.md (sha256 fe61b0f9...; score_l5.json da2791fe). ROI_Q3 Lane L = 4,51 % o
    CA 8 seed (lenh 2026 trung nhau giua cac seed), maxDD_Q3 -1,48 %. He qua da biet truoc: sd(d) ~ 0 nen H-NI thuc chat la so diem:
    mean ROI_Q3 Lane N phai >= ~3,51 %. Cong thuc muc 7 GIU NGUYEN.
(c) AN TOAN shadow (buoc 8): KHONG BAO GIO chay tren Oracle jar co key that (jar live). Shadow chi duoc chay bang jar build STUB khong key
    (kiem bang jar_sec_check), LIVE_IS_SHADOW_HOST=true, adapter paper, Redis rieng. Thiet ke shadow cu the + script phai qua audit doc lap
    va MASTER duyet tai STOP-4 TRUOC khi khoi dong; neu khong dung duoc shadow an toan -> DUNG, MASTER quyet phuong an thay the (khong tu lam).
(d) Chan doan them cho Lane N (mo ta, khong luat): so phut gate PASS va so lenh theo THANG trong Q3 (N vs L) - theo doi rui ro gate lech
    hieu chuan khi doi p15 ma khong reseed (P10).
(e) Dia Oracle: nguong trong >= 15 GB; du lieu nang o Kaggle; file tam xoa ngay. May 242: agent KHONG dung toi; doi model = owner chay script
    mot lenh da qua audit (muc 10).
(f) Diem dung STOP-1..STOP-4 nhu muc 14: agent DUNG va bao MASTER tai moi diem.
