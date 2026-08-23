# QUYẾT ĐỊNH 2026-08-08 — horizon, universe cổ phiếu token hoá, predRisk4H

> Chốt dựa trên bảng trạng thái đo lúc 09:04 ICT hôm nay (bridge rớt sau đó, số liệu chưa refresh).
> Liên quan: `claude/wfo_data_status.md`, `claude/wfo_label_merge_bug.md`, `claude/wfo_data_flow_architecture.md`, `claude/ticker_2026_h1_format_and_build.md`.

## 1. Ba quyết định

**a) Horizon label: giữ cả 4 (4h/12h/24h/72h), không rút còn 1.**
Không cần sửa `gen_funding_wf_predictions.py`. Việc còn lại: export lại label 1m toàn bộ theo
code đã vá lỗi merge (xem `wfo_label_merge_bug.md` mục 6) — CHƯA CHẠY.

**b) Universe 2026: đưa cổ phiếu/hàng hoá token hoá vào, không loại. Rủi ro tính sau.**
`AAPLUSDT, NVDAUSDT, TSLAUSDT, MSFTUSDT, SPYUSDT, QQQUSDT, XAGUSDT, XPTUSDT, NATGASUSDT,
COPPERUSDT, HK0700USDT`… giữ trong universe 806 symbol (hành vi mặc định hiện tại, không cần sửa
`BuildTickerDaily.java`). Lý do Uni chốt: bản chất giá các asset này vẫn chạy theo động lực
MM/thị trường chung, chấp nhận rủi ro model chưa từng thấy asset class này — KHÔNG cần lọc riêng
nữa, đã quyết dứt điểm.

**c) `predRisk4H`: đã xoá khỏi `AIRejectFilter` — LÀM XONG 2026-08-08.**

## 2. Việc đã làm cho (c) — chi tiết để tránh phải re-discover

Grep toàn repo: `predRisk4H` xuất hiện ở **17 file** (44 chỗ). Trong đó **chỉ 1 file** là nơi ra
quyết định filter lệnh sống — `AIRejectFilter.java` (gọi từ `DetectEntrySignal2TradeNormal.java`,
đúng tiến trình trading live). 16 file còn lại dùng `predRisk4H` cho mục đích KHÁC hẳn, KHÔNG đụng:

- `AiPredictionData.java` — chỉ là field chứa giá trị, nhiều nơi khác cần đọc.
- `WFOGateRunner.java` — carry-forward `predRisk4H` từ set gate CŨ (`ai_pred_market_full_basket_v2`)
  làm cột thứ 2 trong `wfo_gate_pred.csv` (comment gốc: "predRisk4H giữ từ set cũ, isolate biến =
  predReturn15M"). Đây là một phần thiết kế của luồng gate WFO đang xây, xoá sẽ vỡ pipeline đang
  chạy — KHÔNG phải rác.
- Các file HPO/genome (`RunHpoMaster_Distributed.java`, `StrategyWfoTask.java`, `WFORunner.java`,
  `SensitivityTool.java`, `RunWorkerKaggle.java`) — `Configs.HARD_RISK_LIMIT_4H` là **1 gene đang
  được tối ưu** trong chuỗi DoubleChromosome theo INDEX cố định. Xoá gene này sẽ lệch index của
  mọi gene phía sau ở hàng chục chỗ hard-code theo vị trí — đây là việc lớn, KHÔNG nằm trong yêu
  cầu "xoá khỏi AIRejectFilter", không tự ý làm.
- Các file validation/backtest còn lại (`ValidateOldPredict3Targets.java`,
  `ProductionVsBacktestDataComparator.java`, `GoldenBacktest.java`, …) — công cụ đối chiếu lịch sử,
  không ảnh hưởng quyết định live tương lai.

**Thay đổi thật trong `AIRejectFilter.java`:**
- Bỏ hẳn nhánh RISK/DD4H trong `evaluate()` — không còn đọc `predRisk4H` ở bất kỳ đường nào
  (`checkSignal`, `checkSignalDynamic`).
- Xoá field đếm `riskReject` (dead sau khi bỏ nhánh) — và sửa luôn `GatePassCountProbe.java`
  (nơi DUY NHẤT đọc `AIRejectFilter.riskReject`) để bỏ cột `riskRej` khỏi log, tránh vỡ compile.
- Giữ nguyên signature `setConfig(float risk, float min15m)` để không vỡ 3 caller
  (`BackTestEngineCombined`, `BackTestEngineMarketThresholds`, `BenchmarkSpeedTest`) —
  `risk` giờ chỉ ghi vào `Configs.HARD_RISK_LIMIT_4H` cho log/HPO đọc, không còn ảnh hưởng PASS/REJECT.
- Đã grep xác nhận không còn nơi nào parse text `reason` (`"DANGER: MaxDD"`) để so khớp chuỗi —
  chỉ có 2 chỗ log thẳng ở `DetectEntrySignal2TradeNormal.java`, an toàn.

**CHƯA làm / cần Uni tự kiểm trước khi deploy:**
- Session này không có `javac`/`mvn` (chỉ có JRE, không có JDK) nên KHÔNG build thử được — cần
  Uni chạy build thật trên máy có Maven trước khi deploy (theo `docs/rules/build-env.md`).
- Vẫn cần deploy 2 tiến trình live (`websocket/BinanceDataIngestor` +
  `trading/BinanceOrderTradingManager`) theo `docs/CORE.md` — người tay, không tự động.
- Hệ quả hành vi: từ sau deploy, filter sống KHÔNG BAO GIỜ reject vì risk4H nữa (chỉ còn MOM15) —
  đúng ý Uni ("bỏ hẳn"), nhưng ghi lại rõ ở đây để nếu sau này thấy tần suất lệnh xấu tăng thì biết
  ngay nguyên nhân là do đã bỏ RISK gate, không phải bug mới.
