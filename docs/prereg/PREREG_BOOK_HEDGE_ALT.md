# PREREG_BOOK_HEDGE_ALT — biến thể "coin tương quan" của BOOK_HEDGE (owner yêu cầu 10-19)

Ngày 2026-10-19. **Commit TRƯỚC khi chạy.** Chỉ đo offline; giữ y nguyên PREREG_BOOK_HEDGE (`8521f018`)
và PREREG_BOOK_HEDGE_ETH (`10bd5a02`) **trừ công cụ hedge**.

## Ghi nhận trung thực (kiểm định bội)
- Đây là lần thử **THỨ BA** trong họ BOOK_HEDGE (1: BTC → NO-GO; 2: ETH → NO-GO). Vì vậy kết quả là **THĂM DÒ**:
  kể cả GO cũng **KHÔNG** được thăng hạng trên DEV; chỉ được chuyển sang xác nhận **1 lần** trên HO4 2026 với h cố định.
- Lý do kỹ thuật: book 97 % alt. Tương quan **ngày** với nhân tố alt (EW, equal-weight) trong 2024: **BTC 0,750 · ETH 0,829**
  trong khi nhiều alt ≥ 0,88 ⇒ thử một alt làm công cụ hedge thay vì BTC/ETH.

## Chọn công cụ — luật chốt TRƯỚC khi đo outcome
Screen 2024 (chỉ năm khám phá, **không đọc 2025/2026**), nguồn kline1m Vision, return ngày = log(close cuối ngày UTC):
- lọc: ≥ 350 ngày có ≥ 1000 phút dữ liệu trong 2024; median quote_volume ngày ≥ **10 triệu USD**;
  loại `BTCUSDT`, `ETHUSDT`, stablecoin và `BTCDOMUSDT` (chỉ số dominance);
- xếp theo **corr(return ngày coin, EW)** trong 2024; **công cụ = hạng 1**.

**Kết quả screen (dữ liệu thiết kế, không phải outcome) — hạng 1 = `ZILUSDT`**
| hạng | sym | corr_ew | corr_btc | med_qv ($/ngày) | beta_ew |
|---|---|---|---|---|---|
| 1 | **ZILUSDT** | **0,908** | 0,673 | 11,9 M | 0,99 |
| 2 | KAVAUSDT | 0,901 | 0,688 | 14,4 M | 0,96 |
| 3 | FLOWUSDT | 0,897 | 0,671 | 17,0 M | 0,98 |
| 4 | AXSUSDT | 0,894 | 0,658 | 37,7 M | 0,99 |
| — | ETHUSDT | 0,829 | 0,798 | 7 492 M | 0,65 |
| — | BTCUSDT | 0,750 | 1,000 | 16 239 M | 0,48 |

Nguồn bảng đầy đủ: `docs/result/BOOK_HEDGE_ALT_SCREEN.md` (253 symbol) + `~/claude_master/bookhedge_alt/screen_2024.json`.

**Luật bắt buộc:** chỉ thử **ZILUSDT**. **KHÔNG** thử coin khác trong pre-reg này; nếu NO-GO ⇒ **đóng**, không đổi coin để "cứu".

## Thay đổi duy nhất so với BOOK_HEDGE
- Công cụ: **short `ZILUSDT` perp**; return phút = log-return close kline1m Vision `ZILUSDT`
  (phút đầu tháng nối với close cuối tháng trước; gap ⇒ return 0, không gán qua khoảng trống).

## Giữ nguyên (không đổi)
- `N(m)` = open notional của book theo phút; hedge = −h · N_open · return của công cụ.
- `h ∈ {0,5; 1,0}`; phí taker **0,05 % × h × |ΔN|**; **BỎ QUA funding** (để so được với BTC/ETH).
- Chỉ số: DD22 (reset), DD toàn kỳ, CAGR22, Calmar22, UW22, ΣPnL, DD cửa sổ LUNA/FTX; ghép cặp theo seed.
- Đo trên **8 seed** (`I.SEEDS`), equity MTM phút Vision, cùng `DAY0`, cùng cửa sổ.

## Luật GO (nguyên văn, không đổi)
**GO ⟺** (số seed có DD nông hơn ≥ 5pp **≥ 7/8**) **VÀ** (`ΔCalmar_mean − 3,499483 · SE > 0`, CI99 một phía với 8 seed)
**VÀ** (`ΣPnL` giảm **≤ 50 %**). Winner = Calmar22 cao nhất trong các arm GO.

## Đầu ra
- `docs/result/BOOK_HEDGE_ALT.md` (bảng theo arm + đọc) và JSON `~/claude_master/bookhedge_alt/book_hedge_alt.json`.
- Báo kèm (mô tả): so ZIL vs BTC vs ETH cùng h (ΔDD, ΔCalmar ghép cặp theo seed); tương quan ngày book ↔ ZIL.
