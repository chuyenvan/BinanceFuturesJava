# PRE-REG — FEE0_RESCORE: chấm lại tín hiệu "chết vì phí" dưới biểu phí Binance USDⓈ-M USDC-margined (MASTER 2026-10-24)

Commit TRƯỚC khi tính bất kỳ PnL nào (kể cả V1). Bước 0 (phí, listing, so giá, spread) đã chạy — chỉ dữ liệu, không PnL.
Agent: fee0. Code `research/fee0/`. Dữ liệu trung gian `~/claude_master/fee0_wk/`.

## 1. Mục tiêu
Có tín hiệu nào từng chết vì phí (SCREEN_WIDE tầng 1 a9fa0f46; E1 Q4 84aa5f22) trở thành hệ "dải đều" nhỏ chạy trên USDC-M (maker 0 %) không.

## 2. Bước 0 — kết quả (trước prereg, không PnL)

**(a) Biểu phí USDC-M.**
- Binance (thông báo 2023-12-28): USDC-M BTC/ETH/BNB/SOL/XRP mở 2024-01-03 12:30 UTC, giảm 10 % so với phí USDT-M.
- Binance (thông báo 2024-03-22, "Limited-Time Trading Fee Discount for USDC-Margined Perpetual Contracts (2024-04-03)"): Regular & VIP1–9 maker **0 %**, taker 0,017 %; 2024-04-03 → 2024-07-03 12:30 UTC; "Standard trading fees apply after the promotion ends".
- Binance Futures X (status 1899688310416765424, 2025-03): "ZERO maker fees and 20 % taker discount on USDC-M contracts… Limited time only".
- Coinlive 2025-05-27 (trích thông báo chính thức Binance): Regular maker 0,0000 % / taker 0,0400 % (BNB 0,0360 %), hết hạn 2025-09-03 06:00 UTC.
- Trang FAQ Binance 360033544231 (cập nhật 2026-05-01) liên kết tới "Binance Updates Limited-Time Trading Fee Discount and Liquidity Provider Program for USDC-Margined Perpetual Contracts (2025-09-11)" — **KHÔNG đọc được nội dung**, không biết ngày hết hạn.
- Bitsgap (bên thứ ba, 2026-09-10): USDC-M 0,00 % / 0,04 %.
- ⇒ **CHƯA XÁC MINH chính thức mức hiện hành và thời hạn.** Ưu đãi "limited-time" đã gia hạn nhiều lần từ 2024-04 (mức taker thay đổi). Prereg dùng maker 0 / taker 0,04 % theo thiết kế MASTER như giả định phản thực tế cho cả lịch sử.

**(b) Symbol USDC-M (Vision S3 listing `data/futures/um/daily/klines/`, file `fee0_wk/usdc_listing.json`).** 40 symbol, trong đó MATICUSDC đã huỷ niêm yết 2024-09-11. Bar 1m đầu tiên trên Vision: BTCUSDC 2024-01-04 12:31, ETHUSDC 2024-01-04 12:36. BNB/SOL/XRP 2024-01-04; DOGE 01-18; SUI 02-08; LINK 02-16; … các symbol sau tới DATAIP 2026-07-03. **Không có USDC-M nào trước 2024-01** ⇒ toàn bộ kỳ E phải dùng proxy USDT-M.

**(c) USDC-M vs USDT-M (2024-01-04 → 2026-09-30, `step0_c.json`).**

| | coverage 1m | corr 1m | corr 15m | corr 1h | TE 1h (bps) | |dev| p50 / p99 (bps) | dev TB ngày min/max (bps) |
|---|---|---|---|---|---|---|---|
| BTC | 100 % | 0,9915 | 0,9990 | 0,99955 | 1,51 | 3,4 / 14,4 | −17,1 / +18,6 |
| ETH | 100 % | 0,9939 | 0,9993 | 0,99975 | 1,55 | 3,3 / 13,4 | −16,5 / +18,5 |

Lệch mức là tỉ giá USDC/USDT (±18 bps); lệch return 1h ~1,5 bps. ⇒ **Quyết định:** dùng giá USDT-M làm proxy cho mọi thời điểm trước bar USDC-M đầu tiên của symbol; từ đó dùng giá USDC-M thật.

