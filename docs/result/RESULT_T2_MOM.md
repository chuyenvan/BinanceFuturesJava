# RESULT T2-MOM — momentum 21 ngày trên alt perp, tầng 2 (MASTER 2026-10-16)

- **Pre-reg:** `docs/prereg/PREREG_T2_MOM.md` (758729a8).
- **Code:** `research/mom/t2_mom.py`; phần mô tả hậu kiểm ở `research/mom/t2_h2desc.py`.
- **Output:** `~/claude_master/1016/t2mom/` (`t2mom_result.json`, `t2mom.log`, `t2_desc.log`, `base_weeks.csv`).

## VERDICT: **NO-GO** cho H1 (biến thể chính) — trượt 8/9 tiêu chí

## Kiểm dữ liệu: tất cả PASS
- **V1:** tái lập tầng 1 X1 goc: excess E 0,455 / C 1,003, so với ref 0,46 / 1,00.
- **V2:** 290 tuần; universe nhỏ nhất 57 coin.
- **V3:** ffill 7 trên 2890 coin-tuần (0,24 %).
- **V5:** trùng 228 tuần với crash-buy.

## H1 = long top decile + short BTC (BASE: trễ 1 ngày, chi phí 0,10 % / 0,06 % mỗi chiều, funding thật)
| Chỉ số | Giá trị | Tiêu chí |
|---|---|---|
| Sharpe toàn kỳ / E / C | 0,29 / 0,39 / 0,22 | G1 ≥ 0,60 ✗; G2 ✗ |
| Chi phí ×2 | 0,22 | G3 ≥ 0,35 ✗ |
| 7 offset ngày, Sharpe toàn kỳ | 0,29 / 0,18 / 0,35 / 0,42 / 0,27 / 0,32 / 0,41 (C: −0,52 … +0,22) | G4 cần 5/7 > 0,30; chỉ đạt 4/7 ✗ |
| Lookback 14 / 28 | 0,17 / 0,45 | G5 ✗ |
| Năm dương | 3/6 (2022 −1,17, 2024 −0,58, 2025 −0,02) | G6 ✗ |
| maxDD | −90 % | G7 ✗ |
| Bootstrap P(mean ≤ 0) | 0,239 | G8 ✗ |
| Correlation tuần với crash-buy C2 | 0,22 | G9 ✓ |
| Deflated Sharpe (N = 50) | 0,05 | chỉ báo cáo |

**Rủi ro.**
- Correlation với BTC: H0 0,61, H1 0,06.
- Có 23 tuần BTC giảm hơn 10 %. Trong các tuần đó, H0 trung bình −19,3 %/tuần, H1 −4,4 %.
- Trong 10 tuần tệ nhất của crash-buy (trung bình −3,1 %), H1 trung bình −11,9 %. Tức là H1 **không đa dạng hoá** đúng vào lúc crash-buy cần nhất.

**Capacity.** Ở vốn $1M, p95 participation là 0,49 % qv ngày. Capacity ước khoảng $1M, nên capacity không phải vấn đề.

## Nguyên nhân: "edge" của tầng 1 là excess so với giỏ alt equal-weight, không phải so với BTC
- Giỏ alt equal-weight chảy máu so với BTC suốt 2021–2026.
- Long top-momentum trừ BTC thì về gần 0. Long top-momentum trừ giỏ alt thì vẫn còn dương.
- Muốn thu phần này phải short cả giỏ alt (H2), không phải short BTC.

## Các biến thể khác (pre-reg cấm chọn sau khi chạy; chỉ ghi nhận)
| | full | E | C | ×2 chi phí | maxDD | Năm dương | Bootstrap p |
|---|---|---|---|---|---|---|---|
| H0 chỉ long | 0,39 | 0,32 | 0,46 | 0,34 | −94 % | 4/6 | — |
| H2 long top − short giỏ universe | 0,65 | 0,35 | 0,87 | 0,55 | −64 % | 4/6 | 0,042 |
| H3 long top − short bottom | 0,76 | 0,28 | 1,08 | 0,64 | lỗ hơn 100 % vốn (tuần −128 %, short squeeze) | 5/6 | 0,039 |

**Mô tả HẬU KIỂM của H2** (`t2_desc.log`; KHÔNG phải phép thử, chỉ dùng để quyết định có đáng forward hay không):
- Bền theo offset: full 0,46–0,82 ở cả 7 offset; riêng C của offset 4 chỉ 0,04.
- Bền theo lookback: lb14 0,50, lb28 0,79.
- Năm 2022 âm ở mọi cấu hình.
- Deflated Sharpe H2 0,21: sau khi phạt multiple testing thì KHÔNG có ý nghĩa thống kê.

## Kết luận
1. Đóng X1-H1 (momentum alt hedge bằng BTC).
2. H2 là ứng viên nhưng bị nhiễm hậu kiểm.
   - Chỉ forward thật mới cho bằng chứng mới. Với Sharpe khoảng 0,65 trên dữ liệu tuần, cần khoảng 1,5–2 năm forward mới phân biệt được với 0.
   - Vận hành nặng: short khoảng 60–150 alt mỗi tuần, maxDD −64 % ở mức gross 2×.
   - Đề xuất: không ưu tiên. Nếu owner muốn, chỉ chạy shadow log tuần (chi phí gần 0) song song.
3. Ledger cộng 1 (T2-MOM).
