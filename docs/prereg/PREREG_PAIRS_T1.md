# PRE-REG — PAIRS_T1: pairs trading / stat-arb market-neutral trên Binance USDⓈ-M perp, tầng 1 (MASTER 2026-10-23)

**Mục tiêu.** Tìm alpha MỚI, market-neutral, bù tính thưa của crash-buy K24 (hệ dùng ≤ 52 % vốn, ~63 % thời gian không vị thế). Chưa từng test pairs cointegration trong repo.

**Bài học đã có, áp vào thiết kế:**
- Track B 09-28 (`RESULT_TRACKB_REDFLAGS.md`): "edge" là artifact của stop mô hình như quyền chọn miễn phí và universe tĩnh. ⇒ Ở đây universe POINT-IN-TIME, mọi lệnh (kể cả stop) khớp tại **open nến kế tiếp**, không khớp tại giá ngưỡng, và bắt buộc control ngẫu nhiên V3.
- T2-MOM (`RESULT_T2_MOM.md`): long-short có tuần −128 % do short squeeze. ⇒ Báo tuần tệ nhất, tiêu chí G5.
- Chi phí thật (BOOK_COST2): taker 0,05 %/chiều, slip ≈ 0. ⇒ Ở đây dùng 0,05 % + 0,02 % slip (thận trọng hơn), báo thêm ×2 và maker.

**CÔNG KHAI trước khi chạy:** chưa tính bất kỳ PnL nào trên dữ liệu thật. Đã chạy trước commit: build panel 1h, smoke formation trên 3 tuần thật (chỉ danh sách cặp, KHÔNG PnL) và smoke engine trên dữ liệu GIẢ LẬP. Quan sát từ smoke formation (không phải PnL): top-10 M1 hay dồn vào 1 coin (vd. ETC/AXS/MERL xuất hiện ở nhiều cặp) — ghi nhận là rủi ro tập trung, KHÔNG sửa luật.

Mã (commit cùng file này): `docs/result/pairs_t1/` — `fetch.sh`, `build_1h.py`, `pairs_t1_core.py`, `pairs_t1_run.py`, `pairs_t1_report.py`, `pairs_t1_v5.py`. Mọi tham số là hằng số đầu `pairs_t1_core.py`. Sau commit này **không sửa luật/tham số**; chỉ được sửa lỗi crash/bug kế toán, mỗi lần là commit riêng ghi rõ, và báo trong RESULT.

## 1. Dữ liệu
- **Giá:** Vision UM kline 1m (Kaggle private `chuyendinh/vz-kline1m-2021` tải mới các tháng 2021-01..11 vào `~/claude_master/pairs/data/kline1m/`; 2021-12..2025-12 đọc read-only từ `~/vz_e1/raw/`). Gộp 1h (`build_1h.py`): open = open phút active đầu giờ, close = close phút active cuối giờ, qv = tổng quote volume; phút `active=False` (volume 0) bị bỏ; giờ không có phút active ⇒ NaN.
- **Funding:** `chuyendinh/vz-funding` file 2021..2025 (Vision fundingRate thật), đặt vào giờ `round((ts−H0)/1h)`.
- **Kỳ DEV:** dữ liệu từ 2021-01-04 00:00Z (bỏ 2021-01-01..03 sát kho 2020s niêm phong) đến 2025-12-31. Cửa sổ trading đầu tiên 2021-02-03 00:00Z, 256 tuần, ngày cuối 2025-12-30. **Không** dùng 2026 (HO), **không** đụng `bcast-*`/2020, **không** Binance REST, **không** đọc 242.
- **Chia kỳ:** E = ngày < 2024-01-01; C = 2024-01-01 → 2025-12-30 (theo ngày UTC trên chuỗi equity liên tục).
- **Universe POINT-IN-TIME** tại đầu mỗi tuần t: top **50** theo tổng quote volume các nến `[t−720h, t)`, trong số symbol: kết thúc `USDT`, không phải quarterly, có ≥ 95 % giờ có close trong formation, có close tại t−1, (max/min − 1) của close formation ≥ 1 % (chặn stable lạ), không nằm trong danh sách loại: `BTCDOM, DEFI, FOOTBALL, BLUEBIRD` (index) và stable `USDC, BUSD, TUSD, FDUSD, USDP, DAI, EUR, USDE, AEUR, BFUSD, XUSD, USD1, RLUSD, PYUSD, EURI, USDS` (+`USDT`). Gồm cả symbol đã delist (panel có 637 symbol, 89 symbol hết dữ liệu trước 2025-12).

