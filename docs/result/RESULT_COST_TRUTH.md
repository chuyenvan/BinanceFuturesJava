# RESULT_COST_TRUTH — CHI PHÍ THẬT: giá khớp của SIM + slip CÓ DẤU theo LOẠI LEG ⇒ 3 mức base/stress/legacy

Ngày: **2026-09-28** (D1, `PLAN_OPENCLAW_ADDENDUM_20260928.md` §A/§D1). Pre-reg: **`docs/prereg/PREREG_COST_TRUTH.md`**
(**commit `8895f82`**, chốt **TRƯỚC**; sau đó **không sửa thiết kế**). Script: `research/analysis/cost_truth.py`.
JSON: `docs/result/cost_truth.json`.

**Tuân thủ:** thuần Python **offline** · **0 sim / 0 train** · giữ box Oracle **nhẹ** · **KHÔNG chạm
production/`242`/ONNX/LIVE** · **KHÔNG push file dữ liệu** · **DEV ≤ 2025-12-31** · chạy lại ~2 s.

---

## 0. KẾT LUẬN (một dòng)

> **SIM vào ở CLOSE nến 1 phút** (`Simulator…:1372`) ⇒ chi phí sim ĐÚNG = **fee + spread±impact = `0,112 %/vòng`**,
> **KHÔNG** phải slip. Trên **991 chân THẬT**, slip có dấu vs close **≈ 0 cho mọi loại leg** (mean −0,05…+0,09 %,
> CI chứa 0); **RIÊNG leg vào lúc sập (nền ≤ −1 %) = `+1,675 %/chân` (CI95 `[+0,90, +2,67]`, n=37) — DƯƠNG
> ĐÁNG KỂ, báo riêng**: đây là **look-ahead của giả định "vào ở close"**, không phải phí thị trường.
> **3 mức: `base 0,112 %` · `stress 0,150 %` · `legacy 0,800 %` (%/vòng)** ⇒ sim đang **trừ oan ~0,56–0,69 pp/vòng**.

---

## 1. VIỆC 1 (i) — SIM VÀO Ở GIÁ NÀO? (đọc code, file:line)

| Điểm | Code | Kết luận |
|---|---|---|
| **GIÁ VÀO** | `research/SimulatorMarketLevelTicker1MStopLoss.java:1372` — `Float entry = ticker.priceClose;` | **close của nến 1 PHÚT** tại tick quyết định. **KHÔNG** open nền sau, **KHÔNG** giá tick (sim không có đường tick cho entry). |
| **GIÁ RA** | `research/OrderTargetInfoTest.java:134` `lastPrice = ticker.priceClose`; gán `priceTP = lastPrice` tại `Simulator…:551,892`; nhánh SL/stop trong nến `priceTP = min(priceOpen, priceClose)` (`:1025,1042`); PreArm SL `:1000` | **close nến** (mặc định) hoặc `min(open,close)` (SL/stop) — **KHÔNG** high/low, **KHÔNG** tick. |
| **MÔ HÌNH CHI PHÍ** | `tradecore/Configs.java:103,117,125` (`RATE_FEE 0,002` · `SLIPPAGE_RATE 0,003` · `APPLY_SLIPPAGE=true`) + `research/OrderTargetInfoTest.java:286-288` (`slip = qty·priceEntry·SLIPPAGE_RATE·2`) | **FLAT `0,80 %/vòng`** = fee `0,20 %` + slip `0,60 %`, **không phân biệt thanh khoản**. |

**HỆ QUẢ (đúng câu hỏi (i)):** vì sim **vào ở close nến** — đúng bằng mốc mà `RESULT_LIVE_FILLS_AUDIT` dùng làm baseline
slip — nên **chi phí sim ĐÚNG = `fee + spread(±impact)`**, **KHÔNG** phải slip. Việc sim **vẫn trừ thêm
`SLIPPAGE_RATE 0,60 %/vòng`** là **cộng thêm trên một giá đã ở close**: hợp lý **chỉ** nếu coi nó là khoản phạt
look-ahead (xem §4), còn nếu coi là "trượt giá" thì **double-count** ⇒ sim **đắt giả tạo**.

