# A1_RETRAIN_ROOT_T1 - audit doc lap Tang 1 (PREREG_RETRAIN_ROOT 899f2fc8 / 6ae0720e4ddfaefb) + khao sat kha thi phan ra
Agent A1 (Opus), 2026-11-24 (+07). Doi tuong: RESULT_RETRAIN_ROOT_T1.md sha256 adf12bf8... (da xac nhan). Chi DEV ts < 2026-01-01; khong sim/Kaggle/mvn/242.
Code + output tai tinh: a1/ (a1_m1_recalc.py/.json, a1_retrain.py/.log/.json, a1_m5_m2.py/.json, a1_leak7h.py/.json). Job nang: 13:04-13:05 (flock + nice, 43 s).

## VERDICT
| phep do | verdict | nhan RUN | nhan A1 xac nhan |
|---|---|---|---|
| M1 (+M3) | PASS (tinh toan) / canh bao MAJOR ve dien giai (muc 4) | ANOMALOUS; khong co huong | ANOMALOUS theo dung luat ghi truoc - nhung YEU: chi R99995 dung vung; R9999 khong ben |
| M5 | PASS-WITH-MINOR | "lane P khong phan biet duoc voi nhieu doi-seed p15" | xac nhan, sat bien (hang 93,8 %) va phu thuoc 2022Q2 |
| M2 | PASS-WITH-MINOR | TYPICAL ve gate | xac nhan |

## A1. Tuan thu prereg
- Dinh nghia M1 (fold k cut 2021-04-01+3k UTC, expanding, recipe G0, WFO_k/LAG_k cung dong, R9999/R99995/Rmax/dp50/F, nguong hop le 0,99, >3 quy loai => INVALID,
  TYPICAL = ca hai ti so trong [min,max], sign >= 14/18) khop code m1_train_pred.py :116-188. Khong lech.
- Quyet dinh thuc thi: quy +07 ghi trong code (mtime 12:47:29) + RUN.progress step0 12:47:39 TRUOC M1 START; trung mep OOS pred.bin A1/G0 va trung cua so +07 cua rt_dcal.py
  (S3/S4 = 00:00 +07) => hop ly, khong chon sau khi thay so. Quantile numpy linear: khong ghi truoc nhung la mac dinh VA trung cach tinh 1,192/1,509 (rt_dcal.py :30-32
  np.quantile mac dinh) => hop ly. Doi method (lower/higher) khong anh huong nhan (xem M5 cho vi du; M1 R99995 lech max xa 1,509).
- M2: thiet ke ghi RUN.progress 12:54:18 truoc START 12:54:26. Errata lan 1: assert sha bins (m2_gate_replay.py :54-62) nam TRUOC moi log.info va moi tinh toan => dung
  truoc khi tinh so la nhat quan voi cau truc code; KHONG kiem duoc truc tiep vi m2.nohup lan 1 bi ghi de va sha code lan 1 (3fb32043) khong luu ban => MINOR (luu ban code/log
  cua lan chay bi dung khi co errata).
- M5: D5 qua score_l5 (import), loc + assert < 2026; dung prereg.

## A2. Du lieu
- M1: loc ts < 2026-01-01 UTC tung chunk khi doc + assert truoc khi dung (:62-81); log: doc 2 889 623, bo 260 183, nap 2 629 440, min 2021-01-01 00:00, max 2025-12-31 23:59 UTC;
  pred.bin A1 max 2025-12-31 23:59 UTC. 0 dong 2026 vao train/predict. Tai lap doc lap: cung so dong, max ts 2025-12-31 23:59.
- M5: printDone start/end < 2026, Update < 20260101 assert (lenh cuoi end 2025-11-28). M2: assert bins/market.bin/C ts < 2026 UTC. Chi DEV. OK.

## A3. Tai tinh doc lap (code rieng, khong import code RUN)
(a) M1 tu npy (quy +07 tinh bang offset 7h co dinh): 18/18 quy, sai lech tuyet doi max 4,7e-6 (lam tron tsv) cho R9999/R99995/F. min/med/max:
    R9999 0,8562/0,9723/1,1429; R99995 0,8577/0,9651/1,1268; F 0,4233/1,0582/1,5022; sign 7+/11-; |logF|>log1,5: 2. TRUNG RUN. Quy min/max: R9999 2021Q3/2022Q3, R99995 2021Q4/2022Q2,
    F 2021Q3/2025Q2 - deu kiem.
