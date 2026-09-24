# PRE-REG K — H1a + GIỚI HẠN PHƠI NHIỄM (viết TRƯỚC khi chạy, 2026-09-03)

## Vì sao mở lại nhánh này
Bản ghi cũ nói "nới gate FAIL" là **gộp 3 run**. Số thật (`qret.py` trên printDone):

| run | equity cuối | 2022 | 2023 | 2024H1 | maxDD | underwater |
|---|---|---|---|---|---|---|
| C2b | 60,390 (+72.5%) | +11.6 | +45.4 | +6.3 | **−13.1** | 93d |
| **H1a** (`SIM_MIN_MOMENTUM_15M` 0.006) | **60,953 (+74.2%)** | +4.1 | +53.6 | +8.9 | **−21.1** | 108d |
| H1b (`PREDICT_SYMBOL_RATE_MAX` 0.30) | 47,143 | −31.6 | +94.4 | +1.3 | −44.3 | 444d |
| H1c | 37,145 | −35.2 | +67.0 | −2.0 | −51.3 | 699d |

H1a **trượt đúng một tiêu chí** (maxDD 21.1% > 15%) trong khi equity cuối cao hơn C2b, 2023/2024 tốt hơn, không năm nào âm. Thảm hoạ nằm ở trục `PREDICT_SYMBOL_RATE_MAX` (H1b/H1c) — **trục đó đóng vĩnh viễn, không đụng.**

Cơ chế thất bại của H1a đã đo (không phải "dồn cụm" như tôi từng khẳng định sai):
- hệ số phân tán lệnh/ngày: C2b 11.24 vs lệnh thêm của H1a **10.14** ⇒ KHÔNG dồn cụm hơn;
- lệnh thêm **có lãi**: n=1243, ROI +1.26%, winrate 81.9%, pnl +10,109;
- nhưng **loãng** (+1.26% vs +3.86% của lệnh trùng) và **lệnh đồng thời phình 29 → 37** (p95 22 → 29).

⇒ Giả thuyết: nút thắt là **phơi nhiễm đồng thời**, không phải số lệnh. Chặn trần lệnh đồng thời sẽ giữ phần lãi thêm mà cắt phần làm sâu drawdown.

## Thiết kế
Chỉ đổi **một** tham số so với H1a: `MAX_CONCURRENT` (mặc định 40; C2b thực tế đạt max 29 / p95 22; H1a đạt max 37 / p95 29).

| run | profile | khác C2b |
|---|---|---|
| **K0** (đối chứng tái lập) | `k0.properties` | `SIM_MIN_MOMENTUM_15M=0.006` |
| **K1** | `k1.properties` | + `MAX_CONCURRENT=25` |
| **K2** | `k2.properties` | + `MAX_CONCURRENT=20` |

**Ba run, không hơn.** Không dò thêm giá trị sau khi thấy kết quả.

K0 vừa là đối chứng khoa học vừa là kiểm chứng kỹ thuật: nó phải tái lập số của `H1a_mom006` (equity ~60,953, maxDD ~−21.1). Nếu KHÔNG tái lập ⇒ có sai lệch giữa jar/profile mới và run cũ ⇒ **DỪNG, điều tra**, không đọc K1/K2.

## Tiêu chí (chốt TRƯỚC)
Thay C2b chỉ khi đạt **HẾT**:
1. equity cuối ≥ **63,410** (= C2b 60,390 × 1.05, tương đương ≈ +2pp CAGR)
2. maxDD ≤ **15.0%**
3. quý dương ≥ **8/10**
4. 2022 ≥ **0%**
5. underwater dài nhất ≤ **120 ngày**

Không đạt ⇒ ghi lại và ĐÓNG nhánh giới-hạn-phơi-nhiễm. Không dò thêm `MAX_CONCURRENT`, không chuyển sang breaker rồi dò tiếp.

Nếu K1/K2 đạt 2–5 nhưng **trượt 1** (equity thấp hơn C2b): kết luận là "cắt phơi nhiễm chữa được DD nhưng ăn mất lãi" ⇒ vẫn ĐÓNG, và ghi lại con số đánh đổi.

## Ràng buộc
- DEV only (`SIM_END_DATE=20240630`). Không chạm VALIDATION.
- Dùng hệ `TRADING_PROFILE` mới (commit `cb073af`): mọi tham số giao dịch nằm trong file profile, không env.
- Oracle chạy **một job java tại một thời điểm**.