## 2. VIỆC 2 (ii) — SLIP CÓ DẤU THEO LOẠI LEG (991 chân THẬT; 976 khớp nến 1m)

Dấu: `s_close = (fill−c)/c` (BUY) · `(c−fill)/c` (SELL) ⇒ **dương = BẤT LỢI = chi phí**.
CI = block-72h, **2000 rep, seed `20260905`, `inflate(5)=1,7941`** (`%/chân`):

| loại leg | n | mean % | median % | CI95 (infl5) % | mean\|.\| % | kết |
|---|---|---|---|---|---|---|
| vào **PREDICT** (nền > −1 %) | 428 | **−0,046** | +0,000 | [−0,232, +0,158] | 0,468 | ≈ 0 |
| vào **BIG_DOWN** (nền ≤ −1 %) | 37 | **+1,675** | +1,320 | **[+0,902, +2,670]** | 1,675 | **DƯƠNG đáng kể → báo riêng** |
| **DCA** (thêm vào vị thế) | 41 | +0,090 | +0,190 | [−0,803, +0,242] | 0,511 | ≈ 0 |
| thoát **STOP_MARKET** (trailing, Σpnl≥0) | 331 | +0,039 | +0,024 | [−0,510, +0,594] | 0,763 | ≈ 0 |
| thoát **STOP_LOSS** (SL/time-stop lỗ, Σpnl<0) | 3 | −2,351 | +0,121 | [−11,29, +2,12] | 2,538 | **n=3 ⇒ chỉ mô tả** |
| **UNKNOWN** (lệnh ngoài cửa sổ 90 ngày) | 136 | −0,523 | −0,079 | [−0,523, −0,523]* | 1,144 | riêng |
| **TỔNG** | 976 | −0,020 | +0,022 | — | 0,716 | (ex-UNKNOWN **+0,062**) |

\* UNKNOWN rơi **hết trong 1 block 72h** (toàn 06-24…06-25) ⇒ CI bootstrap **thoái hoá** (xem §5).

- **Trả lời (ii):** **CHỈ leg vào lúc SẬP có slip dương đáng kể** (`+1,675 %/chân`, CI ngoài 0 phía dương, n=37
  ≈ **8,0 % số chân vào**). **Mọi loại khác ≈ 0** (CI chứa 0) ⇒ **không có slip hướng nào ngoài `fee+spread`**.
- **Độ nhạy** (chỉ để tả, KHÔNG chọn hậu nghiệm): ngưỡng live `−3,157 %` ⇒ n=2, mean `+3,04 %`; "mọi nền đỏ
  (`r<0`)" ⇒ n=245, mean `+0,51 %` — **đơn điệu theo độ đỏ của nền**.

## 3. VIỆC 3 (iii) — CHỐT 3 MỨC + CHI PHÍ DÙNG CHO SIM

```
base   = 2·fee + 2·h(median, S=2000) = 0,0982 + 0,0134 = 0,1116  ⇒ 0,112 %/vòng   (0,056 %/chân)
stress = 2·fee + 2·h(p90,    S=2000) = 0,0982 + 0,0518 = 0,1500  ⇒ 0,150 %/vòng   (0,075 %/chân)
legacy = RATE_FEE 0,20 + SLIPPAGE 2×0,30 = 0,800 %/vòng          (sim đang trừ, FLAT)
```

| mức | %/vòng | %/chân | nguồn | dùng cho |
|---|---|---|---|---|
| **base** | **0,112** | 0,056 | ĐO: fee `0,0491 %/chân` (991 chân) + spread/impact `0,0134 %/vòng` (`RESULT_BOOK_COST2` §3) | ✅ **CHI PHÍ DÙNG cho sim (D2/D3)** |
| **stress** | **0,150** | 0,075 | p90 `bookTicker+aggTrades` (`C(2000)` p90; p90@5 000 = 0,183) | ✅ kiểm bền |
| **legacy** | **0,800** | 0,400 | `Configs.java` (đang trừ) | ❌ **BỎ làm chi phí** |

- **Khớp `RESULT_BOOK_COST2` (`0,112 %`)**: **ĐÚNG** — cùng nguồn (fee 991 chân + `2·h(2000)`); số vòng này
  **không đổi** ⇒ **không cần giải thích sai khác**. Xác nhận chéo: slip có dấu đo trực tiếp trên 991 chân
  **≈ 0** (§2) ⇒ `base` **không bị đánh giá thấp** cho chân thường.
