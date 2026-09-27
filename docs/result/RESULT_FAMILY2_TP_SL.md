# RESULT_FAMILY2_TP_SL — HỌ MỚI #1 (TP nhỏ + SL nhỏ, KHÔNG DCA): **BLOCKER — KHÔNG CHẠY ĐƯỢC**

Pre-reg: `docs/prereg/PREREG_FAMILY2_TP_SL.md` — **chốt TRƯỚC** (điều kiện ABORT §3).
Nhánh `module`. **KHÔNG push.** **KHÔNG sửa code.** **0 sim** (không có arm nào chạy được).

## 0. PHÁN QUYẾT
**BLOCKER**: sim (và cả đường LIVE) **KHÔNG có công tắc TP cố định**, và **KHÔNG có cách tắt arm/trailing
mà vẫn còn đường thoát cho lệnh thắng**. Đường thoát thắng **DUY NHẤT** là **trailing SL đã arm ở `armRate`**.
⇒ Họ mới **"TP nhỏ + SL nhỏ, bỏ máy sinh-đuôi" KHÔNG dựng được trên engine hiện tại** ⇒ **vòng này KHÔNG THỂ LÀM**
(theo đúng điều kiện ABORT đã chốt trước, `PREREG §3`). **KHÔNG tự ý viết lại state machine.**

## 1. CÔNG TẮC TÌM ĐƯỢC (VIỆC 0) — `file:line` · đơn vị · mặc định
| # | việc | key | field (`file:line`) | env | đơn vị | mặc định |
|---|---|---|---|---|---|---|
| i | ngưỡng ARM | `SIM_RATE_PROFIT_STOP_MARKET` | `Configs.RATE_PROFIT_STOP_MARKET` `Configs.java:169` | `:842` | rate; arm khi `peak≥entry·(1+arm)` | `0.03f` · profile `x1_gs_t170`=`0.07` |
| ii | **TP cố định** | — | **KHÔNG TỒN TẠI** | — | — | **KHÔNG CÓ** |
| iii | SL cứng pre-arm | `SIM_PRE_ARM_SL` | `Configs.PRE_ARM_SL` `Configs.java:455` | `:849` | âm; `-0.01`=−1 % trên `firstEntryPrice` | `0f`=TẮT |
| iv | DCA OFF | `WFO_DISABLE_DCA=1` | `Configs.WFO_DISABLE_DCA` `Configs.java:338` | env | bool | `false` |
| v | time-box lỗ | `SIM_LOSER_TIME_STOP_HOURS` | `Configs.LOSER_TIME_STOP_HOURS` `Configs.java:442` | `:846` | giờ (int) | `0`=TẮT · profile=`168` |
| — | ratchet trailing | `SIM_TS_GIVEBACK` (phải `=1`) | `Configs.java:900-903` | — | bool (đường cũ đã xóa) | — |
| — | tỉ lệ nhả đỉnh | `TS_GIVEBACK_RATIO` | `Configs.java:173` | env | rate | `0.5f` |
| — | gate look-ahead | — | `Configs.BLOCK_INTRABAR_LOOKAHEAD` `Configs.java:122` | — | bool | **`true`** |

**Chứng cứ cơ chế (chỉ đường thoát):** `SimulatorMarketLevelTicker1MStopLoss.java:1049` arm=`RATE_PROFIT_STOP_MARKET`;
`:1054` arm khi `peak≥entry·(1+arm)`; `:1057` `updateStatusNew`; `:1058-1060` đóng chỉ khi
`TAKE_PROFIT_DONE|STOP_LOSS_DONE|STOP_MARKET_DONE`; `:1062` ngược lại `updateTPSL` (ratchet).
`OrderTargetInfoTest.java:185-243`: sau arm **chỉ đặt SL trailing**; `TAKE_PROFIT_DONE` (`:206`) nằm **sau**
`if (BLOCK_INTRABAR_LOOKAHEAD) return;` ⇒ **BẤT HOẠT**. Các điểm gán `priceTP` (`:1000` PRE_ARM_SL ·
`:1025` LOSER_TS · `:1042` COND_EXIT · `:551` đóng cuối kỳ · `:892` de-list · `:1091` propagate) = **SL/time-stop,
KHÔNG có mốc lãi**. `DumpConfig.java:71-72`: *"Trailing: đường DUY NHẤT…"*. Quét mọi key `SIM_*`: **không có key TP**.
⇒ Đặt `armRate` lớn = lệnh thắng **không bao giờ đóng** (không phải TP nhỏ); đặt `armRate` nhỏ = **vẫn trailing của HỌ cũ**.

