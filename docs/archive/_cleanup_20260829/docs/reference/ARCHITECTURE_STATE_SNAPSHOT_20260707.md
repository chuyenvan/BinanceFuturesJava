# BẢN ĐỒ KIẾN TRÚC VÀ TRẠNG THÁI TOÀN HỆ THỐNG

> 📸 SNAPSHOT @2026-07-07 (rà lại 2026-07-11, task 146). KHÔNG phải nguồn sự thật sống — dùng
> [architecture.md](../architecture.md) + [DATA_STATE.md](../DATA_STATE.md) +
> [SESSION_START.md](../SESSION_START.md) làm chuẩn (cập nhật hơn). File này giữ lại vì có vài sơ đồ
> ASCII/bảng trình bày gọn (topology, luồng ingest, cây genome 18-gene) có thể tiện tham khảo nhanh; mọi
> số liệu bên dưới ĐÃ được đối chiếu — không có thông tin nào ở đây mà không có ở nơi khác
> (xem `ROADMAP.md`, `FINDINGS.md`, `docs/reports/trailing_stop_sweep_139.md`, `decisions/0012-*.md`).

*Nguồn sự thật hợp nhất từ toàn bộ tài liệu cấu trúc dữ liệu, vận hành và code-digest*

---

## 1. TỔNG QUAN TỐP-LÔ-GHI HẠ TẦNG (TOPOLOGY & NETWORK)

Hệ thống được vận hành phân tán trên 4 nút (nodes) chính với các ranh giới kết nối và rủi ro được cô lập chặt chẽ:

```
                  ┌──────────────────────────────────┐
                  │          KAGGLE CLOUD            │
                  │ (Train GPU, Multi-CPU HPO Worker)│
                  └────────────────┬─────────────────┘
                                   │ (Kaggle API / SSH)
                                   ▼
┌──────────────────┐  Replicate    ┌──────────────────────────────────┐
│     NODE 242     ├──────────────>│             NODE 226             │
│ (LIVE - PRIVATE) │  (on-demand)  │ (Compute, Replicate, Public Net) │
└────────┬─────────┘               └────────────────┬─────────────────┘
         │ (Chỉ kết nối nội bộ)                     │ (Private Key SSH)
         ▼                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                             ORACLE VPS                              │
│         (Compute Lõi, Backtest-lite, WFO/HPO, Aerospike Local)      │
└─────────────────────────────────────────────────────────────────────┘
```

### Chi tiết phân vai và trạng thái kết nối các Node:
1. **Node 242 (103.157.218.242 - live private)**:
   * **Vai trò**: Chạy Product tiền thật [75]. Chỉ dùng cho giao dịch live [173].
   * **Kết nối**: Bị khóa firewall rất chặt, chỉ cho phép kết nối nội bộ từ Node 226 và Oracle [75, 98]. Kaggle và Máy cá nhân không thể kết nối trực tiếp [10, 98].
   * **Trạng thái**: Chạy 2 tiến trình live liên tục (sống lâu): `BinanceDataIngestor` và `BinanceOrderTradingManager` [224].
2. **Node 226 (103.157.218.226 - open internet)**:
   * **Vai trò**: Bản replicate dữ liệu thị trường và kho chứa tính toán/backtest tầm trung [28, 294].
   * **Kết nối**: Internet mở, Kaggle và máy dev có thể truy cập [28, 294].
   * **Trạng thái**: Đang lưu trữ dữ liệu lịch sử và làm cầu nối trung gian đẩy dữ liệu từ Kaggle/Dev sang 242 [28, 98, 298].
3. **Oracle VPS (161.118.212.3 / 161.118.206.1 - compute chính)**:
   * **Vai trò**: Trung tâm xử lý CPU-bound nặng (Replay, Export, Train, WFO/HPO) [119, 173].
   * **Kết nối**: Có cấu hình MTU=1500 (tránh jumbo frame 9000 làm nghẽn mạng Oracle Cloud) [602]. Thông được sang Aerospike 242:3222 [173, 603].
   * **Trạng thái**: Chứa cơ sở dữ liệu **Aerospike Local (127.0.0.1:3222, ns=test)** làm kho lưu trữ test [173, 298].
