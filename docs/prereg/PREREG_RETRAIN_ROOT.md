# PREREG_RETRAIN_ROOT - nguyen nhan goc cua "retrain venh" (T1 FAIL 2026Q3) va quy trinh retrain
MASTER, 2026-11-24 (+07). Viet TRUOC khi chay bat ky phep do nao duoi day. Khao sat chi-doc lam can cu thiet ke:
~/claude_master/v12/RETRAIN_ROOT_RECON_1124.md (agent, 2026-11-24; co so mo ta duoi p15 / pass gate DEV theo quy - KHONG PnL).
Tien de: RESULT_RETRAIN_T1 (932770e5), RESULT_RETRAIN_DIAG + DIAG_MASTER_DECISIONS_1121 (edbf8404, D-D3).

## 0. Su kien da biet (khong do lai)
- Model live p15 = fold_20, cat 2026-04-01 UTC. T1 cat 2026-07-01. Tren 2026Q3: live = du doan "2 quy toi" (LAG), T1 = "1 quy toi" (WFO).
- Backtest DEV da validate = moi quy la OOS cua mot fold rieng (retrain MOI quy, 18 lan doi model, bo dem gate 90 ngay tron cu/moi).
- 2026Q3 (da cong bo, CHI chep lai, khong tinh moi): ti so duoi p15 T1/live q99,99 = 1,192 ; q99,995 = 1,509 ; pass gate L 94, P 127 (x1,35),
  M 108, N 142 (x1,51) ; ROI D5: L +3,122 %, P -0,386 %, N -6,443 % => d_P = -3,508 pp, d_N = -9,564 pp ; 71 % lo cua lenh chi-o-lane tu 3 lenh.
- Pipeline: p15 tai lap trung cay (P15-A), G0 19/19 fold pearson >= 0,9919; S1 trung byte; net015 live train GPU, T1 train CPU (spearman 0,991).
- Nguong TUYET DOI con lai trong duong quyet dinh: MIN_MOMENTUM_15M = 0,008 (DCA_LEVEL1 + leg market-signal) so truc tiep voi p15.

## 1. Cau hoi va gia thuyet
Q-A: buoc nhay thang diem / so lenh / PnL cua T1 so voi live o 2026Q3 la BINH THUONG (nam trong pham vi cac lan doi model lich su va nhieu retrain)
     hay BAT THUONG?
Q-B: model "gia" them 1 quy (LAG) co kem model retrain dung han (WFO) khong - tuc retrain moi quy co gia tri do duoc khong?
Gia thuyet: H-noise (1 duong di, vai lenh), H-age (tuoi model), H-abs (nguong 0,008), H-gate (qua do bo dem), H-pipeline (net015 GPU->CPU),
H-spw (P(win) net015 khong hieu chuan). H-src (tron nguon) xep thap: p15 va net015 T1 khong dung Vision.

## 2. Du lieu duoc phep
- CHI DEV: ts < 2026-01-01 00:00 UTC. Moi bo doc phai loc + assert max(ts) < 2026-01-01 TRUOC khi nap vao bo nho (gate_dataset_full.csv co toi 2026-06-30).
- KHONG doc gi >= 2026-10-01. KHONG tinh gi moi tren 2026Q1-Q3 (chi dung cac so o muc 0). KHONG tune tham so strategy.

## 3. Tang 1 - co che + nhieu (khong chay sim moi)
M1 (p15, khong PnL). Train lai fold k = 0..18 theo recipe G0 (cut 2021-04-01 + 3k thang UTC, expanding tu 2021-01-01, cung tham so, seed G0) tren
  gate_dataset_full.csv. Voi moi quy Q_k (k = 1..18, 2021Q3..2025Q4): WFO_k = fold k du doan Q_k ; LAG_k = fold k-1 du doan Q_k (cung dong, cung feature).
  Kiem hop le: pearson(WFO_k tinh lai, pred.bin A1 hien co) >= 0,99 moi quy; quy nao < 0,99 => loai quy do va bao; > 3 quy bi loai => M1 INVALID.
  Thong ke moi quy: R9999_k = q99,99(WFO)/q99,99(LAG) ; R99995_k ; Rmax_k ; dp50_k = p50(WFO) - p50(LAG) ;
  F_k = frac(p15 >= 0,008 | WFO) / frac(p15 >= 0,008 | LAG) (= M3, muc phoi nhiem H-abs).
  Doc (ghi truoc):
  - TYPICAL neu 1,192 nam trong [min, max] cua R9999_k VA 1,509 nam trong [min, max] cua R99995_k (N = 18). Nguoc lai: ANOMALOUS (ghi ro chi so nao).
  - He thong: neu >= 14/18 quy co log R9999_k cung dau (sign test 2 phia p = 0,031) => them 1 quy du lieu lam dich duoi CO HUONG; nguoc lai: khong co huong.
  - F_k: bao min / median / max va so quy |log F_k| > log 1,5 (mo ta; dung cho thiet ke nguong tuong doi sau nay).
M2 (gate replay offline, khong PnL, TUY KHA NANG). Replay nguong quantile 0,99995 cuon 90 ngay tren r (p15 phut x sp bins A3) cho lane WFO a1.
  Kiem hop le TRUOC khi dung: so pass theo quy cua replay khop log GATE-RATIO cua sim r1-a3 a1 trong +-10 % o >= 15/18 quy (2022Q1+: >= 13/16).
  Khong dat => M2 = KHONG LAM (khong sua cong cu cho khop sau khi thay so). Dat => voi moi Q_k tinh PI_k = pass(LAG_k o Q_k, bo dem truoc ranh gioi
  = chuoi WFO) so voi pass(WFO_k): PI_k = pass_WFO / pass_LAG ; va phan bo pass vuot theo 3 khoang 30 ngay sau ranh gioi.
  Doc: 1,35 (lane P 2026Q3) nam trong [min, max] cua PI_k => TYPICAL ve gate.
