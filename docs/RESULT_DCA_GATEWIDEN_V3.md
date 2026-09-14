# RESULT_DCA_GATEWIDEN_V3 — NOI GATE + cat nua margin + DCA-signal vs T170 GOC

Chay: 2026-09-14. Pre-reg: `docs/PREREG_DCA_GATEWIDEN_V3.md` (commit f95d928, **TRUOC** khi chay).
**KHONG SUA MOT DONG CODE NAO** — HEAD khi chay = `1063dd1` (build cua V2, 137/137 test PASS).
`SIM_GATE_DYN_SCALE` + `SIM_DCA_SIGNAL_*` da tham so hoa day du qua profile, dung nhu da verify o PREREG muc 2.
Dataset `wfo_ds_x1_2021`, `SIM_END_DATE=20251231`, harness `k_runarm.sh`. KHONG 242, KHONG push, holdout 2026 nguyen.

## 1. CONG PARITY — PASS
| cong | tag | profile | md5 printDone (n) | ket qua |
|---|---|---|---|---|
| scale 1.70 + 4 key DCA khai bao nhung `GATE=false` | `DS_PARITY_V3` | `ds_v3_parity.properties` | `efb793e2468ca3a7318da0f0ad23d4fc` (1089), b:111070 | **PASS** |

=> bon key DCA co mat trong profile nhung **vo hai khi flag OFF**. Cong nay manh hon chay lai T170 tran.

md5 ba ban ON: GS100 `9c6d29f3bd3f6da77ec7f0e2251de2f5` (3015) | GS120 `0202fc498becf9c4068fdcf46075acfb` (2177)
| GS140 `09886059d6590f65d73142989a1c6a4a` (1662).

## 2. BANG CHINH vs **T170 GOC** (khong margin-cut, khong DCA)
| tag | gate scale | n(leg) | win% | TSloss% | meanP | mMargin | maxDD% | **UW** | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|---|
| **T170 goc** | 1.70 | 1089 | **88.25** | **9.73** | **5.244** | 1851 | -11.84 | **92** | 111,070 | 29.27 |
| DS_GS100 | 1.00 | 3015 | 82.49 | 13.67 | 3.600 | 1072 | -12.66 | **221** | **121,869** | **31.96** |
| DS_GS120 | 1.20 | 2177 | 82.09 | 12.82 | 3.664 | 937 | -9.77 | **221** | 93,024 | 24.27 |
| DS_GS140 | 1.40 | 1662 | 83.27 | 11.01 | 4.179 | 921 | -8.62 | **221** | 86,635 | 22.32 |
| (T100 tham chieu phu) | 1.00 | 2559 | 84.33 | 15.36 | 3.17 | 1983 | -16.13 | 248 | 121,770 | 31.94 |

**GS100 la ban DAU TIEN trong ca V1/V2/V3 co equity + CAGR VUOT T170** (121,869 / 31.96% vs 111,070 / 29.27%).
Nhung xem muc 4: no VI PHAM tran UW cung.

## 3. (i) SO LENH — noi gate CO keo them lenh THAT (khac han V1/V2)
| tag | n_LEG | d_leg% | **n_CUM (vi the)** | **d_cum%** | leg-signal (leg-2) | leg grid cu |
|---|---|---|---|---|---|---|
| T170 goc | 1089 | — | 1069 | — | 0 | 20 |
| DS_GS100 | 3015 | **+176.9%** | **2604** | **+143.6%** | 359 | 52 |
| DS_GS120 | 2177 | **+99.9%** | **1886** | **+76.4%** | 257 | 34 |
| DS_GS140 | 1662 | **+52.6%** | **1434** | **+34.1%** | 201 | 27 |

**Day la diem KHAC BAN CHAT so voi V1/V2.** O V1/V2, "lenh tang" gan nhu chi la leg-2 cua chinh coin cu
(cum chi +1.0..+3.2%). O V3, so **CUM (coin/vi the moi)** tang **+34% den +144%** — nghia la noi gate
THUC SU keo duoc quan the marginal vao, dung nhu gia thuyet cua user. Leg-signal (201-359) chi chiem
mot phan nho cua muc tang, phan con lai la vi the moi that.

