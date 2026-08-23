# Per-entry path analysis: lướt vs nuôi — KẾT QUẢ (2026-08-16)

Join **170,790/171,130 entry thật** (entry_universe_g008, 2021–2025) × label 15m (maxFav/maxAdv/tHit/retEnd @ 4h/12h/24h/72h). Data: `entry_pathstats_g008.csv`, script `join_paths.py`.

> ⚠️ **Caveat đọc trước khi kết luận**: đây là **raw price excursion**, KHÔNG fee (~0.1% round-trip), KHÔNG funding, KHÔNG leverage/sizing/slippage. Sim exit là **xấp xỉ** (dùng maxFav/maxAdv toàn horizon + thứ tự tHit, không phải path 1m thật). Universe là **g008** (net 0.008), không phải canonical G015K5 chính xác. => Đây là **hình dạng cơ hội (edge shape)**, không phải PnL net thực. Ground truth PnL net vẫn là WFO sim (đã có fee/funding/exit).

## 1. Edge selection: CÓ THỰC và RẤT MẠNH

P(coin được chọn đạt maxFav ≥ 6%):
- **4h: 53.8%** (base rate ~4.6% → **lift ~11.7×**)
- 12h: 71.8% | 24h: 81.2% | 72h: 91.3%

Hơn nửa số lệnh bật ≥6% trong 4h; 91% bật ≥6% trong 72h. Selector+gate thực sự chọn đúng coin pump. Đây là con số "edge có thực" mà trước đó còn thiếu.

## 2. Coin được chọn ĐI RẤT XA quá 4h → lướt 4h "ăn ít" (định lượng)

maxFav median theo horizon: **4h=6.5% → 12h=10.6% → 24h=14.2% → 72h=21.0%**.
Winners@4h (91,883 lệnh bật ≥6% trong 4h): median maxFav_72h = **+27.3%**, retEnd_72h = **+12.6%**, maxAdv_72h chỉ −7.2%.

=> Lướt thoát ở 4h chỉ bắt **~1/3** con sóng. "Chọn coin pump nhưng đánh lướt → ăn ít" **được xác nhận bằng số**.

## 3. "Đuôi lớn (maxDD)" cũng có thực — nhưng đến CHẬM

maxAdv median: 4h=−3.7% → 24h=−6.7% → 72h=−9.8%. Tail p05: 4h=−19% → 72h=−42%.
Giữ càng lâu, drawdown càng sâu. Nuôi mà KHÔNG có stop = ăn đuôi trái −40%.

## 4. PHÁT HIỆN NGƯỢC TRỰC GIÁC: "cắt lỗ nhanh" là SAI ở đây

**P(chạm adverse TRƯỚC favorable @4h) = 66.7%.** 2/3 số coin **dip trước rồi mới pump**.
=> **SL chặt sẽ cắt ngay trước cú pump** → phá edge. Đây là lý do định lượng khiến lướt/cắt-nhanh thất bại.

### Exit sim (raw, mean return / %win / p05):
| Policy | mean | %win | p05 |
|---|---|---|---|
| hold 4h | +3.65% | 67% | −10.6% |
| hold 24h | **+9.38%** | 70% | −16.6% |
| hold 72h | **+10.9%** | 69% | −24% |
| TP6%/SL3% @24h | +0.89% | 43% | −3% |
| TP6%/SL5% @24h | +0.96% | 54% | −5% |
| TP15%/SL5% @24h | +2.39% | 42% | −5% |
| TP20%/SL5% @72h | +2.98% | 35% | −5% |
| TP30%/SL8% @72h | +4.39% | 51% | −8% |

**Mọi TP/SL chặt đều thua xa pure-hold.** Càng nới TP+SL càng tiến về pure-hold. Cắt lỗ nhanh + chốt lời nhỏ = phá ~90% edge (từ +9.4% còn +0.9%).

## 5. Kết luận cho chiến lược (đảo so với suy luận thiết kế ban đầu)

- **"Nuôi khi lãi" = ĐÚNG mạnh.** Edge thật của model là **trend nhiều ngày**, bị label 4h/6% gán nhầm thành "spike ngắn". Giá trị nằm ở việc GIỮ.
- **"Lướt/cắt nhanh khi lỗ" = SAI ở đây.** Vì dip-trước-pump (66.7%), SL phải **RỘNG** (dưới nhiễu dip, ~−15-20% hoặc theo ATR), không chặt. Time-stop 4h cũng sai — edge KHÔNG tắt ở 4h mà LỚN dần.
- **SL đúng vai trò**: chỉ để chặn đuôi trái thảm hoạ (−40%), không phải để "cắt nhanh". Rộng, cách xa entry.
- **TP**: bỏ TP nhỏ, dùng trailing rộng / giữ tới 24-72h.

## 6. Selector & gate

- Label `maxFav_4h≥6%` **quá ngắn**, bán rẻ tín hiệu. Nên relabel horizon **24h/72h** (hoặc retEnd_24h) để objective khớp nơi có tiền. Slot 12h/24h/72h đã có sẵn trong label.
- Nhưng: selection @4h ĐÃ ngầm bắt được trend (4h-pickers chạy tới +27%@72h) → **chỉ cần đổi EXIT sang giữ/trailing đã ăn phần lớn upside**, không nhất thiết retrain ngay.

## 7. Việc tiếp theo (bắt buộc trước khi tin)

Đây mới là **edge shape (raw)**. Phải **validate trong WFO sim thật** (có fee/funding/1x lev): chạy 1 biến thể exit = **SL rộng (−15-20%) + giữ 24-72h / trailing rộng, bỏ TP nhỏ**, so PnL/maxDD net vs config lướt hiện tại. Nếu net vẫn thắng → đổi chiến lược. Kỳ vọng: mean cao hơn nhiều, maxDD cũng cao hơn → cần cân bằng bằng sizing/lev, không bằng SL chặt.

## Trạng thái
5m grid kernel vẫn RUNNING (GPU). entry_pathstats_g008.csv đã lưu để phân tích sâu thêm (per-year, per-regime, trailing sim path 1m thật nếu cần).
