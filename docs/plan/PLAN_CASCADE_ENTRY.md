# PLAN — CASCADE GATE-FIRST: lọc RẺ trước, chỉ ứng viên ĐẠT mới chạy selector + S1

Trạng thái: **CODE SẴN SÀNG (gated, MẶC ĐỊNH TẮT, CHƯA DEPLOY)** · 2026-09-28 · branch `module`
Key khoá: `ENTRY_CASCADE` (**0 = OFF = hành vi y nguyên = byte-identical**).

> ⚠️ **BẬT cascade = ĐỔI ĐƯỜNG LIVE** ⇒ **PHẢI owner duyệt trước khi deploy** (kể cả shadow). Mặc định
> trong repo là TẮT; không có gì thay đổi cho tới khi có người khai `ENTRY_CASCADE>0` trong profile/env.

Tiền đề:
- `docs/plan/PLAN_CADENCE_SPLIT_V2.md` ghi rõ `predictAllCandidates()` chạy ở **CẢ HAI nhịp** (nằm TRÊN
  ranh giới tách) ⇒ nhịp 1' **không** rẻ đi; vì pool 1 thread mà mỗi lượt ~3–4' ⇒ hàng đợi phình
  (đã deploy 27/09 và **rollback**).
- Đo lại 28/09 trên shadow (log `/home/ubuntu/shadow_c3/app/logs/full.log`, xem §1): **~94% thời gian
  một lượt nằm ở tầng predict toàn universe** — trong khi cổng entry lại ĐÓNG với gần hết ứng viên
  (`n_pass=0` nhiều tuần). Predict là phí.

---

## 1. ĐO CHI PHÍ HIỆN TẠI (VIỆC 0) — từ log shadow, 156 lượt trọn vẹn

Nguồn: `full.log`, lọc thread `pool-1-thread-1`, cắt lượt theo `Start check level change` →
`Finish check level change`, lấy mốc thời gian các dòng pha. **Median (ms)**, láy đúng tập 156 lượt có
đủ mọi mốc (kể cả `[S1] nap 1/1 moc gio close` + `[S1] nap OI`):

| pha | median ms | % lượt |
|---|---:|---:|
| prep: đọc 1000' ticker + tính rate (START→btc) | 1 648 | 0,7% |
| tính level (btc→CheckLevel) | 3 | 0,0% |
| level→MarketLevelChange | 0 | 0,0% |
| **FUNDING predict (mkt→S1 feat-load)** | **215 086** | **94,2%** |
| **S1 nạp feat+OI (→score-ready)** | **10 983** | **4,8%** |
| S1 scoreAll | 10 | 0,0% |
| net015 quantile-map (→MAP) | 15 | 0,0% |
| vòng gate (→GATE) | 2 | 0,0% |
| ghi file (→Predict) | 1 | 0,0% |
| đuôi (→Finish) | 0 | 0,0% |
| **TỔNG (START→Finish)** | **228 228** | 100% |

⇒ **"đắt" = 99,0% lượt** nằm ở đúng 2 bucket: **FUNDING predict (94,2%)** + **S1 nạp OI (4,8%)**.
Phần còn lại (net015/gate/ghi file/prep/tính level) ≈ **1%**.

**Bằng chứng phụ — nhịp thực tế đang bị bóp:** shadow hiện chạy `MARKET_SCAN_MIN=1` +
`MARKET_SCAN_PRIORITY=1` (từ 28/09 12:40) nhưng các lượt chỉ nổ cách nhau ~4' (15:22·15:26·15:30·
15:35·15:39·15:43·15:46·15:51) = **đúng bằng thời gian 1 lượt** ⇒ lưới 1' **bất khả thi** với chi phí này.

Tỷ lệ suy ra (dùng cho mô hình §3): funding ≈ **307 ms/coin** (215 086/700), S1 OI ≈ **15 ms/coin**.

---

## 2. THIẾT KẾ CASCADE (VIỆC 1)

**Key duy nhất:** `ENTRY_CASCADE` (`Configs.java`) — `0`/không khai = TẮT; `>0` = BẬT, giá trị = số ứng
viên **tối đa** giữ lại cho tầng predict (nên = `SELECTOR_RANK_TOPK`).

