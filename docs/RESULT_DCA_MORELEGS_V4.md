# RESULT_DCA_MORELEGS_V4 — 3 nhanh "nhieu lenh hon" (A/B/C): NULL 8/8, KHONG nhanh nao thoat tran UW 120

Chay: 2026-09-14/15. Pre-reg: `docs/PREREG_DCA_MORELEGS_V4.md` (commit b4548b5, **TRUOC** khi chay sweep).
**KHONG SUA MOT DONG CODE NAO** — HEAD khi chay `b4548b5` (jar cua V2/V3, 137/137 test PASS).
Dataset `wfo_ds_x1_2021`, `SIM_END_DATE=20251231`, harness `k_runarm.sh`. KHONG 242, KHONG push, holdout 2026 nguyen.

## 1. CONG PARITY — PASS
`DS_PARITY_V4` (profile `ds_v3_parity.properties`: scale 1.70 + 4 key DCA khai bao nhung `GATE=false`)
=> md5 **`efb793e2468ca3a7318da0f0ad23d4fc`** (n=1089, b:111070). PASS truoc khi chay bat ky config nao.

Moi profile cua 8 config duoc sinh tu `ds_gs100.properties` bang MOT lenh `sed` doi DUNG MOT dong
(da verify: `diff` = dung 1 cap dong cho ca 8 file).

## 2. BUOC 0 — CHAN DOAN: UW 221 la **CORRELATED SYSTEMIC EVENT** (tra loi cau hoi cua user)
Khung ngay cua doan underwater DAI NHAT (`research/analysis/uw_window.py`, doc equity cu, khong rerun sim):

| tag | ho co che | UW | dinh truoc DD | bat dau UW | hoi ve dinh |
|---|---|---|---|---|---|
| **RG_A_T170** (PASS hard) | baseline hep | **92** | 2024-04-09 | 2024-04-10 | 2024-07-11 |
| **DS_DCA8** (PASS hard) | T170 + margin-cut + DCA | **88** | 2024-04-09 | 2024-04-10 | 2024-07-07 |
| X1_2XH_V1 | #52 chia margin deu | 223 | 2025-03-03 | **2025-03-04** | 2025-10-13 |
| X1_2XH_V2 | #52 chia margin deu | 222 | 2025-03-03 | **2025-03-04** | 2025-10-12 |
| X1_2XH_V3 | #52 chia margin deu | 221 | 2025-03-03 | **2025-03-04** | 2025-10-11 |
| DS_GS100 | V3 noi gate + DCA | 221 | 2025-03-03 | **2025-03-04** | 2025-10-11 |
| DS_GS120 | V3 noi gate + DCA | 221 | 2025-03-03 | **2025-03-04** | 2025-10-11 |
| DS_GS140 | V3 noi gate + DCA | 221 | 2025-03-03 | **2025-03-04** | 2025-10-11 |

**=> TRUNG KHIT TUNG NGAY.** Sau config that bai thuoc HAI ho co che khac han nhau deu vao underwater
**dung 2025-03-04** (dinh 2025-03-03) va hoi ve dinh **2025-10-11..13**. Day la **CORRELATED SYSTEMIC
EVENT**, **KHONG** phai statistical artifact rieng cua tung co che. Hai config PASS co doan UW dai nhat o
cua so hoan toan khac (2024-04-10 -> 2024-07).

**Khung ngay can in cho user: 2025-03-04 → 2025-10-11 (221 ngay).**

Trong dung khung do (PnL THUC HIEN cua lenh dong trong khung):
| tag | n_leg | PnL | win% |
|---|---|---|---|
| RG_A_T170 (hep) | 61 | **+1,419** | 81.97 |
| DS_GS100 | 313 | **-3,399** | 76.68 |
| DS_GS120 | 198 | **-3,213** | 74.24 |
| DS_GS140 | 136 | **-1,937** | 73.53 |
| X1_2XH_V3 | 142 | **-2,653** | 73.94 |
Quan the HEP lai; moi quan the RONG lo. Khop `ANALYSIS_T170_VS_T100` muc 4b (marginal -13,787 khi chop).