4. **Kaggle Cloud**:
   * **Vai trò**: Huấn luyện model GPU (Funding Selector) và chạy các worker HPO song song [100, 133].
   * **Ràng buộc**: Giới hạn tối đa 5 kernel CPU chạy đồng thời cho cả tài khoản [95]. Thời gian sống tối đa 12 giờ/kernel [96]. Không có kết nối tới 242 [10, 98].

---

## 2. KIẾN TRÚC PHẦN MỀM & LUỒNG THỰC THI (SOFTWARE COMPONENTS)

Hệ thống được thiết kế theo mô hình "Một bộ não" (Java là nguồn chân lý duy nhất cho xử lý logic và trích xuất dữ liệu, Python chỉ tiêu thụ để huấn luyện) [24].

### A. Nhóm tiến trình Ingest (BinanceDataIngestor - P1)
Nhiệm vụ: Cào dữ liệu từ Binance lưu vào Aerospike 242/Oracle local [224].

```
Binance API (REST/WS)
    │
    ├─► [Rest-Price-Loop] (3s) ───────► price_realtime (Set)
    │
    ├─► [Rest-Kline-Loop] (1m) ───────► kline_1m_opt (Set) ──► [Aggregate15m4h] ──► kline_15m/4h_btceth
    │
    ├─► [Funding-Polling] (30s) ──────► funding_data (Set)
    │
    └─► [OI-Forward-Loop] (5m) ───────► open_interest / oi_ls_* / oi_taker_vol (Set)
```

* **Ticker Ingestor**: Chạy `Rest-Price-Loop` (chu kỳ 3s lấy giá thực tế) [384] và `Rest-Kline-Loop` (chu kỳ 1 phút chốt nến `kline_1m_opt`) [384]. Có cơ chế `startDataRepair` để vá nến thiếu tự động [504].
* **Funding Ingestor**: Chạy `Funding-Polling-Thread` (chu kỳ 30s) kiểm tra Premium Index, ghi nhận tỷ lệ funding vào set `funding_data` khi có kỳ settle [384, 504].
* **Open Interest Ingestor**: Chạy `OI-Forward-Loop` (chu kỳ 5 phút) gọi REST per-symbol lấy dữ liệu OI, Long/Short ratio, Taker Volume ghi nhận theo cấu trúc **chunk-tháng** [384, 550].

### B. Nhóm tiến trình giao dịch live (BinanceOrderTradingManager - P2)
Nhiệm vụ: Lắng nghe tín hiệu, tính toán vị thế và khớp lệnh live [223].

```
[DetectEntry] (Loop 100ms, Gate 1m) 
    │
    ├──► Đọc kline_1m_opt & warm-up History (2000 phút)
    ├──► Gọi OnnxInferenceManager (Inference ONNX)
    │        ├──► Model 15M (Reg) ──► predReturn15M ──┐
    │        └──► Model DD4H (Reg) ──► predRisk4H     ──┼─► [AIRejectFilter] (Gate)
    │                                                   │
    ├──► Đọc từ Aerospike ──► pred[0] (P-Fail)        ──┘
    │
    └──► (Nếu lọt Gate) ──► Gửi Order qua Redis Queue
                                │
                                ▼
                       [BinanceOrderTradingManager]
                                │
                                ├──► ThreadManagerOrder (Settle, Trailing TP/SL)
                                └──► BudgetManager (Sizing & Margin-halt 0.50)
```

* **Bộ lọc lối vào (AIRejectFilter)**: Áp dụng cơ chế **Phanh Động (Brake Dynamic)** [61]:
  * *Nhánh Early (Chặn sớm)*: Từ chối ngay nếu Momentum 15M yếu và P-Fail của Funding Model vượt ngưỡng tối đa [61]. Gánh **96.5% tổng số reject** thực tế [62].
  * *Nhánh evaluate*: Kiểm tra điều kiện ngặt nghèo của `predRisk4H` (Risk) và `predReturn15M` (MOM15) [61].