Luồng khi **BẬT** (trong `checkMarketLevelChange2Trade`):

```
levelChange (rẻ, đã tính)  +  predictData (pred thị trường, đã tính)
        │
        ▼  cascadeUniverse()        ← CHỈ dùng dữ liệu RẺ
   • levelChange != null  → giữ NGUYÊN toàn universe (leg market-signal cần pred rộng)
   • predictData == null  → giữ NGUYÊN (không đủ dữ liệu để gate)
   • còn lại  → cascadeGateFirst(): giữ coin ĐANG GIỮ (DCA) + xếp theo pred cache TĂNG,
                giữ coin mà `marketReturn15M >= EntryGate.threshold(predCache)`, dừng ở topK
        │
        ▼  predictAllCandidates(universe đã lọc)   ← tầng ĐẮT
   • universe rỗng → guard trong predictAllCandidates: clear state + return luôn (KHÔNG đọc OI/basket/CS, KHÔNG ghi file)
   • ngược lại → chạy y hệt code cũ, chỉ trên tập đã lọc
```

`predCache` = `LATEST_SEL_MAPPRED` (net015 đã map, nếu profile C3 bật) → không có thì `LATEST_SEL_PNOPUMP`
(dùng `cachedPredFor`). Coin **chưa có cache** ⇒ **GIỮ** (không bỏ vì thiếu thông tin — chống bỏ sót cold-start).
`ENTRY_CASCADE<=0` ⇒ `cascadeUniverse` **trả về ĐÚNG object đầu vào** ⇒ mọi dòng code phía sau chạy y hệt HEAD.

**KHÔNG chạm** ONNX / `NUM_FEATURES` / `extractFeatures45` — chỉ đổi **tập symbol đưa vào** tầng predict.

---

## 3. CÁCH KIỂM "CASCADE KHÔNG BỎ SÓT" (điều kiện sống còn)

1. **OFF ⇒ byte-identical (chặn bắt buộc, chạy TRƯỚC khi tin bất cứ số nào):** chạy lại **2 lượt parity**
   trên **cùng runner** và đối chiếu `storage/printDone.csv`:
   - KEEPLEG0 nhịp 1': md5 `99e42b75cf1a2142f9cd14dc72e371ba`, n=1085, eq=103083
     (`/home/ubuntu/java/devrun/FG_KEEPLEG0`)
   - T170: md5 `efb793e2468ca3a7318da0f0ad23d4fc`, n=1089, eq=111070
     (`/home/ubuntu/java/devrun/X1_GS_T170_2021`)
   **Lệch ⇒ DỪNG, báo rõ** (nhưng xem ghi chú *về cấu trúc* bên dưới).
   *Chú thích cấu trúc:* sim **không** gọi `DetectEntrySignal2TradeNormal`/`cascadeUniverse` — đường entry
   của sim đọc `symbol2Pred` dựng sẵn (`SimulatorMarketLevelTicker1MStopLoss` dòng ~405–455). Vì vậy thay
   đổi chỉ nằm ở class LIVE + 1 field inert trong `Configs` ⇒ parity sim là **chốt chống hồi quy** (không
   phải nơi chứng minh cascade). Đã có test logic `EntryCascadeTest` chứng minh OFF trả về **cùng object**.
2. **ON == OFF trên cùng dữ liệu (bắt buộc, chạy trên **Kaggle**, không chạy trên Oracle):**
   chạy replay/sim 1 đoạn ngắn (≥ vài ngày DEV ≤2025-12-31) 2 lần: `ENTRY_CASCADE=0` và `ENTRY_CASCADE=8`;
   so **số lệnh + từng leg (symbol, thời điểm, level, size)**. **Không khớp ⇒ cascade BỎ SÓT ứng viên ⇒
   KHÔNG deploy, báo rõ.**
