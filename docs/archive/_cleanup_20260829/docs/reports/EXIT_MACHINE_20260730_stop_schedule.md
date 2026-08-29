# EXIT MACHINE 2026-07-30 — stop schedule `s(p)`: dead zone + trần giveback đảo dấu

> Đọc code, KHÔNG chạy job. Phát sinh từ câu hỏi của Uni: "lướt gồm 3 điểm — arm quá nhỏ, dời SL
> chưa đủ tốt, nuôi lãi quá kém — có khi dời SL cũng là nuôi lãi thôi".
> **Kết luận: Uni đúng. Không phải 3 vấn đề, là MỘT đường cong bị vỡ ở 2 chỗ.**

## Khung khái niệm (từ vựng để mô tả)

Trong kiến trúc này KHÔNG có take-profit — trailing-stop là exit **duy nhất**. Vì vậy toàn bộ hành vi
exit được mô tả bởi **một hàm duy nhất**:

> `s(p)` = mức SL đặt tại (tính theo % so entry), như hàm của `p` = **lãi đỉnh đã đạt**.

- **"Lướt"** = hình dạng `s(p)` ở p nhỏ.
- **"Nuôi lãi"** = hình dạng `s(p)` ở p lớn.

Một đường, hai đoạn. Nó *cảm giác* như 3 vấn đề vì đường cong có 3 khúc và 3 gene khác nhau điều
khiển 3 khúc đó.

| Cách gọi cũ (mơ hồ) | Tên đúng | Biến | Giá trị |
|---|---|---|---|
| "RATE_PROFIT_STOP_MARKET quá nhỏ" | **arm threshold** — điểm bật bảo vệ | `RATE_PROFIT_STOP_MARKET` | 1.032% |
| "SL dời chưa đủ tốt" | **ratchet threshold** — điểm SL bắt đầu dời | `* TS_PROFIT_MULTIPLIER 5.21847` | 5.3855% |
| "nuôi lãi quá kém" | **giveback fraction / trailing distance** | `TS_GIVEBACK_RATIO`, `TS_MAX_GAP` | 0.5 / **8pp** |

**Giá trị `TS_MAX_GAP` — phân biệt 2 nguồn (đã verify):** `Configs.java:149` default = **0.08f = 8pp**;
HPO gene range `StrategyWfoTask.java:80` = **[0.04, 0.06] = 4–6pp**. Toàn bộ doc này dùng **8pp
(default)** trừ khi nói rõ khác.
Ngoài ra `maxGap` KHÔNG phải luôn là `TS_MAX_GAP`: `TradeUtils.java:24-26` chọn `TS_MAX_GAP_WEAK`
(`Configs:150` = 0.03f = 3pp) khi `predReturn15M < TS_WEAK_MOMENTUM_THRES` (0.004f).
⚠️ Nghịch lý: dưới gene range HPO, `TS_MAX_GAP_WEAK` ∈ [0.045, 0.060] **RỘNG HƠN** `TS_MAX_GAP` ∈
[0.04, 0.06] — đảo ngược đúng ý định code ("siết chặt khi momentum yếu", `TradeUtils:23`).

## Code — đúng 2 hàm

**ARM (lần đầu đặt SL)** — `research/OrderTargetInfoTest.java:190-197`, nằm trong
`if (priceSL == null)` (`:163`) ⇒ **chạy ĐÚNG MỘT LẦN**:

```
maxGap         = (pred15M < TS_WEAK_MOMENTUM_THRES) ? TS_MAX_GAP_WEAK : TS_MAX_GAP  // TradeUtils:24-26
rateMin2MoveSl = max(RATE_PROFIT_STOP_MARKET, predReturn15M * TS_DYNAMIC_K)         // TradeUtils:39-50
               = max(0.01032, pred15M * 0.29774)                                    // :192
if peakProfit > rateMin2MoveSl -> arm                                               // :193
rateStop = peakProfit - min(peakProfit * TS_GIVEBACK_RATIO, maxGap)                 // TradeUtils:22-37
         -> round về bước 0.005                                                     // TradeUtils:34-35
priceSL  = entry * (1 + rateStop)                                                   // :197
```

**RATCHET (dời SL sau khi đã arm)** — `OrderTargetInfoTest.java:248-262` (`updateTPSL`): ngưỡng `:255`,
điều kiện `:256`, `rateSL` `:257`, guard chỉ-dời-LÊN `priceSLChange > 0 && priceSLNew > priceEntry`
`:260-262`.

Ngưỡng ratchet = `TS_PROFIT_MULTIPLIER * max(0.01032, rateChangeMax90M * TS_DYNAMIC_K)`
= **5.3855%** khi nhánh dynamic không trội.

⚠️ **Hai chỗ KHÔNG cùng input:** arm truyền `predReturn15M` (`:192`), ratchet truyền
**`rateChangeMax90M`** (`:255`). ⇒ ratchet KHÔNG phải chính xác `5.21847×` arm threshold — đẳng thức
đó chỉ đúng khi **cả hai** số hạng dynamic đều dưới `RATE_PROFIT_STOP_MARKET`. Mọi con số dead-zone
dưới đây tính cho trường hợp đó (modal case).

Ghi chú để không phải suy lại: `calRateLossMax` (`:133`) dùng **high của nến hiện tại**, không phải
running max. Nhưng `round_0.005(h − min(h*g, maxGap))` đơn điệu không-giảm theo `h` và ratchet
chỉ-dời-lên ⇒ **tương đương** dùng đỉnh chạy ⇒ khung `s(p)` vẫn đúng.

## Ba khúc của `s(p)` — g=0.5, maxGap=8pp (default `Configs`)

| khúc | p | s(p) | ý nghĩa |
|---|---|---|---|
| 1 | < 1.032% | **không có SL** | `priceSL==null`. `HARD_STOP_LOSS_RATE`=0 và `TIME_STOP_HOURS`=0 (đều tắt mặc định) ⇒ **KHÔNG có exit nào**, chỉ DCA nạp thêm |
| 2 | [1.032%, 5.3855%) | **đóng băng** ở `round_0.005(p_arm × (1−g))` | không phải trailing stop — là **take-profit cố định** chỉ kích hoạt khi hồi |
| 3 | >= 5.3855% | `p - min(p*g, maxGap)` | trail thật; đây mới là "nuôi lãi" |

⚠️ **Khúc 2 = "+0.5%" là MODAL, không phổ quát.** Giá trị đóng băng phụ thuộc `p_arm` = high của
**nến arm**, không phải đúng ngưỡng arm. `s = 0.005` chỉ khi `p_arm ∈ (1.032%, 1.5%)`. Nến arm lớn
(`p_arm = 4%`) ⇒ đóng băng ở `s = 2%`. Vậy con số 4.89pp → 2.89pp dưới đây là **trường hợp phổ biến
nhất**, không phải mọi trade. Phân phối `p_arm` thực CẦN ĐO (thuộc E2).

