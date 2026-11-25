# RESULT_P15_STAB_S2 - Tang S2 (prereg PREREG_P15_STAB dea45002 muc 4): E8 vs C0-PROD, PnL DEV
Agent RUN (Opus), 2026-11-25 09:10-09:25 +07. Chi DEV (ts < 2026-01-01). Khong sim moi, khong mvn/java, khong 242. Tien do + moi lua chon thuc thi (ghi TRUOC khi tinh): RUN_S2B.progress.

## 0. Dau vao (buoc 0, score/s0_verify.py, khong mo khoa tien)
- 8/8 lane/<l>/CHECK.json PASS, 0 truong False. Kiem doc lap them: pred_md5 LANE.json == result.pred_md5_used 8/8; pred_md5_base == A1 5dd6bb4c;
  profile r4_kg0_k16_f015_g155 + profile_hash 0738cca9 + overrides == r1-a3-s7 va == ho5-a3-rep4-s123 (SELECTOR_RANK_TOPK 24, GATE_QUOTA_SKIP_WHEN_FULL true);
  jar cc0f9d11; snapshot mapper/funding sha == rep4; bins sha == A3.json. sha256 result.json / printDone.csv / sim.out.gz tung lane: RUN_S2B.progress + score/S0_verify.json.
- C0 = c0s42 c0s7 c0s123 c0s13 (1 model PROD / lap); E8 = e8g1..e8g4 (trung binh 8 model, nhom seed roi). net015 + S1 WFO, pool/ledger S1 dung lai theo p15 tung lane.

## 1. Kiem cong cu
- ROI D5: score_l5.py (sha256 da34f318) rows/updates/metr import nguyen, quy lich nhu m5_seed_noise.qwin. r1-a3-s7: 18/18 quy (2021Q3..2025Q4) TRUNG M5_result.json (max|d| = 0). PASS.
  A5-1 (d_start == ngay dau quy) dat 8 lane x 16 quy.
- MTM: chuoi baseline ISO_RISK (gvz_mtm import truoc reset_rule_score, R.run_mtm, n700_driver.arm_metrics). Tag kiem gqsf-s7 (OFF_S7 ISO_RISK):
  cagr22 35.63535 / dd_mtm22 -22.74892 == iso_risk_v.json (d = 0.0). PASS. missing = 0 ca 9 tag.

## 2. Tieu chi (e) - DISP = trung vi 16 quy cua sd (ddof 1, 4 lap) ROI_D5 quy (pp)
- DISP(C0) = 0.9813 ; DISP(E8) = 0.7122 ; ti so 0.7257 ; nguong 0.6 x DISP(C0) = 0.5888.
- (e): KHONG DAT.
- Mo ta: so quy sd_E8 < sd_C0 = 13/16 ; trung vi theo quy cua sd_E8/sd_C0 = 0.5926.

## 3. Tieu chi (f) - CAGR22 / maxDD22 MTM (arm_metrics; trung binh 4 lap)
| ho | CAGR22 mean [min; max] | maxDD22 MTM mean [min; max] | Calmar22 mean [min; max] (mo ta) |
|---|---|---|---|
| C0 | 37.508 [35.046; 39.842] | -22.520 [-23.489; -20.690] | 1.673 [1.492; 1.926] |
| E8 | 35.480 [33.816; 36.304] | -23.505 [-24.242; -22.365] | 1.511 [1.457; 1.613] |
- Hieu E8 - C0: CAGR22 -2.028 pp (nguong >= -1.5) => KHONG DAT ; maxDD22 -0.985 pp (nguong >= -2.0) => DAT.
- (f): KHONG DAT.
- So voi baseline da cong bo (ISO_RISK OFF K24+skipFull 8 seed): CAGR22 37.0 (mean 36.98), maxDD22 -22.5, Calmar22 1.65. Luu y: baseline dung jar bcd va
  p15 seed cu (r1/gqsf), S2 dung recipe p15 PROD (seed 42/7/123/13 va nhom E8) + template sim ho5 snapshot (jar tsx cc0f9d11) => khong so sanh truc tiep.

