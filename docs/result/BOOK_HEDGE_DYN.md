# BOOK_HEDGE_DYN — chọn công cụ hedge ĐỘNG theo thời điểm (kết quả, THĂM DÒ)

Ngày 2026-10-19. Pre-reg `docs/prereg/PREREG_BOOK_HEDGE_DYN.md` **`bc7efcf7`** (commit TRƯỚC khi đo).
Lần thử **thứ 4** trong họ BOOK_HEDGE ⇒ **THĂM DÒ**, không thăng hạng trên DEV; chỉ xác nhận **1 lần** trên HO4 2026.

## Luật đã chạy (đúng pre-reg)
Mỗi tháng, chỉ dùng **90 ngày trước**: universe ≥60 ngày dữ liệu + median qv ngày ≥10 M USD, top-30 thanh khoản,
loại BTC/ETH/stable/`BTCDOM`; điểm = **corr return ngày coin ↔ return ngày book** (TB 8 seed); chọn **top-5,
weight 1/5**, rebalance đầu tháng; `h ∈ {0,5; 1,0}`; luật GO y nguyên BOOK_HEDGE.

## Kết quả (8 seed, cùng harness)
| Arm | CAGR22 | maxDD22 | Calmar22 | UW22 | ΣPnL | DD LUNA | DD ≥5pp nông hơn | ΔCalmar CI99 | GO |
|---|---|---|---|---|---|---|---|---|---|
| Nền | 37,95 | −22,55 | 1,69 | 116 | 110 047 | −22,3 | — | — | — |
| **DYN h0,5** | 33,06 | **−11,34** | **2,96** | 171 | 90 536 | −9,6 | **7/8** | **[+0,68; +1,86]** | **GO** |
| DYN h1,0 | 27,51 | −20,15 | 1,37 | 325 | 71 025 | −20,2 | **0/8** | **[−0,60; −0,06]** | **NO-GO** |

Winner: **h0,5**. Chi phí: ΣPnL **−17,6 %** (h0,5) / −35,3 % (h1,0).

## So với các bản trước (cùng harness)
| Bản | ΔDD ≥5pp | ΔDD mean | ΔCalmar | PnL | GO |
|---|---|---|---|---|---|
| BTC h0,5 (`7c6e816e`) | 4/8 | +4,74 | +0,261 | −9,2 % | NO |
| ETH h0,5 (`563810ed`) | 5/8 | +4,53 | +0,271 | −11,3 % | NO |
| **ZIL cứng h0,5** (`59fd8ef9`) | **8/8** | **+10,93** | **+1,209** | −15,2 % | **GO** |
| **DYN h0,5** | **7/8** | **+11,20** | **+1,268** | −17,6 % | **GO** |
| DYN h1,0 | 0/8 | +2,39 | −0,326 | −35,3 % | NO |

⇒ **Chọn động ≈ chọn cứng ZIL ở h0,5** (ΔCalmar +1,27 vs +1,21; PnL xấu hơn 2,4 pp; 7/8 vs 8/8).
Tức ZIL **không phải may mắn**: hiệu ứng là "hedge bằng một coin bám nhân tố alt, đòn h≈0,5", không phải "ZIL thần kỳ".
Nhưng **động không vượt cứng** — nên cái giá của việc chọn đúng coin là không lớn, miễn là coin bám alt.

## Chuỗi lựa chọn (đo được, point-in-time)
- **51/54 tháng k=5**; 3 tháng đầu (2021-07→09) **k=0** vì book returns chỉ bắt đầu 08/07/2021 (chưa đủ 60 ngày).
- **77 coin khác nhau** từng được chọn; **đổi thành viên 51/53 lần** chuyển tháng ⇒ cơ chế thực sự động, không phải basket cố định.
- Xuất hiện nhiều nhất: **SOL 16 tháng · BNB 16 · MATIC 11 · AVAX 10 · FTM 9 · WIF 8 · DYDX 7**.
- Corr giảm rõ theo thời gian: 2021–2022 **0,55–0,60** → 2023 **0,15–0,45** → 2024 **0,29–0,58** → **2025-08 chỉ 0,02–0,06**.

## Hedge PnL theo năm (h0,5, trung bình/seed)
**2022 +15 989** · 2023 **−10 937** · 2024 **−16 401** · 2025 **−8 259** (2021 ≈ −150).
⇒ Cùng cơ chế ZIL: lãi lớn đúng năm sập (2022), trả phí ở năm tăng.

## Đọc
1. **h0,5 pass cả 3 điều kiện GO** (7/8, ΔCalmar CI99 dương, PnL −17,6 % ≤ 50 %).
2. **h1,0 fail nặng** (0/8, ΔCalmar âm): nhân đôi đòn lên basket có nhiều coin corr thấp (đặc biệt 2025) biến hedge thành nguồn lỗ.
   ⇒ **Không tăng đòn; h0,5 là cấu hình duy nhất dùng được.**
3. **Điểm yếu cấu trúc**: từ 2025 corr sụp → basket gần như mù. Nếu thị trường tiếp tục vậy, hedge sẽ chỉ còn là "mua bảo hiểm đắt".
4. **Chưa đo capacity cho basket 5 leg** (mới có cho ZIL 1 leg). Basket chia 5 lệnh nhỏ ⇒ participation/leg thấp hơn,
   nhưng tổng turnover và số lệnh tăng ⇒ **phải đo trước khi triển khai**.

## Bước tiếp (chờ MASTER)
- Nếu muốn đi tiếp: pre-reg **xác nhận 1 lần** trên **HO4 2026** với `h = 0,5`, cửa sổ 90 ngày, k=5 (đúng cấu hình này).
- Trước đó nên: đo **capacity/turnover của basket** và kiểm **độ ổn định cửa sổ** (30/180 ngày — chỉ báo kèm, không đổi luật).

## Ghi chú kỹ thuật (đã sửa trong quá trình)
1. `book_ret.index` (ngày-since-DAY0) vs `rcoin.index` (ngày-since-epoch) ⇒ reindex NaN ⇒ **k=0 mọi tháng**.
2. `sym` categorical + `groupby(sort=False)` ⇒ cực chậm ⇒ `astype(str)` + `observed=True`.
3. `bt_g` chạm đúng `len(grid)` ⇒ `r_dyn` thiếu 1 ô ⇒ `R_MAX = max(Mmax, bt_g.max()+1)`.
4. `np.exp(rr[M])` sai shape ⇒ dùng `rr` trực tiếp như harness gốc.
5. Arm hedge thiếu `luna`/`ftx` ⇒ `KeyError` ⇒ bổ sung khi tính.
Cache: `dyn_minute.npz` (352 MB, 77 coin × 2 321 280 phút) + `dyn_sel.json` ⇒ rerun chỉ ~2 phút.

## ERRATA 2026-10-19 (BOOK_HEDGE_AUDIT, xem docs/result/BOOK_HEDGE_AUDIT.md)
Harness dùng short notional-cố-định cân lại mỗi phút (khác pre-reg "cân lại khi N đổi"). Chấm lại bằng harness giữ số lượng:
coin đơn lệch nhỏ (DD ±0,1–0,4pp); DYN sai nặng do LUNA (h0,5 DD −11,34 → −17,09, Calmar 2,96 → 1,77, NO-GO).
Thêm bootstrap đường giá + cửa sổ 2023+ + impact 25 bps: chỉ ZIL h0,5 qua cả 4 (thăm dò, nhiều thiên lệch chọn); LINK/ADA/DOGE trượt bootstrap.
