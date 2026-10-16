# PRE-REG — REX Bước 1b: market-neutral từ selector S1 (P1, owner chọn 10-16) (MASTER 2026-10-16)

**Công khai mức nhiễm dữ liệu:**
- File này viết SAU khi đã xem S1 trên DEV, gồm cả chẩn đoán: bottom-10 thua mạnh và top thắng yếu.
- VAL 2025 mới chỉ được nhìn với C1 ở dạng IC và top-10 long-only. Dạng long-short trên VAL CHƯA nhìn.
- HO 2026 chưa chạm.

Vì vậy DEV ở bước này KHÔNG được coi là bằng chứng mới. Bằng chứng thật chỉ đến từ VAL (một lần), HO và forward.

## Đầu vào (đóng băng)
- Dự báo walk-forward OOS của S1: `pred_s1_C1.parquet`, `pred_s1_C3.parquet`, `pred_s1_C7.parquet`. Không train lại.
- Giá và funding: `d1.parquet` (Vision 1d).
- Universe: các dòng có trong panel ngày t.

## Danh mục (cố định)
**Chân long:** top-20 theo score trong universe, chia đều trọng số.

**Chân short:** bottom-20 theo score, chỉ trong tập đủ điều kiện short:
- niêm yết ≥ 90 ngày;
- qv30 ≥ 50M (lqv30 ≥ ln 5e7);
- f7 ≥ −0,3 % (né coin đã bị short quá đông và funding âm sâu).

Chia đều trọng số.

**Cân beta:**
- β90 của từng coin = cov/var lợi suất ngày so với BTC, tính tới ngày t. Thiếu dữ liệu thì β = 1.
- Hệ số short `s = clip(mean β_L / mean β_S, 0,5; 2,0)`, áp cho toàn chân short: mỗi coin short nhận trọng số −s/20.
- Chân long tổng +1.
- Lợi suất tính trên 1 đơn vị notional long; gross khoảng 2.

**Tranche:** vốn chia h phần, mỗi ngày làm mới một tranche và giữ h ngày, giống S1.

**Chi phí:**
- 0,10 %/chiều trên Σ|Δw|.
- Funding thật trên cả hai chân: long trả f; short nhận f khi f > 0, trả khi f < 0.

## Biến thể (4; chọn trên DEV theo Sharpe ròng)
| Mã | Mô tả |
|---|---|
| N1 | C1, h = 1 |
| N3 | C3, h = 3 |
| N7 | C7, h = 7 |
| N1b | C1 có buffer: coin long chỉ bị bán khi rớt khỏi top-40; coin short chỉ bị mua lại khi ra khỏi bottom-40; chỗ trống được lấp bằng coin có rank tốt nhất. Mỗi chân luôn đủ 20 coin |

## Thước đo
- Sharpe ngày × √365 trên DEV / VAL; lợi suất năm; maxDD.
- Ngày tệ nhất, tuần tệ nhất.
- % tháng dương; Sharpe theo năm.
- Correlation ngày với BTC; correlation tuần với crash-buy C2.
- Đóng góp lỗ lớn nhất của một coin trong một ngày (chân short).
- Turnover.
- Chi phí ×2.
- Tách riêng phần lợi suất của chân long và chân short.

## Gate GO (biến thể thắng; phải đạt tất cả)
| # | Điều kiện |
|---|---|
| G1 | DEV Sharpe ròng ≥ 1,5 |
| G2 | DEV dương cả 3 năm và ≥ 65 % tháng dương |
| G3 | DEV maxDD ≥ −25 % |
| G4 | DEV ngày tệ nhất ≥ −8 % |
| G5 | \|corr ngày với BTC\| ≤ 0,30 |
| G6 | DEV chi phí ×2: Sharpe ≥ 0,8 |
| G7 | VAL 2025 (một lần): Sharpe ròng ≥ 0,8 và lãi > 0 |

**Nếu GO:**
- Bước 3 (thoát lệnh và stop chân short) chạy trên đường 1m.
- Bước 4 chạy HO 2026 đúng một lần, sau đó forward.

**Nếu NO-GO:** đóng P1.