## 4. Mo ta (khong dung de cham)
- n_trades (dong printDone): C0 3462 / 3585 / 3570 / 3452 ; E8 3607 / 3526 / 3534 / 3596.
- ROI ca ky 2022-01-01..2025-12-30 (metr.roi, %): C0 232.3 / 245.7 / 282.1 / 270.4 ; E8 244.9 / 220.4 / 239.0 / 242.6.
- Lenh vao KHAC NHAU tuyet doi giua 2 lap cung ho (khoa (sym, start, level), |A symdiff B| theo quy, trung binh 6 cap): trung vi theo quy C0 126.4 vs E8 76.8
  (so lenh vao / quy trung vi: C0 166.9, E8 174.1). Trung vi theo quy tung cap: C0 119.0-140.0 ; E8 70.0-92.0.

## 5. Ket luan theo luat muc 4 prereg (E8 DAT S2 <=> (e) VA (f))
- (e) DISP(E8) <= 0.6 x DISP(C0): KHONG DAT.
- (f) CAGR22 E8 - C0 >= -1.5 pp: KHONG DAT ; maxDD22 khong sau hon qua 2.0 pp: DAT ; (f): KHONG DAT.
- E8 Tang S2: KHONG DAT.
- Gioi han ghi truoc: 4 lap moi ho, luc thong ke thap; c0s42/c0s7/c0s123/c0s13 la thanh vien cua e8g1 (khong doc lap hoan toan).

## 6. Lua chon thuc thi / sai lech so voi prereg (thoi diem quyet dinh, chi tiet RUN_S2B.progress)
- 09:13 (truoc moi so): C1-C5 (quy lich +07 nhu M5; khoa lenh = (sym, start, level); MTM qua thu muc tam mtm_in/<lane> voi sim.out giai nen
  (sha noi dung == stream), tro qua R.BASE_OF; khong bu loi MTM 00:00 UTC, nhu baseline).
- 09:15 (truoc moi so MTM): ~/vz_e1/raw/kline1m-* (nguon gia gvz_mtm >= 2021-12) da bi xoa => MT.kp tro ~/claude_master/res1109/r1_s1/kl (Vision tai lai,
  sha khop README; cung patch voi res1109 r1_score.py). Hop le hoa bang gqsf-s7 tai lap d = 0.
- s0_verify lan 1 so ca dict snapshot (khac duong dan mount Kaggle o c0s42/e8g1) => false gia; sua so sha (09:12, truoc moi so tien).
- Khong co sai lech nao ve tieu chi / nguong / ung vien.

## 7. Diem KHONG chac chan
- Moi lane co 91-106 leg dong dung 00:00 UTC (gqsf-s7: 10). Loi legacy MTM (GOLIVE_QUARTERLY) lam equity phut bi thoi cao trong ngay do; CAGR22 (equity ngay
  sim.out) khong bi anh huong; DD22 MTM co the bi - GOLIVE do tac dong DD22 = 0 tren X14, o day KHONG do lai.
- Nguon gia MTM = res1109 kl (khong phai file goc vz_e1/raw da xoa); chi hop le hoa qua 1 tag (gqsf-s7).
- ROI quy D5 dung sum_pnl lenh dong trong quy / equity dau quy (khong MTM).

## 8. File + sha256
- score/S2_result.json de7036399fafcbcd5e3fffe34127d194445254b4eced1449f3c9db769e228b08
- score/S2_lanes.tsv 331b52bdb331dbd5495a5bf09c74b0feb8bb25868971b98afc81b71f3f35c165
- score/S2_roi_q.tsv 7e4dd36c57cd4019d852a510a9d829ff72f4c73850976bd3fe43913b7a5c7ad6
- score/S1_roi.json af061da71a2c7c278d78739b4114ae57cf1280c3cb54e0eaacb0b24998b12aed
- score/S3_mtm.json ec88b3dd0a777e93d4d00a4d27fbb2a4d9b8c67310eff706713fc8b6bd8cd770
- score/S0_verify.json 7fead5928afe5c0dc662d5e91bdf279d4b060091f245e4de8674c1794dc411fd
- score/s0_verify.py cb54129129ab7ce0de65d0672acc5c4e15235b39a28f17b31abcf93afa6be6b3
- score/s1_roi.py 6abfcb779b8e03a1428625ead4b7c76b836ea0f917d3f8b63ac3dee85c3a1951
- score/s3_mtm.py 3b9317ca871e72044e702dec1d1ea5687e2bf55d60ac886234660aeceb74622c
- score/s5_verdict.py b8faaaf8d1b036d449365aa4834a444fa2c120a687f55fa9df0ecb3f4702d04d

