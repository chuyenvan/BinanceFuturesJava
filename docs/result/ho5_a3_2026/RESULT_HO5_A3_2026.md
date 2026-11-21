# RESULT_HO5_A3_2026 - holdout 2026 cua cau hinh A3 (r1-a3) voi 3 model LIVE dong bang - Lane L
Prereg: PREREG_HO5_A3_2026.md (bf3f90a1) + ADD1 (5803ca82) + ADD2 (2725f216) + ADD3 (499700bd). Mo seal: HOLDOUT_UNSEAL_2026_1121.md
(e9095a02), pham vi U1. Thuoc cham: w3/ho5/l5/SCORE_DEFS_L5.md (sha256 03a93453..., chot TRUOC khi co output 2026; khong doi sau).
Agent luot 5, 2026-11-21. Nhat ky: v12/HO5_A3_2026.md (LUOT 5) + .progress.

## 0. Ket luan (luat nguyen van)
- E0 (OOS 2026-04-01..09-30, Lane L): mean SigmaPnL_OOS = +17 195 > 0; 8/8 seed > 0 (>= 6/8) => PASS.
  Theo ADD1 A3: 8 seed KHONG doc lap (cung p15 fold_20 trong 2026; 334-357/357 lenh 2026 trung (sym,start,end,status) voi s123)
  => E0 chi mang nghia "khong am".
- E0b (bootstrap tuan, 27 khoi 7 ngay tu 2026-04-01, 10 000 lan, rng 20261121, PnL trung binh 8 seed): quan sat 17 195,
  CI80 [871 ; 34 365] => can duoi > 0 => "duong co y nghia" (bien do rong; chi 13/27 tuan co PnL != 0).
- R1 (sua boi ADD1 A3): E0 PASS va E0b "duong co y nghia" => ky vong cho PILOT = so HO5 Lane L tren OOS: ROI OOS 10,95 % / 183 ngay
  ~= 23,0 %/nam quy nam ((1,1095)^(365/183)-1), KHONG dung 37,72 % nua. Van phai train lai truoc pilot (luat 3 PREREG_DIAG_NOTRADE_1117).
- R2: khong ap dung (E0 PASS). R3: mean maxDD(W) = -3,05 % (MTM NGAY 07:00) > -22,72 % => KHONG canh bao (khong "gan nguong").
- R4: Lane W = KHONG CO (ADD1 A3). R5: KHONG kich hoat - chay DUNG cau hinh r1-a3 cho ca 8 tag (xem muc 1).

## 1. Tuan thu + kiem chung (PASS/FAIL)
| cong / kiem | ket qua | so |
|---|---|---|
| Tai lap r1-a3-s123 (ADD1 A1/ADD2/ADD3, luot 3-4) | PASS | equity 144 003, 3 584 lenh, md5 printDone a11ce5f9 trung byte (snapshot funding v3) |
| P1 (A3 fold 20251001) | PASS | sha 3343e8e7 == ref |
| P2 (ONNX fold_20) | PASS co dieu kien (ADD2 B2) | max|d| 1,96e-8 vs booster tai dung |
| P3 (net015 ONNX) | PASS | max|d| 3,58e-7 (333 814 dong) |
| Chong lan funding 2025 (ADD3 C1) | PASS | 878 241 moc chung, 0 lech |
| Bo sung (khong phai cong prereg): S1 json af706dc6 vs ONNX live 511add62 | max|d| 1,67e-6 | 200 000 dong DEV 2025 |
| md5 model trong kernel chain26 | PASS | fold_20 8ec99757, net015 e65e683b (ho5_models_ok) |
| Tu kiem funding.bin v2 trong moi kernel sim | PASS 8/8 | dung lai DEV-only md5 == 50c4bc8d (r1-a3), 2 301 064 ban ghi ts<SEAL trung byte (md5 22828050) |
| Kiem chung moi seed (score_l5 check) | PASS 8/8 | xem duoi |
Moi seed: ok=true, java_rc 1 (nhu r1-a3), 20210701..20260930, 273 dong Update 2026 (du 273 ngay W), 0 dong printDone loi/NaN,
n_trades == so dong; pred26 nan 0; bins26 sha khop; market doan DEV == bundle; snapshot funding fb024c40 / overlay 207e7c60;
jar cc0f9d11; prof_run chi khac r1-a3 o SIM_LOSER_TS_EXT_DAYS (= DEV + 4 khoang 2026 tu ho_flags.json) -> profile_hash ef770e13
(khac 0738cca9 CHI do X14 flags 2026, dung prereg); doan <= 2025: moi dong printDone end < 20251230 TRUNG NGUYEN DONG + THU TU voi
r1-a3-<seed> (a1 3622, s123 3584, s13 3462, s2024 3514, s21 3550, s7 3548, s777 3538, s99 3554), 1 644/1 644 dong Update <= 20251230
trung byte. Khong lenh nao mo truoc 2026 con treo sang 2026 (E_start W = equity_final r1-a3).
Khoi dong gate 90 ngay: chay lien tuc tu 2021-07-01 (buffer = du lieu 2025) = cach HO4.