Khúc 1 giải thích đuôi lỗ béo (`avgLoss` −124.59 nhánh A): lệnh không bao giờ chạm +1.03% thì
không bao giờ có SL.

**Sửa cách mô tả của Uni ở một điểm:** arm threshold nhỏ **tự nó không** gây lướt — SL ở +0.5% không
buộc thoát, nó chỉ thoát nếu giá hồi về +0.5%. Cái gây lướt là **khoảng nhả tại thời điểm arm**:
`arm * g = 1.032% * 0.5 = 0.516pp` — mức nhiễu của bất kỳ altcoin nào trong vài phút.
⇒ Hai biến **nhân với nhau**; biến quyết định là `TS_GIVEBACK_RATIO`, không phải arm threshold.

## PHÁT HIỆN 1 — bước nhảy NGƯỢC DẤU tại ratchet threshold (chưa ghi ở đâu)

Khoảng cách SL-tới-đỉnh `d(p) = p - s(p)`:

| p | s(p) | d(p) |
|---|---:|---:|
| 5.3855⁻ (ngay dưới ratchet) | 0.5% | **4.8855pp** |
| 5.3855% (tại ratchet) | 2.5% | **2.8855pp** |

Kiểm tra: `gap = min(0.053855*0.5, 0.08) = 0.026927` → `rateStop = 0.026927` →
`round(5.3854)*0.005 = 0.025`. Siết = `1 − 2.8855/4.8855 = 40.9%`.

**Kết quả này ĐỘC LẬP với `maxGap`**: tại điểm ratchet `p*g = 2.69pp < maxGap` (cả 5pp lẫn 8pp) nên
nhánh `min()` không chạm trần ⇒ 41% đúng ở mọi giá trị maxGap đang dùng.

Máy **siết chặt 41%** đúng vào lúc cú pump đang xác nhận. Nguyên nhân: `RATE_PROFIT_STOP_MARKET` và
`TS_PROFIT_MULTIPLIER` được HPO tune như **hai gene ĐỘC LẬP**, không ràng buộc nhất quán. Trailing
stop bình thường có ratchet threshold **bằng** arm threshold (armed rồi là trail liên tục). Ở đây
lệch 5.2× ⇒ sinh dead zone 4.35pp + bước nhảy.

⚠️ Dead zone kết thúc ở **5.39%**, label selector là **6%**. Hai số gần nhau đáng ngờ — CẦN ĐO,
không đoán.

## PHÁT HIỆN 2 — `min()` đảo dấu: tỉ lệ nhả TEO DẦN theo lãi (chưa ghi ở đâu)

`gap = min(peak * g, TS_MAX_GAP)`:

- p nhỏ → `gap = p*g` = nhả theo **tỉ lệ** → 0.5pp ở p=1% → mức nhiễu, exit vì rung.
- p lớn → `gap = TS_MAX_GAP` **cố định tuyệt đối** → tỉ lệ nhả = `maxGap/p`, **teo dần**.

Với maxGap = 8pp: crossover ở p ≈ 16%; tỉ lệ nhả còn **27% tại p=30%**, **8% tại p=100%**.
Càng thắng to càng bị siết chặt theo tỉ lệ. Lãi 30%, hồi 8pp là ra — mà pump crypto hồi 20–30%
giữa đường là bình thường. **Đây là cơ chế cắt mất đuôi x2/x3** — chỗ duy nhất một lệnh ăn bằng cả
trăm lệnh nhỏ.

**Cái cần là NGƯỢC LẠI:** `gap = max(p * g, minGap)` — nhả theo tỉ lệ, có **sàn tuyệt đối** để nhiễu
không giết lúc p nhỏ. Hiện code là `min` với **trần**. Đổi `min`→`max`, `maxGap`→`minGap` là đảo đúng
ý nghĩa kinh tế.

## `TS_GIVEBACK_RATIO` = biến quyết định CẤU TRÚC, và nó KHÔNG phải gene

Với **g = 1.0** (SESSION_START §0.5 ghi "giveback=1.0 tối ưu"):

- arm: `gap = min(1.032%*1.0, maxGap) = 1.032%` → `rateStop = 0` → **SL = breakeven**.
- dead zone: s đóng băng ở 0% → stop breakeven, lệnh không thể lỗ.
- p ∈ [5.3855%, 8%): `gap = min(p, 8pp) = p` → `rateStop = 0` ⇒ **vẫn breakeven**, chưa trail.
- p >= 8% (= maxGap): `gap = maxGap` ⇒ `s = p − 8pp`, trail cách đỉnh 8pp.

⇒ `s(p) = max(0, p − maxGap)` — **liên tục, KHÔNG bước nhảy**. g=1.0 **xoá hẳn bất liên tục** và cho
đúng hình "SL chặn lỗ khi có lãi rồi nuôi lãi" mà Uni thiết kế. Đó là lý do nó đo ra tối ưu — không
phải vì nhả nhiều hơn, mà vì **xoá cái vỡ**.

Hai đường (g=0.5 vs g=1.0) hội tụ khi **cả hai** chạm trần maxGap: g=0.5 chạm ở `p = maxGap/g` =
**16%**, g=1.0 chạm ở **8%** ⇒ hội tụ từ **p >= 16%** (với maxGap=8pp default).
⇒ toàn bộ khác biệt nằm trong dải **0–16%**, đúng vùng mọi trade thực sự sống.
(Nếu dùng maxGap từ gene range 4–6pp thì mốc hội tụ là 8–12%.)

**Lỗ hổng provenance:** `TS_GIVEBACK_RATIO` đọc từ `config.properties`, default `0.5f`
(`Configs.java:254-255`), **KHÔNG nằm trong 17 gene** ⇒ không xuất hiện trong `bestGenome` của bất kỳ
RESULT_JSON nào ⇒ **KHÔNG truy được step-2 đã chạy 0.5 hay 1.0**. Nếu step-2 chạy 0.5 mà doc ghi 1.0
tối ưu thì verdict M đang đo một exit machine khác cái Uni nghĩ. → hạng mục **P6** trong
`AUDIT_20260730_wfo_constraint_harness.md`.

## Phân biệt với thứ ĐÃ GIẾT — KHÔNG đi lại đường cũ

| Đã giết | Object | Cái đang bàn |
|---|---|---|
| hard-SL/TP first-touch | ngưỡng **cố định**, chấm theo lần chạm đầu | **schedule động** phụ thuộc lãi đỉnh |
| offset-sweep | entry rank | không liên quan exit |
| gate < 0.010 | entry filter | không liên quan exit |

Stop schedule động phụ thuộc `p` **chưa từng được đo**. Không phạm luật "đừng thử lại".

## Thiết kế "+3% → SL cứng +1%" của Uni

`SESSION_START §0.5` ghi chưa implement — **xác nhận đúng**. Code hiện chỉ có arm-1.032% /
ratchet-5.386%. Thuộc Phase 1 exit machine redesign, làm SAU khi harness sạch.

---

# PHẦN 2 — PHƯƠNG PHÁP: dựng exit trên TẬP ENTRY ĐÓNG BĂNG