## 4. (ii)+(iii) DCA CO HAP THU DUOC PHAN LOSS TANG THEM KHONG? — **CO, gan nhu hoan toan**
| tag | lo RAW muc LEG % | d vs T170 | lo HIEU DUNG muc VI THE % | d vs T170 | **phan DCA hap thu** |
|---|---|---|---|---|---|
| T170 goc | 12.03 | — | 10.76 | — | — |
| DS_GS100 | 18.87 | **+6.84pp** | 11.83 | **+1.07pp** | 5.77pp / 84% |
| DS_GS120 | 19.71 | **+7.68pp** | 11.93 | **+1.17pp** | 6.51pp / 85% |
| DS_GS140 | 18.89 | **+6.86pp** | 10.60 | **-0.16pp** | 7.02pp / **102%** |

**Co che cua user hoat dong DUNG va manh.** Noi gate lam ti le lo RAW muc leg tang **+6.8..+7.7pp** (dung
nhu du doan), va DCA-signal keo lai **84-102%** phan tang do o muc vi the. Rieng GS140, lo hieu dung o muc
vi the con **THAP HON T170 goc** (10.60 vs 10.76) du so vi the tang 34%.

Chan doan leg-signal:
| tag | leg-signal | PnL leg-signal (USD) | % cum ban duoc leg-2 | cum leg-1 dang lo | duoc CUU | ti le cuu |
|---|---|---|---|---|---|---|
| GS100 | 359 | **+18,078** | 13.8% | 242 | 153 | 63.2% |
| GS120 | 257 | +8,279 | 13.6% | 187 | 130 | 69.5% |
| GS140 | 201 | +7,288 | 14.0% | 147 | 111 | 75.5% |
Funnel (T1 cham -8% / T2 qua cooldown 60p): GS100 963/859, GS120 722/638, GS140 531/459.
Tie-break voi grid cu: GS100 13 lan, GS120 0, GS140 1.

## 5. RUI RO 1 (UW) — **DA XAY RA, va la thu giet ca ba config**
PREREG muc 1 da canh bao truoc: noi gate mot minh tung lam UW no 92 -> 189 (RESULT_REGIME_GATE, FAIL).
Lan nay co margin-cut + DCA di kem — **van khong cuu duoc**:

### UW theo TUNG NAM (tran cung = 120 ngay)
| tag | 2021 | 2022 | 2023 | 2024 | **2025** | tong |
|---|---|---|---|---|---|---|
| **T170 goc** | 37 | 72 | 63 | 92 | **52** | **92 PASS** |
| DS_GS100 | 47 | 64 | 57 | 88 | **221** | **221 FAIL** |
| DS_GS120 | 33 | **113** | 57 | **145 FAIL** | **221** | **221 FAIL** |
| DS_GS140 | 22 | 109 | 37 | 89 | **221** | **221 FAIL** |

Ca ba config deu co **UW = 221 ngay o nam 2025**, gan gap 2 lan tran 120 va gan gap 2.5 lan T170 (52).
Con so 221 giong het nhau ba ban => cung MOT doan underwater 2025, do chinh quan the marginal keo dai ra.
GS120 con FAIL them 2024 (UW 145).

**Doi chieu lich su**: 221 cung dung bang UW cua thi nghiem #52 (2X_HALFSIZE, 221-223). Hai bai khac han ve
co che nhung ra CUNG mot con so — dau hieu manh rang day la mot **thuoc tinh cua quan the marginal**
(lenh giu lau, holdtime 43.9h vs 28.7h theo ANALYSIS_T170_VS_T100 muc 2), khong phai ngau nhien.