## 2. Dau vao Lane L
- pred p15 2026: ONNX fold_20 (md5 8ec99757) tren store gate 2026 (HO4-P1 Vision q1-q3), kernel chuyendinh/ho5-a3-chain26
  (ho5_chain.py md5 20dce08c = ho4p1_chain 5ec798f7 + run_ho5): 393 120 dong (273 ngay x 1 440), nan 0, md5 64f66a15...
  pred.bin moi seed = pred <SEAL cua seed (gate-sb-<seed>; A1 = pred goc 5dd6bb4c) + 2026 (vd s123 md5 4ee986e9...).
- net015 RAW 2026: ONNX g015x26_f15_cut20251231 (e65e683b), 3 fold: 4 656 471 / 4 952 341 / 5 382 633 dong, nan 0.
- bins A3 2026 (a3lib P1-certified, S1 s1a2x1_cut20251231 json af706dc6, A1 exchangeInfo 20261027 -> 146 id; loai 8 DUP id):
  sha256 20260101 b58099f4..., 20260401 78e4e437..., 20260701 9a914693...; demoted 1,7 % / 8,4 % / 16,3 % (TradFi 2026).
  Dataset chuyendinh/ho5-a3-data26 (private).
- market / ticker 2026: chain ho4p1-chain-y26 (md5 0fcc44d8) / ho4p1-tk26 (273 file md5 khop arts.json). Flags TS_EXT 2026: 20260205-0214,
  0216-0217, 0224-0225, 0611.
- funding phi: snapshot v3 (fb024c40; Aerospike snapshot + crawl fapi cong khai toi 2026-10-01). Lenh 2026 co funding != 0: s123
  Q1 79/119, Q2 107/125, Q3 72/113 (khong con funding = 0 im lang o Q3).

## 3. Bang chi so (MTM NGAY 07:00 cua sim; n theo start, SigmaPnL theo end)

### W
| seed | n | SigmaPnL | ROI | maxDD | Sharpe | % ngay co lenh | E_start | E_end |
|---|---|---|---|---|---|---|---|---|
| a1 | 357.0 | 24030 | 16.53% | -3.08% | 3.03 | 8.79% | 145391 | 169420 |
| s123 | 357.0 | 23982 | 16.65% | -3.06% | 3.01 | 8.79% | 144003 | 167985 |
| s13 | 357.0 | 26375 | 16.31% | -3.18% | 3.01 | 8.79% | 161737 | 188112 |
| s2024 | 357.0 | 23953 | 16.78% | -2.97% | 3.03 | 8.79% | 142744 | 166697 |
| s21 | 357.0 | 24301 | 16.65% | -3.06% | 3.01 | 8.79% | 145914 | 170215 |
| s7 | 357.0 | 22627 | 16.39% | -3.15% | 2.96 | 8.79% | 138042 | 160669 |
| s777 | 357.0 | 26441 | 16.78% | -2.97% | 3.03 | 8.79% | 157565 | 184006 |
| s99 | 357.0 | 26914 | 16.80% | -2.96% | 3.03 | 8.79% | 160201 | 187114 |
| MEAN | 357.0 | 24828 | 16.61% | -3.05% | 3.01 | 8.79% | 149450 | 174277 |