Đề xuất của Uni: đóng băng tập entry, dựng exit tương đối trên đó, thay vì vừa dò exit vừa nắn entry.
**Đồng ý**, và có thêm một lợi ích handoff chưa thấy: **nó KHÔNG đi qua WFO harness** ⇒ miễn nhiễm
toàn bộ L1–L5 ⇒ chạy song song với P0–P5 được, không phải chờ.

## Sample size: KHÔNG hạ gate. Dùng C1.

Uni đề xuất hạ gate về 0.007 để tăng sample. **Bác — vì nó phá chính phép đo:**
gate là filter theo **momentum**, mà momentum là biến quyết định **hình dạng path**. Hạ gate không
thêm "case cùng loại", nó thêm hệ thống các path **momentum yếu hơn** (phân phối `p` dịch xuống,
nhiễu nhiều, run ngắn) ⇒ schedule fit ra sẽ bị kéo về **stop chặt** = ngược cái đang muốn tìm. Rồi
deploy trên tập gate=0.010 = fit sai phân phối. Sample-selection bias, tệ hơn thiếu sample (thiếu
sample thì biết là chưa kết luận được; lệch phân phối thì ra số trông có vẻ dùng được).

**Số đã đo** — `D:\claudedata\freq_probe_table.md` (gate×window, oiz=off, 2026-07-28), Σ w4–w14:

| | gate-pass | so với trade thật (996) | so với gate=0.010 |
|---|---:|---:|---:|
| gate = 0.010 | **26 394** | **26.5×** | 1.00× |
| gate = 0.008 | 43 392 | 43.6× | 1.64× |

⇒ **C1 (bỏ filter vốn, GIỮ gate 0.010) cho 26.5× sample, cùng phân phối momentum, bias = 0.**
Hạ gate xuống 0.008 chỉ thêm 1.64× và kèm bias. **C1 thắng tuyệt đối.** C2 (nạp w0/w1/w15 vào derive,
+909 trade) và C3 (nâng rank-K) **không cần nữa**.

Lý do C1 tồn tại: rất nhiều signal qua gate nhưng KHÔNG thành trade vì margin đã đầy
(`MAX_CONCURRENT_ORDERS`=40, `BUDGET_MARGIN_RATIO_1/2`). Để đo **hình học path**, lệnh không cần
tradeable — chỉ cần thời điểm signal.

### ⚠️ Hai hiệu chỉnh PHẢI làm trước khi tin con số 26 394

1. `gatePass` đếm **signal-minute**, không phải **vị thế độc lập**. Cùng một symbol pass gate ở nhiều
   phút liên tiếp bị đếm nhiều lần. Phải **dedup theo (symbol, cluster)** → số hiệu dụng thấp hơn 26k,
   **chưa biết bao nhiêu**. Không được overclaim.
2. Entry thật còn qua **rank-K8** (top-8/timestamp) SAU gate. Tập đóng băng đúng là
   **gate-pass ∩ rank-topK, bỏ filter vốn** — nằm giữa 996 và 26 394. Bảng freq không tách được.

⇒ **Việc đo đầu tiên**: đếm `gate ∩ rankK` sau dedup, bỏ filter vốn.
`GatePassCountProbe.java` (uncommitted) đã làm nhánh gate; cần biến thể thêm rank-K + dedup.

## Blocker: dữ liệu hiện tại KHÔNG đủ để chấm trailing

`OrderTargetInfoTest` chỉ lưu `maePeak` (đỉnh) và `maeLow` (đáy) — hai **scalar**
(khai báo `maeLow` `:68`, `maePeak` `:71`, comment từ `:65`; cập nhật `:117-124`).
**Không thể** chấm trailing stop từ (MFE, MAE) vì
trailing phụ thuộc **THỨ TỰ** đỉnh/đáy xảy ra: hồi trước đỉnh khác hồi sau đỉnh.

### Instrument cần: zigzag per-entry

Export dãy **cực trị luân phiên** của path forward: `(peak1, trough1, peak2, trough2, ...)`.
Với object đó, **mọi** stop schedule `s(p)` đơn điệu chấm được CHÍNH XÁC, không cần chạy lại sim.
Mỗi trade vài chục điểm ⇒ object nhỏ. Đây là instrument đúng — KHÔNG phải "chạy thêm một WFO".

Yêu cầu tối thiểu mỗi record: `symbolId, entryTs, entryPrice, [(ts, price, isPeak)...], horizonEnd`.

## 4 rủi ro — nói TRƯỚC, không nói sau

**R1 — tập entry KHÔNG thực sự độc lập với exit.** Exit quyết định khi nào vốn giải phóng ⇒ quyết định
entry sau có margin không. Đóng băng tập là **xấp xỉ**. Con số thu được là **per-trade edge**, KHÔNG
phải portfolio PnL. Phải dán nhãn đúng; candidate chọn ra **vẫn phải qua sim full** để xác nhận.
Tuyệt đối không lấy số per-trade đi kết luận CAGR.

**R2 — cần export path, chưa có.** Xem blocker trên. Đây là hạng mục duy nhất thực sự tốn công.

**R3 — overfit KHÔNG mất, nó dịch chỗ.** Fit 4 tham số schedule vẫn là fit. Giữ đúng kỷ luật:
derive trên subset 2022 (như nhánh A đã làm), validate forward w2–w14, pre-register ngưỡng TRƯỚC khi
nhìn. Không thì chỉ đổi overfit-entry thành overfit-exit.

**R4 — verdict cuối vẫn phải qua WFO.** Nghiên cứu exit trả lời "xây cái gì"; harness trả lời "nó có
trụ được không". Bỏ P0–P5 thì đến lúc confirm vẫn bị CAPITAL_LOCK loại đúng cái exit giữ-dài vừa xây.
P0–P5 không bị huỷ, chỉ hạ ưu tiên.

## Thứ tự thực thi + gate dừng

| # | Việc | Gate dừng |
|---|---|---|
| **E0** | Đếm `gate ∩ rankK` sau dedup, bỏ filter vốn (biến thể `GatePassCountProbe`) | nếu số hiệu dụng < ~3 000 ⇒ dừng, xét lại C2/C3 |
| **E1** | Export zigzag cho tập E0 (Kaggle — Oracle disk 89%) | 0 NaN, spot-check 3 trade khớp ticker gốc |
| **E2** | Đo phân phối `p`: % lệnh chết trong dead zone 1.03–5.39%; % từng đạt p>16%; tổng lãi đỉnh **bỏ lại trên bàn** so PnL thực | nếu đuôi phải mỏng (p>16% < ~2%) ⇒ `min→max` KHÔNG đáng làm, dừng |
| **E3** | Grid stop schedule (arm, ratchet, g, minGap), derive-2022 / validate-forward | pre-register trước khi nhìn |
| **E4** | Sensitivity: chấm schedule đã fit trên gate=0.007 | dùng gate lỏng để **kiểm tra**, KHÔNG để fit |

