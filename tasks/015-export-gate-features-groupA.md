# TASK-015: Export feature gate NHÓM A (sẵn-có) + validate RIÊNG từng group

- **status:** TODO (H1 — feature gate bước 1, nhóm sẵn-có). CHẠY sau khi 012 PASS (đã PASS).
- **owner:** _(điền khi claim — đồng bộ `docs/AGENTS.md`)_ · **updated:** _(điền)_
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
- [ ] File feature nhóm A, align `t` với `gate_return.csv`, 2021→nay.
- [ ] Mỗi group validate (a–e) PASS, kèm số liệu.
- [ ] volatilityRegime encode + mapping lưu; cột fundingRateRaw → basketFundingAvg.
- [ ] KHÔNG có TIME / momentum1M-5M / label-cũ trong output.

## (Code điền)
- **Format + #cột + align gate_return:** …
- **Validate từng group (range/NaN/recompute/look-ahead/align):** …
- **Encode volatilityRegime (mapping):** …