## 6. RUI RO 2 (PnL 2025 / theo nam) — **KHONG xay ra o truc PnL; 2025 that ra RAT TOT**
PREREG muc 1 lo rang marginal AM o 2025 (-1,608) se keo return nam 2025 xuong duoi 0. **Khong dung.**

### Return theo TUNG NAM (%)
| tag | 2021 | 2022 | 2023 | 2024 | **2025** |
|---|---|---|---|---|---|
| **T170 goc** | 12.2 | 19.6 | 35.0 | 32.1 | **32.7** |
| DS_GS100 | 7.4 | 16.5 | **36.8** | **43.1** | **42.1** |
| DS_GS120 | 7.5 | 14.7 | 28.1 | 26.4 | 33.2 |
| DS_GS140 | 8.1 | 13.4 | 24.4 | 26.0 | 28.9 |

Khong nam nao am o bat ky config nao. GS100 con VUOT T170 o ca 2023/2024/2025 (36.8/43.1/42.1 vs
35.0/32.1/32.7). Tuc **DCA-signal DA lam duoc dieu ma analysis cu lo**: no cuu phan lo cua marginal
du de 2025 khong am — nhung no **khong** rut ngan duoc doan underwater.

### Return theo TUNG QUY (%)
| tag | 22Q1 | 22Q2 | 22Q3 | 22Q4 | 23Q1 | 23Q2 | 23Q3 | 23Q4 | 24Q1 | 24Q2 | 24Q3 | 24Q4 | 25Q1 | 25Q2 | 25Q3 | 25Q4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T170 goc | 4.6 | 5.3 | 5.5 | 2.9 | -0.4 | 16.2 | 5.9 | 10.1 | 11.3 | -0.9 | 7.8 | 11.1 | 14.6 | 1.6 | 1.3 | 12.6 |
| GS100 | 0.4 | 3.4 | 6.8 | 5.1 | 5.6 | 12.0 | 7.4 | 7.7 | 12.9 | -1.6 | 8.7 | 18.6 | 9.9 | 4.8 | **-1.2** | 24.8 |
| GS120 | 3.2 | 1.8 | 4.4 | 4.5 | 3.5 | 10.1 | 5.7 | 6.4 | 6.9 | **-3.3** | 7.7 | 13.4 | 9.6 | 0.8 | -0.2 | 20.7 |
| GS140 | 3.6 | 1.2 | 3.9 | 4.1 | 0.6 | 11.0 | 4.8 | 6.3 | 9.1 | -2.6 | 7.7 | 10.1 | 8.8 | 1.3 | 1.0 | 15.7 |
quy_min: T170 -0.9 | GS100 -1.6 | GS120 -3.3 | GS140 -2.6 — **tat ca deu con trong tran -5%**. Rang buoc
quy KHONG phai cho chet; cho chet la UW.

## 7. RANG BUOC CUNG THEO NAM (maxDD<=15%, UW<=120, ret nam>=0, ret quy>=-5%)
| tag | 2021 | 2022 | 2023 | 2024 | 2025 | tong |
|---|---|---|---|---|---|---|
| T170 goc | PASS | PASS | PASS | PASS | PASS | **PASS** |
| DS_GS100 | PASS | PASS | PASS | PASS | **FAIL (UW=221)** | **FAIL** |
| DS_GS120 | PASS | PASS | PASS | **FAIL (UW=145)** | **FAIL (UW=221)** | **FAIL** |
| DS_GS140 | PASS | PASS | PASS | PASS | **FAIL (UW=221)** | **FAIL** |