**E2 là chỗ có tỉ lệ thông tin/chi phí cao nhất trong toàn chuỗi hiện tại** — dùng dữ liệu đã có,
không cần harness, trả lời trực tiếp câu hỏi gốc của Uni ("nuôi lãi thì SL/TP phải ra sao").

## Quyết định thuộc Uni

Chạy E0 trước hay gộp E0+E1; horizon export zigzag (30d? tới delist?); và có commit khối uncommitted
trước khi thêm code mới hay không.

---

# KET QUA E0 (2026-07-30, DA CHAY) — **C1 BỊ BÁC. GATE STOP KÍCH HOẠT.**

Run: `EntryUniverseCountProbe`, jar `binance-e0-20260730.jar`, Oracle, log
`/home/ubuntu/claudedata/.run/e0_entry_universe.log`, CSV
`/home/ubuntu/claudedata/entry_universe_e0.csv` (64 522 dòng).
Env: `SIM_GATE_COUNT_ONLY=1 SIM_ENTRY_UNIVERSE_DUMP=1 SELECTOR_RANK_TOPK=8
SIM_MIN_MOMENTUM_15M=0.010 WFO_DATA_DIR=wfo_ds_ret2wf_4h_ff`, range **20210101..20260301**.
Ticker = Aerospike local (env `TICKER_SOURCE` là no-op — xem INFRA_FACTS).

- `gateSeen = 19 419 806`, `gatePass = 64 222`, raw admission = **64 522**
  (chênh 300 = leg `BIG_DOWN` bỏ qua khối filter, `levelChangeOrdinal=3`; selector `ord=5` = 64 222).

## Đối chiếu CÙNG CỬA SỔ w4–w14 (20230101..20251001) — nơi có 996 trade thật

| H (giờ) | vị thế (tất cả) | chỉ selector | **vs 996 trade thật** |
|---:|---:|---:|---:|
| 0 (raw signal-minute) | 11 573 | 11 441 | 11.62× |
| 1 | 1 299 | 1 262 | **1.30×** |
| 4 | 1 138 | 1 101 | 1.14× |
| 12 | 1 042 | 1 005 | 1.05× |
| 24 | **997** | 960 | **1.00×** |
| 72 | 952 | 919 | 0.96× |
| 168 | 912 | 880 | 0.92× |

## KẾT LUẬN: C1 KHÔNG cho thêm sample. Con số 26.5× là ARTIFACT.

Ở mọi H khớp horizon exit thực tế (≥12h), **số vị thế độc lập ≈ số trade đã thực sự vào**
(997 vs 996 = 1.00×). Nghĩa là **filter vốn gần như KHÔNG hề binding** — hệ thống đã vào gần hết
những gì nó được phép vào. "26.5×" trong §PHAN 2 sinh ra 100% do đếm **signal-minute**; hệ số dedup
thực = **~23×**, ăn trọn toàn bộ khoảng lợi tưởng có.

> **Đây là bác bỏ khuyến nghị của chính báo cáo này.** §PHAN 2 viết "C1 thắng tuyệt đối, 26.5×
> sample, bias 0" — **SAI**. Caveat ⚠️#1 (gatePass đếm signal-minute) hoá ra không phải hiệu chỉnh
> nhỏ mà là toàn bộ vấn đề. Phần lập luận **hạ gate gây sample-selection bias vẫn ĐÚNG** và không bị
> ảnh hưởng; chỉ có "C1 là nguồn sample thay thế" bị bác.

## GATE STOP (đã pre-register ở §E0) ĐÃ KÍCH HOẠT

Ngưỡng pre-register: "< ~3000 vị thế ở H hợp lý → DỪNG, xét lại C2/C3 thay vì export zigzag E1".

| phạm vi | H=24h | H=72h | H=168h |
|---|---:|---:|---:|
| w4–w14 | 997 | 952 | 912 |
| toàn kỳ 20210101..20260301 | **2 834** | 2 485 | 2 236 |

Toàn kỳ ở H=24h = 2 834 < 3 000 ⇒ **FAIL ngưỡng, dù sát**. ⇒ **KHÔNG chạy E1.**

⚠️ Ngưỡng 3 000 là **số tôi (Claude) tự đặt** trong doc này, KHÔNG phải Uni pre-register. Uni có
quyền sửa — nhưng sửa **sau khi đã nhìn kết quả** chính là vi phạm luật "pre-register trước khi
xem" (memory: Uni đã bắt Claude vi phạm 2 lần). Nếu đổi ngưỡng thì phải ghi tường minh là đổi
sau-khi-nhìn, kèm lý do độc lập với con số vừa thấy.

## Chỗ sample THẬT SỰ nằm: 2021–2022, không phải filter vốn

Phân bố raw admission theo năm:

| năm | raw admission |
|---|---:|
| 2021 | **29 277** |
| 2022 | 15 611 |
| 2023 | **880** |
| 2024 | 7 377 |
| 2025 | 11 377 |

Toàn kỳ H=24h (2 834) − w4–w14 H=24h (997) ⇒ **~1 837 vị thế độc lập nằm ngoài vùng verdict**, chủ
yếu 2021–2022. ⇒ **C2 (nạp 2021/2022 vào tập DERIVE) là đường DUY NHẤT còn sống**, và nó gấp ~2.8×
tập w4–w14 — trái với §PHAN 2 đã viết "C2/C3 không cần nữa" (**cũng SAI, cần đảo lại**).

Ràng buộc phương pháp khi dùng C2: 2022 là vùng **derive genome frozen** (w0/w1) và 2021 là
**train-only, chưa bao giờ OOS**. Dùng cho **hình học path** thì được; nhưng w2–w14 PHẢI giữ nguyên
làm validation chưa chạm, và mọi schedule fit trên 2021–2022 phải validate forward.

⚠️ 2023 chỉ 880 raw (so 2021: 29 277) — chênh 33×. Đây là bằng chứng độc lập cho "frequency = trần
ràng buộc": cùng gate 0.010, số tín hiệu qua gate phụ thuộc regime cực mạnh. CHƯA giải thích, cần đo.

## Lỗi nhỏ trong probe (cần sửa nếu chạy lại)

Cột `symbolDuyNhat` = 483 ở MỌI cooldown — vì nó đếm số symbol từng được admit, bất biến theo
cooldown. Vô dụng như đang trình bày; nên đổi thành "số vị thế / symbol" hoặc bỏ.

## Uni quyết

(a) Giữ gate stop → dừng nhánh exit-on-frozen-set, quay về P0–P5 (sửa harness); hoặc
(b) Đổi sang C2 (nạp 2021–2022, ~2 834 vị thế) và ghi rõ việc hạ ngưỡng là sau-khi-nhìn; hoặc
(c) Điều tra trước cái chênh 33× giữa 2021 và 2023 — nó có thể quan trọng hơn cả nghiên cứu exit.

## PHẦN 3 — Đã tìm thấy: câu hỏi min-rate ĐÃ được đo trước đây (TASK-139, 2026-07-07)