### Q1
| seed | n | SigmaPnL | ROI | maxDD | Sharpe | % ngay co lenh | E_start | E_end |
|---|---|---|---|---|---|---|---|---|
| a1 | 119.0 | 7314 | 5.03% | -3.08% | 2.24 | 6.67% | 145391 | 152705 |
| s123 | 119.0 | 7409 | 5.15% | -3.06% | 2.24 | 6.67% | 144003 | 151412 |
| s13 | 119.0 | 7815 | 4.83% | -3.18% | 2.17 | 6.67% | 161737 | 169552 |
| s2024 | 119.0 | 7506 | 5.26% | -2.97% | 2.27 | 6.67% | 142744 | 150250 |
| s21 | 119.0 | 7507 | 5.14% | -3.06% | 2.24 | 6.67% | 145914 | 153421 |
| s7 | 119.0 | 6773 | 4.91% | -3.15% | 2.13 | 6.67% | 138042 | 144816 |
| s777 | 119.0 | 8285 | 5.26% | -2.97% | 2.27 | 6.67% | 157565 | 165850 |
| s99 | 119.0 | 8452 | 5.28% | -2.96% | 2.28 | 6.67% | 160201 | 168653 |
| MEAN | 119.0 | 7633 | 5.11% | -3.05% | 2.23 | 6.67% | 149450 | 157082 |

### Q2
| seed | n | SigmaPnL | ROI | maxDD | Sharpe | % ngay co lenh | E_start | E_end |
|---|---|---|---|---|---|---|---|---|
| a1 | 128.0 | 11655 | 6.16% | -0.96% | 4.05 | 8.79% | 152705 | 162110 |
| s123 | 128.0 | 11556 | 6.16% | -0.96% | 4.05 | 8.79% | 151412 | 160737 |
| s13 | 128.0 | 12942 | 6.16% | -0.96% | 4.05 | 8.79% | 169552 | 179996 |
| s2024 | 128.0 | 11469 | 6.16% | -0.96% | 4.05 | 8.79% | 150250 | 159504 |
| s21 | 128.0 | 11710 | 6.16% | -0.96% | 4.05 | 8.79% | 153421 | 162870 |
| s7 | 128.0 | 11055 | 6.16% | -0.96% | 4.05 | 8.79% | 144816 | 153736 |
| s777 | 128.0 | 12660 | 6.16% | -0.96% | 4.05 | 8.79% | 165850 | 176066 |
| s99 | 128.0 | 12873 | 6.16% | -0.96% | 4.05 | 8.79% | 168653 | 179041 |
| MEAN | 128.0 | 11990 | 6.16% | -0.96% | 4.05 | 8.79% | 157082 | 166758 |

### Q3
| seed | n | SigmaPnL | ROI | maxDD | Sharpe | % ngay co lenh | E_start | E_end |
|---|---|---|---|---|---|---|---|---|
| a1 | 110.0 | 5061 | 4.51% | -1.48% | 3.63 | 10.87% | 162110 | 169420 |
| s123 | 110.0 | 5017 | 4.51% | -1.48% | 3.63 | 10.87% | 160737 | 167985 |
| s13 | 110.0 | 5619 | 4.51% | -1.48% | 3.63 | 10.87% | 179996 | 188112 |
| s2024 | 110.0 | 4979 | 4.51% | -1.48% | 3.63 | 10.87% | 159504 | 166697 |
| s21 | 110.0 | 5084 | 4.51% | -1.48% | 3.63 | 10.87% | 162870 | 170215 |
| s7 | 110.0 | 4799 | 4.51% | -1.48% | 3.63 | 10.87% | 153736 | 160669 |
| s777 | 110.0 | 5496 | 4.51% | -1.48% | 3.63 | 10.87% | 176066 | 184006 |
| s99 | 110.0 | 5589 | 4.51% | -1.48% | 3.63 | 10.87% | 179041 | 187114 |
| MEAN | 110.0 | 5205 | 4.51% | -1.48% | 3.63 | 10.87% | 166758 | 174277 |

