# RESULT_BD_DEEP_STEER — kiểm chứng STEER owner 2026-10-01 11:32 ("đổi `rateDown15MAvg` từ MAX → HIGH")

> **PHẦN NÀY LÀ STEER CỦA OWNER (11:32)**, không phải tự đề. Nguyên văn:
> *"thử đổi cách tính của DownAvg15M thay max thành high rồi apply lại vào xem G2 + flat3 thế nào.
> vì cái này nó sẽ nhỏ đi nên có thể nới các ngưỡng liên quan tới nó"*.
>
> Thực hiện 2026-10-01, nhánh `module`. Pre-reg gốc: `docs/prereg/PREREG_BD_DEEP.md` (`2536c43c`).
> **0-sim thuần Python**, KHÔNG chạy Java, KHÔNG chạm 242, KHÔNG chạm 2026, **KHÔNG sửa `.java`**.

---

## 0. KẾT QUẢ CHỐT (đọc trước)

> ### ⚠️ **KHÔNG CÓ GÌ ĐỂ ĐỔI — CODE ĐÃ LÀ `MAX(HIGH)` TỪ TRƯỚC.**
> `rateDown15MAvg` **hiện tại đã** = trung bình 100 coin có `close / (HIGH cao nhất của 15 nến 1M) − 1`
> âm nhất. Biến `symbol2PriceMax` **lấy từ `kline.maxPrice`**, mà `maxPrice` trong
> `KlineObjectSimple` = **HIGH của nến** (không phải close-max).
> ⇒ Đổi "max → high" đúng như steer **là NO-OP**: parity **byte-identical**, `G2 + FLAT3` **không đổi**,
> **KHÔNG cần sim Kaggle**, **KHÔNG cần nới ngưỡng**, **KHÔNG sửa `.java`**.
>
> **Nguồn nhầm:** tên field `maxPrice` **trùng chữ "max"** khiến dễ đọc thành "max của close".
> Nó là **HIGH**. Muốn "đổi max → high" thì phải hiểu là "đổi **close-max → high-max**", tức là đi từ
> trạng thái **KHÔNG tồn tại trong repo** về trạng thái **đang chạy**.

---

## 1. BẰNG CHỨNG 4 LỚP (file:line)

### 1.1 `KlineObjectSimple` — `maxPrice` = HIGH, `minPrice` = LOW

`src/main/java/com/binance/chuyennd/object/sw/KlineObjectSimple.java:36-42`:
```java
result.priceOpen  = Float.valueOf(kline.get(1).toString());
result.maxPrice   = Float.valueOf(kline.get(2).toString());   // index 2 = HIGH
result.minPrice   = Float.valueOf(kline.get(3).toString());   // index 3 = LOW
result.priceClose = Float.valueOf(kline.get(4).toString());   // index 4 = CLOSE
```
(kline Binance chuẩn = `[openTime, open, high, low, close, vol, closeTime, quoteVol, ...]`.)

**Kiểm chứng số (100% = chứng minh `maxPrice` là HIGH):** trên `ticker_20241026.bin.gz`,
**93 600/93 600 dòng** thoả `maxPrice ≥ max(open, close)` và `minPrice ≤ min(open, close)` — tức
**100,0000 %**. (Nếu `maxPrice` là close-max thì tỉ lệ này sẽ ~0 ở nến giảm.)

### 1.2 **TẤT CẢ 6 nơi** dựng `symbol2PriceMax` / `symbol2Max15m` — đều lấy `kline.maxPrice`

| # | file:line | biểu thức |
|---|---|---|
| 1 | `ai_ml/features/export/MarketDataInlineGenerator.java:79` | `priceMax = (priceMax == null) ? kline.maxPrice : Math.max(priceMax, kline.maxPrice);` |
| 2 | `research/ExportMarketData2File.java:118` | `priceMax = Math.max(priceMax, kline.maxPrice);` |
| 3 | `trading/DetectEntrySignal2TradeNormal.java:242` (LIVE) | `if (priceMax == null \|\| priceMax < kline.maxPrice) priceMax = kline.maxPrice;` |
| 4 | `ai_ml/validation/consistency/ProductionVsBacktestDataComparator.java:207` | `if (k.maxPrice > maxP) maxP = k.maxPrice;` |
| 5 | `…/ProductionVsBacktestFeatureComparator.java:272` | 〃 |
| 6 | `…/ProductionVsBacktestFundingComparator.java:261` | 〃 |

Consumer: `tradecore/MarketBigChangeDetector.java:77-80` (`Float maxPrice = symbol2PriceMax.get(symbol);`
→ `rateMax2Symbols.put(rateOf2Double(ticker.priceClose, maxPrice), symbol)`), dòng này **có từ 2025-09-28**
(`git blame` → `d484bff0`). **KHÔNG có đường nào dùng close-max.**

### 1.3 PARITY với chính tín hiệu sim đã chạy (`market.bin`)

| biến thể | `%` phút lệch < 1e-3 (cả ngày) | **sau 15 phút warm-up** | max\|Δ\| (sau warm-up) |
|---|---|---|---|
| **HIGH-max (code hiện tại)** | 99,2 % | **100,00 %** | **0,0002** (nhiễu float32) |
| CLOSE-max (biến thể "đổi thành close") | 41,0 % | (không khớp) | — |