Trước khi làm sweep mới theo yêu cầu Uni (2026-07-30, "min ít nhất 0.03"), phát hiện repo đã có sẵn
`src/main/java/com/binance/chuyennd/ai_ml/wfo/framework/tasks/TrailingStopSweepProbe.java` (commit
`73f8c77`, 2026-07-06) và báo cáo kết quả `docs/reports/trailing_stop_sweep_139.md` (2026-07-07) —
**đúng giả thuyết Uni đang nêu lại hôm nay, đã được xác nhận 3 tuần trước, chưa từng được áp vào
Configs.java production default.**

### Kết quả sweep cũ (giữ nguyên formula trailing hiện tại, chỉ đổi RATE_PROFIT_STOP_MARKET)

| rateTS | Toàn kỳ PnL / calmar / maxDD | holdMed | %hold>60p |
|---|---|---|---|
| 0.01032 (baseline cũ) | 17 804 / 1.65 / 30.9% | 7 phút | 16.1% |
| 0.02032 | 27 747 / 2.55 / 31.0% | 21 phút | 33.0% |
| **0.03032 (Uni chọn)** | 34 442 / 3.06 / 32.1% | 52 phút | 47.6% |
| 0.04032 | 38 346 / 3.41 / 32.1% | 110 phút | 59.2% |
| 0.05032 | 42 405 / 3.78 / 32.0% | 197 phút | 67.0% |

Kết luận cũ: **PnL 2.4×, calmar 2.3×, maxDD gần như không đổi** khi nâng 0.01032→0.03032. 0.03-0.04
là "vùng robust" (2025Q2 — quý phẳng — calmar đỉnh 16.6 tại 0.03, tụt còn 7.5 tại 0.05 ⇒ 0.05 hơi over
ở regime phẳng dù PnL/calmar toàn kỳ cao nhất).

⚠️ Giới hạn của sweep cũ: KHÔNG đổi `TS_PROFIT_MULTIPLIER`/ratchet — nghĩa là toàn bộ cải thiện
holdMed 7→52 phút chỉ đến từ dời điểm arm, cơ chế ratchet-siết 41% và giveback min()-co-lại (đã ghi ở
PHẦN 1) **vẫn y nguyên, chưa được đo cùng lúc**. Việc tách ratchet khỏi arm (đề xuất ở cuối PHẦN 2 hôm
qua) vẫn là việc CHƯA làm, độc lập với thay đổi này.

### Đã áp dụng hôm nay (2026-07-30)

1. `Configs.java` — `RATE_PROFIT_STOP_MARKET`: `0.01032f` → `0.03f` (production default, đường
   KHÔNG qua HPO). Trước đây biến này chỉ đổi qua gene HPO trong WFO, còn đường live/production đọc
   thẳng field này vẫn kẹt ở giá trị cũ suốt từ 2026-07-06 đến nay — tức khuyến nghị của chính báo cáo
   TASK-139 ("HƯỚNG KẾ" mục 1) **chưa từng được thực thi cho production**, chỉ tồn tại trong report.
2. `StrategyWfoTask.java:77` — gene range `RATE_PROFIT_STOP_MARKET`: sàn `0.020` → `0.03` (trần giữ
   `0.050`, đúng vùng TASK-139 xác nhận tốt, loại hẳn vùng cắt-non `[0.020,0.030)` khỏi không gian HPO
   dò).
3. Lý do độc lập củng cố thêm (không chỉ dựa vào sweep cũ): chi phí round-trip = `RATE_FEE`(2 chân,
   0.002) + `SLIPPAGE_RATE`(2 chân, 0.003) = **0.008**. Với giveback 0.5, arm phải > ~0.016 chỉ để hoà
   vốn sau chi phí ở điểm SL đóng băng đầu tiên — 0.03 có biên an toàn ~2×, 0.01032 thì SL đóng băng ở
   +0.5% là lỗ chắc chắn sau phí.

### Phát hiện phụ — 2 bản genome khác vẫn còn range cũ (KHÔNG sửa, vì không nằm trên đường production)

Grep cho thấy 2 file khác định nghĩa lại genome độc lập với `StrategyWfoTask.java` và **không** được
`orchestrator/pipelines/*.json` gọi tới (chỉ `StrategyWfoTask` được `dca_ablation.json` tham chiếu):

- `ai_ml/wfo/WFORunner.java:74` — `RATE_PROFIT_STOP_MARKET` range vẫn `[0.012, 0.025]` (đúng vùng
  cắt-non mà comment TASK-139 gọi là bug).
- `ai_ml/hpo/SensitivityTool.java:82` — range `[0.005, 0.025]` (công cụ đo độ nhạy OAT, còn thấp hơn).

Hai file này là TASK-111/TASK-111(B), có vẻ là runner/tool cũ hoặc chẩn đoán, chưa xác nhận được có ai
còn dùng không. Nếu Uni còn chạy trực tiếp 2 class này, chúng sẽ dò vào đúng vùng đã biết là xấu — cần
Uni xác nhận có cần dọn (đồng bộ hoặc xoá) hay để nguyên vì không ai gọi.

### Việc CHƯA làm (khác với đã làm ở trên — để tránh lẫn)

- Tách ratchet khỏi arm (`ratchet = arm`, bỏ phụ thuộc `TS_PROFIT_MULTIPLIER` vào arm) — đề xuất ở
  PHẦN 2, CHƯA thực hiện, cần Uni chốt riêng.
- Sửa `gap = min(p×g, maxGap)` → `max(p×g, minGap)` (giveback không co lại với lệnh lãi lớn) — CHƯA
  thực hiện.
- Chạy lại N=13 window confirm với default mới để đo tác động thật trên verdict M (khác baseline sweep
  cũ, vốn không qua constraint harness V4 đầy đủ theo window) — ✅ ĐÃ CHẠY, xem PHẦN 4.

---

# PHẦN 4 — N=30 × 16-window confirm CHO min-rate 0.03 (chạy 2026-07-30 tối, DONE 16/16)

Jar `binance-exit003-20260730.jar` (md5 Oracle `f89c5a449de96a4f377e95dae2de936f`, md5 Kaggle
`4145806f1686ec6426c22954a373019a`, cùng HEAD `b203a78`, lệch do PrivateConfig placeholder).
Chạy Kaggle-only 5-node (Oracle 0 — ticker file Oracle đã bị dọn, không dùng được), tag `exit003`,
`WFO_N_SAMPLES=30 WFO_SEED_BASE=42 WFO_MAX_OOS_DATE=20260101`, dataset `wfo_ds_ret2wf_4h_ff`.
`TS_RATCHET_DECOUPLED` KHÔNG bật (mặc định `false`) — run này CHỈ đo tác động của đổi sàn
`RATE_PROFIT_STOP_MARKET` (gene range `[0.012,0.025]` → `[0.03,0.05]`), không confound với ratchet.

## VERDICT: ❌ FAIL/REVIEW (vẫn fail, như verdict M gốc)

