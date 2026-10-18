# PREREG_KILLSW — Menu kill-switch / DD bậc cho K24+skipFull (bảng lựa chọn khẩu vị, KHÔNG phải tìm alpha)

Ngày 2026-10-18. Owner "ok" (10-18) cho MASTER dựng bảng lựa chọn; ngưỡng do OWNER chọn. Chỉ đo hậu kiểm trên lệnh sim có sẵn:
0 sim Java mới, 0 đụng 242/shadow/tiền thật, 0 dùng 2026 để chọn. Commit TRƯỚC khi dựng giá giờ / mô phỏng.

## 0. Bối cảnh đã có (không đo lại)
- Owner 10-10: pilot 10k, DD chấp nhận 40 %; dừng khi trượt > 2,5 % hoặc DD 40 % (golive_1009).
- R1 BURST_COOLDOWN (4e42ef59, sim Java thật, 8 seed): V1 (13 lệnh,120′) DD −22,6→−9,0 %, CAGR22 37,0→24,2 %, Calmar 1,65→3,06;
  V2 (13,360′) DD −7,8, CAGR 21,3, Cal 3,76; V3 (6,360′) DD −6,6, CAGR 17,1, Cal 3,43. NO-GO theo luật alpha (G3) nhưng là
  lựa chọn khẩu vị hợp lệ ⇒ đưa NGUYÊN SỐ vào bảng, nhóm B.
- EDGE_ATTR (2e33810e): rủi ro chính là regime (2022 ≈ 0) + đuôi đợt.

## 1. Dữ liệu
- Lệnh: `~/claude_master/edge_attr/legs.parquet` (ECMEAS bucket DEV, 8 seed, md5 ở `docs/result/edge_attr/build.json`), win = D.
- Giá: close kline1m Vision, lấy nến cuối mỗi giờ UTC (ffill nếu thiếu, tối đa 24h; không có ⇒ unrealized 0) cho mọi symbol có lệnh.

## 2. Mô hình equity (hậu kiểm bậc 1)
- Lưới giờ UTC từ 2021-07-01 00:00 +07 tới 2026-01-01 00:00 +07. Lệnh i: giờ vào h0 = giờ chứa close(M), giờ ra h1 = giờ chứa close(E).
- Equity(h) = 35 000 + Σ_{i vào ≤ h} s_i · c_i(h); c_i(h) = qty_i·(close_h − entry_i) khi h < h1, = pnl_i khi h ≥ h1;
  qty_i = margin_i / entry_i. s_i = hệ số size của trạng thái tại giờ h0−1 (lệnh đang mở giữ nguyên size).
- Giới hạn: không tính lại sizing theo equity (sim compounding), không đổi điểm thoát ⇒ hướng tác động đúng, độ lớn xấp xỉ.

## 3. Biến thể (cố định, không thêm sau khi thấy kết quả)
- A0 = không luật (đối chứng). A40 = luật owner: DD ≤ −40 % ⇒ đóng hết theo giá giờ đó, dừng vĩnh viễn.
- A(d1,d2) ∈ {(10,20), (15,25), (20,30)}: DD = Equity/max(Equity quá khứ) − 1 tính trên giờ đã đóng.
  FULL (s=1) → HALF (s=0,5) khi DD ≤ −d1; → HALT (s=0) khi DD ≤ −d2, giữ 7 ngày rồi về HALF; HALF → FULL khi DD ≥ −d1/2.
  HALT chỉ chặn lệnh mới, không đóng lệnh đang mở.

## 4. Chỉ số (mean ± sd qua 8 seed; cửa sổ 2022-01-01→2026-01-01 như ECMEAS "22")
ΣPnL (cả DFULL), CAGR22, maxDD22 (MTM giờ), Calmar22, số lần vào HALF/HALT, % thời gian HALF/HALT, ΣPnL bỏ lỡ so với A0,
năm 2022 riêng (ΣPnL, maxDD).

## 5. Kiểm hợp lệ (FAIL ⇒ dừng, sửa pipeline, không đổi §3)
- K1: A0 ΣPnL theo end = ECMEAS spnl từng seed (≤ 1 USD).
- K2: A0 maxDD22 giờ cách ECMEAS maxdd22 (phút) ≤ 2,0 pp mỗi seed và nông hơn hoặc bằng (giờ ≥ phút) ở ≥ 7/8 seed.
- K3: A0 CAGR22 cách ECMEAS cagr22 ≤ 2,0 pp (khác biệt do không compounding được báo rõ).

## 6. Diễn giải (chốt trước)
- Không có "GO". Bảng trình owner; MASTER chỉ đánh dấu biến thể bị TRỘI (vừa CAGR22 thấp hơn vừa maxDD22 sâu hơn biến thể khác).
- Biến thể owner chọn phải: (i) xác nhận một lần trên HO 2026 (mô tả) và kho backcast 2020 nếu có lệnh, (ii) port live có test, (iii) shadow.
- Nhóm C (ngắt kỹ thuật: mất dữ liệu, lệch giá, lỗi API, trần vị thế, trượt > 2,5 %) là đặc tả, không mô phỏng.

## 7. Sản phẩm
`research/killsw/`, `docs/result/KILLSW_MENU.md`, `docs/result/killsw/*.json`, ledger.
