# PREREG TREND_T1 — họ trend long-only khung ngày (alpha bổ sung cho crash-buy X14)

Ngày: 2026-10-23. Agent: trendT1. Thiết kế: MASTER. Commit file này + sha256 TRƯỚC khi tính bất kỳ PnL nào của trend.
Đã làm trước prereg (không nhìn PnL trend): resample 1m→ngày (`research/trend_t1/t1_resample.py`), đọc chuỗi equity X14 8 seed (`t1_x14.py`, chỉ X14), kiểm schema/phủ dữ liệu.

## 1. Dữ liệu
- Kline 1m `~/vz_e1/raw/kline1m-YYYY-MM.parquet` 2021-12 → 2025-12 (49 tháng, 636 symbol USDT-M, gồm coin đã delist). `ts` int64 ms (open time), cột `active`=False là bar lấp (volume 0, close = close trước).
- Bar ngày UTC [00:00, 24:00): `close` = close của dòng cuối ngày (thường 23:59); `px01` = close của dòng đầu tiên có phút ≥ 1 (bình thường = nến open 00:01 UTC); `qv` = Σ quote_volume; `n_rows`, `n_active`. Bảng giá biên giờ: `p(t)` = close nến open t−60 s (dùng định giá notional lúc funding).
- Phủ đã kiểm: 415 689 sym-ngày; 537 sym-ngày thiếu phút (n_rows<1440, đều ở ngày niêm yết/delist/lỗ dữ liệu, ghi nhận, không lấp); 512 sym-ngày px01 không phải phút 1 (dùng dòng kế tiếp, đếm và báo). Lỗ dữ liệu toàn thị trường: 2022-02-26..28 và 2022-04-01..02 (~48 symbol thiếu) — nằm trong warm-up; ngày thiếu được forward-fill close cho tính chỉ báo.
- Funding: `~/vz/out/funding/YYYY/YYYY-MM.parquet` (Vision fundingRate; ts int64, rate, interval_h 1/2/4/8). Thời điểm funding T = floor(ts tới giờ) (phần dư đo được ≤ 47 ms). Long trả `q · p(T) · rate` (rate>0 ⇒ trả, rate<0 ⇒ nhận). Symbol-tháng thiếu trong file funding mà coin đang giao dịch ⇒ dùng 0,01 %/8h tại 00/08/16 UTC, báo độ phủ.
- X14: 8 seed `~/kaggle_sim/out/tsx-x14-{a1,s123,s13,s2024,s21,s7,s777,s99}`. Equity ngày = `b + unP` ở dòng `BudgetManagerSimple: Update YYYYMMDD 07:00` của `logs/sim.out` (07:00 +07 = 00:00 UTC ⇒ equity MTM đầu ngày UTC). Return ngày UTC D = E(D+1)/E(D) − 1 (có đến 2025-12-29). Bản chỉ-realized (`b`) báo mô tả.
- "Median seed" X14 = seed hạng 4/8 (tăng dần) theo Sharpe MTM X14 2022-05-01→2025-12-29 = **s2024** (chọn trước khi có PnL trend). G4/G5 chấm trên s2024; báo thêm từng seed.

## 2. Kỳ
Warm-up từ 2021-12-01. KHÁM PHÁ (DEV) 2022-05-01→2023-12-31; KIỂM (TEST) 2024-01-01→2025-12-31. Sleeve chạy liên tục 2022-05-01→2025-12-31 (vốn đầu 1,0); chỉ số mỗi kỳ tính trên return ngày trong kỳ. HO 2026 chỉ mô tả, tuỳ chọn, làm sau cùng nếu còn thời gian.

## 3. Universe U (PIT, tái lập 00:00 UTC ngày 1 mỗi tháng M)
- Ứng viên: symbol có ngày dữ liệu đầu tiên ≤ (ngày 1 của M − 120 ngày), có trong dữ liệu ngày cuối tháng trước.
- Loại: stable-like/pegged `USDCUSDT, PAXGUSDT, XAUUSDT` (+ BUSD/TUSD/FDUSD/USDP/DAI/USDE nếu xuất hiện — không có trong dữ liệu); chỉ số `BTCDOMUSDT, DEFIUSDT, BLUEBIRDUSDT, FOOTBALLUSDT`. (USTCUSDT giữ: đã mất peg, hành vi như coin biến động.)
- Xếp theo median `qv` ngày trên 30 ngày [M1−30, M1−1] (ngày không có dòng = 0); lấy top-30.
- U(M) áp dụng cho mọi quyết định có ngày khớp lệnh thuộc tháng M.

