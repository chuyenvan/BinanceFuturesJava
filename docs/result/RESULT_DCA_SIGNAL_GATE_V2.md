# RESULT_DCA_SIGNAL_GATE_V2 — DCA leg-2 theo TIN HIEU o vung lo SAU (-30/-40/-50%) vs T170

Chay: 2026-09-14. Pre-reg: `docs/prereg/PREREG_DCA_SIGNAL_GATE_V2.md` (commit f6e5c45, **TRUOC** khi sua code).
Code: commit 130ad24. Dataset `wfo_ds_x1_2021`, config `configs/sim_dev_file_2021.properties`,
`SIM_END_DATE=20251231`, harness `k_runarm.sh`. Build `mvn -o package` OK, **137/137 test PASS**
(134 test cu KHONG SUA MOT DONG + 3 test moi). KHONG cham 242, KHONG `git push`, holdout 2026 nguyen ven.

## 1. CONG PARITY — PASS (byte-identical, tren build MOI)
| cong | tag | profile | md5 printDone (n) | ky vong | ket qua |
|---|---|---|---|---|---|
| OFF const 1.70 | `DS_PARITY_T170_V2` | `x1_gs_t170.properties` | `efb793e2468ca3a7318da0f0ad23d4fc` (1089), b:111070 | = T170 | **PASS** |

md5 ba ban ON: DCA30 `0061d8c4cecc867cd23ae9031e6b76f5` (1116) | DCA40 `c5591a72925075239cdf8fccc7da2fcf` (1104)
| DCA50 `e74d28f410e22e34ff9b9accdbe97c46` (1101).

## 2. BANG CHINH (n = so LEG)
| tag | X | cooldown | n | win% | TSloss% | meanP | mMargin | maxDD% | UW | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **T170** | — | — | 1089 | 88.25 | 9.73 | 5.244 | 1851 | -11.84 | 92 | **111,070** | **29.27** |
| DS_DCA30 | -30% | 24h | 1116 | 88.17 | 9.14 | 5.040 | 945 | -6.10 | 88 | 80,595 | 20.37 |
| DS_DCA40 | -40% | 36h | 1104 | 88.22 | 9.60 | 4.711 | 927 | -6.07 | 88 | 76,716 | 19.06 |
| DS_DCA50 | -50% | 48h | 1101 | 88.19 | 9.54 | 4.677 | 926 | -6.07 | 88 | 76,337 | 18.93 |

## 3. PHIEU LOC 3 TANG — cau tra loi chinh cua bai nay
Do trong sim (`[DS-FUNNEL]`, chi bat khi flag ON). Mau so = so CUM trong printDone.csv cua chinh ban do.

| tag | tong cum | **T1** cham nguong X bat ky luc nao | **T2** cham X khi DA qua cooldown | **T3** THUC SU ban leg-2 |
|---|---|---|---|---|
| DS_DCA30 | 1082 | **81 (7.5%)** | **48 (4.4%)** | **14 (1.3%)** |
| DS_DCA40 | 1080 | **42 (3.9%)** | **15 (1.4%)** | **4 (0.37%)** |
| DS_DCA50 | 1080 | **20 (1.9%)** | **5 (0.46%)** | **1 (0.09%)** |
| (V1 doi chieu: DCA5 | 1103 | — | — | 189 (17.1%) ) |

**Tach bach hai nguyen nhan (dung nhu pre-reg yeu cau, KHONG gop):**
- **(A) Nguong qua sau la nguyen nhan LON NHAT.** Chi 7.5% / 3.9% / **1.9%** so vi the TUNG cham -30 / -40 /
  -50% trong suot doi lenh. Truoc do chung da bi `LOSER_TIME_STOP_HOURS=168`, trailing-hinge hoac hard-SL
  dong. Nghia la du KHONG co cooldown nao, tran tren cua co che cung chi la ~7.5% / 3.9% / 1.9%.
- **(B) Cooldown cat tiep khoang mot nua den ba phan tu** cua phan con lai: 81->48 (-41%), 42->15 (-64%),
  20->5 (-75%). Do la cac cum lao doc RAT NHANH: cham nguong sau trong vong 24-48h dau roi bi dong truoc
  khi het cooldown.
