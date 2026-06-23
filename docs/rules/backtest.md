# rules/backtest — Toàn vẹn & tái lập backtest (nạp khi chạy/sửa sim/HPO/golden)

> Đọc cùng [CORE](../CORE.md) (look-ahead, IntegrityGuard, fee/slippage, CONFIG_VERSION đã ở đó). Đây là chi tiết + cạm bẫy.

## Look-ahead (chi tiết)
- Nến đã đóng KHÔNG được vừa dùng `maxPrice` để kích hoạt/đặt SL vừa khớp theo `minPrice`/`lastPrice` cùng nến (không ai biết đỉnh/đáy đến trước). Đặt SL nến này, khớp nến sau.
- Đã sửa ở `OrderTargetInfoTest.updateStatusNew` (nhánh `priceSL==null`). Nhánh `priceSL!=null` (SL có từ nến trước, khớp `minPrice`) là ĐÚNG — KHÔNG đụng.

## Nút chặn duy nhất
- `BacktestIntegrityGuard.assertProductionGrade()` cắm ở `SimulatorMarketLevelTicker1MStopLoss.simulatorWithInitEntry()` — MỌI engine (Master/AIMarket/BudgetRatio/Combined/DynamicFilter/TrailingStop/MarketThresholds/BenchmarkSpeed) đi qua đây → không ai bypass; KHÔNG cần gọi lại ở từng engine.

## Tái lập / chống drift (ADR-0006 golden regression, TRACE)
- Commit TRƯỚC khi chạy; KHÔNG chạy working-tree bẩn. Ghi: commit + giai đoạn + Configs + set Aerospike + slippage.
- `SLIPPAGE_RATE` từng trôi `0.0005 ↔ 0.003` trên working-tree → backtest không nhất quán. Chốt `0.003` (FINDINGS §7).
- Sim KHÔNG random → cùng input phải ra cùng output (golden fingerprint).
- ⚠️ Đừng so "artifact sim cũ ngoài git" (`OrderTestDone.data`) với "chạy tươi Aerospike" — táo vs cam (TRACE).

## Cạm bẫy đọc kết quả
- **Win rate VÔ NGHĨA với martingale** (~99% giả). Đo `profitFactor` / `worstSingleLoss` / `payoffRatio` / maxDD / nearLiq + chất lượng leg ĐẦU (`EdgeAttributionReport`).
- **Backtest đẹp ≠ model tốt** (có thể HPO che lỗi model / martingale cõng). Đo model ĐỘC LẬP (IC holdout chưa-train) trước khi tin.
- **Cửa sổ ngắn lừa:** ablation 7 tháng lãi, 5 năm lỗ. Luôn test qua chu kỳ đầy đủ (gồm bear).
- `predReturn24H` + MOM24 **đã bỏ hẳn** (A=C). Tên `getMaxRateIn90MForTradingStop`/`maxChange90M` thực trả `predReturn15M`, KHÔNG phải biến động 90M — đừng suy theo tên cũ.

## Tests
- KHÔNG có unit-test suite (`src/test` trống, `mvn test` no-op). "Test" = class `main()` thủ công (`*Validator`/`*Checker`/`Benchmark*`...), gọi `main` trực tiếp.