## 4. Tín hiệu (close ngày d) & khớp (close nến 1m 00:01 UTC ngày d+1 = `px01[d+1]`)
Chỉ báo trên chuỗi close ngày (ffill qua ngày thiếu dữ liệu), cần đủ cửa sổ (min_periods = cửa sổ).
- V1 TS-SMA100: tín hiệu long nếu close_d > SMA100_d (SMA gồm d); thoát khi close_d < SMA100_d.
- V2 TS-SMA50: như V1 với SMA50.
- V3 Donchian 20/10: vào khi close_d > max(close_{d−20..d−1}); thoát khi close_d < min(close_{d−10..d−1}).
- V4 Donchian 55/20: như V3 với 55/20.
- V5 XS-MOM: rebalance thứ Hai 00:01 UTC (tín hiệu close Chủ nhật d). mom = close_{d−1}/close_{d−29} − 1 (28 ngày, bỏ ngày gần nhất). Long top-5 của U(tháng của thứ Hai) theo mom, chỉ khi BTC close_d > SMA100_d; ngược lại cash cả tuần.
- V6 = V1 + regime: chỉ vào/giữ khi BTC close_d > SMA100_d; BTC close_d ≤ SMA100_d ⇒ thoát toàn bộ tại 00:01 d+1.
- Strength xếp hạng: SMA: close/SMA − 1; Donchian: close/max_N − 1; XS: mom.

## 5. Chọn lệnh & sizing (sleeve vốn C, 1x, gross ≤ 1)
- V1–V4, V6 (mỗi ngày d): (a) thoát: tín hiệu thoát, hoặc coin không thuộc U(tháng của d+1), hoặc (V6) regime tắt. (b) Vào: slot trống = 10 − số đang giữ; ứng viên = coin ∈ U(tháng d+1), chưa giữ, n_active_d > 0, tín hiệu vào đúng ở d (SMA: trạng thái close > SMA; Donchian: sự kiện breakout đúng ngày d), có σ20; xếp strength giảm dần, lấy đủ slot. Vị thế đang giữ không bị thay bởi tín hiệu mạnh hơn.
- V5: mỗi thứ Hai đặt lại toàn bộ danh mục = top-5 (hoặc cash); giữa tuần không đổi (trừ delist).
- Trọng số: w_i = (1/10)·min(1, 0,04/σ20_i) (V5: 1/5), σ20 = std mẫu (ddof=1) của 20 log-return ngày kết thúc ở d. Notional vào = w_i · E(00:00 ngày khớp); số lượng q khoá đến khi thoát (V1–V4, V6); V5 đặt lại theo trọng số mục tiêu mỗi thứ Hai (phí trên |Δnotional|). Nếu tổng notional (vị thế cũ theo giá px01 + mới) > E ⇒ thu nhỏ tỷ lệ các lệnh mới cho gross = 1. Phần còn lại cash 0 %.
- Delist/ngừng giao dịch: ngày D có n_active = 0 (hoặc không có dòng) mà đang giữ ⇒ thoát cưỡng bức tại close cuối có dữ liệu (= giá giao dịch cuối, bar lấp giữ nguyên close), ghi nhận vào ngày D, có tính phí; ghi danh sách.

## 6. Kế toán PnL (dollar, return ngày = PnL_D / E_{D−1})
- Giữ trọn ngày: q·(close_D − close_{D−1}); vào ngày D: q·(close_D − px01_D); thoát ngày D: q·(px01_D − close_{D−1}).
- Chi phí: 0,05 % taker + 0,05 % slippage = 0,10 %/chiều × notional giao dịch. G6: 0,20 %/chiều (funding giữ nguyên).
- Funding: vị thế được tính funding tại T nếu t_vào (00:01 ngày vào) < T < t_ra (00:01 ngày ra), tức: ngày vào chỉ các T > 00:01; ngày giữ trọn mọi T trong ngày; ngày thoát chỉ T = 00:00.
- Sharpe = mean/std(ddof=1) return ngày lịch × √365 (gồm ngày cash). maxDD trên equity tích luỹ trong kỳ (đỉnh khởi đầu = 1). CAGR = (Π(1+r))^(365/n) − 1.

## 7. Control (100 seed/biến thể)
Lấy danh sách lệnh thật của biến thể (sym, ngày khớp vào, ngày khớp ra). Mỗi seed: thay sym bằng coin ngẫu nhiên đều trong U(tháng ngày vào) đủ điều kiện (n_active>0 ở ngày tín hiệu, có σ20, không trùng coin control đang giữ trong khoảng chồng lấn), giữ nguyên ngày vào/ra (⇒ cùng số vị thế mỗi ngày, cùng phân phối thời gian giữ). Sizing cùng quy tắc (σ20 của coin ngẫu nhiên), cùng kế toán/chi phí/funding; V5 control đặt lại trọng số mỗi thứ Hai như strategy. Coin ngẫu nhiên delist sớm ⇒ thoát cưỡng bức. p95 Sharpe theo kỳ trên 100 seed.

