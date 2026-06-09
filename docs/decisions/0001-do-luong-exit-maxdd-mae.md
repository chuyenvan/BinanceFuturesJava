# ADR-0001: Ba fix tính ĐÚNG ĐẮN của ĐO LƯỜNG backtest (exit-clamp, maxDD per-tick, maeLow)

- **Ngày:** 2026-06-09
- **Trạng thái:** đã chấp nhận
- **Bối cảnh phát sinh:** loạt điều tra "prove edge before optimize" trên engine `SimulatorMarketLevelTicker1MStopLoss`. Phát hiện 3 chỗ ĐO sai làm ĐẢO kết luận. Commit: `e62651f` (maeLow + trueUnrealizedMin song song), `4d7dd3a` (kẹp exit + maxDD-true thành nguồn chính, v8). Nguồn dữ liệu: các tool `VerifyMinPriceMae`, `ClassifyExitOutOfRange`, `RunBreakerBacktest`, `EdgeAttributionReport`.

## Vấn đề

3 đại lượng đo lường (exit price, maxDD, MAE) bị tính sai theo cách khiến backtest **lạc quan giả** và một session sau dễ nhìn code đã-sửa tưởng là "lạ/bug" rồi revert ngược về bản sai.

## Các lựa chọn đã cân nhắc

1. **Giữ nguyên cách cũ** — ưu: không đụng; nhược: PnL/DD/MAE sai hệ thống, mọi phán quyết edge dựa trên số sai.
2. **Sửa tại nguồn đo, thêm field/đại lượng đo riêng tách khỏi field quyết-định** — ưu: số đúng, không đụng logic giao dịch; nhược: code có thêm field "trông thừa" dễ bị dọn nhầm.

## Quyết định

Chọn (2). Ba fix:

### (1) Exit price clamp — book giá thoát trailing-stop ≤ high nến khớp
- **CŨ (sai):** `priceTP = priceSL` (book thẳng mức stop).
- **Triệu chứng/kết luận sai:** khi nến trigger GAP thủng stop (`high < priceSL`), engine book giá bán = `priceSL` cao hơn mức thực đạt được trong nến → **PnL bị THỔI**. Đo bằng `ClassifyExitOutOfRange`: **3256 cụm (5.1%) có exit > high**, **100% là `STOP_MARKET_DONE`**, fabrication=0, **ΣΔPnL_kẹp = 4271 ≈ 6.03% totalPnl**, dồn năm 2025 / ngày 20251011.
- **ĐÚNG (hiện tại):** `OrderTargetInfoTest.updateStatusNew` → `priceTP = Math.min(priceSL, ticker.maxPrice)` tại `src/main/java/com/binance/chuyennd/research/OrderTargetInfoTest.java:173` (và `:158` nhánh look-ahead bất hoạt). Booking-only, KHÔNG đụng điều kiện trigger `minPrice <= priceSL`.
- **Bằng chứng bất biến:** verify `balance 108002→103730` = giảm **4272** (≈ ΣΔPnL_kẹp, sai 1 do làm tròn); `done:14/64719/64738` TRÙNG cũ↔mới (order-flow nguyên vẹn); `unPMin -19680` TRÙNG (clamp không đụng maxDD).

### (2) maxDD nguồn THẬT per-tick (bar.low) thay cho Σ profitMin
- **CŨ (sai):** maxDD (`balanceIndex.unProfitMin`) tính từ `calProfitLossMax = Σ profitMin`, mà `profitMin` dẫn xuất từ `minPrice` (bị reset-LÊN bởi trailing), và chỉ lấy mẫu theo GIỜ.
- **Triệu chứng/kết luận sai:** maxDD **HỤT**. Đo bằng `RunBreakerBacktest` (OFF): maxDD_cũ **-12346 (-35.3%)** vs THẬT **-19681 (-56.2%)**; cũ còn **sai cả NĂM tệ nhất** (báo 2021, thật là sập 2025). maxDD nuôi `HPOFitnessCalculatorV3` (phạt DD) → fitness chấm theo DD hụt.
- **ĐÚNG (hiện tại):** `BudgetManagerSimple.updateTrueUnrealizedMin(...)` cập nhật MỖI TICK = `Σ qty·(bar.low − entry)` của cụm đang chạy (vòng per-tick trong `SimulatorMarketLevelTicker1MStopLoss.java:113-127`), rồi ghi thẳng vào `balanceIndex.unProfitMin`; writer cũ (Σ profitMin) trong `BalanceIndex.updateIndex` đã GỠ. Bump `CONFIG_VERSION` v6→v7.