## 3. BUOC 0 — CHI TIET GS100 (moc tham chieu cho nhanh B va C)
| tag | n_cum | conc_tb | conc_p50 | conc_p95 | conc_max | hold_p50(h) | hold_p90(h) | hold_tb(h) |
|---|---|---|---|---|---|---|---|---|
| **DS_GS100** | 2604 | **2.43** | 0 | 12 | 32 | 10.2 | 168.0 | 36.5 |
| RG_A_T170 | 1069 | 0.81 | 0 | 5 | 27 | 4.8 | 154.6 | 28.8 |
`conc_p50 = 0` o CA HAI: danh muc RONG hon nua so gio. hold_p90 = 168h = `LOSER_TIME_STOP_HOURS`.

Rate + rui ro theo nam (GS100 vs T170):
| tag | nam | n | win% | TSloss% | meanP | mMargin | pnl | maxDD% | UW | ret_nam% |
|---|---|---|---|---|---|---|---|---|---|---|
| GS100 | 2021 | 342 | 80.99 | 17.84 | 2.762 | 526 | 2,601 | -4.33 | 47 | 7.43 |
| GS100 | 2022 | 495 | 78.99 | 16.57 | 2.369 | 548 | 6,203 | -10.83 | 64 | 16.50 |
| GS100 | 2023 | 319 | 88.71 | 12.85 | 6.117 | 967 | 16,099 | -1.52 | 57 | 36.85 |
| GS100 | 2024 | 775 | 85.55 | 12.26 | 4.697 | 1,057 | 25,884 | -7.91 | 88 | 43.15 |
| GS100 | 2025 | 1084 | 80.54 | 12.27 | 2.900 | 1,525 | 36,082 | -6.27 | **221** | 42.06 |
| T170 | 2021 | 149 | 92.62 | 7.38 | 4.368 | 973 | 4,273 | -2.46 | 37 | 12.21 |
| T170 | 2022 | 198 | 83.84 | 11.11 | 3.861 | 1,171 | 7,688 | -11.84 | 72 | 19.58 |
| T170 | 2023 | 126 | 88.10 | 15.87 | 8.074 | 1,993 | 16,331 | -2.73 | 63 | 34.96 |
| T170 | 2024 | 281 | 90.04 | 10.68 | 4.769 | 2,112 | 20,403 | -6.60 | 92 | 32.14 |
| T170 | 2025 | 335 | 87.46 | 6.87 | 5.784 | 2,372 | 27,375 | -4.23 | 52 | 32.71 |

## 4. BANG CHINH — 8 config, so voi **T170 GOC** VA voi **GS100**
| nhanh | tag | bien doi | n(leg) | win% | TSloss% | meanP | mMargin | maxDD% | **UW** | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| — | **T170 goc** | scale 1.70 | 1089 | **88.25** | **9.73** | **5.244** | 1851 | -11.84 | **92** | 111,070 | 29.27 |
| — | **GS100** (moc V3) | scale 1.00 | 3015 | 82.49 | 13.67 | 3.600 | 1072 | -12.66 | 221 | **121,869** | **31.96** |
| A | DS_GS085 | scale 0.85 | 4096 | 79.30 | 17.21 | 2.687 | 951 | -13.94 | 236 | 92,769 | 24.20 |
| A | DS_GS070 | scale 0.70 | 6318 | 76.31 | 20.10 | 1.819 | 693 | **-26.35** | 400 | 57,089 | 11.49 |
| A | DS_GS055 | scale 0.55 | 11562 | 74.32 | 22.38 | 1.314 | 611 | **-41.68** | 359 | 52,804 | 9.57 |
| B | DS_K10_GS100 | K 8->10 | 3526 | 81.85 | 15.00 | 3.312 | 957 | **-16.59** | 279 | 108,902 | 28.70 |
| B | DS_K12_GS100 | K 8->12 | 4005 | 81.40 | 16.10 | 3.246 | 879 | **-20.04** | 425 | 107,765 | 28.40 |
| C | DS_DCA20_GS100 | X -8%->-20% | 2788 | 82.57 | 14.24 | 3.448 | 1070 | -10.99 | 221 | 108,527 | 28.60 |
| C | DS_DCA25_GS100 | X -8%->-25% | 2734 | 83.32 | 14.19 | 3.450 | 1082 | **-10.45** | 212 | 108,822 | 28.68 |
| C | DS_DCA30_GS100 | X -8%->-30% | 2693 | 83.88 | 14.26 | 3.447 | 1081 | -10.66 | **211** | 105,495 | 27.80 |