- **MỤC NÀO BỎ + LÝ DO:** bỏ **`legacy 0,8 %/vòng`** (và **`SLIPPAGE_RATE` 0,6 %/vòng**) làm **chi phí** — vì
  sim **đã vào ở close nến** ⇒ phần "slip" là **double-count**; hạ phí về `base` **thấp hơn `legacy` 7,1×**.
  Giữ `0,8 %` **chỉ làm BIÊN TRÊN bảo thủ** (không phải số đúng). Bỏ `|slip|` vô hướng (0,72 %/chân) làm chi phí
  — đó là **nhiễu biến động** (giữ nguyên luật `RESULT_BOOK_COST2` §6).

## 4. SỐ RIÊNG — LEG VÀO LÚC SẬP (`+1,675 %/chân`, n=37)

- **Nguồn gốc = LOOK-AHEAD của "vào ở close"**: với 37 chân này, `s_open ≈ −0,116 % ≈ 0` (fill **≈ giá mở nền**)
  còn `s_close = +1,675 %` ≈ **−bar_ret** (nền trung bình `−1,758 %`). Nghĩa là: lệnh thật khớp **gần open**,
  còn sim gán giá **close** (sau khi nền đã sập thêm) ⇒ với **nền đỏ**, sim **lạc quan** đúng bằng **độ trôi trong nền**.
- **KHÔNG phải phí thị trường** (spread/impact): đó là **chênh giữa mốc sim dùng và mốc khớp thật**. Nền thường
  (`r>−1 %`) có bar_ret `+0,14 %` ⇒ bù lại; **trung bình toàn bộ chân vào ≈ 0** (`+0,09 %`, ex-UNKNOWN) ⇒ base **không lệch** ở chân thường.
- **Ảnh hưởng /vòng nếu giữ tỷ lệ sập cũ**: `0,080 × +1,675 % = +0,133 %/vòng` (phía vào) ⇒ **base+look-ahead ≈ 0,245 %/vòng**.
  Khuyến nghị: **không** nhét khoản này vào `base` (base = chi phí ĐO của vòng thường); nó đòi hỏi sim **vào ở giá
  đúng thời điểm quyết định** (không dùng close nền) — nếu không sửa được thì cộng `+0,13 %/vòng` như **phụ phí
  look-ahead** cho arm có nhiều leg sập (BIG_DOWN/nới gate).

## 5. HẠN CHẾ (khai trước · đúng pre-reg §8)

1. **KHÔNG có log intent (`level`) của 242** (ràng buộc "không chạm 242") ⇒ `BIG_DOWN` là **PROXY theo nền giá**
   (ngưỡng `−1 %`), `DCA`/`STOP_*` **suy luận** từ vị thế + dấu PnL. Loại leg **chính xác** cần đọc
   `storage/data/order/<YYYYMMDD>/<SYM>-<ts>` trên 242 (`OrderTargetInfo.level`) — **ngoài phạm vi**.
2. Proxy `−1 %` dùng **nền của chính coin** (BIG_DOWN live là sự kiện **market-wide**) ⇒ có thể **lẫn** dump lẻ và
   **bỏ sót** coin rơi nhẹ trong cú sập chung.
3. Cửa sổ 88 ngày; **~35 ngày đầu live đã bị Binance xoá**; vị thế mở trước cửa sổ bị cắt.
4. **136 chân UNKNOWN** (lệnh ngoài `allOrders` 90 ngày, dồn 06-24…06-25) ⇒ CI **thoái hoá**, không kết luận.
5. `STOP_LOSS` **n=3** ⇒ chỉ mô tả.
6. Mọi số là **mô tả quá khứ DEV**, không phải cam kết forward.

## 6. TÁI LẬP

```bash
cd /home/ubuntu/src/BinanceFuturesJava
python3 research/analysis/cost_truth.py          # ~2 s, offline, 0 sim
# input (đã có trong repo, KHÔNG fetch lại): research/live_fills_audit/data/{trades,orders}.csv + slips.json
```