* **Quản lý vốn & Rủi ro (BudgetManager & DcaProcessor)**:
  * *Circuit Breaker*: Bật **Margin Halt ở mức 0.50** (Ngăn mở vị thế mới khi Margin/Vốn ≥ 0.50 để bảo vệ tài khoản khỏi sập hàng loạt) [166].
  * *Dca Processor*: Tính toán trung bình giá khi nến sụt mạnh dựa trên **DCA margin ladder** cứng chưa gene-hóa [203, 497].

---

## 3. BỐN TẦNG DỮ LIỆU VÀ TRẠNG THÁI THỰC TẾ (DATA LAYERS & STATES)

*Trạng thái đo trực tiếp và đối soát đến ngày 2026-07-07* [33]:

### Tầng 1: Ticker File (Ổ đĩa Oracle local)
* **Trạng thái**: ✅ **ĐẦY ĐỦ** [34].
* **Chi tiết**: Có 1886 file `.bin.gz` (từ 01/01/2021 đến 01/03/2026), tổng dung lượng 11GB [34].
* **Chất lượng**: Đã được làm sạch hoàn hảo, bao gồm cả dữ liệu sống/chết của 38 coin delist (LUNA sập về $0.008 đúng mốc, ANC close $0.055, FTT đủ) [34, 36]. Không còn ghost USDC [40].

### Tầng 2: Ticker Aerospike (Oracle ns=test, set=kline_1m_opt)
* **Trạng thái**: ✅ **HOÀN TẤT REGEN SẠCH** [34, 38].
* **Chi tiết**: Chứa 2,703,650 record phút [34].
* **Sự cố & Khắc phục**: Phát hiện bug ghost *USDCUSDT và đuôi đơn 10 coin delist (FTT kẹt giá phẳng $1.59 kéo dài sau delist) [40]. Đã chạy `CleanTickerGhostAndTail` xóa sạch **7400 ghost entry** và **12,089,576 đuôi đơn rác** trước khi đồng bộ [40].

### Tầng 3: Metadata & Feature (Oracle ns=test)
* **symbol_lifecycle**: ✅ **REBUILD SAU CLEAN** [34]. Quản lý 698 symbols gồm 636 LIVE và 62 DEAD [174]. LUNA/ANC ghi nhận DEAD đúng ngày [174].
* **market_data_object**: ✅ **REGEN SAU CLEAN** [34]. Tính toán lại từ tệp ticker sạch, loại bỏ hiện tượng méo chỉ số rổ trong quý 1-2 năm 2026 [34, 40].
* **OI Feature**: ✅ **DÙNG LẠI** [34]. Tệp `oi_percoin_20210101_to_20260624.bin.gz` (3.1GB, 138 triệu records) đã được validate có đầy đủ dữ liệu sập của LUNA, ANC, FTT, AUDIO [34, 39].
* **Gate Feature (ff_*.bin)**: ❌ **CHỈ CÓ 1 THÁNG CŨ (ff_202401.bin)** [34]. Cần chạy lại `RunFullDataCollection` để xuất toàn bộ từ market_data_object sạch mới [34, 38].
* **Set funding_data**: ⏳ **RỖNG** [41]. Đang phải crawl lại từ Binance bằng `HistoricalFundingCrawlerLocal` [41].

---

## 4. QUY TRÌNH WALK-FORWARD (WFO) & BẢN ĐỒ GENOME CHỐT

### Kiến trúc WFO 2 lớp:
1. **WFO Loại 1 (Strategy WFO - WFORunner)**:
   * **Bản chất**: Model ML giữ nguyên (bất biến), chỉ tối ưu hóa các tham số chiến lược (18 gene) [136, 422].
   * **Dữ liệu**: Tiêu thụ `WfoDataset` tĩnh chứa 3 file binary offline (`market.bin`, `pred.bin`, `funding.bin`) để loại bỏ hoàn toàn nghẽn mạng Aerospike [214, 408].
2. **WFO Loại 2 (Model WFO - WFOGateRunner)**:
   * **Bản chất**: Re-train model ML qua từng fold (expanding window), sinh predict mới hoàn toàn trên OOS để chống rò rỉ thông tin [405, 422].

