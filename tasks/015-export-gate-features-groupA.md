# TASK-015: Export feature gate NHÓM A (sẵn-có) + validate RIÊNG từng group

- **status:** REVIEW — code DONE (`ExportGateFeaturesGroupA`); RUN+validate trên 226 (job đọc nặng — chưa chạy từ phiên dev). CHẠY sau khi 012 PASS (đã PASS).
- **owner:** CCD-024 · **updated:** 2026-06-14
- **Spec:** `docs/H1_GATE_SPEC.md` §2.1 + §2.4. Nhóm A = feature ĐÃ CÓ trong `MarketFeatures`/`ComprehensiveMarketFeatureExtractor` — chỉ export + validate, **KHÔNG code feature mới** (candidate nhóm B để task sau).

## Mục tiêu
Export feature nhóm A ra cột, **align `t` với `gate_return.csv`** (sample 15m, 2021→nay), **mỗi group validate RIÊNG** trước khi ghép (§2.5 sau).

## Phạm vi nhóm A (H1_GATE_SPEC §2.1) — đúng các feature này, không hơn
- **momentum BTC:** momentum15M, 1H, 4H, 24H  (BỎ 1M/5M)
- **volatility:** volatility15M, 1H, 24H, volatilityTermStructure, volumeSpike, volatilityRegime (**encode** ordinal/one-hot + lưu mapping)
- **breadth:** advanceDeclineRatio, percentAboveMA20, volumeRatioUpDown, marketBreadthStrength, btcDominance
- **funding:** fundingRateRaw (**đổi tên cột → `basketFundingAvg`**, nghĩa đúng theo ADR-0011 — KHÔNG đổi giá trị), fundingRateAvg24H, fundingRateTrend
- **basket:** basketVolSpike
- ⛔ KHÔNG export: GROUP 5 TIME, momentum1M/5M, label cũ (futureReturn15M/maxDrawdownNext4H).

## Yêu cầu
- Tái dùng `ComprehensiveMarketFeatureExtractor` (stateful — warmup đủ trước mốc đầu). Tính tại mỗi `t` (15m) **khớp đúng mốc `gate_return.csv`**. Look-ahead: extractor chỉ chạm `[.., t]`.
- Format: chốt khớp H2 loader (1 file nhiều cột + key `t`, hoặc file/group — ghi rõ). Join được với `gate_return.csv` theo `t`.

## Validate RIÊNG mỗi group (H1_GATE_SPEC §2.4) — PASS mới sang group kế
- (a) **range/phân bố:** percentile mỗi feature; phát hiện clip/giá trị bất thường.
- (b) **NaN/Inf→0:** đếm; phân biệt 0-thật vs lỗi (feature nào hay 0 → soi).
- (c) **recompute ~5 mốc** bằng đường khác → khớp.
- (d) **look-ahead:** xác nhận extractor không chạm dữ liệu > t.
- (e) **align:** mỗi `t` khớp `gate_return.csv` (cùng tập mốc, cùng số dòng sau khi bỏ gap).

## An toàn / tài nguyên
- Đọc-only market data **226**; ghi file `outputs/`. Chạy **trên 226** (đọc Aerospike nặng) — **KHÔNG chạy đồng thời** với 012/builder-010/013-backfill trên 226 (xem CLAUDE.md "Tài nguyên"). SLF4J.
- ⚠️ **RỦI RO SURVIVORSHIP QUA FEATURE (bắt buộc kiểm):** breadth/basket tính trên universe — phải GỒM 30 coin die đã backfill (data đầy đủ). Kiểm `ComprehensiveMarketFeatureExtractor` có loại coin qua `Constants.diedSymbol` không. Nếu CÓ → 226 lúc export phải dùng config **DIED HẸP (BTCDOM-only)**, TUYỆT ĐỐI không ăn config prod 129 (sẽ loại 30 core vừa backfill → survivorship hỏng, P1 vô nghĩa). Báo số coin tham gia breadth mỗi năm để xác nhận đủ. (Lifecycle 010 giải triệt để sau; trong lúc chờ phải đảm bảo thủ công.)

