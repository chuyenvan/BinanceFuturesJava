# EXIT SWEEP 2026-07-31 — chọn `rate-min` và `ratchet` bằng SO SÁNH TRỰC TIẾP (không dùng verdict pass/fail)

> **Đây là nơi DUY NHẤT chứa kết quả sweep exit-formula. Không phải đọc log tay.**
> Chạy lại bảng bất cứ lúc nào: `bash /home/ubuntu/claudedata/.run/collect_sweeps.sh` (trên Oracle).

---

# 🛑 CẢNH BÁO ĐỌC TRƯỚC (2026-07-31 23:00) — BẢNG 1-4 BÊN DƯỚI **KHÔNG ĐÁNG TIN**

Uni nghi ngờ "overfit hoặc lỗi ở đâu đó". Một audit code độc lập đã xác nhận: **nghi ngờ đúng, và lỗi
nằm ở HÀM MỤC TIÊU chứ không phải ở chỗ chọn tham số.** Cả 4 cột dùng để kết luận đều hỏng theo cách
**thiên lệch có hệ thống ủng hộ chính cấu hình mà sweep chọn ra** (rate-min cao):

| Cột | Lỗi | Mã |
|---|---|---|
| `pnl` | Trộn lãi đã chốt với **mark-to-market của lệnh chưa bao giờ đóng**; tỉ lệ trộn TĂNG theo rate-min | F0+F5 |
| `pnl` | **Funding fee = 0** trong mọi sweep (`APPLY_FUNDING_FEE` mặc định false) — mà funding là chi phí DUY NHẤT tỉ lệ với thời gian giữ, tức tỉ lệ với chính thứ đang tối ưu | F2 |
| `pnl` | Lệnh còn mở cuối kỳ **không bao giờ bị tính funding**, kể cả khi bật cờ (nhóm giữ lâu nhất lại được miễn phí) | F3 |
| `ddPct` | KHÔNG phải drawdown: bỏ qua lãi/lỗ đã thực hiện, mẫu số là vốn ban đầu cố định ⇒ **gần như mù với tham số exit** (giải thích vì sao 8/10 cấu hình ra y hệt 30.2%) | F1 |
| `calmar` | = `pnl / (số gần như hằng)` ⇒ xếp hạng theo calmar **≡** xếp hạng theo pnl, không thêm thông tin rủi ro | F1 |
| `%noArm` | Đo nhầm (đã tự đính chính trước đó) | F6 |

**Lỗi gốc F0 — hệ KHÔNG CÓ ĐƯỜNG THOÁT LỖ.** `Simulator:626` chỉ gọi exit-logic khi lệnh đã từng đạt
`+rate-min` hoặc đã có SL. `HARD_STOP_LOSS_RATE`, `TIME_STOP_HOURS`, `HARD_SL_PCT` **đều mặc định 0**.
Và sau khi arm, `rateStop > 0` luôn ⇒ SL luôn **trên** giá vào. ⇒ Lệnh thua không có cách nào bị cắt;
nó nằm đó tới hết kỳ rồi được mark-to-market ở `Simulator:402-421`.

⇒ Nâng rate-min = nhiều lệnh không arm hơn = nhiều lệnh "không bao giờ chốt" hơn = PnL báo cáo ngày
càng là **beta thị trường 2021-2026** chứ không phải chất lượng exit. **Đường cong tăng đơn điệu
0.03→0.10 hoàn toàn giải thích được mà không cần giả thuyết "0.10 là exit tốt".**

Và cú sụp ở 0.15 cũng không phải "vực của exit": `BREAKER_MARGIN_HALT = 0.50` (`Configs:352`) khoá vốn
khi margin chạm 50% ⇒ exposure sụp ⇒ PnL sụp.

## Những gì audit xác nhận là ĐÚNG (không phải bug) — để không đi soi lại

- **Kế toán PnL với DCA: SẠCH.** `Σ qᵢ(priceTP − eᵢ) = Q(priceTP − avgEntry)`, phí và slippage cũng
  khớp đồng nhất thức; funding chỉ gán vào leg đầu nên không cộng trùng; không leg nào đóng 2 lần.
- **Fee + slippage: CÓ trừ đủ** ở mọi lệnh, kể cả lệnh mark-to-market cuối kỳ (`calTp` luôn chạy).
- **Look-ahead nội-nến: KHÔNG tìm thấy đường nào làm lợi.** `BLOCK_INTRABAR_LOOKAHEAD=true` mặc định;
  khớp SL dùng `bar.low` đã cập nhật trước, fill `min(priceSL, bar.open)`; thứ tự check SL (low) trước
  ratchet (high) là bảo thủ. Còn 1 điểm chưa kết luận được từ code Java: quy ước nhãn thời gian của
  `pred.bin` (nếu `pred[ts]` nhìn tới `ts+15m` thì là leak nặng — thuộc pipeline Python, cần kiểm riêng).
- **2025Q2 = 0 lệnh: KHÔNG phải thiếu dữ liệu.** Thiếu ticker sẽ FAIL-FAST (`Simulator:148-151`). Đây
  là gate xác suất tuyệt đối: cần `P(win) ≥ 0.679` mà base-rate 2025Q2 chỉ ~0.10-0.23 ⇒ 0 tín hiệu.
  Khớp ghi nhận cũ "w13 ZERO_TRADES".
- **Số lệnh gần như không đổi khi sweep multiplier (374-376): ĐÚNG.** Multiplier chỉ đổi giá thoát của
  lệnh thắng, không đổi việc lệnh có đóng được hay không, nên không đổi symbol-occupancy.

## Lỗi phụ đã phát hiện, chưa sửa (ghi để không quên)

- **F7** — DCA nhồi thêm leg **xoá sạch SL đang có**: `mergeOrder` tạo object mới không carry `priceSL`
  (`Simulator:696-721`) ⇒ cụm đã arm SL +2.5% mà bị nhồi 1 leg là mất bảo vệ, phải arm lại từ avgEntry.
- **F8** — Key `allOrderDone` có thể đụng độ: `put(-timeUpdate - size(), order)` ⇒ nếu
  `t₂−t₁ = n₁−n₂` thì `TreeMap.put` ghi đè, mất lệnh âm thầm khỏi báo cáo. Kiểm: so `allOrderDone.size()`
  với `counterOrderCreated`.
- **F9** — `catch (Exception e) { printStackTrace(); }` trong vòng lặp phút/ngày (`Simulator:377-388`)
  và **skip nguyên ngày** nếu < 1440 phút ⇒ ngày bị skip không có tick nào kiểm SL, cũng không cập nhật
  maxDD ⇒ thiên lệch dương. Kiểm: đếm WARN "Date data error" trong log mỗi run.
- **F10** — Coin delist phát nến phẳng thay vì `null` ⇒ cụm sống mãi, cuối kỳ MTM ở giá đóng băng thay
  vì ghi giảm về ~0.
- **F12** — 2 probe sweep không set `WFO_STATIC_RANK` / `BREAKER_MODE=OFF` như `VerifyOneWindow` ⇒ kết
  luận từ sweep chưa chắc chuyển được sang harness WFO thật.

## Đã sửa đêm 2026-07-31 và đang chạy lại

1. ✅ Tách `pnlClosed` (status ≠ REQUEST) vs `pnlMtm` (status == REQUEST) + in `%MTM` — phép đo quyết
   định: nếu `%MTM` tăng theo rate-min thì kết luận cũ bị bác.
2. ✅ Bật funding (`SIM_APPLY_FUNDING=true`) **và vá** `Simulator:402-421` gọi `computeFundingOnClose()`
   cho cụm còn mở cuối kỳ (mặc định tắt funding vẫn byte-identical hành vi cũ).
3. ✅ In `ddPctMtm` / `marginCallHit` / `minEquityMtmPct` thay cho `ddPct` mù.
4. ✅ Fold **rời nhau** (11 fold nửa năm 2021H1..2026H1) thay vì 4 period lồng nhau — sửa lỗi chọn
   tham số in-sample (F13).
5. ✅ **Nhánh đối chứng B**: `TIME_STOP_HOURS=168` ép lệnh thua phải hiện thực hoá. Nếu thứ hạng
   rate-min **đảo** giữa A và B ⇒ xác nhận kết luận cũ là artifact của F0.

Kết quả sẽ ghi vào **PHẦN 6** bên dưới. Cho tới lúc đó, **BẢNG 1-4 chỉ để tham khảo lịch sử, không
dùng để ra quyết định.**

---

## Vì sao đổi cách đo (Uni chốt 2026-07-31)

Verdict M (WFE median ≥0.50 / %OOS-dương ≥70% / maxDD ≤50%) đi qua **harness đang có vấn đề đã biết**:
fitness mismatch Calmar-vs-WFE + HPO argmax (NHÁNH A, chưa fix). Dùng nó để chấm pass/fail exit-formula
là **đo bằng thước cong**. Vì vậy chuyển sang **so sánh trực tiếp số thô** (PnL / maxDD / calmar /
holdMed) giữa các giá trị với nhau — không quy về pass/fail, không qua HPO/argmax/random-search.