### OOS
| seed | n | SigmaPnL | ROI | maxDD | Sharpe | % ngay co lenh | E_start | E_end |
|---|---|---|---|---|---|---|---|---|
| a1 | 238.0 | 16716 | 10.95% | -1.83% | 3.85 | 9.84% | 152705 | 169420 |
| s123 | 238.0 | 16573 | 10.95% | -1.83% | 3.85 | 9.84% | 151412 | 167985 |
| s13 | 238.0 | 18560 | 10.95% | -1.83% | 3.85 | 9.84% | 169552 | 188112 |
| s2024 | 238.0 | 16448 | 10.95% | -1.83% | 3.85 | 9.84% | 150250 | 166697 |
| s21 | 238.0 | 16794 | 10.95% | -1.83% | 3.85 | 9.84% | 153421 | 170215 |
| s7 | 238.0 | 15854 | 10.95% | -1.83% | 3.85 | 9.84% | 144816 | 160669 |
| s777 | 238.0 | 18156 | 10.95% | -1.83% | 3.85 | 9.84% | 165850 | 184006 |
| s99 | 238.0 | 18461 | 10.95% | -1.83% | 3.85 | 9.84% | 168653 | 187114 |
| MEAN | 238.0 | 17195 | 10.95% | -1.83% | 3.85 | 9.84% | 157082 | 174277 |

### Q3 cho retrain (Lane L)
| seed | SigmaPnL_Q3 | equity dau Q3 | ROI_Q3 | maxDD_Q3 |
|---|---|---|---|---|
| a1 | 5061 | 162110 | 4.51% | -1.48% |
| s123 | 5017 | 160737 | 4.51% | -1.48% |
| s13 | 5619 | 179996 | 4.51% | -1.48% |
| s2024 | 4979 | 159504 | 4.51% | -1.48% |
| s21 | 5084 | 162870 | 4.51% | -1.48% |
| s7 | 4799 | 153736 | 4.51% | -1.48% |
| s777 | 5496 | 176066 | 4.51% | -1.48% |
| s99 | 5589 | 179041 | 4.51% | -1.48% |
| MEAN | 5205 | 166758 | 4.51% | -1.48% |

### DEV (cung thuoc MTM ngay, 2022-01-01..2025-12-30)
| seed | CAGR | maxDD | Sharpe | n |
|---|---|---|---|---|
| a1 | 36.45% | -16.85% | 1.97 | 3025 |
| s123 | 36.42% | -17.33% | 1.95 | 3007 |
| s13 | 40.42% | -16.71% | 2.17 | 2860 |
| s2024 | 36.64% | -16.77% | 1.98 | 2944 |
| s21 | 36.56% | -17.05% | 1.97 | 2969 |
| s7 | 34.91% | -17.69% | 1.90 | 2956 |
| s777 | 39.98% | -12.21% | 2.14 | 2989 |
| s99 | 40.10% | -16.65% | 2.10 | 2942 |
| MEAN | 37.69% | -16.41% | 2.02 | 2962 |

## 4. So sanh mo ta voi DEV (r1-a3 2022-01..2025-12, cung thuoc MTM ngay)
DEV mean: CAGR 37,69 % (MTM phut R1_SEC4: 37,72 %), maxDD -16,41 % (MTM phut: -22,72 %), Sharpe 2,02.
W 2026 mean: CAGR quy nam 22.8 % (ROI 16,61 % / 273 ngay), maxDD -3,05 %, Sharpe 3,01.
Ti le: Sharpe_W/Sharpe_DEV = 1,49 ; CAGR_W/CAGR_DEV = 0,61 ; maxDD_W/maxDD_DEV = 0,19.
Tan suat: 357 lenh/273 ngay (~477/nam) vs DEV ~740/nam; % ngay co lenh 8,8 % vs DEV ~10,9 %.

## 5. Bat thuong / nghi van / gioi han
1. 8 seed gan nhu MOT mau: Q2/Q3/OOS ROI va maxDD giong het nhau giua seed (lenh 2026 trung 93,6-100 %); khac biet chi o quy mo
   equity ke thua tu 2025 va vai lenh Q1. => E0 8/8 khong phai bang chung doc lap; dua vao E0b.
2. PnL OOS tap trung theo dot: 14/27 tuan PnL = 0 (2026-04-01 -> ~05-12 khong lenh dong nao); top-5 lenh = 18 % SigmaPnL OOS,
   top-1 = 4 %. CI80 E0b rong (871 .. 34 365).