| tiêu chí (pre-registered) | ngưỡng PASS | verdict M gốc (0.012-0.025) | exit003 (0.03-0.05) | đổi |
|---|---|---|---|---|
| WFE trung vị | ≥ 0.50 | 0.307 (FAIL) | **0.442** (FAIL) | +44% nhưng vẫn dưới ngưỡng |
| % cửa sổ OOS dương | ≥ 70% | 43.8% (7/16) (FAIL) | **37.5% (6/16)** (FAIL) | **XẤU ĐI** |
| maxDD OOS xấu nhất | ≤ 50% | 32.4% (PASS) | **34.3%** (PASS, abs 12021) | xấu đi nhẹ, vẫn qua |

`note` 16 window: SUCCESS=6 (w3,8,9,10,12,15), TOO_FEW_TRADES=5 (w1,5,7,11,14),
ZERO_TRADES=4 (w0,2,4,13), TOO_MUCH_CAPITAL_LOCK=1 (w6).

## ⚠️ Phát hiện quan trọng — cải thiện WFE là ẢO, đến từ ĐÚNG 1 window

Tổng OOS PnL 16 window ≈ **17 906**. Window 15 (2025-10→2026-01) một mình đóng góp **11 611
(64.8% tổng PnL)**, và CŨNG là window có maxDD-OOS **tệ nhất** (34.3% vốn / 35.2% mark-to-market,
minEquity chạm 64.9%) — tức đúng mẫu Uni nêu ra đầu phiên: *"coin pump nhưng đánh lướt → đuôi lớn
(maxDD) mà ăn thì ít"* ở các window khác, và ở đây window ăn nhiều nhất cũng là window rủi ro đuôi
lớn nhất. WFE trung vị nhích lên (0.307→0.442) không phải vì các window khác khá hơn đều — %OOS-dương
thực ra TỆ HƠN (43.8%→37.5%) — mà vì 1 window ăn đậm kéo trung vị/PnL tổng lên. Đây là dấu hiệu
concentration/overfit-1-window, không phải cải thiện breadth thật.

Không có window nào dính margin-call (proxy cross 1x, ngưỡng equity≤0.5%): 0/16 — nhưng minEquity
window 15 xuống 64.9%, biên margin-call không còn xa như các window khác (đa số 96-100%).

## Việc CÒN CHƯA làm (không đổi so trước, nhắc lại để khỏi quên)

- Tách ratchet khỏi arm (PHẦN 2), sửa `gap = min(p×g,maxGap)` → `max(p×g,minGap)` — CHƯA làm.
- Confirm RIÊNG `TS_RATCHET_DECOUPLED=true` (không gộp 2 biến 1 lần đo) — CHƯA chạy.

## Quyết định thuộc Uni (đọc cùng phát hiện ở trên trước khi chọn)

(a) Vẫn coi 0.03-0.05 là cải thiện đủ để tiếp tục nhánh exit (bật thử ratchet-decouple, sửa giveback)
    — nhưng nên biết cải thiện phần lớn đến từ 1 window, chưa chắc generalize; hoặc
(b) Dừng nhánh exit ở đây (2/3 tiêu chí vẫn FAIL, 1 tiêu chí xấu đi) → quay lại NHÁNH A (fix fitness
    mismatch Calmar-vs-WFE, bỏ HPO argmax) — đây là việc audit 07-30 sáng đã chỉ ra là bottleneck gốc,
    tách biệt khỏi exit-formula; hoặc
(c) Điều tra riêng window 15 (regime gì khiến 1149 trades trong 1 window, gấp nhiều lần window khác)
    trước khi quyết — có thể là artifact dataset/regime đặc biệt (2025Q4-2026Q1), không phải do exit
    mới hoạt động tốt hơn.

---

# PHẦN 5 — Confirm THẬT `TS_RATCHET_DECOUPLED=true` (2026-07-31) — **❌ FAIL, và ⚠️ hủy bỏ "ratchet1"**

## ⚠️ Trước tiên: run fanout "ratchet1" trước đó (WfoWorker/JobStore) là **INVALID — bỏ, không dùng**

Sau khi Uni chọn tiếp nhánh (a) và bật `TS_RATCHET_DECOUPLED=true` chạy fanout 16-window qua
`WfoWorker`/`JobStore` như bình thường (tag `ratchet1`), kết quả PnL/wfe ra **byte-identical** với
`exit003` (tức `false`) — nghi vấn cờ không hoạt động. Chẩn đoán theo loại trừ:

1. Push code lên Kaggle đúng — verify bằng `kaggle kernels pull` + diff, không lệch.
2. Jar đúng — verify bằng đọc bytecode `.class` trong jar (cả Oracle lẫn Kaggle), string
   `TS_RATCHET_DECOUPLED` có mặt ở cả hai.
3. **A/B cô lập bằng `VerifyOneWindow`** (không qua `WfoJobStore`, gọi thẳng `task.runJob()`) trên
   cùng window 15: `true` → 1185 trades / oosPnl 11440.58 / wfe 5.7328; `false` → 1149 trades / oosPnl
   11611.40 / wfe 3.7387 (số `false` này khớp hệt số fanout `ratchet1`/`exit003` cũ). **Cờ CÓ hoạt
   động** khi không đi qua `WfoWorker`/`JobStore`.

**Kết luận: bug nằm trong đường `WfoWorker`/`WfoJobStore`, khiến nó bỏ qua env `TS_RATCHET_DECOUPLED`
(hoặc mọi override qua env tương tự) khi chạy multi-window fanout.** Root cause bên trong
`WfoWorker`/`WfoJobStore` **CHƯA tìm ra** (đã soát `reset()`/`putForce()`, chưa thấy cache bug rõ ràng)
— đây là rủi ro hạ tầng còn mở, cần ghi vào `INFRA_FACTS.md`: **mọi confirm fanout dựa vào env-flag
qua `WfoWorker` từ nay về trước có thể đã SAI**, không riêng gì `TS_RATCHET_DECOUPLED`. Số liệu
"ratchet1" (fanout) bị coi là **INVALID, không dùng để kết luận**.

## Phương pháp thay thế: bypass `WfoWorker`, dùng `VerifyOneWindow` trực tiếp (không qua JobStore)

Vì `VerifyOneWindow` đã chứng minh phản ánh đúng cờ, chạy lại đủ N=30×16-window bằng đường này, chia
tải:

- **Oracle** (ticker Aerospike local, `AEROSPIKE_HOST_226=127.0.0.1`) — 10 window nhẹ: 0,1,2,4,5,6,7,
  11,13,14. Launch trực tiếp qua `nohup ... & disown` (KHÔNG dùng `bg_run` — xem ghi chú bug bên
  dưới), song song 3 tiến trình/lần (`xargs -P3`, máy 4 core, `-Xmx4g`/process).
- **Kaggle** — 6 window còn lại qua 4 kernel riêng, mỗi kernel cũng gọi `VerifyOneWindow` trực tiếp:
  `kv-w15`(w15), `kv-w9-12`(w9,w12), `kv-w10-3`(w10,w3), `kv-w8`(w8).

