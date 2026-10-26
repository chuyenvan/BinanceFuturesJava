# PREREG NUP3 — SLEEVE lệnh thêm, ngân sách phơi nhiễm riêng, sổ nền KHÔNG ĐỔI (MASTER 2026-10-26, owner duyệt hướng)

## 1. Lý do
- NUP: lệnh thêm của A2 có edge riêng (+1,4 %/lệnh) nhưng thua vì GIÀNH vốn/slot của lệnh nền (+3,5 %).
- NUP3-S0 (6148a364):
  - lệnh thêm rải ra ~45 % ngày khác B0;
  - edge HO của toàn tập ≈ phí;
  - phần bền là lệnh thêm lúc ALT_EW 24h ≤ −8 % (DEV 2,35 %, HO 2,08 %, 8/8 seed);
  - "dừng khi burst" đạt S0 ở mức biên.
- Thước S0 đo trong sổ chung. NUP3 đo đúng cơ chế bằng sim Java: sleeve có ngân sách phơi nhiễm riêng, sổ nền giữ y nguyên B0.

## 2. Cơ chế sim (code mới, branch `research/nup3-sleeve` tách từ `research/nup-tier2` a221bf80)
- **Sổ nền:** B0 X14 y nguyên (`prof_run` của `tsx-x14-<seed>`). Sizing, throttle U, held-check, gate, quota, K của sổ nền chỉ tính trên vị thế NỀN.
  - **Bất biến bắt buộc:** printDone lọc bỏ lệnh sleeve phải TRÙNG BYTE với run B0 cùng seed.
- **Sleeve:**
  - **Ứng viên:** ứng viên PREDICT bị gate nền từ chối nhưng QUA ngưỡng phân vị `SLEEVE_PCT=0.99985` trên cùng buffer r (cơ chế q2/giờ của TIER2). Không ghi gì vào buffer hay quota của nền.
  - **Sizing:** cùng công thức leg của nền × `SLEEVE_SIZE_MULT=1.0`, throttle `1 − U_s/U_S_MAX` với U_s = phơi nhiễm sleeve / equity CHUNG. `U_S_MAX=0.35`.
  - **Giới hạn khác:** K sleeve = 24/đợt; DCA và exit (trailing, time-stop 168h, X14) y như nền.
  - **Symbol:** sleeve KHÔNG mở symbol mà nền hoặc sleeve đang giữ. Nền KHÔNG xét vị thế sleeve (để giữ bất biến). Đếm và báo số lần nền mở symbol sleeve đang giữ (overlap).
  - **Gắn nhãn:** `book=sleeve` trong printDone.
- **Equity:** một tài khoản chung (CROSS 1x). Kiểm Σ notional (nền + sleeve) ≤ equity tại mọi thời điểm, báo U tổng max; vượt 1,0 thì ghi FAIL kỹ thuật.
- **Bảo mật:** build jar với `PrivateConfig` STUB (mọi hằng là chuỗi rỗng). Kiểm `unzip -p … PrivateConfig.class | strings` không chứa key thật, rồi mới upload dataset Kaggle mới `sim-jar-nup3-sleeve`.
- **Kiểm khi TẮT:** `SLEEVE_ENABLED=false` ⇒ printDone trùng byte B0 (seed a1, s7).

## 3. Arm (chốt, 3 arm)
| Arm | Điều kiện MỞ của sleeve (tại t, chỉ dữ liệu < t) |
|---|---|
| V0 | không điều kiện (mọi ứng viên sleeve) — đối chứng "ngân sách riêng có chữa được việc giành vốn không" |
| V1 | KHÔNG mở khi số leg đầu cụm (nền + sleeve) trong [t−60′, t) ≥ 10 (W_burst) |
| V2 | CHỈ mở khi return ALT_EW 24h tới phút t−1 ≤ −8 % (W_mkt). Series cờ phút dựng sẵn (nhân quả) từ `edge_attr/index.npz` (2021–25) + kernel `tsx-ew2026` (2026), nạp vào sim dạng file input |