3. maxDD la MTM NGAY 07:00 (khong co MTM phut 2026); DEV cho thay MTM phut sau hon ~6 pp. Du cong 9 pp, W van xa nguong R3.
4. Q1-2026 nam trong tap train cua p15 fold_20 -> chi bao cao. OOS = Q2+Q3.
5. Du lieu 2026 la Vision (ADD1 A2): HO5 do "model live tren du lieu Vision", khong phai tai lap DEV; Vision khop DEV thanh phan 13,9-96,5 %.
6. Do phu funding thang 01-03/2026 < 95 % symbol TRADING (mau so = universe 10-2026, canh bao bao thu; ADD3).
7. Su co ky thuat trong luot 5 (da xu ly, khong doi cau hinh): (a) tu kiem funding luot 2 sai thiet ke (DEV funding.bin co 1 ban ghi
   ts == SEAL do ffill 15') -> 4 kernel v1 dung o tu kiem, KHONG chay sim; thay bang tu kiem v2 (manh hon); (b) ho5_sim thieu nhanh
   pred cho A1 -> them A1_PRED (pred goc bundle 5dd6bb4c + 2026); (c) a3_26 M863 duong dan cu mat -> ban 863 cua ho4p1-code
   (md5 9a3e40e9 == manifest chain); (d) score_l5 check doc khoa cu (funding v1, profile_hash) -> sua doc khoa, khong doi tieu chi;
   (e) wait_l5 treo -> fetch tay. Day la sua ky thuat; MASTER nen xac nhan (a)(b) trong ADD4 neu can.
8. 4 kernel v1 loi (s123/s13/s2024/s21, ERROR HO5_FUND_FAIL truoc sim) da duoc push lai cung ten (ban v2 la ban hien tai).

## 6. Duong dan + sha256
- ~/claude_master/w3/ho5/l5/score_l5.json da2791fe99ee8143
- ~/claude_master/w3/ho5/l5/tables_l5.md ea3ff1f6fa2a709f
- ~/claude_master/w3/ho5/l5/SCORE_DEFS_L5.md 03a9345362d38e7a
- ~/claude_master/w3/ho5/l5/score_l5.py da34f31838590609
- ~/claude_master/w3/ho5/l5/diag_l5.json 98db407005f3fb02
- ~/claude_master/w3/ho5/l5/dev_daily.json 90c2362af8d63319
- ~/claude_master/w3/ho5/l5/s1par.json 68b2e24ef0c3215f
- ~/claude_master/w3/ho5/ho5_sim.py a265cb695597302d
- ~/claude_master/w3/ho5/a3/a3_26.py c2b8c3d62ad62b56
- ~/claude_master/w3/ho5/chain/ho5_chainops.py efbbb244fafdd8f9
- ~/claude_master/w3/ho5/a3/data26/DATA26.json bd60d37c0c4352a0
- out/ho5-a3-l26-a1/storage/printDone.csv 56a4624c86e590e5 md5 0f69e6f6
- out/ho5-a3-l26-s123/storage/printDone.csv c5693122799ca9c0 md5 b8a77a46
- out/ho5-a3-l26-s13/storage/printDone.csv d1c666e6544f9164 md5 dcf0f273
- out/ho5-a3-l26-s2024/storage/printDone.csv 3a1864061704daed md5 01301bbc
- out/ho5-a3-l26-s21/storage/printDone.csv 6b0962888ec6244b md5 799255ea
- out/ho5-a3-l26-s7/storage/printDone.csv 3ff15a7420f38e17 md5 cb24a9bb
- out/ho5-a3-l26-s777/storage/printDone.csv b3273bf707e0be79 md5 3116eb0a
- out/ho5-a3-l26-s99/storage/printDone.csv 0fa85468365af217 md5 f50b1b16
- Kernel: chuyendinh/ho5-a3-chain26, chuyendinh/sim-ho5-a3-l26-{a1,s123,s13,s2024,s21,s7,s777,s99} (private). Dataset: ho5-a3-data26, ho5-a3-funding-snap (v3), ho5-a3-mapper-snap.