- **(C) Tang cuoi (top-K + EntryGate + budget) cat tiep** 48->14, 15->4, 5->1. Tuc ngay ca khi cum con song
  va da qua cooldown, phan lon KHONG con lot top-8 cua tick nao ma con lo sau nhu the.

=> Ket luan cho cau hoi "hiem khi lo sau vay" hay "cooldown loc mat": **CA HAI, nhung (A) tro^i hon**.
Nguong sau lam mau so nho tu dau; cooldown va tin hieu chi lam no nho them.

## 4. TIE-BREAK voi grid DCA cu — CO xay ra that
`DS_TIEBREAK` (symbol bi giu lai khoi danh sach grid trong cung tick vi signal-gate uu tien):
**22 lan o CA BA config** (DCA30 22, DCA40 22, DCA50 22). Tuc luat KHONG phai ly thuyet suong —
no kich hoat that trong du lieu. Con so giong nhau ba ban la hop ly: grid chi thanh ung vien khi gia
<= -50%, ma muc do thoa CA BA nguong -30/-40/-50, va nhung cum do deu da mo rat lau (qua ca cooldown 48h).
Grid khong mat leg nao: cac tick sau gia van duoi nguong nen no ban lai.

## 5. BA CAU HOI CUA ROUND TRUOC (giu nguyen cach do)
### (i) So lenh
| tag | n_LEG | d_leg% | n_CUM | d_cum% | leg-signal | leg grid cu |
|---|---|---|---|---|---|---|
| T170 | 1089 | — | 1069 | — | 0 | 20 |
| DCA30 | 1116 | +2.5% | 1082 | +1.2% | 14 | 20 |
| DCA40 | 1104 | +1.4% | 1080 | +1.0% | 4 | 20 |
| DCA50 | 1101 | +1.1% | 1080 | +1.0% | 1 | 20 |
(V1 de doi chieu: DCA5 +20.5% leg / +3.2% cum / 189 leg-signal.)

### (ii) lo RAW muc LEG va (iii) lo HIEU DUNG muc VI THE
| tag | lo RAW muc LEG % | d vs T170 | lo HIEU DUNG muc VI THE % | d vs T170 |
|---|---|---|---|---|
| T170 | 12.03 | — | 10.76 | — |
| DCA30 | 12.10 | +0.07pp | 9.98 | -0.78pp |
| DCA40 | 12.05 | +0.02pp | 10.56 | -0.20pp |
| DCA50 | 12.08 | +0.05pp | 10.65 | -0.11pp |

Hieu ung **gan nhu bien mat** so voi V1 (V1: RAW +2.5..+4.1pp, VI THE -1.9..-2.4pp). Ly do hien nhien tu
muc 3: chi 1-14 leg-signal ban ra tren ~1080 cum, khong du de doi mot ti le nao.

Chan doan leg-signal: DCA30 14 leg / PnL +2,909 USD / 14 cum leg-1 dang lo / **10 duoc cuu**;
DCA40 4 leg / +596 / 4 / **2**; DCA50 1 leg / +166 / 1 / **1**.
Leg-signal VAN lai (100% ba config duong), ti le cuu 71%/50%/100% — nhung n qua nho de noi gi them.

## 6. CI khoi-72h x1.21 (x1_rates.py, NREP=2000, SEED=20260905). Hieu = (T170 - config)
| rate | DCA30 [lo,hi] | ngoaiCI | DCA40 [lo,hi] | ngoaiCI | DCA50 [lo,hi] | ngoaiCI |
|---|---|---|---|---|---|---|
| win% | +0.074 [-0.375,+0.475] | - | +0.021 [-0.401,+0.447] | - | +0.054 [-0.356,+0.462] | - |
| TSloss% | +0.594 [-0.363,+1.453] | - | +0.132 [-0.389,+0.607] | - | +0.197 [-0.235,+0.548] | - |
| meanP | +0.204 [-0.582,+1.175] | - | +0.533 [-0.170,+1.377] | - | +0.567 [-0.134,+1.403] | - |
| mP\|SM | +0.513 [-0.326,+1.523] | - | +0.685 [-0.147,+1.656] | - | +0.684 [-0.129,+1.649] | - |
| mP\|SL | -1.265 [-2.866,+0.183] | - | -0.565 [-1.605,+0.391] | - | -0.034 [-0.539,+0.367] | - |
| n | -27 [-58,-3] | YES | -15 [-35,+0.05] | - | -12 [-30,+1.7] | - |
| mMargin | +907 [+720,+1128] | YES | +924 [+733,+1152] | YES | +926 [+734,+1154] | YES |