## 2. Khung thời gian và thực thi (chung)
- Tuần k: formation `[t−720h, t)`, trading `[t, t+168h)`, cuốn không chồng lấn.
- Tín hiệu tại **close nến h** ⇒ khớp **open nến h+1**. Tín hiệu cuối tại close t+166; mọi vị thế pairs còn mở đóng cưỡng bức tại open t+168 (M1–M3).
- Vào lệnh cần open h+1 hợp lệ cho cả 2 chân. Thoát: open hợp lệ đầu tiên ≥ h+1 (tối đa +168h); không còn dữ liệu (delist) ⇒ close cuối cùng (cờ `delist`).
- **Vốn pairs (M1–M3):** committed capital — 10 slot, mỗi slot gross = 10 % equity đầu tuần; tối đa gross 1× khi đủ 10 cặp mở. Lượng cố định từ lúc vào (không rebalance trong lệnh). Equity cộng dồn theo tuần.
- **Chi phí** mỗi chân mỗi chiều trên notional khớp: BASE = taker 0,05 % + slip 0,02 % = **0,07 %**; ×2 = 0,14 %; maker = 0,02 % (slip 0, không mô hình rủi ro không khớp — chỉ tham khảo); gross = 0 (và không funding).
- **Funding thật cả 2 chân:** mốc f được tính nếu `entry_fill < f ≤ exit_fill`; khoản = −qty × mark × rate (long trả khi rate > 0), mark = open nến f.

## 3. Phương pháp (1 cấu hình chính mỗi phương pháp; không tune)
**M1 — Engle–Granger (Engle & Granger 1987; Gatev-style rolling).** Log close (ffill) formation 720h. Mỗi cặp có corr > 0: OLS cả 2 chiều `y = a + βx + e`, ADF trên e (không hằng số, autolag AIC, maxlag = ceil(12(n/100)^¼) = mặc định `statsmodels coint`), p-value MacKinnon (N=2); giữ chiều có ADF stat nhỏ hơn. Lọc β > 0, p < 0,05, half-life (AR(1) `Δe = c + λe₋₁`, HL = −ln2/λ, Chan 2013) ∈ [6h, 168h]. Chọn top 10 theo p (≡ ADF stat tăng dần). z = (ln y − β ln x − a)/σ_e (σ_e formation, ddof 1). Vào khi 2 ≤ |z| < 4 (z ≥ 2 ⇒ short spread), ra khi z cắt 0, stop |z| ≥ 4, time-stop khi giữ ≥ 2×HL giờ; sau stop/time-stop cặp bị khoá hết tuần; sau thoát thường được vào lại. Chân: y = ±G/(1+β), x = ∓βG/(1+β).
**M2 — Distance (Gatev, Goetzmann & Rouwenhorst 2006).** Giá chuẩn hoá (close/close đầu formation), top 10 cặp SSD nhỏ nhất (mọi cặp trong universe). σ = std chênh lệch chuẩn hoá formation. Trading: chuẩn hoá lại về close t−1; mở khi |d| > 2σ (short chân cao, long chân thấp, dollar-neutral G/2 mỗi chân), đóng khi d cắt 0, được mở lại; không stop.
**M3 — Kalman hedge động trên cặp M1 (Chan 2013 Ex. 3.3).** Trạng thái [β, α] random walk, `Vw = δ/(1−δ)·I`, **δ = 1e-4** (Chan); `Ve` = phương sai residual OLS formation của cặp (Chan dùng Ve = 0,001 cho giá ETF — không chuyển được sang log-giá; chọn ước lượng causal, ghi rõ). Khởi tạo θ = 0, P = 0 tại đầu formation, chạy qua formation làm warm-up. z = sai số dự báo / √Q. Vào |z| ≥ 2 với β dự báo > 0 (β cố định từ lúc vào), ra khi z cắt 0; không stop/time-stop; đóng cuối tuần.
**M4 — Residual stat-arb Avellaneda & Lee (2010).** Universe tuần như trên. PCA trên ma trận tương quan return 1h cửa sổ 720h (tính lại mỗi 24h, dữ liệu < mốc), **K = 3** nhân tố, eigenportfolio `Q_j,i = v_j,i/σ_i`. Mỗi giờ: hồi quy return 168h gần nhất (= 60/252 × 720h, tỉ lệ như AL) lên 3 nhân tố, X = cumsum residual, AR(1) ⇒ κ = −ln b, m, σ_eq; chỉ dùng khi 0 < b < 1 và τ = 1/κ < 84h (nửa cửa sổ, như AL κ > 252/30); s = (X_T − (m − ⟨m⟩))/σ_eq (m quy tâm như AL). Mở long s < −1,25, mở short s > 1,25, đóng long s > −0,50, đóng short s < 0,75 (AL). Danh mục: w = Σ dᵢ(eᵢ − βᵢ·Q), chuẩn hoá Σ|w| = 1 (gross 1× equity), chỉ rebalance khi tập tín hiệu đổi hoặc sang tuần mới; symbol rời universe/delist bị đóng.

