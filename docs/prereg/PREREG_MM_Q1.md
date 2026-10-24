# PREREG MM_Q1 — Pilot đo lường: market making thụ động lúc thị trường YÊN có edge sau phí maker không

Commit file này TRƯỚC khi tính bất kỳ fill/markout/PnL nào. Trước commit agent (mm1) chỉ xem: schema trades/orderbook/kline cryptohftdata, kích thước file, xếp hạng quote volume 2025-07, và một phép thử CHỈ CHẤT LƯỢNG SỔ (không mô phỏng fill, không markout) trên giờ 2025-09-02 12:00 UTC cho BTC/ETH/NEO/NXPC/NEIRO: replay 5,8 s/giờ BTC, RSS ≈ 2 GB, pu_breaks 0, crossed 0, V1 99,4–99,9 %, spread trung vị BTC 1 tick (0,009 bps), NEO 1,5 bps, NEIRO 3,1 bps, NXPC 0,9 bps (6 tick). Chỉ đo lường markout; KHÔNG xây hệ.

## 1. Dữ liệu
- cryptohftdata `binance_futures/{YYYY-MM-DD}/{HH}/{SYM}_{orderbook|trades|kline}.parquet.zst` (tải qua `research/chd/chd_lib.py`, key nạp bằng `chd_env.sh`, không in key). Xử lý TRONG BỘ NHỚ từng symbol-giờ, không ghi file thô ra đĩa. Điều khoản internal-use: dữ liệu chỉ ở Oracle; repo chỉ nhận thống kê.
- orderbook: chỉ diff `event_type=update` (U=first_update_id, u=final_update_id, pu=prev_final_update_id, side, price, quantity chuỗi thập phân, event_time E int64 ms). Không có snapshot ⇒ dựng sổ từ RỖNG.
- trades: trade_id, price, quantity, trade_time int64 ms, is_buyer_maker (true ⇒ taker BÁN = seller-initiated).
- kline 1m cryptohftdata (lọc 1h). Kline Oracle `~/vz_e1/raw/kline1m-2025-07.parquet` dùng cho chọn symbol; kline Oracle 2025-07…12 dùng đối chiếu (V2b).
- Đợt MKT: `~/claude_master/liqx_wk/s1/episodes.parquet`, level = MKT, variant = main (T_on, T_end int64 ms; phủ tới 2025-12).

## 2. Mẫu symbol (chốt, tính bằng `research/mm_q1/mm_universe.py`)
- Xếp hạng: quote volume ngày UTC của 31 ngày 2025-07 (PIT, gồm symbol sau này delist; ngày không có bar = 0), lấy median; chỉ symbol đuôi USDT, loại base stable/index (USDC, FDUSD, TUSD, USDP, USDE, BUSD, BTCDOM, DEFI, FOOTBALL, BLUEBIRD); 501 symbol được xếp hạng; hạng 1 = lớn nhất.
- Lớn (cố định theo MASTER): BTCUSDT (hạng 2), ETHUSDT (1), SOLUSDT (3), XRPUSDT (4).
- Vừa: hạng 20–40 (21 symbol, đều đủ điều kiện) — chọn 4 bằng `np.random.default_rng(20261024).choice(sorted(eligible), 4, replace=False)`: NEIROUSDT (39), TAOUSDT (40), VIRTUALUSDT (34), 1000SHIBUSDT (33).
- Nhỏ: hạng 80–150 (71 symbol, 70 đủ điều kiện; AINUSDT loại vì không đủ 31×1440 bar và không có file cryptohftdata ngày 2025-07-01) — cùng rng, lần gọi thứ 2: NEOUSDT (146), PORTALUSDT (141), MASKUSDT (120), NXPCUSDT (107).
- Điều kiện đủ: đủ 31×1440 bar 1m trong 2025-07 và có cả trades + orderbook cryptohftdata ngày 2025-07-01.

