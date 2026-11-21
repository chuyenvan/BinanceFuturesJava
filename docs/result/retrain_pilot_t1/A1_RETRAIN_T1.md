# A1_RETRAIN_T1 - audit doc lap train T1 (p15 / S1 / net015) + day noi Lane N + script cham (2026-11-21, truoc khi cham Lane N)
Pham vi: PREREG_RETRAIN_PILOT (sha256 7cf7e516) + ADD1-4, UNSEAL e9095a02 (U2). Auditor KHONG doc so PnL/equity Lane N (chi doc: result.json Lane N
3 truong jar_sha256 / ho5.bins26_sha / ten khoa ho5.pred). Output audit: ~/claude_master/w3/retrain_audit/ (a1_*.py/json/log, 204 KB).

## (1) KET LUAN: PASS-WITH-MINOR cho viec CHAM DIEM Lane N
Khong tim thay ro ri du lieu vao 3 model T1; day noi Lane N dung; script cham dung dinh nghia muc 7 + ADD4.
BAT BUOC truoc khi cham: F1 (them assert vao rt_score_n.py) + F2 (MASTER ghi nhan assert muc 3 p15). Khuyen nghi: F5c (khai mo ta truoc).

## (2) Phat hien
| ma | muc do | file:dong | mo ta | bang chung | de xuat |
|---|---|---|---|---|---|
| F1 | MINOR (bat buoc sua) | w3/retrain/work/score/rt_score_n.py:36-76 | Script cham KHONG tu kiem chung truoc khi doc so (muc 7 (i)-(iii)): khong doc/assert check_n.json (rt_nchk) PASS 8/8, khong assert check_l5.json PASS, khong assert E_start lay dung Update 20260701 (eq_series lay Update dau tien >= 0701, im lang) | a1_score.py T6: bo dong "Update 20260701" o 1 seed -> d_start 20260702, script van cham (d=0.018 pp), khong dung | Them: assert check_n.json["PASS"] (N) va check_l5.json["PASS"] (L) cho ca 8 seed; assert m["d_start"]=="20260701" ca 2 lane; (tuy) assert d_end N == d_end L. Sua ha tang, khong doi dinh nghia (N3) |
| F2 | MINOR (MASTER ghi nhan) | prereg muc 3 dong "Moi wrapper assert them..." ; rt_p15_train.py (khong co) | Assert "so dong train >= model truoc" KHONG duoc cai o wrapper nao; voi p15 theo chu se FAIL: T1 2 889 607 < b68563fe 2 889 623 (do mep +07: 15 dong trong purge + 1 dong = S3). S1 12 787 169 >= 6 911 775, net015 48 429 620 >= 39 354 754 (OK) | a1_p15.json: rows_in_purge 15, rows_ge_S3 1 | MASTER ghi 1 dong: nguong p15 dung theo mep +07 (khong phai loi du lieu). Khong can train lai |
| F3 | NOTE | prereg dong 10 | md5 score_l5.py ghi "1a2ea082" = ban score_l5.py.bak1; ban hien tai 1a082088 (sua 09:56, truoc commit prereg 10:28). Diff chi o check() (fund_dev_ok, profile_ok); rows/updates/metr KHONG doi | md5sum + diff bak1 | Ghi chu trong bao cao ket qua |
| F4 | NOTE | prereg muc 6.1 | "Diff run.py chi o tag + ten dataset": thuc te them pred26_md5, bins26_sha[0701], unseal_ref (pin bat buoc) | diff tu lam: 8/8 seed chi dong 21 (CFG) khac; metadata chi id/title/dataset | Chap nhan |
| F5 | MINOR (rui ro dien giai) | prereg muc 6/13 | Lane N khac L ngoai "3 model": (a) gate rolling ratio 90 ngay khong reseed -> TOAN BO Q3 (92 ngay) nam trong cua so tron r cu/moi (p15 T1 Q3 p50 0.00909 vs 0.00887, max 0.145 vs 0.092; DESC_Q3.json); (b) S1 T1 hoc 45.1 % dong tren feat Vision (= nguon suy luan Q3), S1 live chi DEV -> do "refresh + dong bo nguon feature"; (c) gate Vision Q3 loi mapper 8 id tu 07-09 (99.2 % phut, 16/41 cot) - 2 model p15 phan ung khac nhau voi feature hong, prereg chi neu cho T2; (d) ROI D5 Lane L 8 seed 3.1214-3.1217 % -> n hieu dung ~1 | DESC_Q3.json, a1_score T0 | Khong chan. (c) KHUYEN NGHI khai TRUOC khi cham: bang mo ta tach 07-01..07-09 / 07-10..09-30 (khong luat) |
| F6 | NOTE | SCORE_DEFS_L5 / score_l5.metr | SigmaPnL tinh lenh dong tu 07-01 00:00, E_start = Update 07-01 07:00 (da gom PnL 0-7h); E_end = Update 09-30 (khong co Update 10-01) | a1_score T0 d_end 20260930 | Giu (doi xung 2 lane) |
| F7 | NOTE | x1_s1_save_model.py:64-66, x1_feat_v2_build.py:29-33 | feat_v2 gio join ts_h = floor(ts); neu CLOSES_1H khoa theo gio MO nen thi feature thay gia toi ts_h+1h (<= 45' sau dong ledger). Co san trong recipe, DEV/Vision cung quy uoc (K3 99.8 %), << purge 72 h | doc code | Khong kiem duoc quy uoc ts CLOSES_1H; ngoai pham vi T1 |
| F8 | NOTE | rt_a3n.py:20 / a3lib.a1_ids | Demote tradfi bang exchangeInfo 2026-10-27 (sau Q3) - ca 2 lane | doc code | Doi xung |
| F9 | NOTE | jar | Jar sim cc0f9d11 = cung dataset sim-jar-tsx HO5 (8/8 result.json N va L); khong tim thay ban ghi jar_sec_check cho cc0f9d11 trong docs HO5 | grep | Auditor khong kiem duoc stub |

## (3) Ro ri tung model (tu kiem doc lap)
| model | tap train | max ts do doc lap | nhan / cua so | eval set / so cay | ket qua |
|---|---|---|---|---|---|
| p15 T1 c9f13fc0 | gate_dataset_full.csv (a1c78e2f, DEV) ts < 1782837900000 | 1782837840000 (06-30 16:44 UTC); 2 889 607 dong; booster A1 sha256 71e82572 == dev; ORT c9f13fc0 vs booster A1 4.5e-8 | label_oldbasket = basketMaxGain (ts, ts+15'] (ExportGateDataset:66,295) -> ket thuc <= 16:59 < S3 | khong (150 cay co dinh) | PASS |
| S1 T1 8bb11092 | ledger cand_rt26q3_32 (df19411d) g1lite notna, ts < S3-72h; feat_rt26 | 1782440100000 (06-26 02:15 UTC), +72h = 06-29 02:15 < S3; 0 dong trong [S3-72h, S3); 12 787 169 dong; JSON A1 sha 8bb11092 == dev | g1lite (maxFav/retEnd 72h, (t,t+72h], nBars>=288), cong thuc float32 0 lech | khong (300 cay co dinh); OOS Q3 chi de so mo ta | PASS |
| net015 T1 d91fe741 | Tool1 DEV 22 file + nhan DEV 22 file, ts < S3-72h (train_rows :183) | 1782578700000 (06-27 16:45 UTC) - TU LOG kernel (du lieu chi tren Kaggle); P14b assert < tr_cut; ONNX vs JSON 4.9e-7 (60 000 dong tong hop) | retEnd_4h > 0.015, (t,t+4h] | khong (400 cay; eval_metric auc khong co eval_set) | PASS (max ts theo log) |
- 45.1 % dong S1 ts >= S0: hop ly - 2025Q4 6 909 tick x 506 coin (khop OOS S1-A goc 3 499 202), 2026Q1 3.32 M, Q2 2.45 M; tang do gate mo ~78 % tick tu 2025Q4 + so coin tang. NaN feat 2026 0.11 % (DEV 0.48 %).
- P14b: dung; khong tao duong ro moi (loc file nhan khong phai cho chan ro; chan ro la ts < tr_cut, assert sieu chat hon). Voi --fold nhieu cut, cut_lb = cut fold cuoi (khong anh huong vi train_rows van loc ts).
- Pool Q3 (p15 T1) chi vao OOS noi bo S1; khong vao train (0 dong >= S3-72h). Pool H1 = wfo_gate_pred DEV (fold_19/20 OOS).

## (4) Day noi Lane N (a1_b.json)
- pred_2026_N: 260 640 dong ts < S3 trung BYTE Lane L; 132 480 dong ts >= S3 trung BYTE pred26 chain N (c1b00ba9), 0 % trung L; cot risk trung L toan bo; Lane L ds == chain HO5 (64f66a15).
- bins 20260101 / 20260401: sha N == L (b58099f4 / 78e4e437). bins 20260701 N (bb64cde3): khoa (ts,sym) == L == RAW_L; multiset p0 theo tick khac RAW_L 99.9999 % dong (khong phai net015 cu);
  a3lib.assign(binsN, S1 T1) tai lap BYTE (idempotent), assign(binsN, S1 live) lech 81.6 %; doi chung assign(binsL, S1 live) tai lap byte.
- P-N1: MANIFEST rt-chain-pn1 == ho5-a3-chain26 4/4 md5; steps result.json trung. Fork rt_chain = ho5_chain chi 2 cho ten file model (diff tu lam).
- Chain N cfg ghim p15 T1 c9f13fc0 + net015 T1 29d9a79d (sha file trong rt-chain-code tren Oracle trung). RAW_N (e72532c6) khong con tren Oracle -> khong tai lap duoc multiset = RAW_N (dua vao manifest + A3N_build rawN_md5).
- p15 T1 tren gate Vision Q3: gate chi tren Kaggle -> KHONG chay lai ORT; dua vao manifest chain + P-N1 (cung duong code tai lap byte voi model cu).
- run.py 8/8: chi dong CFG khac; jar cc0f9d11 8/8 (N va L); bins26_sha trong result N == pin.

## (5) Script cham rt_score_n.py (907d2af8) - a1_score.json
- Selftest L-vs-L (OUT chuyen sang retrain_audit): d = 0 8/8, LB 0; SigmaPnL mean 5 205.33; E_start mean 166 757.5; ROI D5 3.1215 %; ROI MTM 4.5094 %; maxDD -1.4804 %; d_start 20260701 8/8.
- Thu pha: -2 pp moi seed -> LB -2.0 FAIL; -0.5 pp -> PASS; -0.999 pp -> PASS; 1 seed -4 pp -> LB -1.6823 (= tinh tay) FAIL; 3 seed SigmaPnL am -> n_pos 5 E0 FAIL; 2 seed am -> n_pos 6 E0 PASS;
  thieu seed s777 -> FileNotFoundError (DUNG, khong bo qua); thieu Update 0701 -> IM LANG dung 0702 (F1).
- Dinh nghia khop muc 7 + ADD4: SigmaPnL theo end trong [07-01, 10-01); E_start Update 07-01; ROI = SigmaPnL/E_start; H-E0 mean>0 & >=6/8; LB t 2.3646 ddof=1; H-DD -22.72 % canh bao.
- Script KHONG co buoc "dong end < 07-01 trung L" - nam o rt_nchk.py (chay rieng, 8/8 PASS theo dev) -> F1.

## (6) Cong
P15-A that (noi dung model trung). S1-A that (sha); S1-A lai tren ledger moi chung minh phan DEV ledger+feat cho train < 2025-09-28 trung byte, KHONG chung minh phan 2026H1 (khong co tham chieu).
NET-A = predict-faithful (khong retrain). NET-B = band 0.991 CPU vs GPU + tat dinh CPU. NET-EQ that (trung byte). G-L that sau so hoc float32 (A1 kiem cong thuc 0 lech).
K: A2-1 doi tieu chi sau FAIL nhung truoc so model moi, T1 khong dung file lien quan. 3c/3d hop le. P15-B FAIL da chap nhan (fold_20 khong vao chuoi T1).

## (7) Khong kiem duoc
- Tai lap net015 T1 / max ts tu du lieu (Tool1 + OI chi tren Kaggle, 4 GB) - dua vao log kernel + code.
- ORT p15 T1 tren gate Vision Q3 va RAW_N net015 T1 tren Tool1 Vision Q3 (du lieu chi Kaggle).
- Quy uoc ts CLOSES_1H (F7); jar stub (F9); noi dung check_n.json Lane N (khong mo de tranh lo so).

## (8) sha256 (16 ky tu dau)
prereg 7cf7e516, ADD1 fffbdda2, ADD2 eb60d7ec, ADD3 ee9c4916, ADD4 2c89ba7c, UNSEAL 685c256b, RUN.md 3f71a73c, RUN.progress 41e8dbb0;
train_gate_fold 1819e953, x1_s1_save_model 8f234eda, x1_ledger 574ba611, x1_feat_v2_build 4508fc91, g015_net_train (repo P14b) 96fcbfe6, p14 3a96281a;
rt_p15_train 9ebfdc8a, rt_feat_splice e315a468, rt_g1lite32 04fa5305, run_s1t1.sh b20d212c, rt_a3n cbf8dbce, rt_chain d1d93905, rt_chainops 8f85ea0a,
rt_score_n 907d2af8, score_l5 da34f318, rt_nchk 0cf6eb2d, rt_cfgdiff 83a977c8, a3lib 80e32f18, rt_t1_kernel b9f5ae47;
p15 ONNX c9f13fc0, booster 71e82572, net015 JSON d91fe741, ONNX 29d9a79d, S1 JSON 8bb11092, ONNX 18ed11a0, ledger df19411d, pred_2026_N 711da2c3, bins0701_N bb64cde3, gate_dataset_full 4094424d.