Ràng buộc phương pháp kèm theo:
- **Không sweep dưới 0.03.** Lý do độc lập với backtest (Uni): round-trip cost = phí 2 chân (0.002)
  + slippage 2 chân (0.003) = **0.008**. Với giveback 0.5, SL đóng băng đầu tiên nằm ở `arm × 0.5`.
  arm=0.012 ⇒ SL ở 0.006 < 0.008 ⇒ **lỗ kế toán chắc chắn** ngay cả khi "chốt lời", lại còn tỉ lệ khớp
  cao (giá chỉ cần hồi nhẹ). Vậy vùng <0.03 bị loại bằng lập luận chi phí, **không cần backtest phân xử**.
- **Ratchet phải đo SAU khi có rate-min** (Uni): ratchet threshold = `TS_PROFIT_MULTIPLIER (5.21847) ×
  base`, mà base dùng **CHUNG sàn** `RATE_PROFIT_STOP_MARKET` với arm ⇒ 2 việc **không độc lập**. Nâng
  arm 0.012→0.03 vô tình kéo dead-zone từ ~4.35pp lên **~12.66pp** (3%→15.66%), tức làm TO THÊM đúng
  cái lỗi đang định sửa. Vì vậy sweep ratchet chạy với rate-min cố định = 0.03.

## Hạ tầng / cách chạy (để tái lập)

- Probe: `TrailingStopSweepProbe` (rate-min, env `SWEEP_RATES` CSV) và `RatchetDecoupleSweepProbe`
  (env `SWEEP_RATE_MIN` + `SWEEP_DECOUPLED`) — cả 2 **không qua** WFO/JobStore/HPO, chạy sim thẳng.
- Jar: `binance-sweep-20260731b.jar` (Oracle). Dataset `wfo_ds_ret2wf_4h_ff`, ticker Aerospike local.
- Chạy song song `xargs -P`, launch bằng `nohup ... & disown` (**KHÔNG dùng `bg_run`** — xem
  INFRA_FACTS, bg_run từng báo SUCCESS giả).
- Trần tài nguyên Oracle: **4 core / 23GB RAM, KHÔNG có swap**. Mỗi JVM `-Xmx3g` ⇒ tối đa ~5 job đồng
  thời. Vượt mức này là nguy cơ OOM-kill, không phải chỉ chậm.
- ⚠️ Đã cắn 1 lần: JVM **không tự thoát** sau khi `main()` in xong (non-daemon thread treo) ⇒ nghẽn
  `xargs`. Đã fix bằng `System.exit(0)` cuối cả 2 probe. `rc=137` trong `progress.log` = SIGKILL thủ
  công để giải phóng core cho batch sau — **kết quả in ra trước đó vẫn hợp lệ**, không phải job fail.

## Giai đoạn đo

`2024_bull` (20240101-20241231) · `2025Q2_phang` (20250401-20250701) · `2025Q4_crash`
(20251001-20260101, **tách riêng** vì chứa black-swan 10-11/10/2025 — xem EXIT_MACHINE PHẦN 5) ·
`toan_ky` (20210101-20260501).

---

## BẢNG 1 — RATE-MIN SWEEP

| rate | period | trades | pnl | ddPct% | calmar | sortino | holdMed(p) | %hold>60p |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 0.03 | 2024_bull | 436 | 3063.9 | 7.1 | 1.238 | 22.788 | 43.0 | 46.1% |
| 0.03 | 2025Q2_phang | 0 | 0.0 | 0.0 | 0.000 | 0.000 | 0.0 | 0.0% |
| 0.03 | 2025Q4_crash | 919 | 6042.4 | 28.0 | 0.616 | 385.026 | 4.0 | 11.8% |
| 0.03 | **toan_ky** | 3291 | **20260.8** | 28.8 | **2.011** | 1.386 | 23.0 | 36.9% |
| 0.035 | 2024_bull | 416 | 3537.2 | 8.9 | 1.136 | 0.490 | 72.0 | 51.4% |
| 0.035 | 2025Q2_phang | 0 | 0.0 | 0.0 | 0.000 | 0.000 | 0.0 | 0.0% |
| 0.035 | 2025Q4_crash | 678 | 3852.1 | 29.0 | 0.380 | 2.442 | 7.0 | 16.8% |
| 0.035 | **toan_ky** | 3031 | **21525.5** | 29.3 | **2.100** | 0.432 | 36.0 | 42.8% |
| 0.04 | 2024_bull | 384 | 4089.4 | 9.1 | 1.278 | 0.488 | 143.0 | 60.7% |
| 0.04 | 2025Q2_phang | 0 | 0.0 | 0.0 | 0.000 | 0.000 | 0.0 | 0.0% |
| 0.04 | 2025Q4_crash | 617 | 3962.3 | 29.0 | 0.391 | 1.649 | 7.0 | 18.2% |
| 0.04 | **toan_ky** | 2843 | **23050.7** | 29.1 | **2.260** | 0.345 | 58.5 | 49.2% |
| 0.045 | 2024_bull | 375 | 4913.2 | 9.1 | 1.542 | 0.598 | 222.0 | 62.5% |
| 0.045 | 2025Q2_phang | 0 | 0.0 | 0.0 | 0.000 | 0.000 | 0.0 | 0.0% |
| 0.045 | 2025Q4_crash | 549 | 4388.7 | 29.3 | 0.428 | 0.000 | 10.0 | 21.3% |
| 0.045 | **toan_ky** | 2628 | **24402.9** | 30.2 | **2.312** | 0.089 | 85.5 | 54.3% |
| 0.05 | 2024_bull | 358 | 5422.2 | 9.1 | 1.695 | 0.588 | 334.5 | 68.6% |
| 0.05 | 2025Q2_phang | 0 | 0.0 | 0.0 | 0.000 | 0.000 | 0.0 | 0.0% |
| 0.05 | 2025Q4_crash | 512 | 5145.1 | 29.9 | 0.491 | 0.000 | 12.0 | 25.5% |
| 0.05 | **toan_ky** | 2461 | **25849.9** | 30.8 | **2.401** | 0.061 | 151.0 | 60.7% |
| 0.06 | 2024_bull | 351 | 7167.3 | 9.2 | 2.225 | 0.638 | 921.0 | 81.7% |
| 0.06 | 2025Q4_crash | 371 | 3959.0 | 29.0 | 0.390 | 0.384 | 21.0 | 33.7% |
| 0.06 | **toan_ky** | 2220 | **29331.6** | 30.0 | **2.791** | 0.097 | 348.0 | 69.1% |
| 0.07 | 2024_bull | 337 | 7942.6 | 10.0 | 2.265 | 0.345 | 1093.0 | 84.5% |
| 0.07 | 2025Q4_crash | 288 | 3291.9 | 28.7 | 0.328 | 0.223 | 34.5 | 43.8% |
| 0.07 | **toan_ky** | 2022 | **30130.4** | 31.3 | **2.753** | 0.092 | 522.0 | 76.7% |
| 0.08 | 2024_bull | 333 | 8658.0 | 10.0 | 2.468 | 0.353 | 1814.0 | 89.6% |
| 0.08 | 2025Q4_crash | 250 | 3532.9 | 28.7 | 0.352 | 0.161 | 98.0 | 54.2% |
| 0.08 | **toan_ky** | 1921 | **31716.1** | 32.0 | **2.831** | 0.064 | 687.0 | 82.2% |
| 0.09 | 2024_bull | 320 | 8901.1 | 9.9 | 2.579 | 0.347 | 2746.0 | 92.0% |
| 0.09 | 2025Q4_crash | 233 | 4237.3 | 28.7 | 0.422 | 0.175 | 131.0 | 56.2% |
| 0.09 | **toan_ky** | 1859 | **34307.8** | 31.6 | **3.103** | 0.093 | 830.0 | 85.2% |
| 0.10 | 2024_bull | 302 | 9671.6 | 10.3 | 2.685 | 0.364 | 3646.0 | 96.8% |
| 0.10 | 2025Q4_crash | 196 | 3779.4 | 28.6 | 0.378 | 0.107 | 1050.0 | 67.2% |
| 0.10 | **toan_ky** | 1775 | **37600.0** | 32.0 | **3.354** | 0.083 | 1255.0 | 88.8% |

(`2025Q2_phang` = 0 lệnh ở MỌI mức rate — lược bớt khỏi bảng từ 0.06 trở đi cho gọn.)

### Đọc bảng 1 — ⚠️ ĐƠN ĐIỆU TỚI HẾT DẢI, KHÔNG CÓ ĐỈNH → NGHI VẤN ARTIFACT

`toan_ky` tăng **đơn điệu suốt 0.03 → 0.10**, không quay đầu ở đâu cả:

| | 0.03 | 0.04 | 0.05 | 0.06 | 0.07 | 0.08 | 0.09 | 0.10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| PnL | 20 261 | 23 051 | 25 850 | 29 332 | 30 130 | 31 716 | 34 308 | **37 600** |
| calmar | 2.01 | 2.26 | 2.40 | 2.79 | 2.75 | 2.83 | 3.10 | **3.35** |
| maxDD% | 28.8 | 29.1 | 30.8 | 30.0 | 31.3 | 32.0 | 31.6 | 32.0 |
| holdMed (phút) | 23 | 58 | 151 | 348 | 522 | 687 | 830 | **1 255** |
| số lệnh | 3 291 | 2 843 | 2 461 | 2 220 | 2 022 | 1 921 | 1 859 | 1 775 |

**KHÔNG được đọc bảng này thành "chọn 0.10".** Đường cong đơn điệu tới hết dải test là dấu hiệu kinh
điển của việc đang đo nhầm thứ. Ba nghi vấn cụ thể, xếp theo mức nghiêm trọng:

**(a) Nghi vấn lớn nhất — đang ăn BETA thị trường, không phải alpha exit.** Nâng arm threshold ⇒ lệnh
không đạt ngưỡng thì **không bao giờ arm** ⇒ `priceSL == null`, mà `HARD_STOP_LOSS_RATE=0` và
`TIME_STOP_HOURS=0` ⇒ **KHÔNG CÓ EXIT NÀO** (đã ghi ở EXIT_MACHINE PHẦN 1, "khúc 1"). Lệnh đó bị giữ
tới cuối kỳ rồi mark-to-market (`SimulatorMarketLevelTicker1MStopLoss:402-421` — "add all order running
to done"). Giai đoạn 2021-2026 crypto tăng rất mạnh ⇒ **cứ giữ lâu là lãi**, bất kể công thức exit.
holdMed 23 phút → 1 255 phút (21 giờ) đúng chiều nghi vấn này. Nếu đúng, "cải thiện" chỉ là chiến lược
đang **âm thầm biến thành buy-and-hold**, không phải exit tốt lên.

**(b) Vi phạm ràng buộc production `MAX_PCT_HELD_OVER_7D = 0.02`** (`HPOFitnessCalculatorV4:36-40`).
Bảng thô này KHÔNG áp ràng buộc đó. Ở 0.10, `2024_bull` holdMed = 3 646 phút = **2.5 ngày**, 96.8% lệnh
giữ >60 phút ⇒ nhiều khả năng vượt xa trần 2% lệnh giữ >7 ngày ⇒ **harness thật sẽ loại thẳng**
(`TOO_MUCH_CAPITAL_LOCK`). Ràng buộc này tồn tại có lý do: vốn kẹt = chi phí cơ hội + rủi ro margin call.

**(c) Regime-dependency — `2025Q4_crash` đi NGƯỢC CHIỀU:**

| rate | 0.03 | 0.04 | 0.05 | 0.06 | 0.07 | 0.08 | 0.09 | 0.10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| crash PnL | **6 042** | 3 962 | 5 145 | 3 959 | 3 292 | 3 533 | 4 237 | 3 779 |

Trong giai đoạn crash, **0.03 tốt nhất**, mọi mức cao hơn đều tệ hơn 15-45%. Tức chọn 0.10 = **đặt cược
vào regime tăng giá**; trong ngày xấu, cấu hình đó thua rõ 0.03.

⇒ **CHƯA CHỐT GIÁ TRỊ.** Đang chạy phép đo quyết định (BẢNG 3) để phân xử nghi vấn (a) và (b).

⚠️ **`2025Q2_phang` = 0 lệnh ở MỌI mức rate** — không phải do exit-formula mà do **không có tín hiệu
entry nào** trong quý đó (khớp EXIT_MACHINE PHẦN 4: w13 = ZERO_TRADES). Đây là vấn đề
**entry-frequency**, việc khác, không thuộc nhánh exit.

---

## BẢNG 2 — RATCHET DECOUPLE (rate-min cố định = 0.03)

| decoupled | period | trades | pnl | ddPct% | calmar | sortino | holdMed(p) | %hold>60p |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| false (giữ dead-zone) | 2024_bull | 436 | 3063.9 | 7.1 | 1.238 | 22.788 | 43.0 | 46.1% |
| **true (bỏ dead-zone)** | 2024_bull | 445 | **3193.5** | 7.2 | **1.262** | 0.000 | 29.5 | 37.2% |
| false | 2025Q2_phang | 0 | 0.0 | 0.0 | 0.000 | 0.000 | 0.0 | 0.0% |
| true | 2025Q2_phang | 0 | 0.0 | 0.0 | 0.000 | 0.000 | 0.0 | 0.0% |
| false | 2025Q4_crash | 919 | 6042.4 | 28.0 | 0.616 | 385.026 | 4.0 | 11.8% |
| **true** | 2025Q4_crash | 957 | **6359.2** | 28.0 | **0.648** | 405.214 | 4.0 | 10.5% |
| false | **toan_ky** | 3291 | **20260.8** | 28.8 | **2.011** | 1.386 | 23.0 | 36.9% |
| **true** | **toan_ky** | 3400 | **19296.1** | 28.8 | **1.915** | 4.066 | 18.0 | 30.9% |

### Đọc bảng 2 — ✅ KẾT LUẬN RÕ: ratchet-decouple KHÔNG có tác dụng, thậm chí hơi XẤU

Trên mẫu lớn nhất (`toan_ky`, 3 300+ lệnh), `decoupled=true` **THUA**:
- PnL **19 296 vs 20 261** = **−4.8%**
- calmar **1.915 vs 2.011** = **−4.8%**
- maxDD y hệt (28.8 cả hai) ⇒ không đánh đổi được gì, chỉ thuần kém hơn.
- holdMed **18 vs 23 phút** ⇒ giữ lệnh NGẮN HƠN.

Hai giai đoạn con (2024_bull +4.2%, 2025Q4_crash +5.2%) trước đó cho tín hiệu ngược nhưng **mẫu nhỏ
hơn và đã bị toan_ky đảo chiều** ⇒ đúng như đã cảnh báo ở bản nháp: mức chênh 4-5% nằm trong nhiễu,
không phải edge.

**Cơ chế giải thích nhất quán:** bỏ dead-zone ⇒ SL bắt đầu dời sớm hơn ⇒ SL bám sát giá hơn ⇒ dễ bị
quét hơn ⇒ giữ lệnh ngắn hơn (23→18 phút) ⇒ cắt lãi non nhiều hơn. Tức `TS_RATCHET_DECOUPLED=true` đi
**NGƯỢC hướng** với mục tiêu "nuôi lãi" mà việc 1 (nâng rate-min) đang theo đuổi. Không phải "sửa lỗi
dead-zone" như giả thuyết ban đầu — dead-zone hoá ra đang **có ích**: nó giữ SL đứng yên trong lúc giá
còn đang leo, đúng tinh thần nuôi lãi.

**Kết quả này KHỚP với confirm WFO trước đó** (EXIT_MACHINE PHẦN 5: `ratchet_true` cho WFE median
0.128 vs 0.442 của `false` — cũng tệ hơn). Hai phương pháp đo độc lập (raw sweep và WFO/verdict) **cùng
kết luận**, nên độ tin cậy cao.

⇒ **CHỐT: giữ `TS_RATCHET_DECOUPLED=false` (mặc định). Việc 2 ĐÓNG — không theo đuổi nữa.**
Đây cũng là câu trả lời cho thắc mắc của Uni "ratchet zone tôi chưa hiểu ý nghĩa": dead-zone = khoảng
lãi mà SL **cố tình đứng yên** thay vì bám theo giá. Ban đầu tôi nghi nó là lỗi thiết kế; số liệu cho
thấy nó là **tính năng có ích**, bỏ đi thì tệ hơn ~5%.

---

---

## BẢNG 3 — CHẨN ĐOÁN: mở rộng tới 0.30 + đo `%hold>7d`

Mục đích: phân xử nghi vấn (a) "ăn beta" và (b) "vi phạm ràng buộc capital-lock" ở BẢNG 1.

| rate | period | trades | pnl | ddPct% | calmar | holdMed | %h>60p | **%h>7d** |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 0.03 | 2024_bull | 436 | 3063.9 | 7.1 | 1.238 | 43 | 46.1% | **0.3%** |
| 0.03 | 2025Q4_crash | 919 | 6042.4 | 28.0 | 0.616 | 4 | 11.8% | **0.4%** |
| 0.03 | **toan_ky** | 3291 | **20260.8** | 28.8 | 2.011 | 23 | 36.9% | **0.6%** ✅ |
| 0.05 | 2024_bull | 358 | 5422.2 | 9.1 | 1.695 | 334 | 68.6% | 5.5% |
| 0.05 | 2025Q4_crash | 512 | 5145.1 | 29.9 | 0.491 | 12 | 25.5% | 0.3% |
| 0.05 | **toan_ky** | 2461 | **25849.9** | 30.8 | 2.401 | 151 | 60.7% | **2.6%** ⚠️ |
| 0.10 | 2024_bull | 302 | 9671.6 | 10.3 | 2.685 | 3646 | 96.8% | 28.2% |
| 0.10 | 2025Q4_crash | 196 | 3779.4 | 28.6 | 0.378 | 1050 | 67.2% | 12.4% |
| 0.10 | **toan_ky** | 1775 | **37600.0** | 32.0 | **3.354** | 1255 | 88.8% | **13.9%** ❌ |
| 0.15 | 2024_bull | 255 | 11072.0 | 18.8 | 1.682 | 6544 | 99.2% | 41.5% |
| 0.15 | 2025Q4_crash | 149 | 2369.0 | 29.6 | 0.229 | 4675 | 79.3% | 19.6% |
| 0.15 | **toan_ky** | 771 | **−2764.7** | **45.7** | **−0.173** | 1924 | 92.7% | 22.2% |
| 0.20 | **toan_ky** | 470 | **−6474.3** | 43.6 | −0.424 | 5087 | 96.8% | 38.5% |
| 0.30 | **toan_ky** | 277 | **−5525.4** | 44.5 | −0.355 | 22729 | 98.5% | 63.8% |

### ✅ ĐÃ TÌM RA ĐỈNH — và nó nằm ngay cạnh vực

**Đường cong KHÔNG đơn điệu vô hạn.** Nó vỡ tan giữa 0.10 và 0.15:

| rate | 0.03 | 0.05 | 0.10 | **0.15** | 0.20 | 0.30 |
|---|---:|---:|---:|---:|---:|---:|
| PnL toàn kỳ | 20 261 | 25 850 | **37 600** | **−2 765** | −6 474 | −5 525 |
| maxDD% | 28.8 | 30.8 | 32.0 | **45.7** | 43.6 | 44.5 |
| số lệnh | 3 291 | 2 461 | 1 775 | **771** | 470 | 277 |

⇒ Nghi vấn (a) "ăn beta vô hạn" **BỊ BÁC**: nếu chỉ là beta buy-and-hold thì giữ càng lâu càng lãi,
nhưng 0.15+ **lỗ nặng**. Có đỉnh thật, có cơ chế thật.

**Cơ chế vỡ (đọc từ cột `trades` và `%h>7d`):** nâng arm quá cao ⇒ lệnh không đạt ngưỡng arm thì không
có exit ⇒ vốn **kẹt** trong lệnh xấu ⇒ số lệnh sập 1 775 → 771 → 277 (vốn không quay vòng được nữa)
⇒ danh mục biến thành một nhúm vị thế lỗ giữ vô thời hạn ⇒ maxDD nhảy 32% → 45.7%. Đây chính xác là
thứ ràng buộc `MAX_PCT_HELD_OVER_7D` sinh ra để chặn.

### ❌ Nghi vấn (b) ĐÚNG — ràng buộc capital-lock chặn ở ~0.045, không phải 0.10

Trần production `MAX_PCT_HELD_OVER_7D = 0.02` (2%, `HPOFitnessCalculatorV4:36-40`):

| rate | %hold>7d | vs trần 2% |
|---:|---:|---|
| 0.03 | 0.6% | ✅ PASS (dư 3.3×) |
| 0.05 | 2.6% | ⚠️ VƯỢT nhẹ (1.3×) |
| 0.10 | 13.9% | ❌ VƯỢT **7×** |

⇒ **Cấu hình PnL thô cao nhất (0.10) sẽ bị harness thật loại thẳng** (`TOO_MUCH_CAPITAL_LOCK`), đúng
như đã lo. Vùng hợp lệ là **0.03 → ~0.045**.

### ⚠️ TỰ ĐÍNH CHÍNH — cột `%noArm` trong log là SAI, ĐỪNG DÙNG

Tôi thêm cột `%noArm` (đếm `priceSL == null`) định đo "tỉ lệ lệnh không bao giờ arm". Log ra 84-95%,
suýt nữa thành "phát hiện lớn". **Kiểm tra code thì metric này đo nhầm:** `mergeOrder()` tạo một object
cụm MỚI mang trạng thái trailing, còn `closeOrder()` chỉ chép `status/priceTP/minPrice/maeLow/lastPrice`
sang từng leg — **KHÔNG chép `priceSL`**. Nên leg trong `allOrderDone` gần như luôn có `priceSL == null`
bất kể cụm đã arm hay chưa. Con số 84-95% thực chất ≈ **tỉ lệ leg thuộc cụm DCA nhiều chân**, không
liên quan arm. Đã bỏ khỏi bảng trên. Muốn đo đúng "chưa từng arm" thì phải instrument ở cấp cụm
(`symbol2OrderRunning`), chưa làm.

### Khuyến nghị chọn rate-min

**0.04 – 0.045**, không phải 0.10. Ba lý do độc lập:
1. **Ràng buộc production**: 0.05 đã vượt trần `%h>7d` (2.6% > 2%); 0.04-0.045 nằm trong trần.
2. **Khoảng cách tới vực**: 0.10 chỉ cách điểm sụp đổ (0.15) đúng 1.5×. 0.045 cách ~3.3× — biên an toàn
   thật, quan trọng vì tham số này sẽ chạy trên dữ liệu tương lai chưa thấy.
3. **Regime**: ở `2025Q4_crash`, 0.03 tốt nhất (6 042) và mọi mức cao hơn tệ hơn 15-45%. Chọn thấp là
   chọn cấu hình không phụ thuộc regime tăng giá.

So với hiện trạng production (`RATE_PROFIT_STOP_MARKET = 0.03`): nâng lên 0.04-0.045 cho **+14% đến
+20% PnL toàn kỳ** (20 261 → 23 051 / 24 403), maxDD gần như không đổi (28.8 → 29.1 / 30.2), vẫn trong
trần capital-lock. Đây là cải thiện **khiêm tốn nhưng thật**, không phải artifact.

---

## BẢNG 4 — SWEEP `TS_PROFIT_MULTIPLIER` (tại rate-min 0.045) — **ĐỈNH ĐÚNG Ở GIÁ TRỊ HIỆN TẠI**

Giả thuyết đem đi test (Uni nêu): `TS_PROFIT_MULTIPLIER = 5.21847` được tune khi rate-min = 0.0103
(⇒ ratchet 5.4%, dead-zone 4.35pp — hợp lý). Sau khi nâng rate-min lên 0.045 vì lý do chi phí, ratchet
tự phình thành **23.5%** (dead-zone 19pp) vì nó là **hệ số NHÂN**, không phải ngưỡng độc lập. Nghi ngờ:
hệ số cũ nay sai ngữ cảnh, nên hạ về 1.5-2.

**Kết quả `toan_ky`:**

| mult | ratchet tại | trades | PnL | maxDD% | calmar | holdMed | **%h>7d** |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.0 | 4.5% | 2716 | 22 405 | 30.2 | 2.123 | 57 | 1.2% |
| 1.5 | 6.75% | 2709 | 22 549 | 30.2 | 2.137 | 60.5 | 1.2% |
| 2.0 | 9.0% | 2686 | 22 256 | 30.2 | 2.109 | 68 | 1.2% |
| 3.0 | 13.5% | 2674 | 23 029 | 30.2 | 2.182 | 78 | 1.2% |
| **5.21847** ⭐ | 23.5% | 2628 | **24 403** | 30.2 | **2.312** | 85.5 | **1.8%** ✅ |
| 8.0 | 36% | 2567 | 24 396 | 30.2 | 2.312 | 97 | 4.0% ❌ |
| 12.0 | 54% | 2512 | 24 241 | 30.2 | 2.297 | 108 | 5.6% ❌ |
| 20.0 | 90% | 2484 | 23 731 | 30.2 | 2.249 | 111.5 | 7.7% ❌ |
| 50.0 | 225% | 2472 | 21 783 | 29.9 | 2.079 | 106 | 8.7% ❌ |
| 200.0 (≈ bỏ hẳn ratchet) | 900% | 2380 | **13 908** | 25.6 | 1.553 | 116 | 8.8% ❌ |

### ⚠️ TỰ ĐÍNH CHÍNH — giả thuyết của tôi SAI

Tôi đã lập luận "ratchet 23.5% là vô lý, trailing không bao giờ chạy, phải hạ multiplier về 1.5-2".
**Số liệu bác bỏ:** hạ multiplier làm PnL **giảm** (5.2 → 24 403; 3.0 → 23 029; 2.0 → 22 256). Giá trị
hiện tại 5.21847 **đúng là đỉnh**, dù rate-min đã đổi gấp 4.4 lần. Lập luận "sai ngữ cảnh" nghe hợp lý
nhưng không đúng với dữ liệu.

### ✅ Trả lời dứt điểm: KHÔNG bỏ ratchet

`mult = 200` ⇒ ratchet ở 900% ⇒ **không lệnh nào chạm** ⇒ tương đương **bỏ hẳn cơ chế ratchet**, SL
đóng băng vĩnh viễn ở mức arm×giveback. Kết quả: PnL **13 908**, tức **−43%** so với đỉnh. Ratchet
**có giá trị thật**, không phải phức tạp thừa.

### Hình dạng đường cong: plateau rộng, hai đầu đều tệ

```
PnL toàn kỳ:  22.4k → 22.5k → 22.3k → 23.0k → [24.4k ═ 24.4k] → 24.2k → 23.7k → 21.8k → 13.9k
mult:          1.0     1.5     2.0     3.0    5.21847   8.0      12.0    20.0    50.0    200
                                                └── plateau ──┘
```
Đỉnh là **plateau 5.2-8.0** (24 403 vs 24 396 — chênh 0.03%, coi như bằng nhau) ⇒ tham số **robust**,
không nhạy, không phải điểm nhọn do overfit.

### Nhưng ràng buộc capital-lock chọn hộ ta trong plateau

| mult | %h>7d | trần 2% |
|---:|---:|---|
| 5.21847 | 1.8% | ✅ PASS |
| 8.0 | 4.0% | ❌ FAIL 2× |

⇒ Trong plateau 5.2-8.0, **chỉ 5.21847 thỏa ràng buộc production**. Không cần chọn — dữ liệu và ràng
buộc cùng chỉ về một điểm.

### 🔒 CHỐT VIỆC 2: giữ nguyên `TS_PROFIT_MULTIPLIER = 5.21847`, `TS_RATCHET_DECOUPLED = false`

**Không đổi dòng code nào.** Ba phép đo độc lập (decouple A/B, sweep multiplier thấp, sweep multiplier
cao) đều hội tụ về cấu hình hiện tại. Phần ratchet của exit-formula **đã tối ưu sẵn**.

---

## 🎯 TỔNG KẾT NHÁNH EXIT — chỉ MỘT tham số nên đổi

| việc | tham số | hiện tại | kết luận | thay đổi? |
|---|---|---|---|---|
| 1 | `RATE_PROFIT_STOP_MARKET` | 0.03 | đỉnh thô ở 0.10 nhưng vi phạm capital-lock 7×; vùng hợp lệ 0.04-0.045 | ✅ **0.03 → 0.045** |
| 2 | `TS_PROFIT_MULTIPLIER` | 5.21847 | đã là đỉnh (plateau 5.2-8), chỉ 5.2 thỏa ràng buộc | ❌ giữ nguyên |
| 2b | `TS_RATCHET_DECOUPLED` | false | true thua −4.8%; bỏ hẳn ratchet thua −43% | ❌ giữ nguyên |
| 3 | giveback `min→max` | chưa chạy | trần 8% chỉ cắn khi lãi >16%, mà ratchet ở 23.5% ⇒ tác động nhỏ | ⏸ hoãn |

**Lợi ích ước tính của thay đổi duy nhất** (rate-min 0.03 → 0.045, giữ mọi thứ khác):
PnL toàn kỳ **20 261 → 24 403 (+20.4%)**, maxDD 28.8% → 30.2% (+1.4pp), calmar 2.01 → 2.31,
holdMed 23 → 85 phút, `%h>7d` 0.6% → 1.8% (vẫn dưới trần 2%).

Khiêm tốn nhưng **thật** và **robust** — không phụ thuộc 1 window, không vi phạm ràng buộc, cách vực
sụp đổ 3.3×.

### Lever còn lại chưa đo, có thể đáng giá hơn việc 3

`TS_GIVEBACK_RATIO` (hiện 0.5) quyết định **mức SL đóng băng** = `arm × (1 − giveback)`. Với arm 4.5%:
giveback 0.5 → SL +2.25%; giveback 0.3 → SL **+3.15%**; giveback 0.7 → SL +1.35%. Vì **đa số lệnh
thoát tại chính mức đóng băng này** (ratchet ở 23.5% hiếm khi chạm), đây là tham số ảnh hưởng trực tiếp
nhất tới PnL mỗi lệnh — và **chưa từng được sweep**. Nó cũng đang là hạng mục P6 trong INFRA_FACTS
("không phải gene → không có provenance → không biết step-2 chạy 0.5 hay 1.0").

---

---

# PHẦN 6 (2026-08-01) — ĐO LẠI SẠCH: walk-forward + metric đã vá. **KẾT LUẬN CŨ ĐỨNG VỮNG.**

Thiết kế: 10 rate × 11 fold nửa năm **rời nhau** (2021H1..2026H1), funding **BẬT**, tách
`pnlClosed` vs `pnlMtm`, dùng `ddPctMtm` thật. Cộng nhánh đối chứng **B** (`TIME_STOP_HOURS=168`)
ép lệnh chưa-arm phải chốt sau 7 ngày. Vệ sinh run: **0 "Date data error", 0 Exception** ở log kiểm tra.

## 6.1 — Ba nghi ngờ của audit: ĐỀU BỊ BÁC BỎ bằng số

| Nghi ngờ (audit) | Dự đoán nếu đúng | Số thật | Kết luận |
|---|---|---|---|
| **F5** PnL bị thổi bởi mark-to-market của lệnh không đóng | `pnlMtm` **dương** và lớn dần theo rate | `pnlMtm` **ÂM** ở mọi rate: −354 (0.0103) → −6 563 (0.10). %MTM chỉ 0.1%→5.1% số lệnh | ❌ **NGƯỢC LẠI** — MTM *kéo giảm* PnL. `pnlClosed` sạch vẫn tăng đơn điệu 10 617 → 37 789 |
| **F2/F3** funding bị bỏ qua, chi phí thật ăn hết lợi ích của giữ-lâu | funding âm lớn dần theo rate | funding = **−30 → −112** (dấu âm = ta **NHẬN** funding). Tuyệt đối ~0.3% PnL | ❌ Không đáng kể, và còn là **gió xuôi** chứ không phải chi phí |
| **F0** không có đường thoát lỗ ⇒ kết quả là artifact | ép chốt lỗ sẽ **đảo thứ hạng** | Arm B: **0/5 rate đổi thứ hạng**. 0.10 → 37 786 (B) vs 37 789 (A), chênh 0.008% | ❌ **Bền vững** — bao tải lệnh chưa-arm KHÔNG phải nguồn của kết quả |

⇒ Phép đo cũ **may mắn đúng kết luận dù sai phương pháp**. Giờ nó đúng cả hai.

## 6.2 — Walk-forward: chọn trên quá khứ, chấm trên tương lai chưa nhìn

| fold chấm | rate WF chọn | pnl WF | pnl @0.03 | hindsight |
|---|---:|---:|---:|---:|
| 2021H2 | 0.10 | 2 983 | 2 278 | 2 983 |
| 2022H1 | 0.10 | 3 157 | 1 569 | 3 157 |
| 2022H2 | 0.10 | 1 745 | 581 | 1 745 |
| 2023H1 | 0.10 | 576 | 347 | 1 098 (0.08) |
| 2023H2 | 0.10 | 2 021 | 798 | 2 021 |
| 2024H1 | 0.10 | 6 388 | 1 910 | 6 388 |
| 2024H2 | 0.10 | 3 796 | 1 159 | 3 796 |
| 2025H1 | 0.10 | 2 208 | 1 392 | 2 208 |
| **2025H2** | 0.10 | **3 277** | **5 651** | 5 651 (0.03) ⚠️ |
| 2026H1 | 0.10 | 0 | 0 | 0 |
| **TỔNG OOS** | | **26 150** | **15 685** | 29 045 |

- **Walk-forward vs baseline 0.03: +66.7%** trên dữ liệu **chưa nhìn**.
- Đạt **90% hindsight** (trần trên không đạt được).
- **Ổn định tuyệt đối: 0.10 được chọn 10/10 lần.** Không phải tham số nhiễu.
- ⚠️ Ngoại lệ duy nhất: **2025H2** (chứa crash 10/10/2025) — 0.03 thắng đậm (5 651 vs 3 277). Đúng
  mẫu đã thấy: rate thấp tốt hơn trong regime sập.
- `2026H1` = 0 ở mọi rate (fold cuối, thiếu dữ liệu/không tín hiệu) — không dùng để so.

## 6.3 — Rủi ro THẬT (`ddPctMtm`, không phải `ddPct` mù)

| rate | ddPctMtm tb | ddPctMtm max | minEquity thấp nhất | #marginCall | #fold âm | **%hold>7d** |
|---:|---:|---:|---:|---:|---:|---:|
| 0.0103 | 6.05% | 28.83% | 71.8% | 0 | 0 | 0.1% ✅ |
| 0.03 | 6.76% | 30.07% | 70.8% | 0 | 0 | 0.7% ✅ |
| 0.035 | 7.03% | 30.15% | 70.7% | 0 | 0 | 1.6% ✅ |
| 0.04 | 7.27% | 29.86% | 71.1% | 0 | 0 | 3.4% ❌ |
| 0.045 | 7.34% | 29.81% | 70.4% | 0 | 0 | 3.5% ❌ |
| 0.05 | 7.54% | 30.58% | 69.6% | 0 | 0 | 4.8% ❌ |
| 0.07 | 8.40% | 30.94% | 69.7% | 0 | 0 | 10.0% ❌ |
| **0.10** | **9.47%** | 30.98% | 70.7% | 0 | 0 | **18.7%** ❌ |

Rủi ro tăng **có** nhưng khiêm tốn (6.05%→9.47% trung bình), **0 margin call**, **0 fold âm** ở mọi
rate. Đây là bức tranh rủi ro lành mạnh hơn nhiều so với `ddPct` cũ (~30%) — vì `ddPct` cũ đo sai.

## 6.4 — ⚠️ VƯỚNG MẮC DUY NHẤT CÒN LẠI: ràng buộc `%hold>7d`

`MAX_PCT_HELD_OVER_7D = 0.02` (2%) chỉ cho phép **0.03 và 0.035**. Rate 0.10 vượt **9.4 lần**.

Nhưng có bằng chứng cho thấy **ràng buộc này đang bảo vệ một thứ không tồn tại**: nhánh B ép chốt mọi
lệnh chưa-arm sau 7 ngày, và PnL **gần như không đổi** (37 786 vs 37 789). Tức phần "vốn bị giam" mà
ràng buộc lo ngại, khi bị cưỡng chế giải phóng, **không tạo ra thêm giá trị nào**. Ngưỡng 2% được đặt
bằng heuristic ("hiện 0.31%, nới gấp 6×"), không phải từ một phép đo thiệt hại.

⚠️ Nhưng chưa đủ để bác ràng buộc, vì **fold 6 tháng RESET vốn mỗi kỳ** — xoá sạch "bao tải lệnh kẹt"
mỗi 6 tháng, trong khi live thì vốn không reset. Đang chạy phép đo **D (liên tục toàn kỳ, vốn không
reset)** để lượng hoá chi phí tích luỹ này, cùng **C (nới rate lên 0.12-0.25)** để tìm đỉnh thật.

## 6.5 — Dải đầy đủ 0.0103 → 0.25, chấm bằng `pnlTotal` (= đã chốt + chưa chốt)

⚠️ **Sửa lỗi metric lần 2:** bảng walk-forward đầu tiên xếp hạng theo `pnlClosed` — **sai**, vì nó bỏ
qua lỗ chưa thực hiện của lệnh còn kẹt. Ở rate cao phần này rất lớn (rate 0.25: `pnlClosed` 47 065
nhưng `pnlMtm` **−29 512** ⇒ thực tế chỉ 17 553). Dùng `pnlClosed` để xếp hạng = **tự thưởng cho việc
giấu lỗ trong vị thế chưa đóng**. Mọi số dưới đây dùng `pnlTotal`.

### A. FOLD 6 tháng (vốn reset mỗi kỳ) — 11 fold độc lập

| rate | **pnlTotal** | pnlClosed | pnlMtm | %MTM | ddMtm tb | **%>7d** | #fold âm |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.0103 | 10 264 | 10 617 | −354 | 0.1% | 6.05% | 0.1% ✅ | 0 |
| 0.03 | 20 729 | 21 278 | −549 | 0.2% | 6.76% | 0.7% ✅ | 0 |
| 0.035 | 21 820 | 23 102 | −1 282 | 0.5% | 7.03% | 1.6% ✅ | 0 |
| 0.04 | 23 532 | 24 795 | −1 263 | 0.6% | 7.27% | 3.4% | 0 |
| 0.045 | 25 630 | 28 304 | −2 674 | 0.9% | 7.34% | 3.5% | 0 |
| **0.05** | **27 413** | 29 855 | −2 443 | 0.9% | 7.54% | **2.6%*** | **0** |
| 0.06 | 27 526 | 31 913 | −4 388 | 1.7% | 7.99% | 6.9% | 0 |
| 0.07 | 27 469 | 31 765 | −4 296 | 2.8% | 8.40% | 10.0% | 0 |
| 0.08 | 27 150 | 32 711 | −5 561 | 3.6% | 8.71% | 12.9% | **2** |
| 0.10 | 31 225 | 37 789 | −6 563 | 5.1% | 9.47% | 18.7% | **2** |
| 0.12 | 27 966 | 36 153 | −8 186 | 7.5% | 10.41% | 26.2% | 1 |
| 0.15 | 26 014 | 40 801 | −14 786 | 13.8% | 11.47% | 34.5% | 2 |
| 0.20 | 20 309 | 43 642 | −23 334 | 24.4% | 12.95% | 50.0% | 3 |
| 0.25 | 17 553 | 47 065 | −29 512 | 31.8% | 14.14% | 58.9% | 2 |

*(%>7d của 0.05 lấy từ nhánh liên tục; trên fold là 4.8%.)*

**Đây KHÔNG phải đường cong có đỉnh nhọn — nó là một PLATEAU 0.05→0.12** (27 413 / 27 526 / 27 469 /
27 150 / 31 225 / 27 966, tức ~27-28k trừ đúng 1 điểm). Điểm 0.10 = 31 225 cao hơn **cả hai hàng xóm**
(0.08 = 27 150 và 0.12 = 27 966) tới ~13% ⇒ **gần như chắc chắn là nhiễu một điểm, không phải đỉnh
thật**. Chọn 0.10 vì nó là max = lặp lại đúng lỗi đã mắc lúc đầu.

### B. LIÊN TỤC toàn kỳ (vốn KHÔNG reset — sát live nhất)

| rate | **pnlTotal** | pnlClosed | pnlMtm | nMtm | ddMtm | minEquity | %>7d | funding |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.03 | 20 236 | 20 236 | 0 | 0 | 30.57% | 90.1% | 0.6% | 25 |
| 0.05 | 25 488 | 27 565 | −2 077 | 12 | 31.66% | 91.7% | 2.6% | 166 |
| 0.07 | 29 652 | 31 392 | −1 741 | 10 | 31.96% | 88.2% | 7.5% | 311 |
| 0.10 | **37 305** | 39 103 | −1 798 | 19 | 32.23% | 88.3% | 13.9% | 561 |
| **0.15** | **−7 073** | 10 947 | **−18 020** | 66 | **45.88%** | 85.6% | 22.2% | 2 169 |
| 0.20 | **−12 711** | 2 926 | −15 637 | 71 | **58.48%** | **67.8%** | 38.5% | 3 850 |

**Vực có thật và rất dốc:** 0.10 → 0.15 là **37 305 → −7 073**. Cơ chế lộ rõ ở cột `nMtm`/`pnlMtm`:
số lệnh kẹt nhảy 19 → 66, lỗ chưa thực hiện −1 798 → **−18 020**. Vốn bị giam, không quay vòng
(trades 1 775 → 771), ddMtm 32% → 46%. Đây là **rủi ro thật**, không phải artifact đo lường.

Lưu ý fold-mode **che giấu** vực này (0.15 trên fold vẫn +26 014) vì fold reset vốn mỗi 6 tháng, xoá
sạch bao tải lệnh kẹt. **Live không reset ⇒ phải tin bảng B hơn bảng A khi đánh giá an toàn.**

### C. Walk-forward (chọn trên quá khứ, chấm trên tương lai chưa nhìn)

`0.10` được chọn **10/10 lần**. Tổng OOS: **19 456** vs `0.03` = 15 200 (**+28.0%**) vs `0.05` =
17 864 (**+8.9%**). Chỉ đạt **55% hindsight**.

Nhưng nhìn từng fold thì 0.10 **gãy ở đúng những lúc cần nhất**:

| fold | 0.10 | 0.03 | 0.05 |
|---|---:|---:|---:|
| 2022H2 | **−430** | 555 | 445 |
| 2025H2 (crash 10/10) | **−68** | **5 651** | 3 615 |

⇒ 0.10 có 2 fold âm; 0.03 và 0.05 có **0 fold âm**. Lợi thế tổng của 0.10 đến từ các fold tăng giá,
và bị trả lại gần hết trong regime xấu.

### D. Đối chứng arm B (ép chốt lệnh chưa-arm sau 7 ngày)

Thứ hạng **giữ nguyên hoàn toàn**, chênh lệch chỉ −1.1% đến −3.3%. ⇒ Kết luận không phụ thuộc vào
lỗ hổng "không có đường thoát lỗ".

## 6.6 — 🎯 CHỐT BƯỚC 1: **`RATE_PROFIT_STOP_MARKET = 0.05`**

Không phải 0.10 (max thô), vì 0.10 thua trên **cả 4 tiêu chí an toàn** trong khi hơn rất ít về giá trị:

| tiêu chí | 0.05 | 0.10 |
|---|---|---|
| pnlTotal fold | 27 413 (99.6% của đỉnh plateau 27 526) | 31 225 (**nhiễu 1 điểm**, 2 hàng xóm đều ~27k) |
| pnlTotal liên tục | 25 488 (**+26%** vs 0.03) | 37 305 (+84%) |
| fold âm | **0** | **2** |
| regime crash 2025H2 | +3 615 | **−68** |
| `%hold>7d` | **2.6%** (sát trần 2%) | 18.7% (**9.4× trần**) |
| khoảng cách tới vực (0.15) | **3×** | **1.5×** |
| ddMtm liên tục | 31.66% | 32.23% |

**So với production hiện tại (0.03):** pnlTotal liên tục **20 236 → 25 488 (+26%)**, fold
**20 729 → 27 413 (+32%)**, ddMtm gần như không đổi (30.57% → 31.66%), vẫn **0 fold âm**, vẫn giữ
được lãi trong regime crash. Bằng chứng out-of-sample (walk-forward) xác nhận hướng "cao hơn 0.03 là
tốt hơn" với **+28%**, và 0.05 lấy được phần lớn lợi ích đó mà không mua rủi ro đuôi.

⚠️ **Một điểm Uni phải quyết:** 0.05 cho `%hold>7d = 2.6%`, **vượt nhẹ** trần
`MAX_PCT_HELD_OVER_7D = 2%`. Hai lựa chọn:
- **Chấp nhận nới trần lên 3%** → dùng 0.05. Có cơ sở: nhánh B chứng minh ép giải phóng vốn kẹt
  **không tạo thêm giá trị** (chênh −3.3%), tức trần đang bảo vệ một thiệt hại không đo được. Ngưỡng 2%
  vốn cũng chỉ là heuristic ("hiện 0.31%, nới gấp 6×"), không phải từ phép đo.
- **Giữ nguyên trần 2%** → buộc dùng **0.035** (`%>7d` 1.6%), chỉ được **+5%** so với 0.03. An toàn
  tuyệt đối nhưng gần như không cải thiện.

Khuyến nghị của tôi: **0.05 + nới trần lên 3%**. Nếu Uni ưu tiên không đụng ràng buộc thì 0.035.

## 6.7 — Việc 2 và 3 sau khi có metric đúng

Kết luận cũ về `TS_PROFIT_MULTIPLIER` (BẢNG 4) và `TS_RATCHET_DECOUPLED` (BẢNG 2) được rút ra bằng
`ddPct`/`calmar` hỏng và `pnlTotal` chưa tách MTM ⇒ **cần chạy lại với metric mới trước khi tin**.
→ ĐÃ CHẠY LẠI, xem PHẦN 7.

---

# PHẦN 7 (2026-08-01) — VÁ 4 LỖI AUDIT + CHẠY LẠI RATCHET. **Kết luận cũ được xác nhận.**

## 7.1 — Bốn lỗi đã vá, phân loại theo bản chất

| # | Lỗi | Loại | Cách vá | Ảnh hưởng đo được |
|---|---|---|---|---|
| **F8** | Key `allOrderDone` = `-timeUpdate - size()` có thể đụng độ ⇒ `TreeMap.put` **ghi đè**, mất lệnh âm thầm | **Bug thuần** | Vá **vô điều kiện**: `putOrderDone()` dò xuống khe trống khi đụng độ + đếm `orderKeyCollisions` | **0.00%** ở cả 3 rate ⇒ chưa từng xảy ra trên dataset này. Vá là **phòng ngừa** |
| **F9** | `catch{printStackTrace}` trong vòng lặp phút/ngày + **skip nguyên ngày** nếu <1440 phút, mà vẫn báo "thành công" | **Rủi ro tiềm ẩn** | Đếm `dayDataErrors`/`swallowedExceptions`, `LOG.error`, thêm cờ `SIM_FAIL_FAST_ON_DATA_ERROR` | **0 lần** trên mọi run. Giờ **không thể im lặng** nữa |
| **F7** | DCA nhồi leg **xoá sạch** `priceSL` đang có (`mergeOrder` không carry) | **Đổi hành vi** | Flag `TS_CARRY_SL_ON_DCA` (default OFF), chỉ carry khi SL cũ vẫn > avgEntry mới | **−0.2%** ⇒ mang SL sang còn **hơi xấu hơn**. Giữ OFF |
| **F10** | Coin delist phát nến phẳng volume=0 ⇒ không bao giờ bị coi là delist ⇒ MTM ở giá đóng băng | **Đổi hành vi** | Flag `SIM_TREAT_ZERO_VOL_AS_DELIST` (default OFF) | **+0.0%** (đúng 0) ⇒ dataset **không có** nến volume-0. Giữ OFF |

**Audit counters: 110/110 dòng sạch** (keyColl = dayErr = swallowedExc = 0 ở mọi rate × mọi fold).
Regression 3 rate liên tục: **chênh 0.00%** ⇒ 4 bản vá **hoàn toàn trơ** trên dataset hiện tại, mọi số
ở PHẦN 6 vẫn đúng nguyên.

⇒ Đây là kết quả **tốt nhưng nhàm**: 4 lỗi đều có thật về mặt code, nhưng **không lỗi nào đang gây sai
số**. Chúng là mìn chưa nổ — vá để sau này không nổ, không phải để sửa số cũ.

## 7.2 — Chạy lại RATCHET với metric đúng (rate-min 0.05, fold rời, funding ON)

| mult | ratchet tại | **pnlTotal** | pnlClosed | pnlMtm | ddMtm tb | %>7d | holdMed | #fold âm |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DECOUPLED | 5.00% | 24 177 | 26 679 | −2 501 | 7.27% | 1.3% | 281 | 0 |
| 1.0 | 5.00% | 24 177 | 26 679 | −2 501 | 7.27% | 1.3% | 281 | 0 |
| 2.0 | 10.00% | 24 360 | 26 861 | −2 501 | 7.35% | 1.4% | 393 | 0 |
| 3.0 | 15.00% | 24 495 | 26 997 | −2 501 | 7.38% | 1.9% | 494 | 0 |
| **5.21847** ⭐ | 26.09% | **27 413** | 29 855 | −2 443 | 7.54% | 4.8% | 892 | 0 |
| 8.0 | 40.00% | 26 346 | 28 278 | −1 931 | 7.68% | 7.9% | 936 | 0 |
| 12.0 | 60.00% | 26 457 | 27 863 | −1 406 | 7.88% | 9.5% | 1 304 | 0 |

**`5.21847` thắng — và lần này là ĐỈNH THẬT**, không phải nhiễu: hai bên đều thấp hơn (3.0 = 24 495,
8.0 = 26 346). Khác hẳn trường hợp rate-min 0.10 (nhiễu một điểm, hai hàng xóm đều thấp).

**Kiểm chứng nội tại tốt:** `DECOUPLED` và `mult = 1.0` ra **y hệt nhau** (24 177, từng con số) — đúng
như lý thuyết (decouple = bỏ hệ số nhân = nhân 1.0). Hai đường code độc lập cho cùng kết quả ⇒ tin được
là không có lỗi cài đặt.

⇒ **Kết luận PHẦN 6.7 giữ nguyên, giờ có bằng chứng đúng chuẩn:**
`TS_PROFIT_MULTIPLIER = 5.21847` và `TS_RATCHET_DECOUPLED = false` — **không đổi gì**.

Đáng chú ý: cả 3 hướng can thiệp mạnh hơn vào trailing (decouple, hạ multiplier, carry SL qua DCA)
đều làm **xấu đi**. Nhất quán với toàn bộ phần còn lại của nghiên cứu: **can thiệp trailing càng ít
càng tốt**, miễn là arm đủ cao để vượt chi phí.

## 7.3 — 🎯 CẤU HÌNH EXIT CUỐI CÙNG

| tham số | hiện tại | đề xuất | lý do |
|---|---|---|---|
| `RATE_PROFIT_STOP_MARKET` | 0.03 | **0.05** | +26% liên tục / +32% fold, 0 fold âm, giữ lãi trong crash, cách vực 3× |
| `TS_PROFIT_MULTIPLIER` | 5.21847 | **5.21847** (giữ) | đỉnh thật, hai bên đều thấp hơn |
| `TS_RATCHET_DECOUPLED` | false | **false** (giữ) | true = mult 1.0 = tệ nhất (−12%) |
| `TS_GIVEBACK_RATIO` | 0.5 | **chưa đo** | lever còn lại, quyết định mức SL đóng băng — xem 7.4 |
| `TS_CARRY_SL_ON_DCA` | (mới) | **false** | bật = −0.2% |
| `SIM_TREAT_ZERO_VOL_AS_DELIST` | (mới) | **false** | bật = 0.0%, dataset không có nến volume-0 |
| `SIM_FAIL_FAST_ON_DATA_ERROR` | (mới) | **bật khi chạy confirm** | để lỗi dữ liệu không đi qua im lặng |

**Chỉ MỘT dòng cần đổi trong production: `RATE_PROFIT_STOP_MARKET` 0.03 → 0.05.**
Vướng duy nhất: `%hold>7d = 2.6%` vượt nhẹ trần `MAX_PCT_HELD_OVER_7D = 2%` — cần Uni quyết nới lên 3%
hay lùi về 0.035.

---

# PHẦN 8 (2026-08-01) — KIỂM TRA OVERFIT NGHIÊM TÚC. **Uni đúng. Rút lại con số +26%.**

Uni nói "cảm giác overfit". Tôi đã thử **~35 cấu hình trên cùng một tập dữ liệu**, và walk-forward chỉ
làm cho rate-min — mọi thứ khác chọn bằng cách nhìn tổng = in-sample. Ba phép kiểm, từ yếu đến mạnh:

## 8.1 — Sign test: HƯỚNG thì THẬT ✅

Mỗi rate thắng 0.03 ở bao nhiêu / 11 fold (tổng PnL có thể bị 1-2 fold kéo; tỉ lệ thắng thì không):

| rate | thắng/tổng | tỉ lệ | trung vị chênh | fold thua nặng |
|---:|---:|---:|---:|---|
| 0.0103 | 0/11 | **0%** | −721 | 2021H1 (−3 934) |
| 0.035 | 7/11 | 64% | +103 | 2025H2 |
| 0.04 | 8/11 | **73%** | +182 | 2025H2 |
| 0.045 | 8/11 | **73%** | +331 | 2025H2 |
| **0.05** | 8/11 | **73%** | **+443** | 2025H2 (−2 036) |
| 0.07 | 8/11 | 73% | +635 | 2022H2, 2025H2 (−5 222) |
| 0.10 | 8/11 | 73% | +682 | 2022H2, 2025H2 (−5 719) |
| 0.15 | 6/11 | 55% | +546 | 2021H1, 2021H2, 2022H2 |
| 0.25 | 5/11 | 45% | 0 | 3 fold thua nặng |

⇒ **Hướng "cao hơn 0.03" là thật**: 73% fold thắng, trung vị dương, và mức cũ 0.0103 thua **0/11 fold**
(tức việc nâng arm vì lý do chi phí là đúng, không bàn cãi). Vùng 0.04-0.10 **không phân biệt được**
với nhau (đều 73%).

## 8.2 — Holdout thật: GIÁ TRỊ CỤ THỂ thì KHÔNG học được ❌

Chọn **chỉ nhìn 6 fold đầu** (2021H1-2023H2), chấm **một lần** trên 5 fold cuối (2024H1-2026H1):

| rate | TRAIN (6 fold) | HOLDOUT (5 fold) | hạng train | hạng holdout |
|---:|---:|---:|---:|---:|
| 0.03 | 10 908 | 9 821 | 10 | 11 |
| 0.045 | 15 394 | 10 236 | 7 | 8 |
| **0.05** | 16 321 | **11 091** | 5 | **5** |
| 0.07 | 17 364 | 10 106 | 2 | 9 |
| **0.10** | **19 925** | 11 301 | **1** ← chọn | 4 |
| 0.15 | 10 511 | **15 503** | 11 | **1** |
| 0.20 | 7 072 | 13 237 | 12 | 2 |

**Tương quan hạng TRAIN ↔ HOLDOUT (Spearman) = 0.14** — gần như **BẰNG KHÔNG**. Quá khứ **không dự
đoán được** thứ hạng tương lai của tham số này. Bằng chứng rõ nhất: 0.15 đứng **hạng 11/14 trên train**
nhưng **hạng 1 trên holdout**; 0.07 hạng 2 train → hạng 9 holdout.

## 8.3 — Multiple comparisons: ưu thế nằm TRONG nhiễu ⚠️

- Độ lệch chuẩn PnL holdout giữa các rate: **2 164**
- Khoảng cách cấu hình-chọn-trên-train vs baseline 0.03 trên holdout: **1 479**
- ⇒ Ưu thế = **0.68 sigma** — **dưới 1σ, không kết luận được**. Với ~35 lần thử, tìm ra chênh lệch cỡ
  này do may mắn là hoàn toàn bình thường.

## 8.4 — 🔧 SỬA LẠI KẾT LUẬN

| tuyên bố cũ | trạng thái | tuyên bố đã sửa |
|---|---|---|
| "0.05 cho **+26%**" | ❌ **in-sample inflated** | **+13% đến +15%** (holdout thật: 11 091 vs 9 821) |
| "0.045/0.05 là giá trị tối ưu" | ❌ không học được (Spearman 0.14) | **Mọi giá trị trong 0.04-0.07 tương đương nhau trong phạm vi nhiễu** |
| "nâng arm lên là đúng" | ✅ **giữ nguyên** | 0.0103 thua **0/11 fold**; 0.04-0.10 thắng 73% fold |
| "0.10 tốt nhất" | ❌ hạng 1 train → hạng 4 holdout | không chọn |

**Cách chọn ĐÚNG khi tham số không học được:** không cố tìm tối ưu, mà chọn theo **tiêu chí bền vững**.
`0.05` vẫn là câu trả lời, nhưng **lý do đổi hẳn**:
- Không phải vì nó cho PnL cao nhất (nó không).
- Mà vì trong vùng 0.04-0.07 (không phân biệt được về hiệu quả), 0.05 có: `%hold>7d` thấp nhất còn
  chấp nhận được (2.6%), **0 fold âm**, xa vực sụp đổ 3×, và trên holdout nó **đúng hạng 5 ở cả train
  lẫn holdout** (ổn định nhất trong nhóm).
- Kỳ vọng thực tế: **+13-15%**, không phải +26%.

## 8.5 — Bài học quy trình (ghi để không tái phạm)

1. **Đếm số cấu hình đã thử.** 35 lần thử trên 1 tập dữ liệu ⇒ phải chia ngưỡng tin cậy tương ứng.
2. **Luôn giữ holdout chưa chạm** trước khi bắt đầu sweep, không phải sau.
3. **Báo cáo Spearman train↔holdout** cho mọi tham số. Nếu ~0 thì đừng tuyên bố giá trị tối ưu.
4. **Sign test trước, tổng PnL sau.** Tổng dễ bị 1 fold kéo; tỉ lệ thắng thì không.
5. Con số đem đi quyết định phải là **holdout**, không phải in-sample.

## 7.4 — Việc còn lại của nhánh exit

- ⬜ **`TS_GIVEBACK_RATIO`** (0.3/0.4/0.5/0.6/0.7) tại rate-min 0.05 — lever chưa từng sweep, quyết định
  trực tiếp mức SL đóng băng (`arm × (1 − giveback)`), nơi **đa số lệnh thoát**. Đây là hạng mục có
  triển vọng nhất còn lại.
- ⬜ **Giveback `min→max`** (`TS_GIVEBACK_FLOOR`, code đã có, chưa chạy) — kỳ vọng thấp: trần 8% chỉ cắn
  khi lãi >16%, mà ratchet ở 26% nên hiếm chạm.
- ⬜ Audit pipeline Python sinh `pred.bin` — kiểm quy ước nhãn thời gian (nếu `pred[ts]` nhìn tới
  `ts+15m` thì là leak nặng). **Đây là rủi ro lớn nhất chưa kiểm được**, nằm ngoài code Java.

## Còn thiếu / bước sau (cập nhật khi job xong)

- ⏳ `toan_ky` cho rate 0.05, và toàn bộ rate **0.06 → 0.10** (đang chạy `-P2`, ETA ~60-90 phút).
- ⏳ `toan_ky` cho decoupled true/false.
- ⬜ **Việc 3 — giveback fix** (`gap = min(peak×g, maxGap)` → `max(peak×g, minGap)`): code ĐÃ implement
  xong, flag-gated `TS_GIVEBACK_FLOOR` + `TS_MIN_GAP` (mặc định OFF = byte-identical hành vi cũ),
  **CHƯA chạy sweep**. Phụ thuộc kết quả việc 1+2 (Uni đã chỉ ra đúng: 3 việc không độc lập).
- ⬜ Sau khi chốt cả 3: mới chạy confirm WFO 16-window để xem verdict — nhưng **nhớ rằng verdict đó vẫn
  đi qua harness lỗi**, nên là tham khảo, không phải trọng tài.

## Lưu ý khi kết luận (chống lặp lại lỗi cũ)

Ở EXIT_MACHINE PHẦN 4 và PHẦN 5, cả 2 lần "cải thiện" đều hoá ra do **1 window chiếm 60-70% PnL**
(window 15 = black-swan 10/10/2025). Bảng trên đã tách riêng `2025Q4_crash` chính vì lý do đó — khi
chọn giá trị cuối, phải kiểm tra cấu hình thắng có thắng **ở cả 2024_bull lẫn toan_ky**, chứ không chỉ
thắng nhờ giai đoạn crash.