md5 printDone: GS085 `0f1a345e…` | GS070 `cfca5c34…` | GS055 `b37e6484…` | K10 `f4f64ef1…` | K12 `220428264…`
| DCA20 `71f825d6…` | DCA25 `bbdd7a6e…` | DCA30 `43a422bb…` (tam ban khac nhau => 8 bien deu co tac dung).

## 5. **UW THEO TUNG NAM** — cau hoi cot loi: co nhanh nao thoat tran 120 khong?
| tag | 2021 | 2022 | 2023 | 2024 | **2025** | maxDD min | quy min |
|---|---|---|---|---|---|---|---|
| **T170 goc** | 37 | 72 | 63 | 92 | **52** | -11.84 | -0.92 |
| GS100 | 47 | 64 | 57 | 88 | **221** | -10.83 | -1.62 |
| DS_GS085 | 47 | 53 | 53 | **114** | **236** | -13.94 | **-9.83** |
| DS_GS070 | 34 | **318** | 63 | **242** | **302** | **-26.35** | **-13.36** |
| DS_GS055 | 67 | **144** | 85 | **263** | **359** | **-41.68** | **-21.83** |
| DS_K10_GS100 | 46 | **187** | 33 | 88 | **223** | -13.46 | -2.08 |
| DS_K12_GS100 | 46 | **224** | 53 | 86 | **222** | **-16.10** | -2.01 |
| DS_DCA20_GS100 | 47 | 64 | 57 | 92 | **221** | -10.23 | -2.42 |
| DS_DCA25_GS100 | 47 | 64 | 57 | 91 | **183** | -9.97 | -1.64 |
| DS_DCA30_GS100 | 47 | 63 | 57 | 91 | **183** | -10.03 | -2.28 |

**KHONG CONFIG NAO co UW <= 120 o tat ca cac nam.** Gan nhat = DCA25/DCA30 (2025 UW **183**) — van
gap 1.5 lan tran, va van gap 3.5 lan T170 (52).

### Khung ngay cua doan UW dai nhat cua tung config moi (doi chieu truc tiep voi muc 2)
| tag | UW | dinh truoc | bat dau UW | hoi ve dinh | thoat khung 2025-03-04? |
|---|---|---|---|---|---|
| DS_GS085 | 236 | 2025-03-03 | **2025-03-04** | 2025-10-26 | KHONG (y nguyen khung) |
| DS_GS070 | 400 | 2022-02-16 | 2022-02-17 | 2023-03-24 | doi khung nhung TE HON nhieu |
| DS_GS055 | 359 | 2025-01-05 | 2025-01-06 | **CHUA HOI** | khong hoi ve dinh trong cua so |
| DS_K10_GS100 | 279 | 2021-11-15 | 2021-11-16 | 2022-08-22 | doi khung, van 279 |
| DS_K12_GS100 | 425 | 2021-11-15 | 2021-11-16 | 2023-01-15 | doi khung, van 425 |
| DS_DCA20_GS100 | 221 | 2025-03-03 | **2025-03-04** | **2025-10-11** | KHONG (trung KHIT GS100) |
| DS_DCA25_GS100 | 212 | 2021-11-15 | 2021-11-16 | 2022-06-16 | doi khung, van 212 |
| DS_DCA30_GS100 | 211 | 2021-11-15 | 2021-11-16 | 2022-06-15 | doi khung, van 211 |

