# PREREG FUNDNEG_T1 — long khi funding âm cực đoan (short crowding ⇒ squeeze)

Ngày: 2026-10-23. Agent: fundnegT1 (thực thi), thiết kế: MASTER. Commit file này TRƯỚC mọi tính return/PnL.
Mục tiêu: lệnh MỚI ngoài crash-buy X14 (bù độ thưa). Đây là tín hiệu HƯỚNG, không phải carry/arbitrage.

## 1. Dữ liệu (đã kiểm schema/phủ, chưa nhìn PnL)
- Funding: `~/vz/out/funding/YYYY/YYYY-MM.parquet` (Vision `data/futures/um/monthly/fundingRate`, pipeline VZ_DATA_LAKE), cột `ts:int64` (= Vision `calc_time`, ms), `sym`, `interval_h:int16` (= `funding_interval_hours`), `rate:double` (= `last_funding_rate`, rate ĐÃ settle). 2022–2025: 1.706.746 dòng, 636 symbol; interval {8h: 754.939, 4h: 889.890, 1h: 58.431, 2h: 3.486}.
  - Kiểm sơ bộ: offset `ts` so với tròn giờ 0–31 ms (max) ⇒ calc_time = thời điểm settlement; 0 dòng lệch lưới interval; 0 trùng (sym, phút). Năm 2024 khớp tuyệt đối với nguồn thứ hai `~/vz_e1/raw/funding-2024.parquet` (439.989/439.989 dòng, Δrate = 0).
  - τ := ts − ts mod 60.000 (phút settlement, luôn tròn giờ).
- Giá: `~/vz_e1/raw/kline1m-YYYY-MM.parquet` 2021-12 → 2025-12, `ts:int64` = open time ms, `active` = volume>0 (dòng volume 0 là nến lấp, close = close trước — dùng nguyên trạng). Symbol có `_` (delivery) bị loại khỏi universe.
- X14: printDone 8 seed `~/kaggle_sim/out/tsx-x14-{a1,s7,s13,s21,s99,s123,s777,s2024}/storage/printDone.csv` (cùng bộ 8 tag mà LIQ_PROXY dùng; glob `tsx-x14-s*` chỉ ra 7, seed thứ 8 là `a1`). `sym` thiếu hậu tố ⇒ thêm `USDT`. `start`/`end` giờ +07 ⇒ UTC = −7h. Phủ 2021-07-09 → 2025-11-21 (sim X14 dừng 2025-11-21).
- Không dùng 2020, không dùng 2026.

## 2. Định nghĩa
- f_8h(τ) = rate(τ) × 8 / interval_h(τ) (chuẩn hoá tương đương 8h). Chỉ dùng để XÉT ngưỡng; dòng tiền funding dùng `rate` gốc.
- Universe PIT (tái lập mỗi tháng M): ngày UTC D0 = ngày 1 tháng M; cửa sổ D0−30 … D0−1 (30 ngày); quote volume ngày = Σ `quote_volume` nến 1m trong ngày UTC; ngày không có dữ liệu = 0; xếp theo median 30 ngày; top-100 (loại sym có `_`). Coin delist sau đó vẫn ở universe tháng đó (không survivorship).
- Sự kiện: (sym, τ) với sym ∈ Universe(tháng của τ), f_8h(τ) ≤ ngưỡng.
- Vào lệnh: giá vào P0 = close nến 1m có open ts = τ + 60.000 (nến [τ+1′, τ+2′), thời điểm vào t_in = τ + 120.000). Không nhận funding τ. Thiếu nến này ⇒ bỏ sự kiện (đếm).
- Thoát: P1 = close nến 1m open ts = τ + H + 60.000 (t_out = τ + H + 120.000). Nếu symbol hết dữ liệu trước đó (delist): P1 = close nến cuối cùng có dữ liệu, gắn cờ `exit_fallback` (đếm, báo). Sự kiện có τ + H + 60.000 > 2025-12-31 23:59 UTC (ngoài dữ liệu) ⇒ bỏ (đếm).
- Một vị thế/coin (mỗi biến thể, áp trên tập ALL theo thời gian): nhận sự kiện nếu t_in ≥ t_out của lệnh trước cùng coin, ngược lại bỏ.
- Funding trong lúc giữ: mọi settlement τ' của sym với t_in < τ' ≤ t_out (tức τ < τ' ≤ τ+H). Dòng tiền long trên 1 đơn vị notional ban đầu: −rate(τ') × P(τ')/P0, P(τ') = close nến 1m open ts τ' − 60.000 (giá tại τ'); thiếu ⇒ dùng P0. (Long NHẬN khi rate < 0.)
- Chi phí: taker 0,05 %/chiều + slippage 0,10 %/chiều = 0,15 %/chiều, trừ cộng dồn 0,30 %/vòng trên notional ban đầu.
- net = P1/P0 − 1 + Σfunding − 0,0030. Chi phí ×2: net2 = P1/P0 − 1 + Σfunding − 0,0060.
- Biến thể (4): ngưỡng f_8h ∈ {−0,0005 (−0,05 %), −0,0010 (−0,10 %)} × H ∈ {24h, 72h}.
- Kỳ (theo τ): KHÁM PHÁ 2022-01-01 ≤ τ < 2024-01-01; KIỂM 2024-01-01 ≤ τ < 2026-01-01.