### (3) maeLow — đo MAE bằng đáy THẬT, KHÔNG dùng minPrice
- **CŨ (sai):** MAE = `(minPrice − entry)/entry`. Nhưng `minPrice` là tham chiếu trailing-stop, **bị reset-LÊN** ở `updateStatusNew`/`updateTPSL`/`mergeOrder`.
- **Triệu chứng/kết luận sai:** MAE nông giả. Đo bằng `VerifyMinPriceMae`: `minPrice` chỉ khớp đáy-thật-độc-lập **4.7%**.
- **ĐÚNG (hiện tại):** thêm field `maeLow` (`OrderTargetInfoTest.java:54-58`), bám đáy nến chỉ-đi-xuống ở `updatePriceByKlineSimple` (`:98-100`), KHÔNG reset; `EdgeAttributionReport.legMaePct` dùng `maeLow`. Bằng chứng: `new(maeLow)` khớp đáy-độc-lập **100% (|Δ|=0)**.

## LÝ DO (vì sao code trông "lạ" mà KHÔNG được sửa ngược)

Đây là phần cốt: cả 3 fix tạo ra code "trông thừa/ngược trực giác", session sau dễ tưởng bug.

- **`maeLow` trông TRÙNG `minPrice` → KHÔNG được "dọn cho gọn".** Hai field CỐ Ý khác mục đích: `minPrice` = tham chiếu trailing-stop, **phải reset lên** mỗi khi dời SL (đúng cho việc của nó); `maeLow` = đáy thật từ leg đầu, **không bao giờ reset** (chỉ để đo MAE, không tham gia quyết định). Gộp/xoá một trong hai = làm sai một trong hai chức năng.
- **`priceTP = Math.min(priceSL, ticker.maxPrice)` trông như "làm yếu" fill SL → KHÔNG revert về `priceTP = priceSL`.** `min` chỉ cắn vào ca GAP (`high<priceSL`, ~5% lệnh); ca thường `min=priceSL` không đổi gì. Revert = trả lại 6% PnL thổi.
- **Block per-tick tính `unProfitMin` theo bar.low + đã GỠ writer Σ profitMin trong `BalanceIndex` → KHÔNG "khôi phục" writer cũ vì tưởng thiếu.** Dùng bar.low ở đây là METRIC (không phải quyết định) nên KHÔNG vi phạm luật look-ahead. maxDD thật sâu hơn (~-56% vs -35%) là ĐÚNG, không phải bug.
- Tất cả đều **không đổi `totalPnl`/order-flow** (đã verify): chúng chỉ sửa cách ĐO. Vì vậy nếu một thay đổi tương lai làm `totalPnl` đổi thì đó mới là dấu hiệu phá nhầm.

## Hệ quả

- maxDD báo cáo của hệ là **~-56% vốn (mode OFF)**, không phải -35% → đánh giá rủi ro/breaker phải dùng số này.
- `HPOFitnessCalculatorV3` nay phạt DD theo DD thật → fitness landscape đổi → cache HPO cũ vô hiệu (xem [ADR-0004](0004-ky-luat-config-version.md)).
- PnL backtest "thật" thấp hơn ~6% so với trước fix exit-clamp.
- Mọi report MAE (`EdgeAttributionReport`, monotonicity, ablation) nay tin được.
- Liên quan [ADR-0002](0002-look-ahead-guard.md) (vì sao dùng bar.low cho metric không vi phạm look-ahead).