⚠️ **Bug phụ phát hiện trong lúc làm — CE `bg_run` báo SUCCESS giả cho job Oracle đầu tiên**: launch
qua `bg_run` trả về `exit_code=0` gần như tức thời kèm log rỗng (0 byte) — trong khi chạy đúng lệnh đó
thủ công qua SSH trực tiếp thì Java chạy thật, ra log đầy đủ, tốc độ khớp Kaggle (~15-20 phút/window).
Vậy `bg_run` (không phải Java/Aerospike/dữ liệu) có lỗi launch/detect với script này — nguyên nhân sâu
CHƯA tìm, workaround là chạy `nohup` trực tiếp thay `bg_run`. Cần thêm vào danh sách lỗi hạ tầng đã
biết của CE.

## Kết quả 16/16 window (`TS_RATCHET_DECOUPLED=true`, N=30, seed_base=42)

| win | label | nguồn | wfe | oosPnl | oosDdPct | oosTrades | note |
|---:|---|---|---:|---:|---:|---:|---|
| 0 | 20220101..20220401 | Oracle | 0 | 0 | 0% | 0 | ZERO_TRADES |
| 1 | 20220401..20220701 | Oracle | 0.061 | 296.3 | 0.28% | 4 | TOO_FEW_TRADES |
| 2 | 20220701..20221001 | Oracle | 0 | 0 | 0% | 0 | ZERO_TRADES |
| 3 | 20221001..20230101 | Kaggle | 0.226 | 638.5 | 0.64% | 64 | SUCCESS |
| 4 | 20230101..20230401 | Oracle | 0 | 0 | 0% | 0 | ZERO_TRADES |
| 5 | 20230401..20230701 | Oracle | 0.119 | 176.1 | 1.74% | 8 | TOO_FEW_TRADES |
| 6 | 20230701..20231001 | Oracle | 0.956 | 738.3 | 0.80% | 41 | TOO_MUCH_CAPITAL_LOCK |
| 7 | 20231001..20240101 | Oracle | 0.137 | 160.3 | 0.15% | 8 | TOO_FEW_TRADES |
| 8 | 20240101..20240401 | Kaggle | 0.333 | 644.0 | 1.63% | 36 | SUCCESS |
| 9 | 20240401..20240701 | Kaggle | 0.242 | 424.6 | 1.87% | 89 | TOO_MUCH_CAPITAL_LOCK |
| 10 | 20240701..20241001 | Kaggle | 0.412 | 967.0 | 2.96% | 106 | SUCCESS |
| 11 | 20241001..20250101 | Oracle | -0.047 | -102.2 | 1.30% | 7 | TOO_FEW_TRADES |
| 12 | 20250101..20250401 | Kaggle | 0.442 | 716.7 | 3.78% | 82 | SUCCESS |
| 13 | 20250401..20250701 | Oracle | 0 | 0 | 0% | 0 | ZERO_TRADES |
| 14 | 20250701..20251001 | Oracle | 0.048 | 119.5 | 0.14% | 27 | TOO_FEW_TRADES |
| 15 | 20251001..20260101 | Kaggle | **5.737** | **11 422.9** | **34.34%** | 1185 | SUCCESS |

`note` tổng hợp: SUCCESS=5 (w3,8,10,12,15), TOO_FEW_TRADES=5 (w1,5,7,11,14), ZERO_TRADES=4
(w0,2,4,13), TOO_MUCH_CAPITAL_LOCK=2 (w6,w9).

## VERDICT: ❌ FAIL (rõ ràng hơn cả verdict M gốc và exit003)

| tiêu chí (pre-registered) | ngưỡng PASS | verdict M gốc | exit003 (false) | **ratchet_true** |
|---|---|---|---|---|
| WFE trung vị | ≥ 0.50 | 0.307 (FAIL) | 0.442 (FAIL) | **0.128 (FAIL, TỆ HƠN CẢ HAI)** |
| % cửa sổ OOS dương | ≥ 70% | 43.8% (FAIL) | 37.5% (FAIL) | **68.75% (11/16) (FAIL, sát ngưỡng, tốt hơn cả hai)** |
| maxDD OOS xấu nhất | ≤ 50% | 32.4% (PASS) | 34.3% (PASS) | **34.34% (PASS, ~bằng exit003)** |

`TS_RATCHET_DECOUPLED=true` **không cải thiện WFE** — median tụt mạnh xuống 0.128 (thấp hơn cả
baseline gốc 0.307), dù %OOS-dương nhích lên gần ngưỡng 70%. WFE trung vị bị kéo xuống vì nhiều
window OOS chỉ đạt vài trade (wfe gần 0) trong khi window 15 kéo giá trị trung bình lên rất cao —
median không "thấy" được điều đó, phản ánh đúng là phần lớn window KHÔNG cải thiện thực chất.

## ⚠️ Concentration window 15 — TỆ HƠN exit003, không phải cải thiện

Tổng OOS PnL 16 window ≈ **16 202**. Window 15 một mình đóng góp **11 423 (70.5% tổng PnL)** — CAO
HƠN mức 64.8% đã cảnh báo ở PHẦN 4 cho exit003 — và vẫn là window có maxDD-OOS **tệ nhất tuyệt đối**
(34.3%, gấp ~9× window kế tiếp là w12 với 3.78%). Bật `TS_RATCHET_DECOUPLED=true` **không xóa vấn đề
concentration đã nêu ở PHẦN 4 — nó làm nặng thêm**. Đây tiếp tục là dấu hiệu overfit-1-window
(2025Q4-2026Q1), không phải cơ chế ratchet-decouple hoạt động tốt hơn nói chung.

## Điều tra window 15 (2026-07-31) — **KẾT LUẬN: black-swan 1-ngày, KHÔNG phải regime hay edge**

Uni yêu cầu điều tra riêng trước khi kết luận (thay vì đoán). Phương pháp: dùng lại
`entry_universe_e0.csv` (64 522 dòng, raw admission với gate **CỐ ĐỊNH** 0.010 — độc lập hoàn toàn với
genome HPO chọn cho từng window) để tách bạch "dữ liệu/regime có thật nhiều tín hiệu hơn" khỏi
"HPO chọn genome quá lỏng cho riêng window 15".

**Bước 1 — raw admission theo window (gate cố định 0.010, không liên quan genome):**

| win | rows | symbols | | win | rows | symbols |
|---:|---:|---:|---|---:|---:|---:|
| 0 | 1 732 | 77 | | 8 | 1 601 | 109 |
| 1 | 9 267 | 120 | | 9 | 1 300 | 77 |
| 2 | 74 | 28 | | 10 | 3 577 | 108 |
| 3 | 4 538 | 95 | | 11 | 899 | 82 |
| 4 | 18 | 13 | | 12 | 2 991 | 122 |
| 5 | 297 | 45 | | 13 | 163 | 41 |
| 6 | 281 | 34 | | 14 | 162 | 26 |
| 7 | 284 | 47 | | **15** | **8 061** | **192** |