## 3. Chồng lấn X14 (cờ OVERLAP)
Leg X14 = mỗi dòng printDone (union 8 seed), khoảng [start_u, end_u] UTC. Sự kiện OVERLAP nếu:
(a) cùng sym có leg X14 với [start_u, end_u] giao [τ − 24h, τ + 24h] (giao khoảng — bao trùm cả "leg bắt đầu trong ±24h"); HOẶC
(b) ngày UTC của τ có ≥ 1 leg X14 bất kỳ (start_u rơi vào ngày đó, mọi sym/seed) — "ngày sập".
NON-OVERLAP = phần còn lại = alpha mới; tiêu chí chấm trên NON-OVERLAP. Báo cả ALL.
Giới hạn: X14 printDone dừng 2025-11-21 ⇒ sự kiện sau 2025-11-22 không thể bị gắn cờ (b)/(a) — báo riêng số lệnh này.

## 4. Control (100 seed)
Mỗi sự kiện e (của tập đang chấm) được thay bằng 1 lệnh ngẫu nhiên: cùng τ (cùng ngày UTC, cùng giờ settlement, cùng t_in/t_out), cùng H, coin ngẫu nhiên đều trong Universe(tháng τ) cùng tercile vol30 với coin sự kiện tại ngày τ, ≠ coin sự kiện, có P0 và P1 hợp lệ (cùng quy tắc giá/funding/chi phí/fallback). vol30(sym, d) = độ lệch chuẩn log-return ngày (close ngày UTC) trên 30 return d−30…d−1, cần ≥ 20 return; tercile tính trong universe tháng (coin có vol30) tại ngày d. Coin sự kiện không có vol30 ⇒ pool = cả universe (đếm). Không áp quy tắc 1 vị thế/coin cho control. Seed numpy `default_rng(1000+s)`, s=0..99. Thống kê: mean net/lệnh mỗi seed ⇒ p95 qua 100 seed, theo kỳ.

## 5. Tiêu chí (NON-OVERLAP, TỪNG biến thể, đạt TẤT CẢ ⇒ GO)
- F1: kỳ KIỂM mean net/lệnh > 0 VÀ CI 95 % bootstrap theo NGÀY có cận dưới > 0. Bootstrap: resample các ngày UTC (của τ) có lệnh, có hoàn lại, B = 10.000, rng `default_rng(20261023)`, thống kê = mean net trên mọi lệnh của các ngày được rút (trọng số theo lệnh), CI percentile 2,5–97,5.
- F2: kỳ KHÁM PHÁ mean net > 0.
- F3: kỳ KIỂM ≥ 50 lệnh NON-OVERLAP mỗi năm dương lịch (2024 và 2025 đều ≥ 50).
- F4: mean net > p95 control ở CẢ 2 kỳ.
- F5: kỳ KIỂM mean net2 (chi phí ×2) > 0.
ỨNG VIÊN: F1–F3 đạt nhưng F4 hoặc F5 trượt. Còn lại NO-GO. Báo cả 4 biến thể; không chọn biến thể theo kết quả, không đổi ngưỡng/H.