### Bản đồ Genome 18 Gene chốt (ADR-0012)
Hệ thống áp dụng cơ chế **OFF CỨNG** (vô hiệu hóa hoàn toàn nhánh logic trong code engine) cho 9 gene cụm C phẳng nhiễu, chỉ giữ lại **18 gene tinh nhuệ** trong vòng tối ưu [375, 376, 377]:

```
   ┌────────────────────────────────────────────────────────┐
   │                     GENOME HPO (18)                    │
   └───────────────────────────┬────────────────────────────┘
                               │
       ┌───────────────────────┼────────────────────────┐
       ▼                       ▼                        ▼
[ENTRY FILTER (5)]       [DCA NHỒI (4)]          [TRAILING / BUDGET (9)]
- MIN_MOMENTUM_15M       - DCA_LOSS_BIG_DOWN     - RATE_PROFIT_STOP_MARKET
- PREDICT_MAX_THRES      - DCA_TIME_BIG_DOWN     - TS_MAX_GAP
- AI_DYNAMIC_MUL         - DCA_TIME_BIG_UP       - TS_DYNAMIC_K
- HARD_RISK_LIMIT_4H     - DCA_LOSS_BIG_UP (OFF) - TS_MAX_GAP_WEAK
- AI_DYNAMIC_MIN                                 - TS_PROFIT_MULTIPLIER
                                                 - TS_WEAK_MOM_THRES
                                                 - BUDGET_MARGIN_RATIO_1
                                                 - BUDGET_MARGIN_RATIO_2
                                                 - BUDGET_DIVIDER_2
```

* **9 Gene cụm C (ĐÃ OFF CỨNG)**: `AI_DYNAMIC_MAX`, `MS_UP_BIG_THRES`, `DCA_LOSS_BIG_UP`, `BUDGET_DIVIDER_1`, `MS_DOWN_SMALL_AVG_OR_15M`, `MS_UP_SMALL_THRES`, và 3 gene `PREDICT_SYMBOL_RATE_*` [376].

---

## 5. CHẨN ĐOÁN & THỰC TRẠNG HIỆU NĂNG GIAO DỊCH

Hệ thống đã trải qua các cuộc kiểm tra và thực nghiệm khắt khe để phát hiện lỗi ẩn:

* **PAYOFF > 1 nhưng hệ thống vẫn lỗ qua chu kỳ**: Do cơ chế DCA martingale không trần cũ nhồi vô hạn vào các coin rác sập vĩnh viễn (LUNA, FTT) [55, 56].
* **Lá chắn thực sự**: Là **Margin-halt 0.50** (Cắt giảm max Drawdown từ -58.6% về -29.5% mà chỉ đánh đổi -27% PnL) [347]. Các loại DCA-cap per-cluster đều vô dụng trên danh mục thực tế [346].
* **Thực tế Sizing**: Tăng kích cỡ lệnh (sizing) không phải là đòn bẩy để đạt 20%/năm [706]. Khi nâng size gấp 5, CAGR chỉ tăng từ 3.2% lên 4.8% và số quý không trade vẫn cao [706]. Hệ thống bị **giới hạn bởi tần suất cơ hội vào lệnh (timing quá chặt)**, không phải do size [706].
* **Điểm ngọt Trailing-Stop**: Phát hiện giá trị `RATE_PROFIT_STOP_MARKET = 0.01032` cũ làm trailing-stop kích hoạt quá sớm khiến bot bị quét stop non, chốt cụt đuôi lãi phải (Holding median chỉ 7 phút) [722]. Khi nâng lên **0.03032**, PnL toàn kỳ tăng 2.4 lần (17.8k -> 34.4k) và Calmar tăng vọt lên 3.06 trong khi maxDD giữ nguyên [722].
* **Hướng đi tiếp theo**: Áp dụng bộ lọc mới **0.01 | 72H | pump** (label lỏng 1%, nhìn xa 72 giờ và thêm nhóm feature crowdedness/thanh khoản) để mở rộng phễu cơ hội an toàn cho bot giao dịch đều đặn [707, 708].