(b) Retrain doc lap fold 0,1,17,18 (V3FULL doc tu drv.py bang ast; tham so drv.retrain G0; cut UTC-15'): WFO/LAG cua 2021Q3 va 2025Q4 vs m1_{wfo,lag}.npy: pearson 1,0; max|d| = 0
    (bit-exact); R9999/R99995 trung tung chu so (0,85617/0,90893; 0,91392/0,92897). train max ts = 23:44 UTC ngay truoc cut (= 06:44 +07 ngay dau Q_k).
(c) M5: tu viet parser printDone + 'Update ... 07:00 b+unP': 8 seed x 18 quy ROI trung M5_result max|d| 3,6e-15 pp (vd a1 2022Q2 -5,0516, s13 2024Q1 16,3987, s99 2025Q4 13,5191).
    Phan phoi rong 28 cap x 18 = 504 dung; p95 = 3,8948 (linear), 3,8146 (lower), 3,9089 (higher) - nhan khong doi theo method; 31/504 gia tri >= 3,508.
    MO TA: bo 2022Q2 => p95 = 3,5035 < 3,508 => cach doc DAO (prereg gop moi quy nen khong ap dung).
(d) M2: tu dem GATE-RATIO trong sim.out.gz r1-a3-a1: 18/18 quy trung cot 'log' cua M2 (383,182,103,249,53,100,...); hop le tu tinh 16/18, 14/16 => HOP LE.
    PI 2022Q4 (min) 0,5757, 2023Q3 (max) 1,7273, 2025Q4 1,0197: so hoc + tong 3 khoang 30 ngay trung. KHONG tu viet lai replay gate (chi kiem so hoc + thiet ke).
    Thiet ke PI (bo dem truoc ranh gioi = chuoi WFO, trong Q_k = LAG_k) KHOP voi cau hinh 2026: Lane L va P deu co bo dem = fold_20 tren Q2, Q3 = fold_20 vs T1 (rt_chain run_ho5,
    PREREG_RETRAIN_PILOT :198). Khac: 1,35 lay tu sim day du (co phan hoi duong di), PI_k tu replay khong phan hoi, full_mask = 0 phut (sim skipFull = 58) - MINOR.

## A4. So sanh duoc giua M1 va 1,192 / 1,509 (diem MASTER lo)
GIONG: cua so quy +07 (rt_dcal S3=1782838800000 = 07-01 00:00 +07; Q3 n = 132 480 = 92 x 1440); don vi dong = PHUT THI TRUONG (pred.bin (ts,p15,risk), 1 gia tri/phut, khong phai
phut x coin); quantile numpy linear; chieu ti so WFO/LAG = T1/live (T1 = 1 quy toi, live fold_20 = 2 quy toi); feature 33 V3FULL cung thu tu.
KHAC (moi khac biet ve CACH SINH pred):
 1. Nguon feature suy luan: 2026Q3 = gate Vision ho4p1-x26-q3 (gate.csv*, exporter Vision, chi tren Kaggle) qua rt_chain.py run_ho5 :469; M1 = gate_dataset_full.csv (DEV). Gate Vision Q3
    ban A co loi mapper 8 id: 16/41 cot, 99,2 % phut tu 2026-07-10 (HO4_P1.md :96; breadth 0,4-1 %, funding ro 3-5 %, basket 0,1-1,8 %). Ca hai model cung nhan feature hong (cap noi bo
    nhat quan) nhung dai rong M1 KHONG chua hieu ung "hai model phan ung khac nhau voi feature lech nguon/hong" (A1_RETRAIN_T1 F5c da neu). DEV vs Vision 2026H1: 49,3 % o bang.
 2. Engine: 2026 = ONNX Runtime float32 (ca hai, cung kernel chain; pn1 tai lap pred live 64f66a15); M1 = xgboost native predict. |d| ~1e-7 - khong dang ke.
 3. Recipe/dong doi: live fold_20 = WFOGateRunner -> train_gate_fold.py, cut 2026-04-01 UTC, purge 0, file train goc mat (tuong duong bit a1c78e2f theo AUDIT_FOLD20_DATA);
    T1 = rt_p15_train.py -> train_gate_fold.py b41c9159, cut +07 - 15' (2 889 607 dong). M1 = drv G0, cut UTC - 15'. Khac biet nho (P15-B max|d| 6,75e-5).
 4. Ti le du lieu them: 2026 them 1 quy vao 5,25 nam (+4,7 % dong); DEV them +100 % (2021Q3) ... +5,5 % (2025Q4). Dai lich su vi vay RONG hon (bao thu) cho cau hoi "them 1 quy".
 5. 2026Q1-Q2 cua cap 2026 khac che do (DCAL Q1 ti so q99995 0,753 - ca hai in-sample).
=> Ve CONG THUC: cung dinh nghia. Ve DOI TUONG: cap 2026 = "them 1 quy" + nguon feature Vision/mapper + 1 che do thi truong; cap M1 = "them 1 quy" thuan tren feature DEV.
Do ben (mo ta, khong doi cach doc; a1_m1_recalc.json): q99,995 tren ~130k phut = 6-7 phut dau.
 - Leave-one-day-out (bo tung ngay +07): bao R9999 toan bo [0,764; 1,234] (2021Q4 bo ngay max -> 1,234 > 1,192); bao R99995 [0,789; 1,477].
 - Bo ngay chua max(WFO,LAG) moi quy: R9999 [0,764; 1,234]; R99995 [0,789; 1,477] (2021Q4: 0,858 -> 1,477).
 - Bootstrap khoi ngay (300 lan/quy) p5-p95: bao R99995 [0,728; 1,497].
 => Nhan R9999 "ngoai" KHONG ben (1 ngay doi duoc). R99995 1,509 van ngoai moi bao nhieu nhung chi hon 1,477/1,497 ~1-2 %. Ti so 2026Q3 tu no cung nhay nhu vay (max T1 0,145
    vs live 0,092 - vai phut) nhung KHONG duoc tinh LODO tren 2026 o luot nay.
KET LUAN 4: ANOMALOUS dung theo luat ghi truoc (R99995 ngoai, ben voi LODO/bootstrap o muc bien). Nhung nhan chi noi "lech duoi T1/live lon hon dai 'them 1 quy' tren feature DEV";
KHONG quy duoc cho cong thuc T1 vi cap 2026 con khac o nguon feature suy luan (Vision + mapper) - yeu to chua co doi chung. Muc do: MAJOR (dien giai), khong phai loi tinh.

## A5. Ro ri 6h45'
Xac nhan: fold k train toi 23:44 UTC ngay truoc cut = 06:44 +07 ngay dau Q_k (405 phut Q_k trong train WFO_k; LAG_k khong). Bo 6h45' dau moi quy: R9999 [0,8569; 1,1424], R99995
[0,8579; 1,1267], sign 7/11 (trung so nhay cua RUN); 0/126 phut top-7 (WFO hoac LAG) nam trong vung ro. Anh huong khong dang ke; cung mep voi G0/pred.bin goc. MINOR.

## Loi theo muc
- MAJOR (dien giai, khong phai tinh toan): M1 null khong chua nguon feature suy luan Vision/mapper cua 2026 => ANOMALOUS khong chi ra T1 recipe; R9999-out khong ben LODO.
- MINOR: M5 null = cap seed DEV co danh muc phan ky tich luy tu 2021 trong khi L vs P cung trang thai tai S3 => null co the RONG hon dung => thien ve "khong phan biet"; cach doc
  dao neu bo 2022Q2. M2: 1,35 tu sim co duong di vs PI replay khong phan hoi; full_mask 0 vs skipFull 58; errata lan 1 khong luu artefact. Ro ri 6h45'.
- Khong thay loi tinh toan nao.

## PHAN B - kha thi phan ra (chi doc)
(i) Khac biet recipe. T1 p15 = Oracle w3/retrain/work/rt_p15_train.py (runpy) -> vz_e1_wt/ml/gate/train_gate_fold.py md5 b41c9159, CUTOFF=20260701, GATE_PURGE_MS=26100000, DATA
    gate_dataset_full.csv a1c78e2f, 2 889 607 dong, ts_max 06-30 16:44 UTC (out/p15_t1/manifest_rt.json). rt-chain-n26 CHI la kernel suy luan Kaggle (ONNX tren gate Vision);
    g015_net_train.py la cua net015 (khong lien quan p15). So voi G0 (drv.py :114-157): cung 33 V3FULL/thu tu, cung XGB params/seed 42/n_jobs 4; khac: (1) mep: T1 = 00:00 +07 - 15'
    vs G0 = 00:00 UTC - 15' (G0 ro 6h45'); (2) train_gate_fold doc CSV float64 roi ep float32, khong sort, khong loc nhan NaN (G0: dtype float32, sort ts, isfinite(y)) -
    P15-A cho thay ket qua trung cay; (3) wrapper runpy + export ONNX. Tai cut 0701: CSV ket thuc 06-30 17:00 UTC => G0 cut 0701 UTC (= model b68563fe, deploy242/model_cut20260701,
    2 889 623 dong) chi hon T1 16 dong (16:45-17:00 UTC). fold_20: WFOGateRunner -> train_gate_fold, cut 0401 UTC, purge 0, 2 759 040 dong, file goc mat (= a1c78e2f tren cua so
    train), ONNX 8ec99757; khac G0-cut0401 = purge 0 vs 15' (15 dong) + doc file; P15-B: retrain vs fold_20 max|d| 6,75e-5.
    => (d)/(c) ~ 1 va (b)/(a) ~ 1 gan nhu chac chan; gan toan bo 1,19/1,51 se roi vao (c)/(b).