**(d) Spread / độ sâu.** Phương pháp: Vision UM `bookTicker` (chỉ có 2023-05-16 → 2024-03-30) cho các ngày 2024-02-14, 2024-03-13, 2024-03-27; lấy quote cuối mỗi giây, spread tương đối (ask−bid)/mid; nửa spread hs = 0,5 × trung bình (theo ngày) của trung bình theo giây (`half_spread.json`, script `f0_halfspread.py`).
- hs: BTCUSDC 0,014 bps; ETHUSDC 0,024 bps (đều ~1 tick, ngang BTCUSDT 0,009 / ETHUSDT 0,016). Alt USDC: SOL 0,52, BNB 0,70, XRP 0,90, DOGE 0,94, LINK 1,48, ORDI 2,01, SUI 2,23, AVAX 2,28, 1000PEPE 2,58, WLD 2,66 bps.
- Symbol không đo được (niêm yết sau 2024-03 hoặc thiếu file): hs = ALT_DEFAULT = max alt đo được = 2,66 bps (bảo thủ).
- Độ sâu `bookDepth` ±1 % (notional trung vị, USD): BTCUSDC 46–52 tr vs BTCUSDT 131–174 tr; ETHUSDC 23–27 tr vs 64–80 tr; SOLUSDC 3,8–5,1 tr vs 15–20 tr (ngày 2026-03-11, 2026-09-16; ngày cũ hơn lỗi định dạng cột — không dùng). Đủ sâu cho quy mô retail.
- Giới hạn: spread đo ở 2024Q1 (USDC-M mới mở), áp cho cả kỳ.

## 3. Tín hiệu (định nghĩa/tham số GIỮ NGUYÊN)
Giá tại T = close của nến 1m có open_time = T − 1′ (như sw_run.py). Thời gian ET như sw_run.py (cùng phép cộng Timedelta).
- **S1** (BTC, ETH): long 21:00 → 23:00 UTC mỗi ngày (2021-01-02 → 2026-09-30). PnL ghi ngày thoát.
- **S7** (BTC, ETH): long 16:00 ET thứ Sáu → 10:00 ET thứ Hai. PnL ghi ngày thoát.
- **S8** (BTC, ETH): nến :00 của giờ 00/04/08/12/16/20 UTC, imb = (2·taker_buy − vol)/vol tính trên **USDT-M** (như gốc); bỏ imb = 0/NaN; vào tại close nến tín hiệu, giữ 4h; hướng = dấu E gốc × sign(imb), dấu E gốc = −1 cho cả BTC và ETH (screen_result.json). PnL ghi ngày vào (như gốc).
- **Q4** (E1 H-F): biến thể **M15_12h_imb_dev15** — chọn HẬU KIỂM vì |spread quintile| lớn nhất có CI95 không chứa 0 trong §6c.4 (−2,6 bps); chỉ mô tả, đây là lựa chọn sau khi thấy kết quả. Sự kiện: phút :00/:15/:30/:45, quote_volume(nến) ≥ 50 000, imb = 2·taker_buy_quote/quote_volume − 1, imb_dev15 = imb − TB imb 15 dòng trước (như e1_q4_imbalance.py). IC âm ⇒ long quintile 1 (imb_dev15 thấp nhất), short quintile 5; quintile = ceil(rank_pct × 5) mỗi mốc, chỉ mốc có cả q1 và q5. Giữ 12h: vào close nến mốc, ra close nến mở tại ts + 12h (bỏ nếu thiếu). Danh mục: 48 cohort chồng nhau, mỗi cohort 1/48 vốn, nửa long nửa short, chia đều trong quintile; chân không khớp ⇒ vốn chân đó đứng yên (0). PnL ghi ngày thoát.
  - Universe **C**: symbol USDC-M PIT (có bar USDC-M), tín hiệu VÀ thực thi bằng kline USDC-M của chính symbol; 2024-01-01 → 2026-09-30.
  - Universe **E**: không có USDC-M ⇒ proxy = 5 symbol mở đầu USDC-M (BTC, ETH, BNB, SOL, XRP) trên USDT-M, `~/vz_e1/raw` (có cột `active`), **2022-01-01 → 2023-12-31** (raw bắt đầu 2021-12).
- Thực thi S1/S7/S8: giá USDT-M trước bar USDC-M đầu tiên (2024-01-04 12:31 BTC / 12:36 ETH), giá USDC-M sau đó (high/low/close của USDC-M dùng cho luật khớp).

## 4. Mô hình chi phí (chốt)
Mọi mô hình trừ funding thật: lệnh trả −side × Σ rate các settlement trong (t_vào, t_ra]; rate USDC-M (Vision fundingRate) từ bar USDC-M đầu tiên, trước đó rate USDT-M (lake `1016/carry/fund`) làm proxy. (Gốc chỉ tính funding cho S6/S7; ở đây tính cho mọi tín hiệu theo thiết kế MASTER — S1 không chạm settlement.)
- **C_M0** (lạc quan, chỉ báo cáo): maker 0 hai chân, khớp chắc tại giá tín hiệu và giá thoát.
- **C_M1 (chính)**: vào bằng limit maker 0 % tại giá tín hiệu P0; long khớp nếu ∃ nến mở trong [T, T + W) có low < P0 (xuyên mức, strict); short nếu high > P0; W = 15′; không khớp ⇒ bỏ lệnh (return 0). Khớp: giá vào = P0, phạt adverse selection 2 bps; thoát taker 0,04 % + hs tại giá thoát theo lịch. r = side·(P_ra/P0 − 1) − 0,0002 − (0,0004 + hs) − funding.
- **C_M2**: taker 0,04 % + hs cả hai chân, khớp chắc.
- Độ nhạy W ∈ {5′, 30′} (C_M1).