Chi tiet (maxDD% / UW / ret_nam% / quy_min%):
- GS100: 2021 -4.33/47/7.43/0.18 | 2022 -10.83/64/16.50/0.42 | 2023 -1.52/57/36.85/5.57 | 2024 -7.91/88/43.15/-1.62 | 2025 -6.27/**221**/42.06/-1.20
- GS120: 2021 -3.03/33/7.50/1.26 | 2022 -9.77/**113**/14.72/1.83 | 2023 -1.48/57/28.12/3.51 | 2024 -7.59/**145**/26.37/-3.31 | 2025 -6.43/**221**/33.15/-0.16
- GS140: 2021 -1.85/22/8.12/2.95 | 2022 -8.62/109/13.38/1.22 | 2023 -1.31/37/24.36/0.61 | 2024 -5.62/89/26.01/-2.63 | 2025 -5.65/**221**/28.89/1.00
- T170: 2021 -2.46/37/12.21/4.44 | 2022 -11.84/72/19.58/2.90 | 2023 -2.73/63/34.96/-0.37 | 2024 -6.60/92/32.14/-0.92 | 2025 -4.23/52/32.71/1.27

**maxDD thi TOT hon T170 o GS120/GS140** (-9.77 / -8.62 vs -11.84) — margin-cut co tac dung. Chi UW hong.

## 8. CI khoi-72h x1.21 (x1_rates.py, NREP=2000, SEED=20260905). Hieu = (T170 goc - config)
Hieu DUONG o `win%`/`meanP`/`mP|SM` = **T170 TOT hon**; hieu DUONG o `TSloss%` = **config TOT hon**.

| rate | GS100 [lo,hi] | ngoaiCI | GS120 [lo,hi] | ngoaiCI | GS140 [lo,hi] | ngoaiCI |
|---|---|---|---|---|---|---|
| win% | +5.759 [+1.539,+10.031] | **YES (T170 hon)** | +6.161 [+1.902,+10.525] | **YES (T170 hon)** | +4.973 [+2.693,+7.405] | **YES (T170 hon)** |
| TSloss% | -3.931 [-7.992,+0.482] | - | -3.082 [-7.745,+1.778] | - | -1.277 [-3.818,+1.096] | - |
| meanP | +1.644 [-0.301,+3.494] | - | +1.579 [-0.449,+3.604] | - | +1.065 [+0.059,+2.019] | **YES (T170 hon)** |
| mP\|SM | +0.704 [-0.752,+2.146] | - | +0.826 [-0.673,+2.418] | - | +0.728 [-0.127,+1.574] | - |
| mP\|SL | +0.495 [-4.203,+5.137] | - | +0.783 [-3.868,+5.763] | - | +0.929 [-2.801,+4.610] | - |
| n | -1926 [-2840,-1062] | YES | -1088 [-1870,-336] | YES | -573 [-732,-425] | YES |
| mMargin | +779 [+506,+1109] | YES | +914 [+659,+1219] | YES | +930 [+754,+1149] | YES |

**So rate CHAT LUONG ngoai CI theo huong TOT CHO CONFIG: GS100 = 0, GS120 = 0, GS140 = 0.**
(GS100/GS120 co 1 rate ngoai CI la win% nhung theo huong XAU; GS140 co 2 rate ngoai CI — win% VA meanP —
**ca hai deu theo huong XAU**.) Nguong THANG = >= 2 theo huong TOT. Khong config nao dat.

## 9. VERDICT — **NULL o CA BA CONFIG. GIU T170.**
Luat pre-reg: THANG = (>=2 rate chat luong ngoai CI theo huong TOT) VA (rang buoc cung PASS MOI nam).
- **GS100**: 0 rate tot ngoai CI; **FAIL** hard (UW 2025 = 221 > 120). => NULL — du equity 121,869 va
  CAGR 31.96 deu VUOT T170. Day la truong hop "kiem tien nhieu hon nhung vo tran rui ro", khong duoc tinh.
- **GS120**: 0 rate tot; **FAIL** hard (UW 2024 = 145, UW 2025 = 221). => NULL.
- **GS140**: 0 rate tot (2 rate ngoai CI deu xau); **FAIL** hard (UW 2025 = 221). => NULL.
Khong tune lai, khong them config. **Incumbent van la T170.**