## 6. Mô tả thêm (không vào tiêu chí)
Số sự kiện/năm (thô trước 1-vị-thế, ALL, NON-OVERLAP); hit rate (net > 0); median net; theo năm; theo coin (top-5 coin: tỷ trọng số lệnh và tỷ trọng Σnet); sleeve 2 % vốn/lệnh (compounding trên equity đã thực hiện, PnL ghi tại t_out; equity, CAGR, maxDD trên equity thực hiện, max số vị thế đồng thời) theo kỳ, tập NON-OVERLAP và ALL; MFE/MAE trung vị (high/low 1m trong (t_in, t_out]: nến phút 2–59 giờ τ, đủ các giờ giữa, phút 0–1 giờ τ+H); tương quan (Pearson, Spearman) net với BTC trend: BTC return 7 ngày trước t_in (close nến τ+1′ / close nến τ−7d+1′ − 1) và BTC return trong lúc giữ; tỷ trọng lệnh khi BTC 7d < 0. Số exit_fallback, số sự kiện sau 2025-11-21.

## 7. Validation (bắt buộc trước khi báo)
- V1 look-ahead: (i) offset ts so với tròn giờ ≤ 60 s mọi dòng (calc_time = settlement, không phải công bố sớm); (ii) tải lại 2 file CSV Vision gốc (BTCUSDT + 1 coin 4h, 1 tháng) so với parquet: calc_time/rate khớp tuyệt đối; (iii) assert t_in > τ mọi lệnh; (iv) không dùng premiumIndex/rate dự báo realtime.
- V2: assert ts int64 mọi bảng; không trùng (sym, τ) trong funding & sự kiện; sau resample giờ: số (sym, giờ) duy nhất = số dòng, số nến/giờ ≤ 60.
- V3: script ĐỘC LẬP (không import pipeline, đọc thẳng raw kline/funding/printDone, tự tính universe, sự kiện, 1-vị-thế, overlap, giá, funding) tái lập mean net biến thể (−0,10 %, 24h) kỳ KIỂM, cả ALL và NON-OVERLAP: |Δ| < 1e-9 và cùng số lệnh.
- V4: kiểm tay 10 lệnh ngẫu nhiên (seed 7): in nến 1m thật tại vào/ra, các dòng funding trong lúc giữ, tính lại net bằng tay, so khớp.
- V5: dấu funding 3 ca tổng hợp: rate âm (long nhận +), rate dương (long trả −), hỗn hợp; chạy qua đúng hàm accrual của pipeline.

## 8. Ngân sách
Thư mục trung gian `~/claude_master/fundneg_t1_wk/` (< 3 GB), python ≤ 5 GB, xử lý từng tháng (1m → panel giờ/ngày). Code `research/fundneg_t1/`, kết quả `docs/result/FUNDNEG_T1.md` + `docs/result/fundneg_t1/`.

## Lệch thiết kế (so với brief MASTER)
1. Seed thứ 8 = `tsx-x14-a1` (glob `s*` chỉ có 7) — theo quy ước LIQ_PROXY.
2. "Nến 1m τ+1′" hiểu là nến có open time τ+1′ (đóng τ+2′) — trễ thêm 1′, bảo thủ.
3. Overlap (a) dùng giao khoảng giữ leg với ±24h (rộng hơn "leg bắt đầu trong ±24h") — bảo thủ cho "alpha mới".
4. F3 hiểu là MỖI năm kiểm ≥ 50 (chặt hơn trung bình).
5. Funding cashflow nhân P(τ')/P0 (notional theo mark xấp xỉ bằng close 1m) thay vì notional cố định.