Doc: khi mot config "thoat" khung 2025-03-04 thi no chi vi mot doan UW KHAC (2021-11 hoac 2022-02) da
DAI HON — khong phai vi doan 2025 bien mat. DCA25/DCA30 ha duoc UW 2025 tu 221 xuong 183 (DCA ban som hon
o quan the rong => cuu duoc mot phan) nhung doan 2021-11 lai thanh doan dai nhat (211-212).

## 6. CI khoi-72h x1.21 (hieu = T170 goc - config). Rate chat luong = win% / TSloss% / meanP
Quy uoc huong: `win%` duong = T170 hon (**XAU** cho config); `TSloss%` **am** = T170 it stop-loss hon
(**XAU** cho config); `meanP` duong = T170 hon (**XAU** cho config).

| tag | win% | TSloss% | meanP | so rate ngoai CI | **so rate ngoai CI theo huong TOT** |
|---|---|---|---|---|---|
| DS_GS085 | +8.949 [5.152,12.980] YES | -7.478 [-11.436,-3.214] YES | +2.556 [0.704,4.433] YES | 3 | **0** |
| DS_GS070 | +11.940 [8.025,15.717] YES | -10.368 [-14.254,-6.247] YES | +3.424 [1.401,5.450] YES | 3 | **0** |
| DS_GS055 | +13.925 [10.412,17.642] YES | -12.641 [-16.062,-9.010] YES | +3.930 [2.081,5.688] YES | 3 | **0** |
| DS_K10_GS100 | +6.397 [2.177,10.832] YES | -5.269 [-9.470,-0.750] YES | +1.932 [-0.067,3.846] - | 2 | **0** |
| DS_K12_GS100 | +6.848 [2.634,11.124] YES | -6.371 [-10.624,-1.772] YES | +1.998 [0.026,3.870] YES | 3 | **0** |
| DS_DCA20_GS100 | +5.678 [1.462,9.834] YES | -4.506 [-8.532,-0.164] YES | +1.796 [-0.124,3.707] - | 2 | **0** |
| DS_DCA25_GS100 | +4.925 [0.760,9.152] YES | -4.458 [-8.481,-0.016] YES | +1.794 [-0.116,3.663] - | 2 | **0** |
| DS_DCA30_GS100 | +4.362 [0.260,8.571] YES | -4.525 [-8.590,-0.218] YES | +1.796 [-0.146,3.634] - | 2 | **0** |

**MOI rate ngoai CI o CA 8 CONFIG deu theo huong XAU cho config.** Nguong THANG = >= 2 theo huong TOT.

## 7. VERDICT TUNG CONFIG (khong gop nhanh)
Luat: THANG = (>=2 rate chat luong ngoai CI theo huong TOT) VA (rang buoc cung PASS MOI nam:
maxDD<=15%, UW<=120, ret nam>=0, ret quy>=-5%).

| tag | rate tot ngoai CI | hard-constraint | **verdict** | vi pham |
|---|---|---|---|---|
| DS_GS085 | 0 | FAIL | **NULL** | UW 2024=114 (sat), **2025=236**, quy min -9.83 |
| DS_GS070 | 0 | FAIL | **NULL** | maxDD -26.35, UW 2022=318/2024=242/2025=302, quy -13.36 |
| DS_GS055 | 0 | FAIL | **NULL** | maxDD -41.68, UW 2025=359, quy -21.83 |
| DS_K10_GS100 | 0 | FAIL | **NULL** | maxDD -16.59, UW 2022=187 / 2025=223 |
| DS_K12_GS100 | 0 | FAIL | **NULL** | maxDD -20.04, UW 2022=224 / 2025=222 |
| DS_DCA20_GS100 | 0 | FAIL | **NULL** | UW 2025=221 |
| DS_DCA25_GS100 | 0 | FAIL | **NULL** | UW 2025=183 |
| DS_DCA30_GS100 | 0 | FAIL | **NULL** | UW 2025=183 |