## 9. Bang ROI_D5 theo quy (pp), sd, ti so, lenh khac nhau (score/S2_roi_q.tsv)
```
quarter	c0s42	c0s7	c0s123	c0s13	e8g1	e8g2	e8g3	e8g4	sd_C0	sd_E8	ratio	diff_C0	diff_E8
2022Q1	7.4454	7.7688	6.9140	6.7443	7.5014	7.5368	7.2790	6.7896	0.4732	0.3442	0.7273	68.5	47.3
2022Q2	-7.2751	-6.0428	4.0447	-4.7444	-7.9475	-6.5623	-7.3541	-4.6182	5.1377	1.4504	0.2823	324.0	194.5
2022Q3	7.8603	6.0464	8.4615	9.2856	7.3815	6.4028	8.0953	7.3421	1.3750	0.6942	0.5049	52.0	29.5
2022Q4	-1.9893	-1.6303	-3.5309	-2.4263	-2.2495	-3.4276	-2.3557	-2.3982	0.8248	0.5501	0.6670	90.8	59.0
2023Q1	12.3551	10.4894	12.5190	11.7432	11.4653	11.6265	11.1123	12.1014	0.9209	0.4107	0.4459	106.7	63.0
2023Q2	20.7680	15.9366	18.7350	16.5134	18.7004	17.9717	19.5921	19.7223	2.2113	0.8204	0.3710	162.5	90.5
2023Q3	10.1669	10.0680	9.9595	12.4681	10.9404	10.8425	11.0338	11.1983	1.2046	0.1514	0.1257	57.5	43.7
2023Q4	16.8115	18.0455	19.0814	19.7634	20.7238	19.3297	18.7343	19.6939	1.2871	0.8352	0.6489	211.3	140.3
2024Q1	12.7909	13.6455	12.2259	14.0484	11.3831	10.5006	13.7665	11.2350	0.8231	1.4170	1.7216	200.0	165.7
2024Q2	0.9825	1.0827	1.3953	0.6563	2.7469	0.6759	1.5891	0.4454	0.3045	1.0457	3.4340	146.2	110.3
2024Q3	5.5495	5.9316	6.0135	7.5290	5.3406	5.7527	5.6133	4.6978	0.8725	0.4680	0.5364	66.2	57.5
2024Q4	15.6093	17.7278	16.8648	17.5810	18.5575	18.5244	15.8009	18.3932	0.9674	1.3473	1.3927	229.0	153.5
2025Q1	11.1774	11.2754	10.5386	14.0353	11.6579	8.7657	10.5593	8.7985	1.5538	1.4161	0.9114	257.8	166.0
2025Q2	3.2325	5.9850	3.0912	3.3209	2.7759	2.7544	2.4623	3.5083	1.3883	0.4456	0.3210	71.8	26.8
2025Q3	0.3569	2.3339	1.6890	0.8335	1.5179	1.2941	1.4055	0.7454	0.8808	0.3426	0.3890	43.3	31.3
2025Q4	12.7477	13.4757	14.8475	12.7261	12.5079	12.7226	13.3915	14.1254	0.9952	0.7301	0.7337	214.5	170.0
```
## 10. Bang lane (score/S2_lanes.tsv)
```
lane	family	n_trades	roi_all_2022_20251230_pp	cagr22	dd_mtm22	calmar22	uw_mtm22_days	legs_end_0000utc
c0s42	C0	3462	232.333	35.0463	-23.4892	1.4920	256.3	102
c0s7	C0	3585	245.680	36.3832	-23.1684	1.5704	186.5	91
c0s123	C0	3570	282.076	39.8418	-20.6902	1.9256	140.0	106
c0s13	C0	3452	270.403	38.7606	-22.7329	1.7050	201.3	100
e8g1	E8	3607	244.883	36.3045	-24.2093	1.4996	187.1	102
e8g2	E8	3526	220.393	33.8158	-23.2049	1.4573	186.7	102
e8g3	E8	3534	238.997	35.7187	-24.2417	1.4734	186.5	102
e8g4	E8	3596	242.645	36.0826	-22.3654	1.6133	164.3	103
```