## 10. DIEU BAI NAY DA CHUNG MINH (ca mat duong lan mat am — day la gia tri chinh cua V3)
**Gia thuyet co che cua user la DUNG, va V3 la lan dau chung minh duoc bang so:**
1. Noi gate **that su** keo them vi the moi (+34% den +144% so CUM) — khac han V1/V2 noi "lenh tang" chi la
   leg-2 cung coin (+1.0..+3.2% cum). Nut that "ti le giai ngan von du tru" cua V1/V2 **da duoc go**:
   fire-rate leg-2 len 13.6-14.0% va mMargin khong con sup (921-1072 vs 916-945 cua V1).
2. Noi gate **that su** lam ti le lo RAW muc leg tang **+6.8..+7.7pp** — dung nhu user du doan.
3. DCA-signal **that su** hap thu **84-102%** phan lo tang them do o muc vi the (GS140 con ve duoi T170).
4. Va PnL theo nam khong nam nao am — ke ca 2025, nam ma analysis cu lo nhat.

**Nhung no NULL vi mot truc hoan toan khac: UNDERWATER.**
Quan the marginal khong chi "lo nhieu hon" — no **giu lau hon** (holdtime 43.9h vs 28.7h,
ANALYSIS_T170_VS_T100 muc 2). DCA sua duoc **ti le lo** va **do sau DD** (maxDD GS120/GS140 tot hon T170)
nhung **khong sua duoc THOI GIAN**: mot cum duoc DCA cuu ve hoa von van nam duoi dinh equity cu rat lau.
UW 2025 = 221 ngay giong het nhau o ca ba config — va giong het #52 (221-223) du co che khac han.

=> **Ket luan co che: UW la rang buoc BINDING cua moi huong "tang so lenh", bat ke tang bang cach nao
(coin moi o #52, leg-2 o V1/V2, hay noi gate o V3), va DCA KHONG phai cong cu de sua UW.**

## 11. NHUNG GI DA BI LOAI TRU SAU V1+V2+V3
| huong | trang thai |
|---|---|
| DCA leg-2 theo tin hieu o lo NONG (-5/-8/-12%) tren gate T170 | NULL (V1) — von dong bang 83-90% |
| DCA leg-2 o lo SAU (-30/-40/-50%) + cooldown 24-48h | NULL (V2) — von dong bang ~99%, TE HON |
| Noi gate (1.00/1.20/1.40) + margin-cut + DCA | **NULL (V3) — UW 221 o CA BA, vo tran 120** |
| Chia nho margin de mo coin moi (khong DCA) | NULL (#52) — UW 221-223 |
| Gate regime-adaptive (UP 1.00 / NOT-UP 1.70) | NULL (RESULT_REGIME_GATE) — UW 189 |

**Bon trong nam huong chet vi CUNG MOT thu: UW.** Bat ky bai tiep theo theo huong "nhieu lenh hon" deu
phai co mot co che **nham thang vao UW** (vi du: cat lo theo thoi gian chat hon cho rieng nhom marginal,
hoac chan mo lenh moi khi danh muc dang underwater qua N ngay) — chu khong phai them mot lop cuu PnL nua.
Ghi lai de dinh huong; **KHONG tu y chay tiep** — bat ky bai nao nhu vay phai co pre-reg RIENG.

## 12. KY LUAT
- Tham so khoa tu f95d928 (TRUOC khi chay). KHONG tune sau khi thay ket qua. KHONG them config.
- **KHONG SUA MOT DONG CODE NAO** trong V3; chay tren dung build da PASS 137/137 test cua V2.
- Cong parity PASS truoc khi chay bat ky config ON nao.
- Hai rui ro o PREREG muc 1 duoc ghi TRUOC khi chay: rui ro 1 (UW) **da xay ra dung nhu the**;
  rui ro 2 (2025 am) **khong xay ra** — ca hai deu bao cao nguyen van, khong to hong, khong bao chua.
- KHONG deploy 242, KHONG `git push`, holdout 2026 nguyen ven (SIM_END_DATE=20251231).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
