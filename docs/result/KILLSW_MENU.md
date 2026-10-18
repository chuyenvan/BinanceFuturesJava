# KILLSW_MENU — bảng lựa chọn kill-switch / DD bậc cho K24+skipFull

Ngày 2026-10-18. Pre-reg `docs/prereg/PREREG_KILLSW.md` 437d7ea9 + addendum 1 e34cb766 (K2 FAIL ở equity giờ ⇒ chuyển equity phút,
không đổi biến thể/ngưỡng). Script `research/killsw/killsw_m.py`; JSON `docs/result/killsw/ksm.json`. Chỉ đo hậu kiểm trên lệnh ECMEAS
bucket DEV, 8 seed; 0 sim mới, 0 đụng 242/tiền thật, 0 dùng 2026. Ngưỡng do OWNER chọn.

## 0. Kết luận

1. **DD bậc (A) KHÔNG giảm được maxDD** của hệ này: tốt nhất −22,6 → −22,0 % (A10_20) nhưng mất 2,9 pp CAGR22 và Calmar giảm
   1,60 → 1,52. Cả 3 biến thể A đều có Calmar thấp hơn không luật. Lý do: lỗ lớn đến từ **đợt** (13–24 lệnh mở cùng phút, BURST_RISK_1016)
   — thiệt hại xảy ra trong vài giờ từ vị thế ĐÃ mở; luật DD chỉ chặn lệnh MỚI, nên chủ yếu cắt mất phần hồi phục sau đáy.
2. **Luật owner DD 40 % (A40) không bao giờ kích hoạt trên DEV** (DD tệ nhất −24,7 %). Giữ làm phanh thảm hoạ, không phải công cụ điều chỉnh.
3. Đòn bẩy thật để giảm DD là **giới hạn phơi nhiễm theo đợt** (R1 BURST_COOLDOWN, sim Java thật): DD −22,6 → −9,0 % nhưng CAGR22
   37,0 → 24,2 % — hoặc đơn giản là **giảm size** (DD tỉ lệ gần tuyến tính với size). Đây là quyết định khẩu vị.
4. Khuyến nghị MASTER cho pilot: A40 (phanh thảm hoạ) + bộ ngắt kỹ thuật C; KHÔNG dùng DD bậc A. Nếu owner muốn DD thấp hơn ⇒ chọn
   giữa giảm size và R1 (cần pre-reg port live + HO 2026 + shadow trước khi bật).

## 1. Kiểm hợp lệ (bản phút)

K1 ΣPnL = ECMEAS (|Δ| < 1e-9 USD, 8/8), K2 maxDD22 = ECMEAS tới 1e-11 pp (8/8), K3 CAGR22 trùng (8/8) ⇒ PASS. Phủ giá 100 %.
Bản giờ (lưu `ks_hourly.json`, không dùng) FAIL K2: nông hơn 1,9–4,7 pp — lấy mẫu giờ bỏ lỡ đáy trong phút sập.

## 2. Bảng A — DD bậc (mean 8 seed; cửa sổ 2022–2025)

| biến thể | ΣPnL (USD) | CAGR22 | maxDD22 (tệ nhất) | Calmar22 | 2022 ΣPnL | thời gian HALF / HALT | lệnh bỏ / nửa size |
|---|---|---|---|---|---|---|---|
| A0 không luật | 105 358 | 36,1 % | −22,6 (−24,7) | 1,60 | +3 127 | 0 / 0 | 0 / 0 |
| A40 owner (dừng hẳn ở −40 %) | 105 358 | 36,1 % | −22,6 (−24,7) | 1,60 | +3 127 | không kích hoạt | 0 / 0 |
| A20_30 | 102 668 | 35,4 % | −22,6 (−24,6) | 1,58 | +843 | 4,0 % / 0 | 0 / 178 |
| A15_25 | 98 123 | 34,3 % | −22,3 (−24,4) | 1,55 | −287 | 9,1 % / 0 | 0 / 368 |
| A10_20 | 93 555 | 33,2 % | −22,0 (−23,8) | 1,52 | −645 | 16,3 % / 0,4 % | 48 / 564 |

Luật A(d1,d2): DD ≤ −d1 ⇒ nửa size lệnh mới; ≤ −d2 ⇒ ngừng lệnh mới 7 ngày rồi về nửa size; về full khi DD ≥ −d1/2.

## 3. Bảng B — giới hạn theo đợt (số từ R1 BURST_COOLDOWN 4e42ef59, sim Java thật, 8 seed — không đo lại)

| biến thể | maxDD22 | CAGR22 | Calmar22 | ghi chú |
|---|---|---|---|---|
| gốc K24+skipFull | −22,6 % | 37,0 % | 1,65 | |
| V1 (sau đợt ≥13 lệnh nghỉ 120′) | −9,0 % | 24,2 % | 3,06 | UW 116→220 ngày, lệnh 742→438/năm |
| V2 (≥13 lệnh, nghỉ 360′) | −7,8 % | 21,3 % | 3,76 | |
| V3 (≥6 lệnh, nghỉ 360′) | −6,6 % | 17,1 % | 3,43 | |

## 4. Nhóm C — ngắt kỹ thuật (đặc tả, không mô phỏng; ngưỡng đề xuất để owner duyệt)

| mã | điều kiện | hành động |
|---|---|---|
| C1 dữ liệu | ticker/kline trễ > 3 phút hoặc > 10 % symbol thiếu giá | ngừng lệnh mới, báo Telegram |
| C2 trượt giá | chân vào trượt > 2,5 % so với close nến quyết định (luật pilot owner) | ngừng lệnh mới, báo |
| C3 API | ≥ 5 lỗi đặt lệnh liên tiếp hoặc ≥ 10 lỗi/5 phút | ngừng lệnh mới, báo |
| C4 phơi nhiễm | số vị thế mở > 90 (DEV max 83) hoặc tổng margin > trần owner chọn | chặn lệnh mới |
| C5 sống | app không tick > 5 phút (healthcheck cron đã có) | báo; không tự restart khi đang có lệnh mở chưa đồng bộ |
| C6 thảm hoạ | DD MTM ≤ −40 % (A40) | đóng hết, dừng, chờ owner |

## 5. Giới hạn
Hậu kiểm bậc 1: không tính lại sizing theo equity và không đổi điểm thoát ⇒ A ước lượng đúng hướng; B là số sim thật. DEV có 1 sự kiện
cực đoan (LUNA 05/2022) chi phối maxDD ⇒ mọi so sánh DD là mẫu rất nhỏ.