## 3. Giờ mẫu
- KHÁM PHÁ (D): giờ H (đầu giờ UTC, int64 ms) ∈ [2025-07-01 00:00, 2025-12-31 23:00] (4 416 giờ). KIỂM (K): [2026-01-01 00:00, 2026-09-30 23:00] (6 552 giờ).
- Thứ tự ứng viên: D = `np.random.default_rng(202507).permutation(hours_D)`, K = `np.random.default_rng(202601).permutation(hours_K)`; CHUNG cho mọi symbol. Với mỗi symbol, duyệt ứng viên theo thứ tự, nhận giờ đạt mọi điều kiện dưới đây cho tới khi đủ 60 giờ/kỳ (hết ứng viên ⇒ báo số nhận được).
- Điều kiện "YÊN" (lệch thiết kế §12-1): (a) chỉ kỳ D: loại H nếu [H, H+1h) giao [T_on − 6h, T_end + 6h] của bất kỳ đợt MKT main; (b) mọi kỳ: |r_BTC(H)| < 1 % và |r_sym(H)| < 2 %, r(H) = close(bar 1m mở lúc H+59′)/open(bar mở lúc H) − 1 từ kline cryptohftdata (lọc kline_start_time ∈ [H, H+1h), dedupe theo start_time giữ bản nhận sau cùng, cần đúng 60 bar trên lưới); nếu kline không đủ 60 bar ⇒ r = giá trade cuối/giá trade đầu trong [H, H+1h) − 1 (cùng định nghĩa); BTC không đủ cả hai ⇒ giờ bị loại (đếm).
- Có file: thiếu trades hoặc orderbook ⇒ loại ("no_data", đếm; symbol delist trong K được báo).
- Chất lượng sổ (sau dựng §4) ⇒ loại và lấy ứng viên kế: pu_breaks > 0, hoặc u không tăng ngặt, hoặc E giảm giữa message, hoặc tỉ lệ giây không hợp lệ (crossed bb ≥ ba hoặc thiếu một phía) trên lưới k = 300…3599 s > 1 %.
- Ghi mọi ứng viên bị loại kèm lý do.

## 4. Dựng sổ
- Giá → số nguyên chính xác: d = số chữ số thập phân lớn nhất trong các chuỗi giá (orderbook ∪ trades của symbol-giờ), p_int = int(chuỗi bỏ dấu chấm)·10^(d − số lẻ). tick = gcd các hiệu của giá orderbook phân biệt (đã sắp). Đếm trade có giá không bội tick.
- Message = các hàng liền kề cùng u; message có u đã xuất hiện trước đó bị bỏ (đếm). pu_breaks = #(pu_i ≠ u_{i−1}).
- Replay từ RỖNG: qty = 0 ⇒ xoá mức, ngược lại gán qty. Sau mỗi message ghi trạng thái (E, best bid bb, best ask ba, qty tại bb, qty tại ba, qty tại bb − tick, qty tại ba + tick).
- Đồng hồ sổ = event_time E: "sổ tại τ" = trạng thái sau message cuối có E ≤ τ. Warm-up 300 s đầu giờ bị bỏ.

## 5. Mô phỏng fill
- Mốc quote t = H + k·1000 ms, k = 300…3299 (3 000 mốc; dừng 300 s trước cuối giờ để markout 300 s nằm trong cùng file — lệch §12-2). Mỗi mốc: 1 đơn vị bid + 1 đơn vị ask, sống [t, t + 1 000 ms), độc lập giữa các mốc; ≤ 1 fill/phía/mốc.
- Độ trễ L ∈ {0, 100, 300} ms: giá quote lấy từ sổ tại t − L; sổ không hợp lệ (thiếu phía / bb ≥ ba) ⇒ không quote mốc đó.
- Khoảng cách: d0 = quote bid tại bb, ask tại ba; d1 = bid tại bb − tick, ask tại ba + tick.
- Fill BẢO THỦ (cons): bid fill tại trade đầu tiên trong [t, t+1s) có is_buyer_maker = true và giá < giá quote; ask fill tại trade đầu tiên có is_buyer_maker = false và giá > giá quote. Giá fill = giá quote. t_fill = trade_time của trade đó.
- Fill LẠC QUAN (opt, chỉ báo cáo): như cons, HOẶC trade cùng hướng có giá = giá quote và Σ qty các trade đó từ t (trong cửa sổ 1 s) ≥ queue ahead (qty mức đó trong sổ tại t − L; d1 dùng qty tại bb − tick / ba + tick, 0 nếu mức trống); lấy fill sớm hơn.
- Trades: dedupe trade_id, sắp (trade_time, trade_id).