**Trial ledger:** 4 phép thử (M1–M4). Control không tính là phép thử.

## 4. Kiểm vệ sinh (bắt buộc; FAIL ⇒ không kết luận)
- **V1 không look-ahead:** 5 tuần cố định k ∈ {10, 60, 120, 180, 240}: thay mọi dữ liệu ≥ t bằng rác ⇒ universe + cặp M1/M2 (+ tham số) phải giống hệt; thay dữ liệu ≥ t+169 bằng rác ⇒ lệnh + đường PnL M1/M2/M3 giống hệt (trừ lệnh khớp trễ vì gap); M4: rác sau h ⇒ s-score tại h giống hệt. Mọi slice formation/universe trong code là `[t−720, t)`.
- **V2 delist:** liệt kê symbol đã delist từng vào universe; số chân lệnh trên chúng; số lần khớp cờ `delist`/`gap`. PASS nếu có symbol delist trong universe (không survivorship).
- **V3 CONTROL ngẫu nhiên:** C1 (50 lần): M1/M3 — 10 cặp ngẫu nhiên/tuần từ cùng universe (β OLS > 0, HL kẹp vào [6,168]); M2 — 10 cặp ngẫu nhiên; cùng luật vào/ra; **hướng mỗi lệnh đảo ngẫu nhiên p = 0,5**. M4 — cùng s-score, hướng mỗi tín hiệu ngẫu nhiên. Phải có gross ≈ 0 và net ≈ −chi phí. **Luật:** |t| của gross trung bình năm hoá (qua 50 lần) < 2,5; ngược lại ⇒ **DỪNG, báo artifact**. C2 (20 lần, chỉ chẩn đoán): cặp ngẫu nhiên nhưng hướng theo luật — cho biết phần gross đến từ chọn cặp hay từ mean-reversion chung.
- **V4 đối soát:** 40 lệnh ngẫu nhiên/phương pháp M1–M3: giá vào/ra = open phút Vision active đầu giờ (đọc lại parquet thô, so bằng), funding tính lại từ parquet funding thô (rel ≤ 1e-9), PnL chân = qty×(px−pe); tổng lệnh = đường PnL cuối tuần cho mọi tuần (≤ 1e-12); M4: Σ attribution theo symbol = equity − 1 (≤ 1e-8).
- **V5 tính tay 1 tuần:** tuần đầu tiên có t ≥ 2023-06-01: dựng lại nến 1h từ parquet thô bằng pandas, universe bằng pandas, EG bằng `statsmodels.coint` (thư viện), luật lệnh bằng vòng lặp riêng, PnL/phí/funding tính trực tiếp ⇒ phải trùng engine; kèm 2 lệnh ví dụ đủ số. Thêm: ADF nhanh của engine vs `statsmodels.coint` trên 400 cặp ngẫu nhiên — 0 lần lệch quyết định p < 0,05.

## 5. Tiêu chí SỐNG tầng 1 (mỗi phương pháp, BASE, phải đạt TẤT CẢ)
- **G1** net Sharpe (ngày, √365) ≥ 1,0 ở CẢ E và C.
- **G2** maxDD (equity MTM giờ, toàn DEV) ≤ 20 %.
- **G3** ×2 chi phí: lợi nhuận tích luỹ > 0 ở CẢ E và C.
- **G4** ≥ 60 % tháng dương ở C.
- **G5** tuần tệ nhất (cửa sổ 168h) ≥ −10 %.
- **G6** bỏ top-3 cặp (M4: top-3 symbol) theo đóng góp net, phần còn lại vẫn > 0.

Báo thêm (không phải tiêu chí): gross Sharpe E|C, CAGR, maker, turnover, lệnh/tháng, phơi nhiễm TB, funding, capacity (participation chân lệnh = notional @ $1M / ADV 30 ngày trước, p50/p95, vốn để p95 = 1 %), tương quan ngày/tuần với crash-buy (P0 = `OFF_*`, X14 = `X14_*`, TB 8 seed, `~/claude_master/tsx/deep_cache/eq_dev.npz`, 2021-07 → 2025-11), PnL TB của phương pháp trong 5 % ngày tệ nhất của crash-buy, PnL trong đợt crash (cố định trước): 2021-05-12..23, 2021-12-03..05, LUNA 2022-05-07..14, 3AC 2022-06-10..19, FTX 2022-11-06..13, 2024-04-12..17, 2024-08-02..06, 2025-02-02..04, 2025-03-03..11, 2025-10-10..11. Deflated Sharpe (N = 4, chỉ báo cáo).

**Sống tầng 1 ⇒ CHỈ là ứng viên.** Tầng 2 (prereg riêng): HO 2026, stress squeeze/funding, khớp thật — để sau. Không phương pháp nào được chọn cấu hình sau khi thấy kết quả.
