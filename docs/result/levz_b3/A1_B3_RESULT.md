# A1_B3_RESULT - audit ket qua chay that LEVZ B3 (run 16:30-16:57, sha256 code == ban A1 da audit) - 2026-11-26
A1 tu tinh lai bang code rieng (LightGBM tham so prereg, n_jobs 1, 10 seed; GroupKFold theo quy; port.py B1 goc). Khong goi wfo_b3 / cv_b3.

## KET LUAN: KET QUA XAC NHAN. "B3 KHONG DAT" la DUNG (Q1, Q2, Q3, Q5, Q6, Q7, Q8 truot; chi Q4 dat; C1, C2 truot).

## Bang so A1 vs report (WFO 2025 = chinh thuc)
| so | A1 | report | lech |
|---|---|---|---|
| n train / test 2025 | 25 294 / 3 531 | 25 294 / 3 531 | 0 |
| exit 2025 / 2024 | xi 72 H24 / xi 170 H336 | nhu nhau | 0 |
| T20 M1 2025 (q80 OOF) | 0.0220397 | 0.0220397 | 0 |
| n chon CHINH | 1 306 | 1 306 | 0 |
| CHINH ret / n lenh / maxDD xau | -0.3256 / 220 / 0.3615 | nhu nhau | 0 |
| tong net / bo 11 lenh loi nhat | -3 256.03 / -4 889.68 | nhu nhau | 0 |
| theo thang | 12 thang trung tung so | | 0 |
| BL_Z30 2025 | +0.2049 / 87 / DD 0.0924 | nhu nhau; == grid_b1 F3 (W7 E0 z3.0 K5 SL.3 H24 a7 g2) va == port B1 + exits.npz xi 72 | 0 |
| BL_S20 2025 | -0.0507 / 185 lenh (nguong s 2.370) | -0.0507 / 185 | 0 |
| IC M1 2025 / 2024 | -0.0708 / -0.0805 | nhu nhau | 0 |
| 10 nhom M1 2025 va 2024 | trung tung so | | 0 |
| IC OOF train 2025 / 2024 | -0.0457 / -0.0525 | nhu nhau | 0 |
| RAND p_keep | 1306/3531 = 0.36987 | 0.36987 | 0 |
| RAND seed khac (200 luot) | p 0.945, trung vi -0.125 | p 0.97, trung vi -0.1205 | cung ket luan |
| WFO 2024 CHINH | -0.5079 / 130 / DD 0.528 | nhu nhau | 0 |
| C1 dem | 7/12 | 7/12 | 0 |
| IC CV 2023Q2 / 2024Q1 / 2025Q4 (A1 train lai) | 0.3087 / 0.0100 / -0.1408 | nhu nhau | 0 |
| C2 pnl 2023/24/25; C3 | -1350.5 / 608.8 / -2449.7 (C2 sai vi 2023, 2025 < 0 va -0.319 < BL 0.336); C3 +0.0972 | nhu nhau | 0 |
Bootstrap CI cua IC: A1 KHONG tinh lai (chi kiem so diem).

## Hop le
- Ledger CHINH 2025: ke tu 2025-01-01 00:00, kx toi da 2025-12-31 23:00 (= kl, dong 'eod' cua fold), 0 lenh vao >= kl; moi cid thuoc tap
  test va co diem >= T20; ret lenh (khong eod) == nhan [cid] (lech 1e-16). Equity 10 000 dau nam (ret x 10 000 == tong net).
- Purge / train / exit / nguong: nhu tren, khop.

## Muc 3 - diem nguoc dau: TINH CHAT DU LIEU, KHONG PHAI LOI
- Nhan = loi suat lenh SHORT: 20/20 ung vien tay: (p0 - p_exit)/p0 cung dau voi nhan (sai khac = truot gia 0.1-0.3 % + phi + funding).
- Diem xep giam dan (CandB1 sort -score), chon diem >= T20 (phan vi TREN): n chon 1 306 = so te >= q80 OOF.
- IC in-sample train +0.51 (2025), +0.44 (2024): model hoc dung chieu quan he trong train (neu dao dau o dau do, IC in-sample phai am).
- IC OOF train am vi quan he dao chieu giua cac quy: IC OOF tung quy (2025-train) tu -0.45 (2022Q3) toi +0.40 (2024Q3); 2024-train
  tu -0.67 toi +0.54. Model hoc quan he cua cac quy khac, quy kiem di nguoc => tren nam kiem cung am. Gain top = dac trung thi truong
  (btc20, btcvol7, ew*) = cung che do thi truong, khong ben.
=> Khong co loi CHAN; ket qua dung duoc.

## Cau chu report
- "IC OOF train ... [in-sample]": OOF khong phai in-sample, nhung la so trong khoang train - van KHONG duoc dung lam bang chung.
- Tieu de WFO 2024 lap nhan 2 lan (my thuat). Khong thay cau nao noi qua so lieu; ket luan dung nhan ERRATA1.

## Duoc noi / KHONG duoc noi voi owner
DUOC: WFO 2025 (khong nhin truoc): CHINH -32.6 %, 220 lenh, maxDD 36 %; RAND p 0.97 (A1 seed khac 0.945) - model khong hon chon ngau
nhien; 9/9 bien the M1 am; 10/10 model mot-seed am; IC -0.071 (CI theo dot am); B3 KHONG DAT.
KHONG (hoac chi kem nhan): IC train 0.52 / IC OOF (in-sample); moi so CV C1-C3 ke ca C3 +0.097 va BL_S20-CV +0.336 (co nhin truoc);
toan bo WFO 2024 (duoi nguong mau); M2 IC 2025 +0.042 (mo ta, CI chua 0, khong phai tieu chi); BL_Z30 +20.5 % 2025 la doi chung =
dung ket qua B1 F3 da co tu truoc (khong phai phat hien moi, da bi chon qua nhieu phep thu B1); do quan trong dac trung.
