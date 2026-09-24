# RESULT_DCA_SIGNAL_GATE — chia doi margin/lenh + DCA leg-2 theo TIN HIEU vs T170

Chay: 2026-09-14. Pre-reg: `docs/prereg/PREREG_DCA_SIGNAL_GATE.md` (commit 7266bc2, TRUOC khi code mot dong nao).
Code: commit bd45a50 (flag `SIM_DCA_SIGNAL_GATE` default OFF). Dataset `wfo_ds_x1_2021`,
config `configs/sim_dev_file_2021.properties`, `SIM_END_DATE=20251231`, harness `k_runarm.sh`.
Build `mvn -o package` OK, **134/134 test PASS** (128 test cu KHONG SUA MOT DONG + 6 test moi
`DcaSignalGateTest`). KHONG cham 242, KHONG `git push`, holdout 2026 NGUYEN VEN.

## 1. CONG PARITY — PASS (byte-identical)
| cong | tag | profile | keys | md5 printDone (n) | ky vong | ket qua |
|---|---|---|---|---|---|---|
| OFF const 1.70 | `DS_PARITY_T170` | `x1_gs_t170.properties` | 20 (hash 0d0fa221) | `efb793e2468ca3a7318da0f0ad23d4fc` (1089), b:111070 | = T170 | **PASS** |

=> code moi KHONG dung vao duong sim cu. Chi sau khi cong nay PASS moi chay 3 config ON (dung thu tu pre-reg).

Ba profile ON (moi cai = profile T170 + DUNG 4 key, keys=24):
`ds_dca5` hash 5738572ea0c7bb9f | `ds_dca8` hash 2f0ce812c932db51 | `ds_dca12` hash d969c3d36babd033.
md5 printDone: DCA5 `91cba69e359dbda65cb7d10584cb740d` (1312) | DCA8 `e4d7cb4859f64b7230b896a23866ae29` (1276) |
DCA12 `00e99d9edd548acf6cd9a5f6004df166` (1227) — ba ban khac nhau va khac baseline => flag co tac dung that.

## 2. BANG CHINH (wfo_ds_x1_2021, 2021-07..2025-12). n = so LEG (dong printDone.csv)
| tag | X | n | win% | TSloss% | meanP | mMargin | maxDD% | UW(ngay) | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|---|
| **T170** (incumbent) | — | 1089 | **88.25** | 9.73 | 5.244 | 1851 | -11.84 | 92 | **111,070** | **29.27** |
| DS_DCA5 | -5% | 1312 | 86.89 | 7.93 | 5.113 | 916 | -7.62 | 164 | 85,904 | 22.09 |
| DS_DCA8 | -8% | 1276 | 85.66 | **7.76** | **5.316** | 941 | -7.46 | **88** | 88,159 | 22.80 |
| DS_DCA12 | -12% | 1227 | 84.68 | 8.15 | 5.242 | 940 | **-6.66** | **88** | 85,083 | 21.83 |

## 3. TRA LOI TRUC DIEN CAU HOI CUA USER
### (i) So lenh tang bao nhieu?
| tag | n_LEG | d_leg% | n_CUM (vi the) | d_cum% | leg-signal | leg grid cu |
|---|---|---|---|---|---|---|
| T170 | 1089 | — | 1069 | — | 0 | 20 |
| DCA5 | 1312 | **+20.5%** | 1103 | **+3.2%** | 189 | 20 |
| DCA8 | 1276 | **+17.2%** | 1101 | **+3.0%** | 155 | 20 |
| DCA12 | 1227 | **+12.7%** | 1100 | **+2.9%** | 107 | 20 |

