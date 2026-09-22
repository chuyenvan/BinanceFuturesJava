# PREREG_REVERSAL_BOUNCE — đo edge "reversal-bounce long" (tổng quát hóa `isBtcTrendReverse`)

Chốt: 2026-09-22, **TRƯỚC khi chạy bất kỳ phép đo nào**. Commit file này phải có TRƯỚC mọi
commit kết quả. Nếu thứ tự commit ngược → toàn bộ kết quả bị coi là **VOID**.

Phạm vi dữ liệu: **DEV trọng điểm** 2022-01-01 .. 2024-06-30 (khớp WFO DEV). Bổ sung đối chiếu
trung thực 2021 và 2024-07..2025-12-31. **KHÔNG chạm HOLDOUT 2026.**

Nguồn gốc: `docs/SURVEY_OLDCODE_SIGNALS.md` mục 5 SHORTLIST "GO — Reversal-bounce long",
`/home/ubuntu/trend_review/REVIEW_OLD_ERA_METHODS.md` mục 4 (`isBtcTrendReverse`), code gốc
`MarketBigChangeDetector.isBtcTrendReverse`.

---

## 0. Mục tiêu + tiên lượng ghi trước (không sửa sau khi thấy số)

Hỏi: tín hiệu **reversal-bounce long** (sau một chân giảm, long khi giá bật lên vượt mốc
đáy-đảo) có edge dương **sau phí** trên DEV không, và nó có **độc lập thời gian với MOM15**
không (fire ở ngày MOM15 im).

Tiên lượng ghi trước: **nhiều khả năng NO-GO**. Lý do (từ SURVEY + REVIEW):
1. `isBtcTrendReverse` gốc là thủ tục **FIT** (vòng `while` hạ ngưỡng 0.0005/bước cho đến khi
   bắt được dip) — "đo bằng vòng lặp nới ngưỡng" gần như luôn TRUE, không phải detector. Ta bỏ
   vòng lặp, dùng **1 ngưỡng cố định** (xem §1).
2. Mean-reversion bounce ngắn hạn thường bị **chi phí** (taker fee + slippage) ăn hết edge thô.
3. Về pha thì độc lập MOM15 (MOM15 fire lúc đang-rơi, reversal fire lúc đảo-lên), NHƯNG các cược
   vẫn **cụm quanh cùng các đợt selloff** → ICC theo episode có thể chỉ giảm vừa, không về 0.
   Phải đo overlap/ICC trước khi tin là "độc lập thật" (CAVEAT trung thực của SURVEY).

---

## 1. TRIGGER — tham số hóa, 1 ngưỡng CỐ ĐỊNH (không vòng lặp nới ngưỡng)

Dữ liệu: close/high/low/open 1M per-symbol (nguồn §3). Mốc "15m-aligned" = nến có
`epoch_minute % 15 == 14` (nến đóng của block 15 phút) — khớp `getCurrentMinute % 15 == 14`
của code gốc.

Với mỗi mốc 15m-aligned `j` (có đủ 30 nến quá khứ `j>=29`):

- `max15(j) = max( high[j-14 .. j] )` — đỉnh cửa sổ 15 phút.
- `max30(j) = max( high[j-29 .. j] )` — đỉnh cửa sổ 30 phút.
- `drop15(j) = close[j]/max15(j) - 1`, `drop30(j) = close[j]/max30(j) - 1`.
- `drop(j) = min(drop15, drop30)` — mức sụt nặng hơn.
- **Điều kiện chân giảm:** `drop(j) <= -DROP_THRESH`.

Tham số CỐ ĐỊNH (khóa, không tune):
- `DROP_THRESH = 0.01` (1.0%). Lý do: = `BTC_TREND_REVERSE_RATE_MAX` gốc (ngưỡng "thật" trước
  khi vòng lặp FIT hạ dần xuống 0.006). Một chân giảm ≥1% trong 15/30 phút là "leg down" có nghĩa.
- Mốc đảo `priceReverse(j) = open[j-14]` (giá mở của block 15 phút — mốc "đáy-đảo").
- **Bounce fire:** long tại nến đầu tiên `t > j` có `close[t] > priceReverse(j)` (vượt lên qua
  mốc đáy-đảo). Vì quét tới theo thời gian và reset anchor sau mỗi lần fire, điều kiện "lần
  vượt ĐẦU TIÊN" (không có nến trung gian `close >= priceReverse`) được đảm bảo tự động.
- Nếu một chân giảm mới (mốc 15m-aligned khác, `drop <= -DROP_THRESH`) xuất hiện khi anchor cũ
  chưa bounce → **cập nhật anchor mới** (mốc gần nhất — khớp "most recent" của code gốc).

