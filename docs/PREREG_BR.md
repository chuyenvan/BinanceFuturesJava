# PRE-REG BR — BẬT CIRCUIT BREAKER (kiểm soát phơi nhiễm tầng danh mục)

*Viết TRƯỚC khi chạy, 2026-09-03. Thay cho `PREREG_K.md` đã VÔ HIỆU.*

## Vì sao được phép chạy tiếp sau khi K "trượt"
K **không trượt — K vô hiệu**. `MAX_CONCURRENT_ORDERS` chỉ được dùng bên trong `evaluateCircuitBreakerCore`, mà `SIM_BREAKER_MODE=OFF` nên khối đó không chạy. Bằng chứng: K1 (`MAX_CONCURRENT=25`) cho kết quả **giống hệt từng byte** K0 (`b:59580`, done 291/1603/1603, chỉ khác `PROFILE_HASH`). Không có dữ liệu nào được sinh ra ⇒ giả thuyết "giới hạn phơi nhiễm" chưa từng được kiểm.

Điều khoản "không chuyển sang breaker rồi dò tiếp" trong `PREREG_K.md` là để chặn việc dời cột gôn sau một phép thử **hợp lệ** thất bại. Ở đây phép thử không hợp lệ ngay từ đầu.

**Sai lầm đã ghi nhận:** thiết kế thí nghiệm dựa trên giả định về ý nghĩa tham số thay vì đọc chỗ nó được dùng. Đây là lần thứ 3 trong ngày (hướng score, múi giờ, giờ là ngữ nghĩa `MAX_CONCURRENT`). Quy tắc mới: **tra `docs/CONFIG_INVENTORY.md` + grep chỗ dùng TRƯỚC khi viết pre-reg**.

## Cơ chế thật (đã đọc code, không đoán)
`MarketBigChangeDetector.evaluateCircuitBreakerCore`, gọi từ `SimulatorMarketLevelTicker1MStopLoss:978`, chỉ chạy khi `BREAKER_MODE != OFF`:
- **Lớp 1 — mật độ lũy thừa**: cho phép `baseBurst + DENSITY_SUSTAIN × phút^DENSITY_ALPHA` lệnh, với `baseBurst = MAX_CONCURRENT_ORDERS` (40), `DENSITY_SUSTAIN=10.0`, `DENSITY_ALPHA=0.6`. Vượt ⇒ chặn mở mới.
- **Lớp 2 — chống bão**: chặn khi `(tổng lệnh − lệnh an toàn) > MAX_CONCURRENT_ORDERS × CIRCUIT_DANGER_RATIO` (0.7). "An toàn" = đã chốt lời dương, hoặc đang chạy và đã dời SL lên dương. Có vùng miễn trừ khi tổng lệnh < `baseBurst/2`.
- Độc lập: `BREAKER_MARGIN_HALT=0.50` chặn mở mới khi `marginRunning/balance ≥ 50%`. **C2b đạt đỉnh margin 53% ⇒ ngưỡng này CÓ bind.**

Giá trị hợp lệ `SIM_BREAKER_MODE`: `OFF` / `MARGIN` / `DCA` / `BOTH`. Mặc định trong code là `MARGIN`; C2b cố ý đặt `OFF`.

## Nền so sánh (đo lại hôm nay, cùng jar + cùng `configs/sim_dev.properties`)
| run | equity cuối | maxDD | quý ≥+5% | underwater |
|---|---|---|---|---|
| **C2b** | **60,390** | −13.1% | 6/10 | 93d |
| K0 = C2b + `mom 0.006` | 59,580 | chờ đo | — | — |

## Thiết kế — 3 run, không hơn
Nền = **C2b nguyên vẹn** (mom 0.008), chỉ bật breaker:

| run | profile | khác C2b |
|---|---|---|
| **BR1** | `br1.properties` | `SIM_BREAKER_MODE=MARGIN` |
| **BR2** | `br2.properties` | `SIM_BREAKER_MODE=BOTH` |
| **BR3** | `br3.properties` | `SIM_BREAKER_MODE=MARGIN` + `SIM_MIN_MOMENTUM_15M=0.006` |

BR1/BR2 trả lời: breaker có cải thiện đường đi của chính C2b không.
BR3 trả lời câu hỏi gốc: **nới gate + kiểm soát phơi nhiễm** có giữ được phần lãi thêm mà cắt phần làm sâu drawdown không.

Không dò `MAX_CONCURRENT`, `DENSITY_*`, `CIRCUIT_DANGER_RATIO`, `BREAKER_MARGIN_HALT` trong vòng này. Chúng giữ nguyên giá trị mặc định.

## Tiêu chí (chốt TRƯỚC)
**Thay C2b** chỉ khi đạt **HẾT**:
1. equity cuối ≥ **63,410** (= 60,390 × 1.05)
2. maxDD ≤ **13.1%** (không tệ hơn C2b)
3. quý dương ≥ 8/10 và quý ≥+5% ≥ **6/10**
4. 2022 ≥ 0%
5. underwater dài nhất ≤ **93 ngày** (không tệ hơn C2b)

**Kết luận phụ được phép rút ra** (ghi lại, không dùng để thay ứng viên):
- Nếu maxDD giảm rõ (≤ 11%) mà equity giảm < 5%: ghi nhận "breaker mua được đường đi mượt bằng một ít lãi" — đưa vào hồ sơ để quyết khi bàn khẩu vị rủi ro, KHÔNG tự động chọn.
- Nếu BR3 > BR1 cả về equity lẫn DD: xác nhận cơ chế "nới gate + kiểm soát phơi nhiễm" có giá trị, mở một vòng pre-reg riêng.

Không đạt và không rơi vào 2 trường hợp trên ⇒ **ĐÓNG nhánh kiểm-soát-phơi-nhiễm**, ghi lại, không dò thêm.

## Ràng buộc
- DEV only (`SIM_END_DATE=20240630`). Không chạm VALIDATION.
- Dùng `TRADING_PROFILE`; mỗi run ghi `PROFILE_HASH` vào log để về sau không phải đoán config.
- Oracle chạy một job java tại một thời điểm.