## 6. Markout
- side = +1 (bid fill, mua), −1 (ask fill). mid(τ) = (bb + ba)/2 của sổ tại τ; sổ không hợp lệ ⇒ markout fill đó ở horizon đó = thiếu (đếm, loại khỏi mẫu số horizon đó).
- markout_h = side × (mid(t_fill + h) − p_fill)/p_fill, h ∈ {1, 10, 60, 300} s (đơn vị: phân số; báo bps). net_h = markout_h − 0,0002 (phí maker VIP0 0,02 %/fill, không BNB).

## 7. Tổng hợp và thống kê
- Lưu mỗi symbol-giờ: theo (L, d, rule, side): n_fill, Σ markout_h, n hợp lệ_h. Tier = {lớn, vừa, nhỏ}, kỳ = {D, K}.
- Mean net/fill của tier-kỳ = Σ_{symbol-giờ, 2 phía} (Σ markout_h − 0,0002·n hợp lệ_h) / Σ n hợp lệ_h (gộp theo fill).
- CI 95 %: bootstrap percentile 10 000 lần, `np.random.default_rng(7)`, đơn vị resample = GIỜ lịch (H) — mọi symbol-giờ của tier có cùng H thuộc một cụm; thống kê = Σ net / Σ n của các cụm được rút.
- fill/giờ = n_fill bid + ask (cons, L = 300, d0) trong cửa sổ 3 000 s của symbol-giờ; báo trung vị theo symbol-giờ của tier-kỳ (không quy đổi lên 3 600 s — bảo thủ; kèm số ×1,2 mô tả).

## 8. Tiêu chí "CÓ CỬA" (sang bước 2 — mô phỏng inventory)
Tier X đạt ⇔ ở CẢ D và K, với L = 300 ms, fill cons, d0, h = 60 s: (i) mean net/fill > 0; (ii) cận dưới CI 95 % > 0; (iii) trung vị fill/giờ ≥ 20; (iv) V1 của tier-kỳ ≥ 99 % (điều kiện tin cậy; trượt ⇒ tier đó "KHÔNG ĐO ĐƯỢC").
- GO: ≥ 1 tier đạt, và V2, V3, V5 đạt.
- ỨNG VIÊN: không tier nào đạt với d0 nhưng ≥ 1 tier đạt đủ (i)–(iv) với d1 (+1 tick) — MASTER quyết (bổ sung kỹ thuật §12-3).
- NO-GO: còn lại ⇒ ĐÓNG họ MM thụ động retail.
- Không đổi tham số sau khi thấy kết quả. Bug phát hiện sau khi thấy kết quả ⇒ sửa, ADDENDUM, báo số trước/sau.

## 9. Mô tả thêm (không thuộc tiêu chí)
- Mọi tổ hợp L × d × rule × h (mean gross = adverse selection trước phí, mean net, CI); theo symbol; theo phía.
- Spread trung vị (bps và tick) theo giây hợp lệ của symbol-giờ, trung vị theo tier.
- Theo giờ trong ngày UTC: [0,8), [8,16), [16,24) — mean net (L300, cons, d0, h60).
- Ước lợi nhuận/ngày thô = mean net × trung vị fill/giờ × 24 × 100 USD (1 lot = 100 USD/fill; KHÔNG tính inventory risk, không tính giới hạn vị thế, không tính việc fill hai phía không cân).
- Mô tả kỳ D: số giờ nhận được nếu thêm điều kiện LIQX_S1 (|Σ r_mkt EW alt 1h| < 1,5 % và không bucket I_mkt ≥ θ_MKT 99 = 0,006492) từ `liqx_wk/s1/mkt.parquet` — chỉ đếm/so mô tả, không lọc.