Khác biệt với code gốc (ghi rõ để minh bạch): code gốc dùng **high nến đơn** tại `j-29`/`j-14`
(chứ không phải max cửa sổ) — REVIEW đã gắn cờ indexing này "mong manh". Ta dùng **max cửa sổ
15/30m** (đúng tinh thần "cửa sổ 15/30m" và đúng gợi ý redefinition của REVIEW: "dip >= X% từ
đỉnh 30m trong N phút rồi close hồi phục >= Y"). Đây là **lựa chọn thiết kế chủ động**, ghi
trước, không đổi sau khi thấy số.

Universe: **toàn bộ symbol USDT perp** có file 1M trong nguồn (627 symbol, gồm cả coin đã delist
— không lọc survivorship, để trung thực). Mở rộng từ `specialSymbol` (BTC) → cross-section.

---

## 2. HOLD + PnL (giống FORCED_SELLER để so táo-với-táo)

- Entry = `close[t]` (nến bounce đã đóng — causal).
- **HOLD cố định 24h** = 1440 phút. Exit = close tại phút `t+1440`.
- Nếu symbol hết dữ liệu trước `t+1440` (delist) → exit tại nến cuối có dữ liệu, đánh dấu
  `short_delist` (giữ lại, KHÔNG loại — đo tác động delisting riêng).
- Censoring: nếu `t+1440` vượt quá cuối dải dữ liệu → loại khỏi mẫu (edge-censored).

**Chi phí (sau phí):**
- Taker fee: `0.0005 * 2 = 0.10%` (mở + đóng).
- Slippage: `0.5 * (high[t] - low[t]) / entry` (nửa biên độ nến 1m lúc entry).
- Funding: tổng funding rate trong thời gian giữ (nguồn Aerospike `funding_data`, per-symbol,
  8h cadence) — cộng/trừ vào net.
- `net_ret = raw_ret - fee - slip - funding` (dấu theo chiều long: funding dương là trả phí).

---

## 3. Nguồn dữ liệu 1M closes (causal, leak-free)

- **Aerospike set `kline_1m_opt`** (host 127.0.0.1:3222), key `YYYYMMDD-HHMM` (GMT+7), value =
  protobuf nén Snappy chứa `{symbol: [open, high, low, close, totalUsdt]}` per-phút. Đây là
  **cùng nguồn** mà BD/MOM15 dùng (SURVEY §1). Chỉ dùng nến **đã đóng** (`epoch_minute` của
  phút trước), không có nến in-progress → **causal**.
- Đã extract thuần Python (client `aerospike` + `cramjam`) thành `raw/<sym>.f32` (mỗi dòng 24
  byte: `int32 epoch_minute, float32 O/H/L/C/V`), 627 symbol, 619M dòng, dải 2021-01-01 ..
  2025-12-31 (UTC). Script extract ngoài git (`/home/ubuntu/claudedata/rvb_extract2.py`); script
  đo trong repo chỉ đọc `raw/*.f32`, không ghi Aerospike.
- Causal check: fire dùng `close[t]` của nến đã đóng; không dùng dữ liệu tương lai.

---

## 4. MOM15 — định nghĩa (để tính overlap) + overlap/ICC

**MOM15** (định nghĩa từ SURVEY §1 + code `getMarketStatus1M`): tín hiệu breadth cross-sectional
`rateDown15MAvg` = trung bình của **100 symbol sụt sâu nhất** theo `(close - max15m)/max15m`
(= `calRateChangeAvg(rateMax2Symbols, 100)`). "MOM15 fire" = `rateDown15MAvg < -0.028`
(ngưỡng `SMALL_DOWN_15M` — bản live của MOM15, SURVEY §2 "= MOM15 live").

Cách đo overlap (2 tầng, cùng báo):
1. **Tầng phút (primary, causal):** tính `rateDown15MAvg` từ chính `raw/*.f32` (tự túc, không
   phụ thuộc sim) trên lưới 15m; với mỗi fire, xác định MOM15 có đang fire (`< -0.028`) tại mốc
   15m gần nhất trước fire không.
2. **Tầng ngày (đối chiếu, khớp "ngày MOM15 im" của SURVEY):** `printDone.csv` run C2b DEV
   (`/home/ubuntu/java/devrun/C2b/storage/printDone.csv`, 970 lệnh) — ngày MOM15 **có giao dịch**
   vs ngày MOM15 **im**. Đếm % fire rơi vào ngày MOM15 im + % fire trùng (symbol, ngày) với lệnh MOM15.

**ICC** (intra-class correlation) của `net_ret` cụm theo ngày entry: công thức một chiều chuẩn
`ICC = (MSB - MSW) / (MSB + (k0-1)*MSW)`. Báo thêm ICC theo episode 72h.

Điều kiện TIÊN QUYẾT (SURVEY §5): nếu fire gần trùng MOM15 (overlap cao) → **NO-GO dù edge dương**.

---

## 5. Phép đo thống kê (khóa trước khi chạy)

- **Headline:** `mean(net_ret)` trên DEV, hit-rate = `P(net_ret > 0)`.
- **Null test:** permutation test — hoán vị nhãn forward-return theo **khối** (block permutation,
  block = 72h episode), 2000 lần, so phân phối null của `mean(net_ret)` với giá trị thực.
- **CI:** block-bootstrap (circular moving-block, **block = 72h**), **2000 rep**, **seed
  20260905**, lấy percentile 2.5/97.5 rồi **nới ×1.21** (CI inflate — đúng chuẩn đã dùng trong
  repo). Báo `p(mean>0)`.
- **Decay theo năm** (2021..2025) để phát hiện sign-flip / không ổn định.
- **%coin+**: tỷ lệ symbol có `mean(net_ret) > 0` (≥1 / ≥5 / ≥10 trade).

---

## 6. GATE GO/NO-GO (tầng sau)

GO (tăng tầng sau) khi **ĐỒNG THỜI**:
1. `mean(net_ret) > 0` trên DEV, và CI block-72h ×1.21 **loại 0** (`p(mean>0)` cao, CI95 không
   chứa 0 theo chiều âm).
2. ICC theo episode **đủ thấp** (không cụm quá mạnh — không phải vài episode quyết định toàn bộ).
3. **Overlap MOM15 thấp** — phần lớn fire rơi vào ngày MOM15 im (độc lập thời gian thật).

Không đạt bất kỳ điều nào → **NO-GO**, ghi rõ nguyên nhân. Không thêm biến thể, không đổi
ngưỡng, không nới cửa sổ sau khi thấy số (chống leak L2 / multiple-comparison).