## 2. BẢNG ARM — **RỖNG (VOID)**
Không arm nào chạy (không có công tắc TP). Cột số liệu **N/A** cho N1..N4.
| arm | cấu hình | n · entry/tháng · CAGR · maxDD · UW · qmin · conc · `%top-1` · `TF50` · `asym` · `sign%` · `q*` | (a) | (b′) |
|---|---|---|---|---|
| **N0** | baseline `cd-sel15` (DÙNG LẠI) | 744 · 13,77 · +17,29 % · −6,27 · 166 · −3,36 · 6,77 · 19,13 · −17.551 · 3,375 · 88,44 (từ `RESULT_SHAPE1_EARLY_CUT`) | FAIL | FAIL |
| N1..N4 | arm/trailing OFF + TP… + DCA OFF | **VOID — không thực thi được (BLOCKER §1)** | — | — |

## 3. PARITY
**Không sửa code** ⇒ **không cần parity lại**. md5 giữ nguyên: KEEPLEG0 `99e42b75cf1a2142f9cd14dc72e371ba` ·
T170 `efb793e2468ca3a7318da0f0ad23d4fc` (khớp `RESULT_EXIT_STRUCT` §0). ⇒ **PASS (không đổi).**

## 4. TRẢ LỜI (bắt buộc)
1. **Arm nào PASS (a) VÀ (b′)?** **KHÔNG arm nào** — **0 arm chạy được** (BLOCKER). Không có số để đối chiếu.
2. **`asym` từng arm — có cái nào <1 mà PnL dương?** **Không đánh giá được** (không arm). *Trạng thái đã biết*:
   trong HỌ cũ `asym<1` **luôn kèm lỗ** (`RESULT_GROSS_ASYMMAP`: 32 run asym<1 đều fail; cấu trúc kéo asym xuống =
   win-rate thấp + cắt lỗ sớm + `loss_mean` nhỏ). **Câu hỏi trung tâm vẫn CHƯA trả lời được** vì engine thiếu TP.
3. **Arm/trailing OFF có làm `%top-1` giảm mạnh?** **Không test được.** Lưu ý cơ học: "tắt arm" bằng `armRate→∞`
   làm **lệnh thắng không đóng** ⇒ `%top-1` sẽ **tệ/không xác định**, KHÔNG phải "giảm mạnh" như kỳ vọng.
4. **Kết luận — họ mới khả thi?** **Chưa thể kết luận NULL** (chưa chạy được 1 arm nào). Đây là **BLOCKER công cụ**,
   KHÔNG phải kết quả khoa học. **Bước tiếp (đề xuất, cần owner duyệt vì đụng state machine):**
   - **(A) Thêm nhánh TP cố định** vào `startUpdateOldOrderTrading`/`updateStatusNew`: key `SIM_TAKE_PROFIT_RATE`
     (mặc định `0`=OFF ⇒ byte-identical) — thoát `min(stop, open)`/`min(exitPrice, open)` khi `peak ≥ entry·(1+TP)`.
     Đây là **1 nhánh mới**, KHÔNG viết lại state machine; kèm **cổng parity OFF = y nguyên** (bắt buộc).
   - **(B) Không đụng code:** đổi **nhãn train** mục tiêu nhỏ (horizon ngắn) / đổi **khung thời gian** / đổi **cách
     chọn coin** — tìm họ "PnL không phụ thuộc đuôi" từ phía tín hiệu thay vì phía thoát.

## 5. GHI CHÚ RÀNG BUỘC
0 sim Oracle; không chạm production/242/ONNX/`NUM_FEATURES`/`extractFeatures45`/LIVE; DEV ≤ 2025-12-31;
không chạm 2026; KHÔNG push git. Số N0 lấy nguyên từ `RESULT_SHAPE1_EARLY_CUT` (không đo lại).