**So rate CHAT LUONG (win%/TSloss%/meanP) ngoai CI: DCA30 = 0, DCA40 = 0, DCA50 = 0.**
Nguong pre-reg de goi la THANG = **>= 2 theo huong TOT**. Khong config nao dat.

## 7. RANG BUOC CUNG THEO NAM (maxDD<=15%, UW<=120, ret nam>=0, ret quy>=-5%)
| tag | 2021 | 2022 | 2023 | 2024 | 2025 | tong |
|---|---|---|---|---|---|---|
| T170 | PASS | PASS | PASS | PASS | PASS | **PASS** |
| DCA30 | PASS | PASS | PASS | PASS | PASS | **PASS** |
| DCA40 | PASS | PASS | PASS | PASS | PASS | **PASS** |
| DCA50 | PASS | PASS | PASS | PASS | PASS | **PASS** |

Chi tiet (maxDD% / UW / ret_nam% / quy_min%):
- DCA30: 2021 -1.44/37/8.42/2.97 | 2022 -6.10/73/16.38/2.62 | 2023 -1.41/63/19.33/-0.16 | 2024 -3.42/88/20.70/0.49 | 2025 -2.16/52/26.74/0.78
- DCA40: 2021 -1.44/37/8.42/2.97 | 2022 -6.07/73/13.39/2.32 | 2023 -1.41/63/19.33/-0.17 | 2024 -3.58/88/20.37/0.21 | 2025 -2.38/52/24.16/0.78
- DCA50: 2021 -1.44/37/8.42/2.97 | 2022 -6.07/73/13.24/2.32 | 2023 -1.40/63/19.33/-0.16 | 2024 -3.59/88/19.94/0.17 | 2025 -2.38/52/24.17/0.78

## 8. RETURN THEO QUY (%)
| tag | 22Q1 | 22Q2 | 22Q3 | 22Q4 | 23Q1 | 23Q2 | 23Q3 | 23Q4 | 24Q1 | 24Q2 | 24Q3 | 24Q4 | 25Q1 | 25Q2 | 25Q3 | 25Q4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T170 | 4.6 | 5.3 | 5.5 | 2.9 | -0.4 | 16.2 | 5.9 | 10.1 | 11.3 | -0.9 | 7.8 | 11.1 | 14.6 | 1.6 | 1.3 | 12.6 |
| DCA30 | 2.6 | 5.6 | 3.1 | 4.2 | -0.2 | 9.1 | 3.8 | 5.5 | 6.6 | 0.5 | 5.6 | 6.7 | 9.1 | 0.9 | 0.8 | 14.2 |
| DCA40 | 2.6 | 4.8 | 3.1 | 2.3 | -0.2 | 9.1 | 3.8 | 5.5 | 6.6 | 0.2 | 5.6 | 6.7 | 8.6 | 0.9 | 0.8 | 12.4 |
| DCA50 | 2.6 | 4.6 | 3.1 | 2.3 | -0.2 | 9.1 | 3.8 | 5.5 | 6.6 | 0.2 | 5.6 | 6.4 | 8.6 | 0.9 | 0.8 | 12.4 |

## 9. VERDICT — **NULL o CA BA CONFIG. GIU T170.**
Luat pre-reg: THANG = (>=2 rate chat luong ngoai CI theo huong TOT) VA (rang buoc cung PASS moi nam).
- **DCA30**: **0** rate ngoai CI (rang buoc cung PASS) => NULL.
- **DCA40**: **0** rate ngoai CI (rang buoc cung PASS) => NULL.
- **DCA50**: **0** rate ngoai CI (rang buoc cung PASS) => NULL.
Khong config nao dat nguong. Khong tune lai, khong them config. **Incumbent van la T170.**

