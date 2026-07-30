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