3. **Đếm trực tiếp "ứng viên bị bỏ mà lẽ ra ĐẠT":** khi ON, mỗi lượt log `[CASCADE] ... keep=N` (đã có).
   Bổ sung khi đo: sau vòng gate, nếu có coin bị lọc khỏi universe mà (theo `symbolPred` THẬT của lượt)
   sẽ ĐẠT ⇒ đếm + log `[CASCADE-MISS]`. **Cơ chế chống bỏ sót** đã có sẵn: `ENTRY_CASCADE=0` ⇒ giữ nguyên.
4. **Bất biến test được:** `cascadeGateFirst` (hàm THUẦN) — kết quả **⊆ universe**, luôn giữ held,
   coin chưa cache không bị bỏ, tôn trọng topK. Bằng chứng: `src/test/java/.../EntryCascadeTest.java`
   (5 test PASS, không chạm ONNX/mạng).

---

## 4. CÁCH ĐO CHI PHÍ (VIỆC 2)

Đo **không cần** đụng code prod: mỗi pha đã có dòng log mốc thời gian (`Start…`, `Btc ticker size`,
`Check level market`, `Market level change`, `[S1] nap …`, `[S1] score`, `[MAP]`, `[GATE]`, `Predict:`,
`Finish…`) trên **cùng một thread** (`pool-1-thread-1`). Script phân tích:
`/tmp/tickcost.py` (đọc log, cắt lượt, hiệu mốc → bảng ms). Khi bật cascade, `funding` sẽ tụt theo
`keep.size()`; so **OFF vs ON** bằng cùng script + dòng `[CASCADE]`.

**Mô hình chi phí (từ tỷ lệ đo được §1) — ON (dự phóng, CHƯA đo bằng run):**

| tình huống | công thức | ≈ ms | hệ số giảm |
|---|---|---:|---:|
| OFF (hiện tại) | đo được | **228 228** | 1× |
| ON, cổng ĐÓNG (universe rỗng) | prep | **≈ 1 650** | **≈ 138×** |
| ON, cổng MỞ (≤8 ứng viên) | prep + 8×(307+15) + map/gate/ghi | **≈ 4 300** | **≈ 53×** |

**Nhịp khả thi:** budget/lượt nếu quét mỗi phút = 60 000 ms. ON (kể cả cổng mở, ≈4,3 s) **thừa sức** cho
**1'** (và tất nhiên 5'/15'). OFF (≈228 s) **không** cho 1' (lượt dài hơn khoảng cách nhịp ⇒ phình).

---

## 5. RỦI RO

- **Bỏ sót ứng viên (chính):** gate dùng `predCache` của lượt TRƯỚC ⇒ nếu giá trị đổi mạnh giữa 2 lượt,
  coin "sẽ ĐẠT" có thể bị bỏ. ⇒ **BẮT BUỘC** kiểm §3.2 trên dữ liệu thật trước khi deploy. Cơ chế giảm nhẹ:
  giữ held, giữ coin chưa cache, `topK` ≥ `SELECTOR_RANK_TOPK`.
- **Đổi phân bố feature cross-sectional:** `predictAllCandidates` có PASS-2 rank (#33..#35) và
  `LiveBuildMap.assign` (quantile-map) tính trên **tập** ứng viên ⇒ lọc tập sẽ **đổi giá trị** (kể cả khi
  không bỏ coin nào đáng lẽ ĐẠT). Đây là lý do **ON==OFF có thể KHÔNG khớp** dù logic đúng ⇒ phải đo §3.2.
- **S1/net015:** vẫn cần `selPnp`/`selFeat45` của đúng tập đã lọc; khi universe rỗng thì bỏ luôn (đúng ý).
- **Lưu trữ:** ON chỉ ghi `prediction*` cho ứng viên ĐẠT ⇒ giảm tải đĩa (tốt, đĩa đang 93%).

## 6. ROLLBACK

Tắt key: **`ENTRY_CASCADE=0`** (hoặc bỏ khỏi profile/env) + restart = về **byte-identical HEAD**.
Không cần đổi code, không có di trú dữ liệu.

## 7. CẦN OWNER DUYỆT

1. Duyệt **bật cascade** (đổi đường LIVE) sau khi §3.2 PASS.
2. Duyệt **chạy 2 lượt parity + 2 lượt ON/OFF replay trên Kaggle** (không chạy trên Oracle — shadow đang chạy).