Window 15 đứng thứ 2 về raw admission (sau w1: 9 267) nhưng **dẫn đầu tuyệt đối về số symbol** (192,
kế tiếp là w12 với 122) — bất thường. Nhưng: w1 cũng raw-admission cao tương đương (9 267) mà OOS thực
tế chỉ ra 4 trade / PnL 296 (bảng PHẦN 5 trên) — nghĩa là **raw admission cao không tự nó giải thích
được** vì sao riêng w15 nổ ra 1185 trade / PnL 11 423. Phải đào tiếp bên trong w15.

**Bước 2 — bóc theo tháng trong quý w15 (Oct 2025 → Jan 2026):**

| tháng | rows |
|---|---:|
| 2025-10 | **7 604** (94.3% của cả window) |
| 2025-11 | 453 |
| 2025-12 | 4 |

**Bước 3 — bóc theo ngày trong tháng 10/2025:** `2025-10-11` một ngày duy nhất chiếm **6 639/7 604
(87.3% của cả tháng, 82.4% của cả window 15)**, trải trên **149 symbol khác nhau CÙNG NGÀY** — không
phải một vài coin lẻ tẻ mà gần như toàn thị trường cùng lúc.

**Đối chiếu sự kiện thật:** ngày 10-11/10/2025 là sự kiện **crash/thanh lý hàng loạt lớn nhất lịch sử
crypto derivatives** — tổng thanh lý toàn thị trường **>19 tỷ USD** (~1.6 triệu tài khoản), BTC giảm
~14.5% trong vài giờ, ETH ~12-16%, nhiều altcoin sập **50-90%**, khởi phát từ tin thuế quan 100% của Mỹ
với Trung Quốc và bị khuếch đại bởi lỗi định giá tài sản thế chấp trên Binance + đòn bẩy quá mức. Đây
KHÔNG phải regime bình thường hay lỗi dữ liệu — là một sự kiện thị trường có thật, cực đoan, một-lần
(nguồn: CryptoRank, CoinGecko, FTI Consulting — xem link cuối báo cáo).

**Kết luận:** đóng góp 70.5% tổng PnL của window 15 KHÔNG đến từ "regime altseason kéo dài" hay từ cơ
chế `TS_RATCHET_DECOUPLED` hoạt động tốt hơn — nó đến gần như hoàn toàn từ việc chiến lược **vô tình
bắt được biến động cực đoan trong ĐÚNG MỘT NGÀY** (10/10-11/10/2025), một sự kiện black-swan không lặp
lại theo lịch sử ổn định. Đây cũng giải thích tại sao window 15 vừa là window PnL cao nhất **vừa** là
window maxDD tệ nhất (34.3%) — biến động cực đoan tạo cả cơ hội lẫn rủi ro đuôi cùng lúc, đúng loại
"đuôi lớn (maxDD) mà ăn thì ít" Uni nêu ra đầu phiên, chỉ có điều ở đây "ăn" lại rất nhiều vì mô phỏng
tình cờ đứng đúng phía có lợi trong 1 ngày.

**Thêm 1 bằng chứng phụ đã có sẵn từ A/B cô lập trước đó:** `TS_RATCHET_DECOUPLED=true` cho w15 ra
oosPnl 11 423, còn `false` ra 11 611 — **chênh chưa tới 1.6%**. Nghĩa là dù bật hay tắt cờ đang test,
kết quả window 15 gần như không đổi. ⇒ Ngay cả nếu chấp nhận đóng góp của w15, nó **không phải nhờ**
cơ chế ratchet-decouple — cờ này không có tác động đáng kể tới đúng window đang chiếm áp đảo PnL.

⇒ **Verdict FAIL ở PHẦN 5 giữ nguyên, và độ tin cậy của nó còn THẤP HƠN con số cho thấy**: loại bỏ
window 15 (vì lý do black-swan 1-ngày, không phải edge lặp lại được), 15 window còn lại gần như chắc
chắn cho WFE trung vị thấp và %OOS-dương cũng chỉ quanh mức đã tính (median tính trên 15 window không
đổi nhiều vì thứ hạng window 15 vẫn ở cuối dù loại bỏ, do nó vốn đã là outlier).

## Việc còn treo (chưa làm, ghi lại để không quên)

- Root cause bug `WfoWorker`/`WfoJobStore` bỏ qua env override — **chưa tìm ra**, cần ghi vào
  `INFRA_FACTS.md` như rủi ro hạ tầng đang mở (ảnh hưởng mọi confirm dùng cờ qua env trong `WfoWorker`
  fanout, không riêng flag này).
- Root cause bug `bg_run` báo SUCCESS giả — chưa tìm ra, đã workaround bằng `nohup` trực tiếp.
- Sửa `gap = min(peak×giveback, TS_MAX_GAP)` → `max(peak×giveback, minGap)` (PHẦN 2/PHẦN 4) — vẫn
  CHƯA làm.
- ✅ Điều tra window 15 — ĐÃ XONG (mục trên): black-swan 1-ngày (10/10-11/10/2025), không phải regime
  hay genome edge.
- Đề xuất phương pháp mới rút ra từ vụ này: **pre-register một ngưỡng "max %PnL từ 1 window" (vd
  <30-40%) cho mọi confirm 16-window tương lai** — đây là lần thứ 2 liên tiếp (PHẦN 4 rồi PHẦN 5) một
  window chiếm >60% PnL kéo verdict lên giả tạo; nên chặn tự động thay vì phải đào tay mỗi lần.

## Quyết định thuộc Uni

(a) `TS_RATCHET_DECOUPLED=true` **KHÔNG đạt**, và window 15 đã xác nhận là black-swan không lặp lại
    được — dừng thử biến này, quay lại sửa `min→max` giveback (mục còn lại của nhánh exit) hoặc chuyển
    hẳn sang NHÁNH A (fix harness); hoặc
(b) Thêm ngưỡng pre-register "max %PnL/1-window" vào quy trình confirm, rồi chạy lại các thử nghiệm
    exit trước đó (bao gồm cả verdict M gốc và exit003) qua lăng kính này để xem chúng có cùng vấn đề
    không; hoặc
(c) Ưu tiên vá bug `WfoWorker`/`JobStore` trước (ảnh hưởng độ tin cậy của MỌI confirm fanout tương lai
    dùng cờ qua env), rồi mới chạy tiếp các thử nghiệm exit khác.

---

**Nguồn tham khảo sự kiện 10/10-11/10/2025:**
- [The October 11, 2025 Crypto Market Crash: Situation Overview — CryptoRank.io](https://cryptorank.io/insights/analytics/crypto-market-crash-2025-10-11-overview)
- [What Is October 10th? Crypto's 10/10 Mass Market Liquidation Event — CoinGecko](https://www.coingecko.com/learn/october-10-crypto-crash-explained)
- [Crypto Crash Oct 2025: Leverage Meets Liquidity — FTI Consulting](https://www.fticonsulting.com/insights/articles/crypto-crash-october-2025-leverage-met-liquidity)