Ví dụ ngày sập 2025-10-11: HIGH-max sau warm-up **100,00 % < 1e-3, max 0,0002**; CLOSE-max **không** khớp.
⇒ `market.bin` (nguồn sim đọc) **được sinh bằng HIGH-max** ⇒ khẳng định trên là sự thật đo được, không phải suy đoán.
(Chênh lệch "cả ngày" 99,2 % so với 96,7 % ở mẫu 100 ngày là **do cold-start đầu ngày** khi tái lập offline —
buffer 15 nến bị reset mỗi ngày, còn exporter giữ buffer liên tục.)

### 1.4 Hệ quả theo đúng lập luận của steer

Steer viết: *"high ≥ close ⇒ close/high − 1 ≤ close/close_max − 1 ⇒ rateDown15MAvg ÂM HƠN / LỚN HƠN về
độ lớn ⇒ BIG_DOWN và DCA sẽ BẬT NHIỀU HƠN"*. **Lập luận ĐÚNG — nhưng nó đã đang xảy ra**: trạng thái
hiện tại (HIGH-max) chính là trạng thái "bật nhiều hơn". Vế trái (`close/close_max`) **chưa từng tồn tại**.

---

## 2. VẪN ĐO COUNTERFACTUAL NGƯỢC (HIGH → CLOSE) — để trả lời "nới ngưỡng bao nhiêu"

Đo trên **cùng mẫu 100 ngày** (tất cả 56 ngày BIG_DOWN + 44 ngày thường, seed 20261001), N=100, WIN=15,
ngưỡng −0,03157. `research/analysis/bd_deep_steer.py` → `RESULT_BD_DEEP_steer.json`.

| | HIGH-max (**đang chạy**) | CLOSE-max (biến thể ngược) |
|---|---|---|
| phút DCA ON | **1 916** | 1 495 (**−21,96 %**) |
| episode | 260 | — |
| mean series | −0,007857 | (nhẹ hơn) |
| Jaccard vs HIGH | 1,00 | **0,78** |
| corr(HIGH, CLOSE) | — | 0,990 |
| **tắt** (ON→OFF) | — | **421 phút** |
| **bật thêm** (OFF→ON) | — | **0** |

- **0 phút "bật thêm"** ⇒ `CLOSE-max ON ⊂ HIGH-max ON` (đúng toán học) ⇒ kiểm tra tự-nhất-quán PASS.
- Muốn CLOSE-max giữ **đúng 1 916 phút ON** như HIGH-max@−0,03157 thì ngưỡng phải **nới từ −0,03157 →
  −0,02752** (lệch **+0,00405**, tức nới ~13 % về độ lớn).
- Nhưng chiều đang chạy là **HIGH-max**, nên **câu hỏi "nới ngưỡng" KHÔNG có cơ sở** để đặt ra.

---

## 3. ÁP VÀO `G2 + FLAT3` — kết quả

`profiles/g2_flat3.properties` = baseline B0 (sim Kaggle `sim-jar-gdv2`, printDone md5
`650c386f0d0dfea334af9d55ca2f21d4`, n 2517, eq 131 908 — trùng khít artifact `de-p1`).

| hạng mục | kết quả |
|---|---|
| Thay đổi code cần làm | **KHÔNG** (đã là HIGH-max từ trước) |
| Parity sau thay đổi | **byte-identical** (không thay đổi gì) |
| `n` lệnh | **2 517 — KHÔNG ĐỔI** |
| T3 (win% / TSloss%) | **KHÔNG ĐỔI** (cùng tín hiệu) |
| UW / maxDD | **KHÔNG ĐỔI** |
| Sim Kaggle cần chạy | **KHÔNG** (0 thay đổi ⇒ 0 thông tin mới) |
| Số `.java` bị sửa | **0** (đúng ràng buộc "chỉ đề xuất") |

**Không có 4 tầng §9 nào để xét** vì **không có biến thể**. Ghi rõ để không sinh ảo giác "đã cải thiện".

---

## 4. KẾT LUẬN

1. **Steer như phát biểu = NO-OP.** `rateDown15MAvg` **đã** dùng **MAX(HIGH)** của cửa sổ 15 nến 1M.
   Không sửa code, không chạy sim, `G2 + FLAT3` **nguyên trạng** (n 2517, md5 `650c386f…`).
2. **Nhầm gốc là TÊN FIELD**: `KlineObjectSimple.maxPrice` = HIGH (index 2), `minPrice` = LOW (index 3).
   Đề nghị (chỉ đề xuất, **không tự sửa**): cân nhắc đổi tên/comment `maxPrice → highPrice` để chặn
   hiểu nhầm này tái diễn.
3. **Nếu owner muốn một biến thể THẬT**, biến thể duy nhất nằm cạnh steer là **HIGH → CLOSE**
   (bớt 421/1 916 phút DCA ON, phải nới ngưỡng +0,00405) — **nhưng đây là đi NGƯỢC hướng owner muốn**
   (ít tín hiệu hơn), và **chưa có bằng chứng PnL**; theo `BD_THRESHOLD_FRAGILITY` ngưỡng hiện tại
   **đang là đỉnh PnL** nên nới rộng **có bằng chứng NGƯỢC**. ⇒ **NO-GO.**
4. **Vẫn đứng nguyên NO-GO của `RESULT_BD_DEEP`**: nút đáng đi duy nhất là **chuẩn hoá theo phân vị universe**.

## 5. Giới hạn

- 0-sim ⇒ **không** suy PnL từ §2 (đúng pre-reg §3); §2 chỉ là **tần suất tín hiệu**.
- Cold-start đầu ngày trong tái lập offline gây lệch ≤0,046 ở **14 phút đầu mỗi ngày** (đã loại khi so parity).