Diem quan trong: so LEG tang 13-21% nhung so VI THE chi tang ~3%. Tuc "gia tang lenh" o day gan nhu
HOAN TOAN la nhoi lai chinh coin cu, KHONG phai mo them coin moi — dung thiet ke (va dung cho no
KHAC #52, noi so lenh doc lap tang 1.93-2.36x).

### (ii) Ti le lo RAW muc LEG co TANG khong? — **CO, dung nhu gia thuyet**
### (iii) Ti le lo HIEU DUNG muc VI THE co GIAM khong? — **CO**
| tag | lo RAW muc LEG % | d vs T170 | lo HIEU DUNG muc VI THE % | d vs T170 |
|---|---|---|---|---|
| T170 | 12.03 | — | 10.76 | — |
| DCA5 | 14.56 | **+2.53pp** | 8.34 | **-2.42pp** |
| DCA8 | 16.14 | **+4.11pp** | 8.45 | **-2.31pp** |
| DCA12 | 16.14 | **+4.11pp** | 8.91 | **-1.85pp** |
(RAW = `100*(pnl<=0)` tren moi dong leg. HIEU DUNG = gom cum `(sym,end)`, cong `pnl` cac leg, roi `100*(tong<=0)`.)

**Co che hoat dong DUNG nhu user hinh dung.** Chan doan cu the:
| tag | leg-signal | PnL cua rieng leg-signal (USD) | cum co leg-signal ma leg-1 DANG LO | trong do duoc CUU (tong cum > 0) | ti le cuu |
|---|---|---|---|---|---|
| DCA5 | 189 | +9,179 | 87 | 63 | 72.4% |
| DCA8 | 155 | +10,373 | 104 | 84 | **80.8%** |
| DCA12 | 107 | +8,455 | 90 | 74 | 82.2% |
Leg-signal LAI o ca 3 config, va ~3/4 so cum dang lo o leg-1 duoc keo ve duong. Gia thuyet cua user
ve CO CHE la DUNG.

## 4. CI khoi-72h x1.21 (x1_rates.py, NREP=2000, SEED=20260905, n_eff=96 khoi ca 4 ban)
Bang in hieu **(T170 - config)**: hieu DUONG o `win%`/`meanP` = T170 TOT hon; hieu DUONG o `TSloss%`
= config TOT hon (it stop-loss hon). "Rate chat luong" = win% / TSloss% / meanP (bo n, mMargin).

| rate | DCA5 hieu [lo,hi] | ngoaiCI | DCA8 hieu [lo,hi] | ngoaiCI | DCA12 hieu [lo,hi] | ngoaiCI |
|---|---|---|---|---|---|---|
| win% | +1.356 [-0.479,+3.318] | - | +2.588 [+0.582,+4.364] | YES (T170 hon) | +3.568 [+1.492,+5.310] | YES (T170 hon) |
| TSloss% | +1.807 [+0.150,+3.309] | YES (config hon) | +1.975 [+0.487,+3.395] | YES (config hon) | +1.584 [+0.436,+2.699] | YES (config hon) |
| meanP | +0.131 [-0.618,+0.832] | - | -0.072 [-0.864,+0.667] | - | +0.002 [-0.811,+0.855] | - |
| mP\|SM | +0.627 [-0.194,+1.420] | - | +0.540 [-0.291,+1.369] | - | +0.514 [-0.371,+1.459] | - |
| mP\|SL | -0.019 [-2.484,+2.269] | - | -1.078 [-3.235,+1.133] | - | -0.986 [-2.726,+1.010] | - |
| n | -223 [-357,-102] | YES | -187 [-309,-80] | YES | -138 [-247,-49] | YES |
| mMargin | +935 [+762,+1135] | YES | +910 [+740,+1112] | YES | +911 [+736,+1117] | YES |

**So rate CHAT LUONG ngoai CI theo huong TOT CHO CONFIG**: DCA5 = **1** (TSloss), DCA8 = **1** (TSloss,
va win% ngoai CI theo huong XAU), DCA12 = **1** (TSloss, va win% ngoai CI theo huong XAU).
Nguong pre-reg de goi la THANG = **>= 2**. => khong config nao dat.

## 5. RANG BUOC CUNG THEO NAM (maxDD<=15%, UW<=120, ret nam>=0, ret quy>=-5%)
| tag | 2021 | 2022 | 2023 | 2024 | 2025 | tong |
|---|---|---|---|---|---|---|
| T170 | PASS | PASS | PASS | PASS | PASS | **PASS** |
| DCA5 | PASS | PASS | PASS | PASS | **FAIL (UW=164)** | **FAIL** |
| DCA8 | PASS | PASS | PASS | PASS | PASS | **PASS** |
| DCA12 | PASS | PASS | PASS | PASS | PASS | **PASS** |

Chi tiet (maxDD% / UW / ret_nam% / quy_min%):
- DCA5: 2021 -1.33/37/9.41/3.69 | 2022 -7.62/73/17.75/3.30 | 2023 -1.21/62/20.10/-0.16 | 2024 -4.80/88/22.37/-0.55 | 2025 -4.42/**164**/29.68/0.78
- DCA8: 2021 -1.55/37/8.84/3.64 | 2022 -7.46/73/20.25/3.08 | 2023 -1.41/63/19.74/-0.16 | 2024 -3.74/88/23.26/-0.10 | 2025 -3.85/52/30.44/0.78
- DCA12: 2021 -1.87/37/8.30/3.64 | 2022 -6.66/73/19.21/3.08 | 2023 -1.40/63/19.74/-0.16 | 2024 -3.35/88/23.02/0.42 | 2025 -3.85/52/27.87/0.78
- T170: 2021 -2.46/37/12.21/4.44 | 2022 -11.84/72/19.58/2.90 | 2023 -2.73/63/34.96/-0.37 | 2024 -6.60/92/32.14/-0.92 | 2025 -4.23/52/32.71/1.27

## 6. RETURN THEO QUY (%)
| tag | 22Q1 | 22Q2 | 22Q3 | 22Q4 | 23Q1 | 23Q2 | 23Q3 | 23Q4 | 24Q1 | 24Q2 | 24Q3 | 24Q4 | 25Q1 | 25Q2 | 25Q3 | 25Q4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T170 | 4.6 | 5.3 | 5.5 | 2.9 | -0.4 | 16.2 | 5.9 | 10.1 | 11.3 | -0.9 | 7.8 | 11.1 | 14.6 | 1.6 | 1.3 | 12.6 |
| DCA5 | 3.5 | 5.4 | 3.3 | 4.5 | -0.2 | 9.5 | 4.1 | 5.5 | 7.5 | -0.5 | 6.9 | 7.0 | 9.9 | 1.6 | 0.8 | 15.3 |
| DCA8 | 3.3 | 7.7 | 3.1 | 4.9 | -0.2 | 9.1 | 4.1 | 5.5 | 7.8 | -0.1 | 7.0 | 7.0 | 11.1 | 1.5 | 0.8 | 14.8 |
| DCA12 | 3.4 | 5.6 | 3.1 | 5.9 | -0.2 | 9.1 | 4.1 | 5.5 | 7.8 | 0.4 | 6.4 | 6.7 | 10.9 | 0.9 | 0.8 | 13.3 |

Cac config thua T170 o gan nhu MOI quy co song manh (23Q2 16.2 vs 9.1-9.5; 23Q4 10.1 vs 5.5;
24Q1 11.3 vs 7.5-7.8; 24Q4 11.1 vs 6.7-7.0) va chi hon o 25Q4 (12.6 vs 13.3-15.3) — dung hinh dang
cua mot danh muc bi GIAM DON BAY chu khong phai danh muc "chat luong hon".

## 7. VERDICT — **NULL o CA BA CONFIG. GIU T170.**
Luat pre-reg: THANG = (>=2 rate chat luong ngoai CI theo huong TOT) VA (rang buoc cung PASS moi nam).
- **DCA5**: 1 rate tot ngoai CI, va **FAIL rang buoc cung** (UW 2025 = 164 > 120). => NULL.
- **DCA8**: 1 rate tot (TSloss) NHUNG win% ngoai CI theo huong XAU; rang buoc cung PASS. => NULL.
- **DCA12**: 1 rate tot (TSloss) NHUNG win% ngoai CI theo huong XAU; rang buoc cung PASS. => NULL.
Khong config nao dat nguong. Khong tune lai, khong them config, khong doi baseline. **Incumbent van la T170.**

## 8. TAI SAO — nguyen nhan so hoc (khong dien giai mem)
Co che DCA-signal chay DUNG (muc 3): lo muc vi the giam 1.9-2.4pp, leg-signal lai, 72-82% cum lo duoc cuu.
Nhung no KHONG bu duoc phan von bi rut ra:
- `mMargin` roi 1851 -> 916-941 (**-50%**). Ngay ca khi tinh o muc CUM (gop ca leg-signal), margin trung binh
  cum chi 1049-1091 vs 1886 cua T170 (**~57%**).
- Ly do: leg-signal chi ban cho **9.7-17%** so cum (107-189 / ~1100). **83-90% so vi the song ca doi voi
  dung 50% von** — dung nhu pre-reg da bao truoc la CHAP NHAN, va do chinh la cho lam gay CAGR.
- Ket qua: CAGR 29.27 -> 21.8-22.8 (**-6.5 den -7.4pp**), equity 111,070 -> 85,083-88,159.

## 9. KHAC #52 o cho nao (ghi lai de khong lam lai lan ba)
| | #52 2X_HALFSIZE (def3db1) | Bai nay (DCA-signal) |
|---|---|---|
| von du duoc dung de | mo COIN MOI (lenh doc lap) | nhoi lai CHINH coin cu, chi khi con pass tin hieu |
| so vi the | 1.93-2.36x | chi +2.9-3.2% |
| UW | **no 92 -> 221-223 (VI PHAM)** | 88-88 (DCA8/DCA12, **TOT hon ca T170**), 164 o DCA5 |
| maxDD | nong hon | -6.66..-7.62 vs -11.84 (tot hon nhieu) |
| CAGR | 21.4-24.0 | 21.8-22.8 |
| chat luong lenh | meanP 5.24 -> 3.7-4.3 (pha loang) | meanP 5.24 -> 5.11-5.32 (**GIU nguyen**) |

=> DCA-signal **thang #52 ro rang o rui ro va o chat luong lenh**: no KHONG pha loang meanP (vi khong nap
lenh marginal) va KHONG keo dai UW (vi khong giu them vi the moi). Ca hai deu nhat quan voi thiet ke.
Nhung ca hai bai cung chet vi MOT nguyen nhan: **rut 50% von ra khoi vong quay ma khong tra lai duoc du**.