## Acceptance
- [~] File feature nhóm A, align `t` với `gate_return.csv`, 2021→nay. — **CODE XONG**, chưa chạy (job nặng 226; data 226 hiện dừng ~2026-06-07 per scan 023).
- [~] Mỗi group validate (a–e) PASS, kèm số liệu. — **CODE XONG** (chạy cùng tool), chưa có số (chưa chạy 226).
- [x] volatilityRegime encode + mapping lưu; cột fundingRateRaw → basketFundingAvg. — ordinal LOW=0/NORMAL=1/HIGH=2 + sidecar `gate_features_groupA_volatilityRegime_mapping.txt`; cột đổi tên `basketFundingAvg` (giá trị = fundingRateRaw, KHÔNG đổi).
- [x] KHÔNG có TIME / momentum1M-5M / label-cũ trong output. — chỉ 19 feature §2.1; loại rsi14/distMA20/momentumAcceleration/trendStrengthETH/trendConsistency/volatility1M/TIME/label.

## (Code điền) — `ExportGateFeaturesGroupA.java` (commit pending) · compile PASS javac11
- **Format + #cột + align gate_return:** 1 file `outputs/gate_features_groupA.csv`, key `tEpochMs` (+`tDate`), **19 feature** (4 momentum + 6 volatility[gồm volatilityRegime ordinal] + 5 breadth + 3 funding + 1 basket). Sample 15m, warmup 48h, emit từ 2021-01-01 07:00 GMT+7. Extractor `ComprehensiveMarketFeatureExtractor` stateful, feed CHRONOLOGICAL mỗi phút (idempotent với `extractAllFeatures` do `processKline` overwrite cùng startTime). `momentum15M` lấy từ `MarketDataObject.rateDown15MAvg` (đúng nguồn extractor — tên §2.1 là "BTC" nhưng giá trị giữ nguyên feature sẵn-có). Join 025 theo `t`.
- **Validate từng group (range/NaN/recompute/look-ahead/align):** lớp `Validate` chạy sau export: (a) min/p1/p50/p99/max mỗi feature; (b) đếm NaN/Inf→0 + 0-count mỗi feature (phân biệt 0-thật vs lỗi); (c) recompute độc lập momentum1H/4H/24H BTC (đọc close trực tiếp t & t−N, đường khác ring); (d) look-ahead inherent (feed ≤t, ring/getReturn + funding ≤t); (e) **align**: đọc `gate_return.csv`, kiểm mọi t của gate có trong feature (feature ⊇ gate vì gate cắt t+24h); (e') **survivorship**: #coin breadth (getTopCoin) theo năm.
- **Encode volatilityRegime (mapping):** ordinal LOW=0, NORMAL=1, HIGH=2 (theo độ biến động tăng); mapping ghi `outputs/gate_features_groupA_volatilityRegime_mapping.txt` + log.
- **✅ SURVIVORSHIP (đã kiểm code — quan trọng):** path KHÔNG lọc `Constants.diedSymbol` ở read (`readDataFromAerospike1M` đọc mọi ticker proto) / `HistoryManager.updateHistory` (feed mọi symbol) / `CoinRankManager.updateRanking` (xếp từ `getAllSymbolsShort`) / `extractBreadthFeatures` (dùng getTopCoin xếp theo VOLUME). ⇒ điều kiện "phải dùng DIED hẹp" KHÔNG kích hoạt; coin die tham gia tự nhiên miễn data 1m có trên 226 (TASK-005 backfill 30 core). Validate (e') xác nhận bằng #coin/năm. **Vẫn nên chạy với config backtest/train (không cần ép DIED hẹp), nhưng phải đảm bảo set ticker 226 có 30 core.**
- **⛔ CHẶN/lưu ý chạy:** job đọc nặng → chạy TRÊN 226, KHÔNG đồng thời 012/010-builder/013 (ghi PID/.run theo luật dọn-job). Scan 023 báo **kline@226 dừng ~2026-06-07** → output tới mốc đó (không phải lỗi). Cần `gate_return.csv` (012) ở `outputs/` để validate align.