## 5. Kỳ và thước đo
E = 2021-01-01 → 2023-12-31 (Q4: 2022–2023); C = 2024-01-01 → 2026-09-30. Không có holdout mới. Sharpe = mean/sd PnL ngày (mọi ngày lịch, ngày không lệnh = 0) × √365; maxDD trên (1+r).cumprod() trong từng kỳ (như sw_run.stats). Mỗi lệnh dùng toàn bộ vốn (S), Q4 như §3.

## 6. Tiêu chí (từng tín hiệu: S1_BTC, S1_ETH, S7_BTC, S7_ETH, S8_BTC, S8_ETH, Q4 — 7 phép thử chính)
- G1: Sharpe C_M1 ≥ 1,0 ở CẢ E và C.
- G2: Sharpe C_M2 ≥ 0,5 ở cả E và C.
- G3: maxDD C_M1 ≥ −25 % ở cả E và C.
- G4: corr PnL ngày C_M1 với X14 (seed trung vị = hạng 4/8 theo Sharpe MTM 2022-05-01 → 2025-12-31 như `research/trend_t1/t1_x14.py`; = s2024) trên các ngày chồng lấn ≤ 0,3.
- G5: tỉ lệ khớp maker C_M1 (W = 15′) ≥ 60 % ở cả E và C, VÀ dấu Sharpe C_M1 ở E và C không đổi khi W = 5′, 30′.
- G6: DSR ≥ 0,5 — công thức như `research/mom/t2_mom.py dsr()` trên PnL ngày C_M1 toàn kỳ (E ∪ C), N = 89 + 7 = 96 (độ nhạy N = 110 chỉ báo).
- GO: G1–G6. ỨNG VIÊN: Sharpe C_M1 ở C ≥ 1,0, ở E trong [0,7; 1,0) và G2–G6 đạt. Còn lại NO-GO.
- Danh mục ghép (nếu ≥ 2 tín hiệu GO/ỨNG VIÊN): trung bình đều PnL ngày C_M1, chỉ mô tả.
- Rủi ro đa kiểm định: ledger 89 test cũ + 7 test này = 96, cùng dữ liệu E/C đã nhìn ⇒ mọi GO vẫn cần forward.

## 7. Validation
- V1: tái lập tầng 1 (chỉ USDT-M, taker 0,05 % và maker 0,02 % mỗi chiều, funding chỉ S7): Sharpe S1/S7/S8 BTC & ETH khớp screen_result.json / sw_diag.log (|Δ| ≤ 0,01) TRƯỚC khi chạy chi phí mới.
- V2: ts int64 ms; assert lưới 1m exec đủ phút (số bar = kỳ vọng), ts unique, ts % 60000 = 0; Q4 moc table ts unique.
- V3: tái lập ĐỘC LẬP PnL ngày S7_BTC C_M1 (script tối giản không import pipeline, đọc zip/parquet trực tiếp) ⇒ max |Δ| < 1e-9.
- V4: kiểm tay 5 lệnh maker (S1/S7 BTC kỳ C, chọn ngẫu nhiên seed 20261024): in nến cửa sổ, P0, quyết định khớp/không theo luật xuyên mức.
- V5: look-ahead — S8/Q4: tính lại tín hiệu trên dữ liệu cắt tại t cho mẫu ngẫu nhiên mốc, phải trùng; S1/S7 chỉ theo đồng hồ. Kiểm thêm luật khớp chỉ dùng nến mở ≥ T.

## 8. Lệch thiết kế
1. Q4 E chỉ 2022–2023 (raw bắt đầu 2021-12) và universe E là 5 symbol proxy (không có USDC-M trước 2024) — PIT không khả thi; chọn 5 symbol mở đầu USDC-M là thông tin tương lai nhẹ (đều là top vốn hoá 2021–2023).
2. Q4 C: tín hiệu tính trên kline USDC-M của chính symbol (USDT-M 2026 không có trên Oracle); S8 giữ tín hiệu USDT-M như gốc.
3. hs đo 2024Q1 áp cả kỳ; alt không đo dùng ALT_DEFAULT.
4. Funding tính cho mọi tín hiệu (gốc chỉ S6/S7).
5. ETH được chấm như phép thử riêng (gốc có ETH cho họ S).