## 10. Validation
- V1 dựng sổ: trade trong [H+300 s, H+3600 s): mua (is_buyer_maker = false) đạt nếu giá ≥ ba − tick; bán đạt nếu giá ≤ bb + tick; so với sổ tại trade_time HOẶC sổ sau message kế tiếp (dung sai lô 100 ms). Ngưỡng ≥ 99 % gộp theo tier-kỳ; báo phân phối theo symbol-giờ (min, p5).
- V2: ts int64 (assert E, trade_time, kline_start_time); dedupe trade_id (đếm trùng); đếm trade không bội tick; số mốc quote = 3 000/symbol-giờ. V2b: với giờ D nhận được, r_sym từ kline cryptohftdata vs kline Oracle |Δ| < 1e-9 (mô tả nếu trượt; dùng để kiểm nguồn).
- V3: script ĐỘC LẬP tối giản (không import pipeline; đọc thô, tự đổi giá, tự replay sổ bằng cấu trúc khác, tự fill/markout) cho 1 symbol-giờ lớn + 1 nhỏ ⇒ |Δ Σ markout| < 1e-9 và n_fill trùng cho mọi (L, d, cons, side, h).
- V4: in tay 5 fill (L300, cons, d0) của 1 symbol-giờ: mốc quote, sổ dùng, trade kích hoạt (id, giá, giờ, is_buyer_maker từ file thô), mid(t_fill + 60 s), markout — kiểm bằng mắt.
- V5 dấu: giả lập quote tại mid m của sổ tại t (L = 0), fill khi trade bán < m (bid) / mua > m (ask); AS0 = side × (giá trade − m)/m phải âm và mean AS0 / (−mean nửa spread tương đối) ∈ [0,8; 2,0] (gộp mọi symbol-giờ; báo theo tier).

## 11. Tài nguyên
- Xử lý trong RAM từng symbol-giờ (RSS ≈ 2 GB cho BTC/ETH), ≤ 3 tiến trình song song; kết quả nhỏ JSON/symbol-giờ ở `~/claude_master/mm_wk/res/`; xoá mm_wk khi xong (giữ artefact trong repo: bảng thống kê symbol-giờ, json tổng hợp).

## 12. Lệch thiết kế
1. Tiêu chí yên: không tính được I_mkt/EW-alt cho 2026 từ dữ liệu trên Oracle (kline 2026 không có trên Oracle; Vision metrics 2026 không có taker volume để dựng P2) ⇒ dùng điều kiện dự phòng của MASTER (|r_sym| < 2 %, |r_BTC| < 1 %) cho MỌI giờ cả hai kỳ (đối xứng); kỳ D GIỮ thêm loại ±6h quanh đợt MKT (dữ liệu có sẵn); điều kiện LIQX_S1 chỉ mô tả ở D.
2. Mốc quote chỉ k = 300…3299 s (không tới 3599 s) để markout 300 s không cần file giờ sau; fill/giờ đếm trên 3 000 s (bảo thủ).
3. Nhãn ỨNG VIÊN cho trường hợp chỉ d1 đạt (MASTER không định nghĩa nhãn; d0 là tiêu chí chính).
4. Đồng hồ sổ dùng event_time E (thời điểm sàn phát), không transaction_time — bảo thủ cho độ trễ.
5. "Chọn 4 trong dải hạng" MASTER không nêu cách ⇒ rng seed 20261024 như §2.