**NULL 8/8. KHONG config nao thoat tran UW 120. Incumbent van la T170.**
Khong tune lai, khong them config.

## 8. DOC TUNG NHANH
### Nhanh A (ha tiep gate scale) — **DONG HAN, xau DON DIEU**
scale 1.70 -> 1.00 -> 0.85 -> 0.70 -> 0.55:
n 1089 -> 3015 -> 4096 -> 6318 -> **11562**; CAGR 29.27 -> 31.96 -> 24.20 -> 11.49 -> **9.57**;
maxDD -11.84 -> -12.66 -> -13.94 -> -26.35 -> **-41.68**; meanP 5.24 -> 3.60 -> 2.69 -> 1.82 -> **1.31**.
**GS100 (scale 1.00) la DINH cua duong cong CAGR**; di tiep xuong duoi 1.00 lam SUP ca loi nhuan lan rui ro.
Gia thuyet "nhieu lenh = on dinh hon" **bi bac bo truc tiep** o day: n gap 10.6 lan T170 ma maxDD gap 3.5
lan va CAGR con 1/3. Them lenh o day khong pha loang rui ro — no NAP them lenh chat luong thap
(meanP 1.31 vs 5.24) va lam danh muc dong pha theo cung mot dot chop.

### Nhanh B (tang K tren nen GS100) — **xau, va doi cho dau vo**
K 8 -> 10 -> 12: maxDD -12.66 -> -16.59 -> **-20.04** (K10/K12 vo tran 15%); UW 2022 64 -> 187 -> **224**.
Dang chu y: tang K **doi doan UW dai nhat sang 2021-11 -> 2022** (bear 2022) thay vi 2025. Tuc K lon lam
danh muc phoi nhiem nang hon vao bear 2022. CAGR gan nhu khong doi (28.70 / 28.40 vs 31.96) => **tra them
rui ro ma khong duoc them loi nhuan**. Khop huong voi `RESULT_K_DENSITY` (K16 tren T170 lam UW=164).

### Nhanh C (DCA nguong sau tren nen GS100) — **tot nhat trong 8, nhung van NULL**
X -8% -> -20% -> -25% -> -30%: maxDD **-12.66 -> -10.99 -> -10.45 -> -10.66** (TOT hon GS100 va tot hon
ca T170 -11.84); win% 82.49 -> 82.57 -> 83.32 -> **83.88**; UW 2025 221 -> 221 -> **183 -> 183**.
CAGR 31.96 -> 28.60 -> 28.68 -> 27.80 (mat ~3.3pp so GS100).

**Phat hien dang chu y (khac han V2)**: tren nen GS100, nguong sau **KHONG** lam co che chet nhu tren nen
T170 hep. O V2 (nen T170), X=-30% chi con 14 leg-signal / 1082 cum (1.3%) va ket qua sup; o V3/V4
(nen GS100) X=-25/-30% van giu duoc maxDD tot hon va ha duoc UW 2025 tu 221 xuong 183. Ly do dung nhu
pre-reg muc 3 da du doan: quan the GS100 giu lenh lau hon va nhieu hon nen ti le cham nguong sau cao hon
han. **Du doan o PREREG muc 6 rang nhanh C "khong dong toi UW" la SAI** — no co ha UW (221->183), chi la
khong du de qua tran 120. Ghi ro vi day la diem pre-reg doan sai.

## 9. TRA LOI TRUC DIEN GIA THUYET CUA USER
User: "nhieu lenh hon = on dinh hon" (it lenh de overfit; nhieu lenh pha loang rui ro 1 coin chet).
**Du lieu KHONG ung ho o truc rui ro danh muc**, va ly do la co che chu khong phai thong ke:

| n (leg) | 1089 | 2693 | 3015 | 4005 | 4096 | 6318 | 11562 |
|---|---|---|---|---|---|---|---|
| tag | T170 | DCA30 | GS100 | K12 | GS085 | GS070 | GS055 |
| maxDD% | -11.84 | -10.66 | -12.66 | -20.04 | -13.94 | -26.35 | -41.68 |
| UW max | 92 | 211 | 221 | 425 | 236 | 400 | 359 |

Tang n tu 1089 len ~2700-3000 giu duoc maxDD (tham chi DCA30 tot hon T170) nhung **UW van no 2.3x**.
Tang tiep len 4000+ thi ca maxDD lan UW deu sup. **"Pha loang rui ro 1 coin chet" co xay ra o truc maxDD
(do sau), NHUNG khong xay ra o truc UW (thoi gian)** — vi cac lenh them vao **khong doc lap**: chung
cung bi mot dot chop macro danh (bang muc 2), nen chung KHONG pha loang ma CONG DON theo thoi gian.
Ve lo ngai overfit: dung la n=1089 mong, nhung cach chua khong phai la nap them lenh chat luong thap
(meanP tut 5.24 -> 1.31 khi n x10.6) — do la doi mot rui ro nay lay mot rui ro khac.

## 10. TONG KET NHUNG GI DA BI LOAI TRU (V1 -> V4)
| huong | ket qua |
|---|---|
| DCA leg-2 o lo nong (-5/-8/-12%) tren gate T170 | NULL (V1) |
| DCA leg-2 o lo sau (-30/-40/-50%) + cooldown 24-48h | NULL (V2) |
| Noi gate 1.00/1.20/1.40 + margin-cut + DCA | NULL (V3) — UW 221 |
| **Noi gate tiep 0.85/0.70/0.55** | **NULL (V4-A) — xau don dieu, maxDD toi -41.68** |
| **Tang K 10/12 tren nen GS100** | **NULL (V4-B) — maxDD -16.59/-20.04, doi UW sang bear 2022** |
| **DCA nguong sau -20/-25/-30% tren nen GS100** | **NULL (V4-C) — tot nhat: maxDD -10.45, UW 2025 183** |
| Chia nho margin mo coin moi (#52) | NULL — UW 221-223 |
| Gate regime-adaptive | NULL — UW 189 |

**Muoi mot huong, tat ca chet vi UW.** Va buoc 0 cua V4 cho biet TAI SAO: cac ban "nhieu lenh" deu vao
underwater **dung cung mot ngay 2025-03-04** — do la mot su kien he thong cua quan the marginal, khong
phai nhieu thong ke rieng le cua tung co che.

**=> Ket luan cho vong sau (KHONG tu y chay, phai co pre-reg RIENG):** moi co che "them lenh" da duoc thu
deu khong dong toi duoc bien so quyet dinh la THOI GIAN UNDERWATER. Huong con lai phai nham THANG vao no,
vi du: (a) time-stop chat hon cho rieng nhom marginal; (b) chan mo lenh moi khi danh muc da underwater
qua N ngay; (c) chap nhan tran UW cao hon nhu mot quyet dinh cua user (doi tieu chi, khong phai doi model).
Ghi lai de dinh huong; **KHONG chay tiep khi chua co pre-reg**.

## 11. KY LUAT
- Tham so khoa tu b4548b5 (TRUOC khi chay). KHONG tune sau ket qua. KHONG them config.
- **KHONG SUA MOT DONG CODE NAO** trong V4; ca 8 profile sinh bang `sed` doi DUNG 1 dong tu `ds_gs100`.
- Cong parity PASS truoc khi chay. Buoc 0 chi doc output cu, khong rerun sim.
- Du doan o PREREG muc 6 co mot y SAI (nhanh C co ha UW) — da ghi ro o muc 8, khong sua pre-reg.
- KHONG deploy 242, KHONG `git push`, holdout 2026 nguyen ven (SIM_END_DATE=20251231).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