⚠ V2 được hình thành SAU khi thấy HO 2026 (S0) ⇒ HO 2026 KHÔNG dùng để xác nhận V2 (chỉ mô tả). Kỳ xác nhận V2 = 2021-07-01 → 2021-12-31 (S0 chưa chạm), cộng forward/paper ≥ 4 tuần trước mọi dùng thật.

## 4. Thực thi
1. Code + unit test (mỗi điều kiện sleeve, bất biến nền, symbol, U tổng). Cổng TẮT trùng byte (a1, s7). Cổng BẬT: printDone lọc `book=sleeve` trùng byte B0 (a1).
2. Pha 1: V0/V1/V2 × 4 seed DEV (a1, s7, s21, s99).
3. Pha 2: mọi arm qua G1–G3 ở Pha 1 ⇒ thêm 4 seed DEV (s13, s123, s777, s2024) + 8 seed HO (42, 7, 13, 21, 99, 123, 777, 2024).

## 5. Thước đo
- Toàn danh mục (nền + sleeve) so với B0 cùng seed, DEV 2022–25 theo giờ +07 đóng lệnh như NUP:
  - cụm/năm từng năm, ΣPnL, stress −20 bps, CAGR22, maxDD MTM (pipeline NUP ADDENDUM B, missing = 0), Calmar, U tổng max, số vị thế max.
- Riêng sleeve: cụm/năm, ROI/lệnh, ROI_stress, ΣPnL_stress theo năm/seed, overlap, N_eff (đợt riêng < 6h, ngày có lệnh, tương quan PnL ngày với nền).

## 6. Luật (chốt; median seed, ghép cặp B0)
- **G1:** cụm/năm toàn danh mục ≥ 1,30× B0, VÀ mỗi năm 2022–25 ≥ 1,15×.
- **G2:** ΣPnL toàn danh mục ≥ 1,00× B0 (nền không đổi nên sleeve phải không âm), VÀ ΣPnL_stress của sleeve > 0 ở ≥ 3/4 năm, VÀ ≥ 3/4 seed (Pha 1) hoặc ≥ 6/8 seed (Pha 2).
- **G3:** maxDD MTM toàn danh mục: median ≥ −32 %, seed tệ ≥ −36 %. U tổng max ≤ 1,0.
- **G4, xác nhận, chỉ Pha 2:**
  - V0/V1 trên HO 2026: ΣPnL_stress sleeve median > 0, VÀ ≥ 6/8 seed > 0, VÀ ROI_stress sleeve ≥ +0,5 %/lệnh, VÀ maxDD realized toàn danh mục HO ≥ −15 %.
  - V2 trên 2021H2: ΣPnL_stress sleeve > 0 ở ≥ 6/8 seed. HO 2026 chỉ mô tả.
- **GO** = qua G1–G4. Nhiều arm GO ⇒ chọn cụm/năm cao nhất. GO chỉ là ứng viên v1.3: cần forward/paper shadow ≥ 4 tuần (V2 bắt buộc). Không đổi v1.1/v1.2 trước D 12-08.
- Trial ledger họ NUP: +3. Không thêm arm, không đổi ngưỡng sau khi thấy số. Bug ⇒ ADDENDUM, báo số trước/sau.

## 7. Giới hạn đã biết
- **Live one-way:** nền và sleeve cùng symbol sẽ gộp thành một vị thế. Nếu GO, live cần luật symbol độc quyền ⇒ chưa đo được tác động lên nền (báo số overlap để ước lượng).
- Sim không có trượt giá; lệnh sleeve dồn vào lúc sập (V2) có thể trượt nhiều hơn ⇒ nhìn kỹ stress.
- U_S_MAX = 0,35 là giả định thiết kế (nền max ~0,62, để tổng ≤ 1,0), không tune.