## 10. QUAN SAT (KHONG phai tieu chi pre-reg, KHONG duoc dung lam ket luan)
Ti so CAGR / |maxDD|: T170 = 2.47 | DCA5 = 2.90 | DCA8 = **3.06** | DCA12 = **3.28**.
Tuc theo don vi rui ro, ba config deu tot hon T170. Dieu do GOI Y mot cau hoi khac: neu bu lai don bay
(vd nang F_BASE de mMargin ve ~1851) thi co giu duoc loi the rui ro khong?
**KHONG duoc tra loi cau do trong bai nay**: ti so nay khong nam trong luat thang/thua da khoa, va thu
"nang don bay cho den khi thang" chinh la tune sau khi thay ket qua. Neu muon, do phai la mot bai RIENG
voi pre-reg RIENG (chon truoc DUNG mot muc F_BASE, chay mot lan). Ghi lai o day de khong bi quen,
KHONG phai de tu y lam tiep.

## 11. KY LUAT
- Tham so khoa tu 7266bc2 (truoc khi code). KHONG tune sau khi thay ket qua. KHONG them config.
- Cong parity byte-identical PASS TRUOC khi chay bat ky config ON nao.
- 128 test cu KHONG SUA mot dong; 6 test moi (`DcaSignalGateTest`) kiem dung hai manh de vo:
  (a) flag OFF => `gridLegCount == size()`; (b) flag ON => leg-signal khong day ladder grid len bac.
- Flag `SIM_DCA_SIGNAL_GATE` de lai trong code, **default OFF**, khong profile production nao khai bao.
- KHONG deploy 242, KHONG `git push`, holdout 2026 nguyen ven (SIM_END_DATE=20251231).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