(ii) Feature p15 Q3: chi tren Kaggle (output kernel ho4p1-x26-q3, gate.csv*, 132 480 dong; ban sua mapper = ho4p1-dupfx gateB). Oracle chi co MANIFEST/log
    (1011/ho4p1/kaggle/out/ho4p1-x26-q3/out). gate_dataset_full.csv dung 06-30 17:00 UTC => du cho train cut 0701, KHONG co Q3. Pred: (a) w3/ho5/a3/data26/ds/pred_2026.bin md5 64f66a15;
    (d) w3/retrain/out/k/rt-chain-n26/out/pred26/pred_2026.bin md5 c1b00ba9; ca hai 6 289 924 B = int32 BE n=393 120 + n x (ts >i8, p15 >f4, risk >f4=0), cap thi truong, 2026 ca nam.
    Model: (a) ~/claudedata/wfo_models/fold_20/*.onnx; (c) 1002/deploy242/model_cut20260701 (b68563fe); (d) w3/retrain/out/p15_t1 (ONNX + booster.json).
(iii) Dong 2026H1 trong gate_dataset_full.csv: DEV (ExportGateDataset tu store Aerospike Oracle, file 08-08), CUNG exporter/nguon voi 2021-2025 - khong phai Vision. Luu y provenance:
    store ghi lai 07-07 (2021-01..2026-05), kline 2026-06/07 ghi lai 08-05/08-13, market_data_object 2026-06 cuoi ghi lai 08-15 (sau file) => store hien tai chi khop 20 % o 2026-06
    (AUDIT_FOLD20_DATA :28-31, bang 3b). (c) hoc 2026Q2 DEV nhung suy luan Q3 bang Vision.
(iv) Chi phi: (b),(c) train Oracle duoi lock ~1-2 ph (doc CSV 12 s + fit 17-40 s/model; c da co san b68563fe); suy luan Q3 can gate Vision => hoac tai output ho4p1-x26-q3 ve Oracle
    (nho, ~vai chuc MB) + ORT vai giay, hoac 1 kernel Kaggle fork rt-chain (~vai phut CPU). Ca hai cham 2026Q3 => can phu luc prereg + quyen U4a. B1 (recipe T1 tren 18 cut DEV):
    Oracle duoi lock ~3 ph (nhu M1 2 ph 37 s), RAM ~1,7 GB.
(v) Rui ro / thieu:
  - Phan ra gan nhu tam thuong: d/c (16 dong) va b/a (purge 15 dong) ~1 => ket qua du kien ~ (1 x 1,19-1,5 x 1); khong tach them duoc gi ngoai xac nhan "khong phai cong thuc".
    B1 cung gan trung M1 (so nhay 7h cua RUN da xap xi B1: khong doi).
  - Ti so quantile 6-7 phut: moi nhan to don le nam trong nhieu (LODO o DEV doi R99995 toi ~0,6); can dai bat dinh cho tung nhan to, khong chi uoc diem.
  - THIEU (de xuat, can prereg): (1) hieu ung NGUON feature: cung cap model (vd G0 cut0101 vs cut0401) suy luan 2026Q2 tren DEV CSV vs gate Vision q2 => Vision co khuech dai ti so duoi?;
    (2) hieu ung MAPPER: ti so T1/live tren gateA vs gateB (dupfx) va tach 07-01..07-09 / 07-10..09-30; (3) mot mau "them 1 quy" trong che do 2026 hoan toan OOS: G0 cut0101 vs cut0401
    (~fold_20) tren 2026Q2; (4) nhieu seed cua cap (c,b) tren Q3 (8 seed, re) de so voi dai alt [0,82; 1,20] cua RECON; (5) LODO cua chinh ti so Q3 (ngay nao gay 1,51).

## Diem KHONG kiem duoc
- Lan chay M2 #1 dung truoc khi tinh (artefact bi ghi de). Replay gate doc lap (chi kiem so hoc/thiet ke). File gate Vision Q3 (chi Kaggle) va noi dung pred 2026 (khong tinh thong ke 2026).
- Vi sao G0 vs pred.bin A1 chi pearson 0,992 (khong bit-exact) - khong anh huong M1 (WFO/LAG cung recipe) nhung nguong hop le 0,99 sat.