Luu y trung thuc: rang buoc cung PASS het KHONG phai la diem cong — ba ban nay gan nhu KHONG khac T170
ve hanh vi lenh (chi 1-14 leg-signal), chung chi la "T170 chay o nua don bay". maxDD dep (-6.07..-6.10)
va UW 88 la he qua co hoc cua viec giam don bay, khong phai bang chung cua mot edge moi.

## 10. TAI SAO — va canh bao o PREREG muc 4 da DUNG
PREREG_V2 muc 4 (viet TRUOC khi chay) da bao: nguong sau hon + cooldown dai hon => so lan thoa dieu kien
gan chac chan THAP hon V1, tuc van de "von dong bang" co the TE HON. So do:

| | V1 DCA5 | V1 DCA8 | V1 DCA12 | **V2 DCA30** | **V2 DCA40** | **V2 DCA50** |
|---|---|---|---|---|---|---|
| % cum ban duoc leg-2 | 17.1 | 14.1 | 9.7 | **1.3** | **0.37** | **0.09** |
| mMargin | 916 | 941 | 940 | 945 | 927 | 926 |
| CAGR% | 22.09 | 22.80 | 21.83 | **20.37** | **19.06** | **18.93** |
| equity | 85,904 | 88,159 | 85,083 | **80,595** | **76,716** | **76,337** |

Co che that su la thuan tuy so hoc: **leg-1 bi cat con 50% von cho MOI vi the (100%), nhung von du tru chi
duoc giai ngan cho 0.09-1.3% vi the.** Tuc ~99% von du tru nam khong lam gi ca suot 4.5 nam. CAGR roi
8.9-10.3pp so voi T170 — **te hon ca V1** (-6.5..-7.4pp), dung nhu da canh bao.

Cang day nguong sau, ba con so cang hoi tu ve chinh T170-o-nua-don-bay: DCA50 co dung **MOT** leg-signal
trong ca 4.5 nam, va equity cua no (76,337) gan nhu la can duoi cua ho.

## 11. DIEU BAI NAY DA LOAI TRU (gia tri am tinh, de khong thu lai)
1. **Khong phai do nguong "qua nho".** Gia thuyet cua user o V1 ("5/8/12% la qua nho") da duoc kiem:
   day nguong len 30-50% lam ket qua **XAU DI don dieu**, khong phai tot len. Huong "nguong sau hon" DA DONG.
2. **Khong phai do thieu cooldown.** Them cooldown 24-48h khong cuu duoc gi; no chi cat them mau so.
3. **Nut that THAT SU la ti le giai ngan von du tru**, khong phai chat luong cua leg-2 (leg-2 lai o ca
   6/6 config, V1 lan V2). Bat ky bien the nao con giu cau truc "cat 50% von cua MOI lenh de cho mot su
   kien hiem" deu se that bai theo dung cach nay — do la ket luan chung cho ca V1 va V2.

## 12. KY LUAT
- Tham so khoa tu f6e5c45 (TRUOC khi sua code). KHONG tune sau khi thay ket qua. KHONG them config.
- Cong parity OFF byte-identical PASS TRUOC khi chay bat ky config ON nao (tren build moi).
- 134 test cu KHONG SUA mot dong; 3 test moi kiem: cooldown do tu leg-1 (khong phai tu luc cham nguong),
  va cham DCA50 vs rung dau grid -50% (khoa su kien lam tie-break tro nen bat buoc), va `selectCands`
  giu nguyen semantics top-K (de tap `dsReserved` va lenh moi luon nhin cung mot tap ung vien).
- Flag `SIM_DCA_SIGNAL_GATE` + tie-break de lai trong code, **default OFF**; khong profile production nao khai.
- KHONG deploy 242, KHONG `git push`, holdout 2026 nguyen ven (SIM_END_DATE=20251231).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