## 8. So với X14
Tương quan Pearson return ngày (ngày chung). Danh mục ghép r_c = 0,7·r_X14 + 0,3·r_T (cộng return ngày, xấp xỉ kế toán, ngầm rebalance ngày). Kỳ TEST chấm X14 đến 2025-12-29.

## 9. TIÊU CHÍ (từng biến thể; đa kiểm định: 6)
- G1 net Sharpe ≥ 0,8 ở cả DEV và TEST.
- G2 maxDD ≥ −35 % mỗi kỳ.
- G3 Sharpe > p95 control ở cả 2 kỳ.
- G4 corr ngày với X14 (s2024) ≤ 0,3 cả 2 kỳ.
- G5 ghép 70/30 Sharpe > X14 một mình cả 2 kỳ VÀ maxDD ghép ≥ maxDD X14 − 3 điểm % mỗi kỳ (s2024).
- G6 chi phí ×2 (0,20 %/chiều) Sharpe TEST ≥ 0,5.
- GO: G1–G6 đều đạt. ỨNG VIÊN: TEST Sharpe ≥ 0,8, DEV Sharpe trong [0,5; 0,8) và G2–G6 đạt. Còn lại NO-GO.
- Mô tả thêm: CAGR, exposure % (ngày có ≥1 vị thế; gross TB), turnover/năm (Σ|notional giao dịch|/E TB/năm), số lệnh/năm, Sharpe theo năm, PnL theo coin top/bottom, % ngày X14 (s2024) không có leg mà trend có vị thế; G4/G5 từng seed.

## 10. Validation (bắt buộc trước khi báo)
- V1 look-ahead: với ≥5 ngày cắt d, nhân mọi giá/volume sau d ×3 ⇒ toàn bộ quyết định (vào/ra/ứng viên/strength/U) có ngày tín hiệu ≤ d không đổi (cả 6 biến thể).
- V2 assert bar ngày: ≤1440 dòng/sym-ngày, ts int64, không trùng (sym,ts); số ngày thiếu phút ghi rõ.
- V3 tái lập ĐỘC LẬP (không import pipeline, đọc thẳng parquet 1m và funding) PnL V1 và V3 cho BTC, ETH, SOL ở chế độ 1 coin (universe = {coin}, w = (1/10)·min(1, 0,04/σ20)); |Δ equity ngày| < 1e-6.
- V4 dấu funding: kiểm tay 3 khoảng giữ (có rate dương và âm).
- V5 kiểm tay 10 lệnh ngẫu nhiên: giá vào/ra = close nến 1m open 00:01 UTC thật đọc thẳng từ parquet 1m.

## 11. Lệch thiết kế / chi tiết kỹ thuật bổ sung
1. Thêm PAXG, XAU vào danh sách loại (tài sản neo vàng, không phải crypto biến động) — không có trong danh sách MASTER nhưng cùng tinh thần "stable-like".
2. Vị thế của coin rời U khi đổi tháng ⇒ thoát 00:01 ngày 1 (MASTER không nêu; chọn để danh mục luôn ⊂ U PIT). V5 không áp (chỉ đổi thứ Hai).
3. Donchian dùng sự kiện breakout đúng ngày (literal "vào khi close > max20"); SMA dùng trạng thái. Không thay incumbents bằng tín hiệu mạnh hơn.
4. X14 equity dùng MTM `b+unP` (đúng bản chất corr ngày); MASTER nêu X14 Sharpe 1,80 / CAGR 27,6 % / maxDD −22,9 % — số đo từ sim.out cho Sharpe 2022-05→2025-12 ≈ 2,05–2,41 (MTM), CAGR ≈ 39–45 %: khác số MASTER, CHƯA GIẢI THÍCH (có thể khác định nghĩa/kỳ/von); không ảnh hưởng tính G4/G5 vì so trên cùng chuỗi.
5. Control giữ nguyên ngày vào/ra của strategy ⇒ control khớp cả timing tổng (bao gồm regime BTC của V5/V6); G3 đo giá trị chọn coin trong cùng chuỗi exposure.
6. Kế toán ghép 70/30 dùng cộng return ngày (theo thiết kế).
7. Resample tháng lớn nhất đạt peak RSS 5,2 GB (vượt nhẹ khuyến nghị 5 GB) — đã xong, không chạy lại; phép tái lập V3 đọc lọc theo symbol.
