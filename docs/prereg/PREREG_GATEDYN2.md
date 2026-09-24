# PREREG_GATEDYN2 — grid 2 chieu pct × window (time rolling) quanh GD92

Viet TRUOC khi chay bat ky sim nao. Khong sua sau khi thay ket qua.
Yeu cau user 2026-09-09 12:21 (Telegram): *"B va them grid time rolling"* = chon phuong an
(sweep pct) VA mo rong thanh grid ca window days (time rolling).

## 0. Ket qua goc (GATEDYN, da chay)
- Gate cung 0.008: CV quy 0.712, UW 227 (FAIL). GD92 (pct=0.92, W=90d): CV 0.518, UW 116
  (PASS), 0 rate xau ngoai CI, mP|SL +2.54 tot hon. GD88 LOAI (win%/TSloss% xau), GD96 LOAI
  (2023 win% xau).
- Cau hoi con: pct toi uu co nam dung 0.92 khong? W=90 co phai tot nhat khong? => grid 2 chieu.

## 1. Thiet ke — 6 bien the moi (quota 6, khong them sau khi thay so)
Grid pct × W quanh diem thang GD92 (0.92, 90) — diem do da co lam ref, khong chay lai:

| run | pct | W (days) | tag |
|---|---|---|---|
| 1 | 0.90 | 60 | X1_C3_FULL_G90W60 |
| 2 | 0.90 | 120 | X1_C3_FULL_G90W120 |
| 3 | 0.92 | 60 | X1_C3_FULL_G92W60 |
| 4 | 0.92 | 120 | X1_C3_FULL_G92W120 |
| 5 | 0.94 | 60 | X1_C3_FULL_G94W60 |
| 6 | 0.94 | 120 | X1_C3_FULL_G94W120 |

Ref co san: X1_C3_FULL_GD92 (=G92W90), X1_C3_FULL_PARITY_R (=0.008 cung).
Profile copy tu `x1_c3_full.properties` + `SIM_GATE_ROLLING_PCT` + `SIM_GATE_ROLLING_DAYS`.

## 2. Tieu chi (giong GATEDYN, chot TRUOC)
**PRIMARY (do deu):** CV so lenh theo quy giam >= 20% tuong doi so voi parity VA min-quy
khong thap hon parity qua 20%. So sanh tung run voi parity VA voi GD92 (0.92/90).

**RANG BUOC (giu chat luong):** 0 rate chat luong XAU ngoai CI (win%, TSloss%, mP|SM, mP|SL,
meanP) so voi parity tren TOAN cua so — khuon K12/GATEFEAT, CI block 72h x1.21.
**RANG BUOC CUNG:** maxDD tung nam khong xau hon parity qua +3pp; khong nam am (parity 2025
+16.45%); khong quy moi < -5% ma parity khong co. UW <= 120 la muc tieu phu (GD92 dat 116).

**QUY TAC QUYET DINH:**
1. Run nao vi pham rang buoc chat luong/cung -> LOAI ngay.
2. Trong cac run con lai: chon run co CV thap nhat (deu nhat) ma khong kem GD92 o bat ky rate
   nao ngoai CI (khong hy sinh chat luong de lay do deu).
3. Neu GD92 (0.92/90) van tot nhat hoac tuong duong trong CI voi moi run moi -> GIU GD92,
   ghi "grid xac nhan vung 0.90-0.94 x 60-120d deu on dinh, khong lech ngoai CI".
4. Equity bao rieng, KHONG phai tieu chi. Khong chon theo equity.

## 3. Quy trinh
1. Build dataset 1 lan (gate 33f goc + bins X1): `ExportWfoDataset` WFO_SET_PRED=
   ai_pred_market_gate_wfo -> `wfo_ds_x1_gd2` (xoa sau khi cham).
2. Chay 6 run tuan tu (1 slot JVM), profile `x1_gd2_*.properties`.
3. Cham: md5 parity noi bo (khop 2478e90d…), x1_rates.py (rate + CI), `gd_evenness.py`
   (CV/min-quy), so sanh bang muc 2.
4. Ghi `docs/result/RESULT_GATEDYN2.md`, commit. Xoa dataset tam.

## 4. Pham vi
DEV 2022-01-01..2025-12-31. KHONG 2026 (holdout seal). KHONG sua code Java (chi profile copy).
KHONG sua bins. Gate 33-feature goc (GATEFEAT da quyet giu).