M5 (nhieu retrain, PnL DEV DA CO - khong sim moi). Tu 8 seed r1-a3 (seed chi doi p15): ROI theo quy cua tung seed bang DUNG cong thuc D5 cua
  rt_score (khong ap duoc nguyen ven => M5 = KHONG LAM, khong tu che cong thuc). Phan phoi rong = |hieu ROI quy| cua moi cap seed trong cung quy
  (28 cap x so quy). Doc: |d_P| = 3,508 pp <= phan vi 95 cua phan phoi rong => "lane P khong phan biet duoc voi nhieu doi-seed p15". > phan vi 95 =>
  "vuot nhieu seed" (KHONG ket luan retrain hong: T1 con khac live o du lieu + tuoi - xem M4). d_N = -9,564 pp chi dat vao de MO TA (N doi ca 3 model).

## 4. Tang 2 - gia tri cua retrain dung han (sim moi; CHI chay sau khi Tang 1 da ghi ket qua + sha)
M4. Lane W = WFO (co san, 8 seed). Lane G_p = moi quy Q_k dung p15 cua fold k-1 (LAG), net015 + S1 giu WFO (pool/ledger S1 dung lai theo p15 moi nhu
  rt_lane). Lane G_all (phu, neu du quota Kaggle) = ca 3 model LAG; vi net015 LAG phai train CPU nen can them lane doi chung W_cpu (net015 WFO train CPU)
  va so G_all voi W_cpu, KHONG so voi W. Doi OOS_MONTHS / wrapper = thay doi cong cu, ghi diff vao ket qua.
  d_k = ROI_D5(W, Q_k) - ROI_D5(G, Q_k), trung binh 8 seed, k tren cac quy 2022Q2..2025Q4 co du artefact (N du kien 15-16).
  Chinh: mean(d_k) cua G_p, CI95 bootstrap theo quy (10 000 lan, seed 20261124), sign test.
  Doc (ghi truoc):
  - CI95 nam tren 0 => model gia 1 quy KEM model retrain dung han (H-age co that) => quy trinh phai retrain moi quy nhu DEV.
  - CI95 chua 0 => KHONG co bang chung tuoi 1 quy lam giam ket qua (luc thap: n ~ 16 chi bat duoc hieu ung >= ~0,7 sd - ghi ro, khong doc la "bang nhau").
  - CI95 nam duoi 0 => retrain dung han KEM => dung, dieu tra truoc moi quy trinh retrain.
  - Vi tri cua 2026Q3: d_P = -3,508 (so voi d_k cua G_p) va d_N = -9,564 (so voi d_k cua G_all neu co): nam trong [min, max] => "khong bat thuong so voi lich su".
  Gioi han: 2 seed ~ 1 mau cho net015/S1; hieu ung duong di; N nho.

## 5. Cay quyet dinh (ap co hoc; khong nhanh nao cho phep doc du lieu 2026)
- CASE A: M1 TYPICAL va (M5 "khong phan biet" HOAC d_P nam trong [min, max] cua M4) => ket luan "T1 FAIL khong phai bang chung retrain hong; phep thu
  1 quy khong du luc". Quy trinh retrain de xuat = retrain dung han nhu DEV, nghiem thu bang (i) tai lap pipeline, (ii) thuoc xep hang Tang A khong kem,
  (iii) cac chi so co che (R9999, R99995, F, PI neu co) nam trong dai [P5, P95] lich su tu M1/M2; KHONG nghiem thu bang PnL mot quy. Buoc xac nhan tren
  du lieu >= 2026-10-01 (U4b, mot lan) can prereg rieng + owner duyet.
- CASE B: M1 ANOMALOUS => dich thang cua T1 lon hon moi lan doi model lich su => dieu tra khac biet rieng cua T1 (mep +07, purge 15', du lieu 2026Q2)
  bang addendum (ap recipe T1 len cac cut DEV); CHUA de xuat quy trinh.
- CASE C: M4 CI95 duoi 0 => khong retrain theo quy trinh hien tai; xet (d) khong retrain toi khi thuoc bao suy giam / (h) trung binh fold - prereg rieng.
- H-abs (nguong 0,008 tuyet doi): doi sang nguong tuong doi la DOI STRATEGY => prereg rieng + validate DEV/HO day du; prereg nay chi do F_k.
- Moi truong hop khong roi vao A/B/C => "KHONG KET LUAN", bao owner, khong chon cach doc theo so da thay.

## 6. Quy trinh
- Agent RUN chay; agent A1 KHAC kiem doc lap (tai tinh >= 5 so, kiem assert du lieu, kiem thu tu ghi: Tang 1 ghi + sha TRUOC khi mo output sim Tang 2).
- Job nang Oracle: flock oracle_heavy.lock (khong long), RAM >= 4000 MB, dia >= 15 GB. Kaggle: jar STUB khong key.
- Ket qua: docs/result/retrain_root/. Khong sua nguong / cach doc sau khi thay so; sai sot cong cu => errata + bao ca hai luot.
