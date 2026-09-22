# RESULT_COST_LIQUIDITY — (2) decile thanh khoản/biến động trên 1089 lệnh T170 + (1) audit mô hình chi phí & điểm hòa vốn

Ngày: 2026-09-23. Pre-reg: `docs/PREREG_COST_LIQUIDITY.md` (**commit `cd5e758`**, chốt TRƯỚC khi đo;
sau đó **không sửa thiết kế**). Script: `research/analysis/liq_decile_t170.py` (việc 2),
`research/analysis/cost_breakeven.py` (việc 1). **Thuần Python** — **không** chạy Java trên Oracle
(đang có job shadow), **không** `claude-run`/Claude Code, **không push**, **không chạm HOLDOUT 2026**
(mốc dữ liệu ≤ 2025-12-31). Trung gian: `/tmp/liq_decide/` (dọn sau khi commit).

---

## 0. KẾT LUẬN (một dòng mỗi việc)

> **(2) KHÔNG cắt bớt universe theo thanh khoản.** Decile **kém thanh khoản nhất KHÔNG lỗ** — nó
> **lãi nhiều nhất** (`+4,927%/lệnh`, CI95 block-ngày `[+2,974%, +8,159%]`, 99/109 lệnh lãi), còn decile
> **thanh khoản cao nhất lại lãi ít nhất** (`+1,754%`). Quét **8 ngưỡng cắt** (p = 0…60) đều cho
> `meanP_net` **đi ngang 3,32–3,78%** ⇒ cắt chỉ **làm mất 10–64% lãi** mà **không** cải thiện chất lượng
> mỗi lệnh. Tương quan hạng giữa `L60` và net%/lệnh ≈ **0** (`rho = −0,0086`, `p = 0,78`) ⇒ **không có
> tín hiệu để cắt**, không phải "tín hiệu yếu".
>
> **(1) Mô hình chi phí của sim KHÔNG khớp thực tế — nó ĐẮT hơn 4–20 lần.** `calTp()` trừ
> **0,800% round-trip** mỗi lệnh (= `RATE_FEE`×1 chân **0,20%** + `SLIPPAGE_RATE`×2 chân **0,60%**, **phẳng,
> không phân biệt thanh khoản**), trong khi thực tế Binance USDⓈ-M là **0,04% (maker) – 0,10% (taker)**.
> Nhưng **mọi nhóm lệnh đang chạy đều có `c*` ≫ 0,10%**: T170 toàn bộ `c* = +5,244%`,
> selector `+4,221%`, BIG_DOWN `+4,786%`, DCA `+52,888%`, neo MOM15 `+1,769%` ⇒ **chi phí KHÔNG phải
> nút thắt của chúng**. Ngược lại, **2 ứng viên quay vòng gần nhất có `c*` ÂM** (FUNDING_TOPK K=20
> `−0,046%`, RANGE4H K=10 `−0,325%`) ⇒ chúng **chết trước cả phí** (`slip × turnover`); giảm phí về 0
> cũng **không** cứu. **Cần giảm slip tới đâu**: với 2 ứng viên đó là **bất khả** (phải giảm slip về
> **âm**); với T170/MOM15 thì **không cần giảm gì** — dư địa còn 4,2–52,9% / 1,77%.

| Việc | Quyết định | Căn cứ |
|---|---|---|
| (2) Cắt universe theo thanh khoản | **KHÔNG** | d1 (kém thanh khoản nhất) `+4,927%` CI ngoài 0 **về phía DƯƠNG**; `rho ≈ 0`; mọi ngưỡng cắt đều trung tính hoặc hại |
| (1) Mô hình chi phí | **khớp CÁCH ÁP, lệch MỨC** — đóng kín 1089/1089 lệnh, nhưng đắt 4–20× | `fee_slip` = 0,800000% đúng 1089/1089; `RATE_PROFIT_STOP_MARKET` **không phải** chi phí; `DumpConfig` in sai 0,010 |
| (1) Giảm slip tới đâu mới có cửa | T170/MOM15: **không cần**; 2 ứng viên: **vô vọng** | `c*`: T170 +5,244%, MOM15 +1,769%, FUNDING_TOPK K=20 −0,046%, RANGE4H K=10 −0,325% |

---

## 1. Tuân thủ + cổng tự-kiểm

| Cổng | Kỳ vọng | Vòng này | Đạt |
|---|---|---|---|
| **G1** md5 `printDone.csv` | `efb793e2468ca3a7318da0f0ad23d4fc` | `efb793e2468ca3a7318da0f0ad23d4fc` | ✔ |
| G1 n dòng | 1089 | 1089 | ✔ |
| **G2** `raw.v == totalUsdt` (Aerospike) | phải khớp | khớp **byte** (BTCUSDT `2025-12-01 00:09 UTC` = **104 505 976.0** cả 2 nguồn) | ✔ |
| G2 `raw.v == volume`(printDone) cho 1089 lệnh | ≥ 95% | **1089/1089** (sai số tương đối lớn nhất **5,1e−08**) | ✔ |
| **G3** lệnh có nến tại `t` khớp `entry` ±0,5% | 1089 | **1089** (thiếu nến: 0; lệch entry: 0) | ✔ |
| **G4** MOM15 DEV 24h net @0,10% | +1,6690% ±0,05pp | **+1,6690%** | ✔ |
| **G5** không có dòng ≥ 2026 | 0 | **0** (`start` ∈ 2021-07-27 … 2025-12-01, GMT+7) | ✔ |

**Sửa chính tả (không phải sửa thiết kế):** pre-reg §1 **ban đầu** ghi md5 `efb793e2468ca3a7318da0f0f0ad23d4fc`
(**thừa `0f`**) — chuỗi này **chép từ đề bài**, không phải md5 tự tính. md5 thật của file là
`efb793e2468ca3a7318da0f0ad23d4fc`; đã đối chiếu `md5sum` 2 lần và **đã sửa lại đúng trong pre-reg**.

---

## 2. Chứng minh nguồn thanh khoản (làm trước khi đo)

`test.kline_1m_opt` (127.0.0.1:3222) — key `yyyyMMdd-HHmm` **GMT+7**, bin `data` =
**Snappy(`MinuteDataFinal` proto)** theo `src/main/proto/MinuteDataFloat.proto`
(`KlineObjectOptimized`: priceOpen(1), maxPrice(2), minPrice(3), priceClose(4), **totalUsdt(5)**).
Giải mã bằng `google.protobuf` (dựng descriptor lúc chạy) + `cramjam.snappy.decompress_raw`.

- Ảnh chụp `20251201-0709` ⇒ 576 symbol; `BTCUSDT` = `{o 89071.296875, h 89240.203125, l 88900.0, c 89101.0, totalUsdt 104505976.0}`.
- Cùng phút đó `raw/BTCUSDT.f32` (ts = 29409129 = phút epoch UTC) = **y hệt** (`totalUsdt 104505976.0`)
  ⇒ **`raw.v` chính là `totalUsdt`** ⇒ dùng `raw/*.f32` làm nguồn thanh khoản là hợp lệ, **không** cần Aerospike cho phần đo.
- `printDone.volume` = `totalUsdt` **của chính phút vào lệnh** ⇒ **không causal**, chỉ dùng đối chiếu.

**Quy ước thời gian đã kiểm:** `start`/`time_start_format` là **GMT+7**; `t` = nến UTC = `start − 7h`.
Chứng minh: PIPPIN `start = 20251201 07:09` → nến UTC `2025-12-01 00:09` có `close = 0,14737` **đúng bằng** `entry` trong printDone.

---

## 3. VIỆC (2) — decile thanh khoản (1089/1089 lệnh dùng được, coverage `L60` = 100%)

Chỉ số **causal**: `L60` = mean `totalUsdt` trên `[t−60, t−1]` (nến `t` **không bao giờ** được đọc).
Decile **rank-based** tất định trên **đúng 1089 lệnh**, decile **1 = kém thanh khoản nhất**.

### 3.1 Bảng CHÍNH — decile theo `L60`

| d | n | ΣPnL (USDT) | meanP_net (%) | mean_gross (%) | win% | slip_proxy (%) | `L60` median (USDT/phút) | %ΣPnL | CI95 `meanP_net` (block-ngày) |
|---|---|---|---|---|---|---|---|---|---|
| **1** | 109 | **10 672,9** | **+4,927** | +6,439 | 90,8 | 1,3265 | 2,20e+04 | 14,0% | **[+2,974, +8,159]** |
| 2 | 109 | 6 985,0 | +3,664 | +4,680 | 89,9 | 1,5613 | 5,83e+04 | 9,2% | [+1,975, +5,903] |
| 3 | 109 | 8 664,5 | +4,387 | +5,696 | 88,1 | 2,3258 | 9,96e+04 | 11,4% | [+2,340, +7,541] |
| 4 | 109 | 3 746,8 | +1,916 | +4,554 | 84,4 | 2,0383 | 1,62e+05 | 4,9% | [+0,924, +6,692] |
| 5 | 108 | 8 480,8 | +4,541 | +5,000 | 86,1 | 2,1461 | 2,19e+05 | 11,1% | [+1,208, +7,687] |
| 6 | 109 | 10 359,3 | +4,944 | +6,138 | 85,3 | 2,1243 | 3,12e+05 | 13,6% | [+2,102, +8,944] |
| 7 | 109 | 9 376,3 | +4,285 | +6,757 | 88,1 | 2,3594 | 4,61e+05 | 12,3% | [+1,766, +11,174] |
| 8 | 109 | 10 422,2 | +4,637 | +5,470 | 91,7 | 2,1967 | 7,35e+05 | 13,7% | [+3,172, +6,087] |
| 9 | 109 | 4 363,0 | +2,130 | +3,927 | 88,1 | 2,1896 | 1,28e+06 | 5,7% | [+0,957, +5,941] |
| **10** | 109 | **2 999,4** | **+1,754** | +3,775 | 87,2 | 2,2086 | 3,35e+06 | **3,9%** | [+0,529, +6,308] |
| **Σ** | **1089** | **76 070,2** | **+3,773** | +5,244 | 88,0 | 2,0476 | — | 100% | — |

`slip_proxy` = mean `0,5·(high−low)/close` tại nến vào lệnh — **ƯỚC LƯỢNG biến động, KHÔNG phải slip đo được**.

- **Trả lời câu hỏi quyết định:** decile **kém thanh khoản nhất** net = **+4,927%/lệnh**
  (ΣPnL **+10 672,9 USDT**, n = 109, **99/109 lệnh lãi**, win 90,8%), CI95 **hoàn toàn dương**.
  ⇒ **KHÔNG lỗ** ⇒ **không có lý do cắt vì lý do "nhóm kém thanh khoản lỗ"**.
- **Tập trung PnL:** decile thanh khoản **cao nhất** chỉ đóng góp **3,9%** ΣPnL; **top-3 decile thanh khoản cao**
  (d8+d9+d10) = **23,4%**; **bottom-3** (d1+d2+d3) = **34,6%**. ⇒ PnL **phân tán**, hơi nghiêng về phía **kém thanh khoản**.

### 3.2 Tương quan hạng (Spearman) chỉ số ↔ net%/lệnh

| Chỉ số | `rho` | p (2 phía) | n |
|---|---|---|---|
| `L60` (thanh khoản 60′) | **−0,0086** | 0,778 | 1089 |
| `L240` (thanh khoản 240′) | **−0,0233** | 0,443 | 1089 |
| `R1` (biên độ nến `t−1`) | **+0,0310** | 0,307 | 1089 |
| `R15` (biên độ 15′) | **+0,0525** | 0,084 | 1089 |

⇒ **Không** chỉ số nào có quan hệ đơn điệu đáng kể với lợi nhuận mỗi lệnh. "d1 lãi nhất" trong §3.1 là
**nhiễu mẫu**, không phải một edge thanh khoản — nhưng điều đó **củng cố** kết luận **không cắt**, vì cắt
theo một biến **không có quan hệ** với kết quả thì chỉ **giảm n**, không **tăng chất lượng**.

### 3.3 Quét ngưỡng cắt (BÁO HẾT — không chọn ngưỡng tốt nhất)

Cắt = giữ lệnh có `L60 ≥` phân vị `p` của chính 1089 lệnh:

| p | n giữ | %lệnh bị cắt | ΣPnL giữ | meanP_net giữ (%) | win% giữ | %ΣPnL giữ |
|---|---|---|---|---|---|---|
| 0 (không cắt) | 1089 | 0,0% | 76 070,2 | **+3,773** | 88,0 | 100,0% |
| 5 | 1034 | 5,1% | 68 340,2 | +3,597 | 87,5 | 89,8% |
| 10 | 980 | 10,0% | 65 397,3 | +3,634 | 87,7 | 86,0% |
| 20 | 871 | 20,0% | 58 412,2 | +3,631 | 87,4 | 76,8% |
| 30 | 762 | 30,0% | 49 747,7 | +3,525 | 87,3 | 65,4% |
| 40 | 653 | 40,0% | 46 000,9 | +3,784 | 87,7 | 60,5% |
| 50 | 545 | 50,0% | 37 520,1 | +3,646 | 88,1 | 49,3% |
| 60 | 436 | 60,0% | 27 160,8 | +3,315 | 88,8 | 35,7% |

**Đọc theo quy tắc đã chốt trước (§3.4 pre-reg):** `meanP_net` **KHÔNG** tăng đơn điệu ở `p ∈ {5…40}`
(chuỗi `3,773 → 3,597 → 3,634 → 3,631 → 3,525 → 3,784` — dao động ±0,26pp, **không** xu hướng) **VÀ**
CI95 decile thấp nhất **KHÔNG** nằm ngoài 0 về phía âm (`[+2,974, +8,159]`).
⇒ **KẾT LUẬN: KHÔNG CẮT UNIVERSE THEO THANH KHOẢN.** Cắt ở `p = 60` (bỏ 60% lệnh kém thanh khoản nhất)
**giảm 64,3% ΣPnL** mà `meanP_net` **giảm** 0,46pp ⇒ thuần thiệt.

### 3.4 PHỤ — decile theo chỉ số khác (dán nhãn rõ, KHÔNG dùng để tuyên bố)

| Chỉ số | decile 1 (nhỏ nhất) | decile 10 (lớn nhất) | CI95 d1 | CI95 d10 | đọc |
|---|---|---|---|---|---|
| `L240` (thanh khoản 240′) | +4,898% | +3,024% | [+3,702, +6,984] | [+0,597, +6,235] | cùng hướng `L60`: kém thanh khoản vẫn **lãi**, không âm |
| `R1` (biên độ nến `t−1`) | +4,998% | +6,082% | [+0,203, +13,503] | [−2,973, +13,731] | biến động **cao hơn** → lãi **cao hơn** (nhưng d10 CI **chứa 0**) |
| `R15` (biên độ 15′) | +3,508% | **+13,942%** | [−0,445, +11,110] | **[+6,071, +15,366]** | biến động cao → lãi cao (đây là **dấu ngược** với "cắt theo thanh khoản") |

⇒ Cả 3 chỉ số phụ **đều không** cho thấy nhóm "xấu" (kém thanh khoản / biến động nhỏ) bị **lỗ**. Nếu cắt
theo **biến động thấp** thì lại **cắt mất nhóm lãi nhất**.

### 3.5 Giới hạn nhận thức (đã ghi trước ở pre-reg §3.5)

Decile ở đây là **trên chính 1089 lệnh của MỘT run** (`X1_GS_T170_2021`) ⇒ lệnh tồn tại **chỉ vì selector
đã chọn coin đó** (**selection bias**). Kết luận đúng phạm vi: *"trong các coin T170 **đã chọn**, nhóm
thanh khoản thấp **không lỗ**"* — **KHÔNG** suy ra *"coin thanh khoản thấp nói chung có lãi"*.
Ngoài ra `meanP_net` mỗi lệnh (~+4,57% net ở chi phí sim) **không phải** CAGR tài khoản: phép cộng theo
lệnh **bỏ qua** ràng buộc vốn/số vị thế đồng thời (`U_MAX = 0,60` equity, `BASE_BUDGET ≈ 700 USDT/lệnh`).

---

## 4. VIỆC (1) — audit MÔ HÌNH CHI PHÍ

### 4.1 Kiểm kê hằng số (đọc CODE, không suy đoán)

**a) `src/main/java/.../tradecore/Configs.java`**

| Hằng | Giá trị | file:dòng | Bản chất |
|---|---|---|---|
| `RATE_FEE` | **0,002** | `Configs.java:103` | **CHI PHÍ** — phí sàn, trừ **1 lần** trên notional entry |
| `SLIPPAGE_RATE` | **0,003** | `Configs.java:117` | **CHI PHÍ** — trượt giá **mỗi chân**, áp **×2** (entry + exit) |
| `APPLY_SLIPPAGE` | `true` | `Configs.java:125` | công tắc (đang BẬT) |
| `APPLY_FUNDING_FEE` | `false` (default) | `Configs.java:132` | công tắc funding; **profile bật `true`** |
| `FUNDING_MARK_NOTIONAL` | `false` (default) | `Configs.java:137` | cách tính funding; **profile bật `true`** |
| `FUNDING_SCALE` | 1,0 | `Configs.java:105` | hệ số nhân funding (stress) |
| `RATE_PROFIT_STOP_MARKET` | 0,03 | `Configs.java:169` | **KHÔNG PHẢI CHI PHÍ** — xem §4.3 |
| `LEVERAGE_ORDER` | 1 | `Configs.java:102` | đòn bẩy (1×, không phải chi phí) |

**b) `profiles/x1_gs_t170.properties` (profile ĐANG chạy của run T170)**

`SIM_RATE_PROFIT_STOP_MARKET=0.07` · `SIM_APPLY_FUNDING=true` · `SIM_FUNDING_MARK=true` ·
`SIM_RATE_FEE` **KHÔNG có** (⇒ dùng default code 0,002) · `SIM_SLIPPAGE_RATE` **KHÔNG có** (⇒ 0,003) ·
`SIM_FUNDING_SCALE` **KHÔNG có** (⇒ 1,0) · `CAPITAL_START=35000` · `LEVERAGE_ORDER` ⇒ 1.
⇒ **Profile không hề đụng vào phí/slip** ⇒ chi phí của run T170 = **hằng số code**.

**c) Có phân biệt maker/taker không?** **KHÔNG.** Sim chỉ có **một** `RATE_FEE` cho mọi chân (không đọc
`makerCommission`/`takerCommission`), không có spread/book, không có `MM` riêng. Và **không theo thanh khoản**:
mọi lệnh trả **cùng 0,30%/chân slip** bất kể `totalUsdt` là 2e4 hay 3e6 USDT/phút.

### 4.2 Mô hình ĐÓNG KÍN trên đúng 1089 lệnh (kiểm chứng số học)

`calTp()` — `research/OrderTargetInfoTest.java`, gọi trong `TraceOrderDone.printOrderTestDone`:

```
pnl = qty·(tp − entry) − qty·entry·RATE_FEE − qty·entry·SLIPPAGE_RATE·2 − calFundingFee()
```

| Đại lượng | Quan sát |
|---|---|
| `fee_slip` = `(qty·entry·0,002 + qty·entry·0,003·2)/margin` | **0,800000%** — **min = median = max = mean** |
| Số lệnh khớp **đúng** 0,800000% (\|Δ\| < 1e−6 pp) | **1089/1089** |
| `funding_pct` = `−funding/margin` (âm = ĐƯỢC thu) | mean **+0,1209%**, median 0,0000% |
| `cost_implied` = `gross% − net%` | mean **0,6791%**, median **0,8000%** |
| Sai số đóng \|`cost_implied` − (0,80 − `funding_pct`)\| | max **1,0e−05 pp** ⇒ **mô hình khớp tuyệt đối** |

⇒ Chi phí của run T170 = **0,800% round-trip + funding**, **phẳng** cho mọi lệnh.

### 4.3 Hai phát hiện audit

1. **`SIM_RATE_PROFIT_STOP_MARKET` / `RATE_PROFIT_STOP_MARKET` KHÔNG phải chi phí.** Nó là **khoảng dời SL
   tối thiểu** (ngưỡng ARM trailing stop) tại `Configs.java:169`, **không** trừ vào PnL. Nó **được chỉnh VÌ**
   chi phí — comment `Configs.java:164` ghi rõ: *"nâng 0,01032 → 0,03. Lý do: round-trip cost
   (RATE_FEE 2 chan 0.002 + SLIPPAGE_RATE 2 chan 0.003 = 0.008) ăn hết lợi nhuận của bất kỳ lệnh nào thoát
   dưới ~0,016 profit"* — nhưng bản thân nó là **tham số exit**, **không phải** chi phí. Đếm nó vào chi phí
   (như giả thuyết trong đề bài) là **cộng sai 2 lần**: một lần hoang tưởng về chi phí, một lần bỏ qua rằng
   nó **làm thay đổi hành vi exit**. `AUDIT_BIGDOWN_DEEP.md:183` đã ghi nhận đúng điều này.
2. **Mâu thuẫn nội bộ về con số round-trip.** `DumpConfig.java:68` in
   `derived.cost_roundtrip=%.5f (fee %.5f x2 + slip %.5f x2)` = **2·0,002 + 2·0,003 = 0,010**, trong khi
   đường **thật** `calTp()` trừ **`RATE_FEE`×1 + `SLIPPAGE_RATE`×2 = 0,008**. Kiểm chứng trên dữ liệu:
   `fee_slip` mean = **0,800000%** ⇒ **con số đúng là 0,80%**, con số 1,00% chỉ là **dòng in**.
   Thêm một mâu thuẫn nữa: `config.properties` của chính run ghi *"RATE_FEE=0.001 (code dung 0.002)"* ở
   khối 20 key đã bị xoá vì *"giá trị của chúng trong file cũ là SAI SỰ THẬT"*.
   ⇒ **Quy tắc: lấy chi phí từ `calTp()` + `fee_slip` tính từ dữ liệu, KHÔNG đọc DumpConfig.**
3. **Sim không phân biệt maker/taker, không theo thanh khoản, không có spread.** Trong khi proxy biến động
   1 phút cho thấy chênh lệch **rất lớn** giữa các nhóm: `slip_proxy`/lệnh = **1,2881%** (selector) ·
   **3,6943%** (BIG_DOWN) · **12,8022%** (DCA_LEVEL1); và giữa decile thanh khoản: 1,33% → 2,36%.
   ⇒ mô hình slip **phẳng 0,30%/chân** vừa **quá thấp** cho DCA/BIG_DOWN (nếu proxy đúng), vừa **quá cao**
   cho các lệnh selector thanh khoản (nếu ước lượng công nghiệp 0,02–0,10% đúng).

### 4.4 Điểm hòa vốn theo nhóm lệnh — `net(c) = mean(gross) − c`, `c` = chi phí **round-trip**

| Nhóm | n | mean gross (%) | funding thực (%/lệnh) | `slip_proxy` (%) | net@0,02% maker | net@0,05% | net@0,10% taker | net@0,15% | **`c*` (chi phí tối đa còn dương)** |
|---|---|---|---|---|---|---|---|---|---|
| **T170 TOÀN BỘ** | 1089 | **+5,244** | +0,1209 | 2,0476 | +5,224% | +5,194% | +5,144% | +5,094% | **+5,244%** |
| `PREDICT_SYMBOL_TRADE` (selector) | 821 | **+4,221** | +0,1479 | 1,2881 | +4,201% | +4,171% | +4,121% | +4,071% | **+4,221%** |
| `BIG_DOWN` | 248 | **+4,786** | +0,0413 | 3,6943 | +4,766% | +4,736% | +4,686% | +4,636% | **+4,786%** |
| `DCA_LEVEL1` | 20 | **+52,888** | +0,0000 | 12,8022 | +52,868% | +52,838% | +52,788% | +52,738% | **+52,888%** |
| **Neo MOM15** (M-LEVEL k=1, HOLD 24h, DEV) | 7128 | **+1,769** | −0,1004 | 1,1769 | +1,749% | +1,719% | **+1,669%** ✔(G4) | +1,619% | **+1,769%** |
| `FUNDING_TOPK_ROTATE` **K=20** (8h) | 8758 chu kỳ | **−0,046** | (đã gộp) | 0,1495/chu kỳ | −0,066% | −0,096% | −0,146% | −0,196% | **−0,046% (ÂM)** |
| `FUNDING_TOPK_ROTATE` K=5 (đối chiếu) | 8758 | **−0,122** | (đã gộp) | 0,2660 | −0,142% | −0,172% | −0,222% | −0,272% | **−0,122% (ÂM)** |
| `RANGE4H_TOPK` **K=10** (4h) | 8758 | **−0,325** | (đã gộp) | 0,3857 | −0,345% | −0,375% | −0,425% | −0,475% | **−0,325% (ÂM)** |

**Đọc bảng:**

- **Nhóm đang chạy (T170 3 nhóm + MOM15) có dư địa chi phí khổng lồ**: `c*` từ **+1,769%** (MOM15) đến
  **+52,888%** (DCA). Ở **mức chi phí thực tế 0,04–0,10%**, **mọi** nhóm vẫn dương rất đậm ⇒ **chi phí
  KHÔNG phải nút thắt** của chúng. Kể cả ở **0,15%** (1,5× taker) vẫn dư.
- **2 ứng viên quay vòng gần nhất có `c*` ÂM** ⇒ **không tồn tại mức phí nào** cứu được: phải có **phí ÂM**
  mới hòa vốn. Đúng như pre-reg tiên lượng, nút thắt là **slip × turnover**, không phải phí exchange
  (khớp `RESULT_FUNDING_TOPK_K13.md` §4 và `RESULT_RANGE4H_TOPK.md` §5).
- **`DCA_LEVEL1` n = 20** — mẫu rất nhỏ, `c*` lớn chủ yếu do **cổng lọc mẫu** (leg DCA chỉ còn khi
  vị thế đã hồi mạnh), **đừng** đọc +52,888% như "edge"; đọc như "không thể chết vì chi phí".

### 4.5 Mô hình chi phí có khớp THỰC TẾ không?

**Mốc thực tế dùng được (đọc docs, không tự bịa):** `docs/PREREG_HARNESS_CONTROL.md:38`
(*"taker `0.0005×2 = 0,10%` + slippage 0,5×(high−low)/entry + funding"*);
`docs/PREREG_HEDGE_OVERLAY_A.md:117` và `docs/DESIGN_HEDGED_BOOK.md:112` (*"taker fee 0,05%, slippage 1bp"*).
⇒ Binance USDⓈ-M: **maker 0,02%/chân, taker 0,05%/chân** ⇒ round-trip **0,04% / 0,10%**.

| Thành phần | Sim T170 | Harness Python | Thực tế (Binance) | Sim ÷ thực tế |
|---|---|---|---|---|
| Phí (round-trip) | **0,200%** (`RATE_FEE`×1 chân) | 0,100% (taker×2) | **0,040%** maker / **0,100%** taker | **2,0×** vs taker, **5,0×** vs maker |
| Slip (round-trip) | **0,600%** (`SLIPPAGE_RATE`×2, **phẳng**) | 2 × proxy 1m (**2,05%/chân** đo được ⇒ ~4,1% RT) | ~0,02–0,10% (ước lượng) | **6–30×** (nếu lấy 0,02%) |
| Tổng round-trip | **0,800%** + funding | ≈4,20% + funding | 0,04–0,20% | **4–20×** |
| Funding | CÓ (`SIM_APPLY_FUNDING=true`, `SIM_FUNDING_MARK=true`) | CÓ | CÓ | **khớp** |
| Maker/taker | **không phân biệt** | taker | có 2 mức | **thiếu** |
| Theo thanh khoản | **không** | có (qua range) | có (impact ∝ size/liquidity) | **thiếu** |

**Kết luận khớp:** mô hình sim **khớp về CÁCH ÁP** (đóng kín 1089/1089, gồm cả funding, không bỏ sót chân
nào) nhưng **lệch về MỨC theo hướng BẢO THỦ (đắt hơn) 4–20 lần**, và **sai về CẤU TRÚC** ở đúng 2 điểm
quan trọng: **không có giá maker** và **slip không co giãn theo thanh khoản/biến động**.

**Bằng chứng slip ĐO ĐƯỢC (fill thật): KHÔNG CÓ trong repo** — đã quét:
`ledger.csv` ở gốc là dữ liệu **test tổng hợp** (`AAAUSDT`/`CCCUSDT`, `ts=0`, `HedgeBook` mock), **không**
phải fill thật; `docs/PHASE1_DECISION_SURFACE.md:40` ghi thẳng *"CÒN THIẾU: giá trị fee/slippage BASE chưa
xác nhận"*; `docs/ROADMAP.md:67` để ngỏ *"Calibrate chi phí từ log product thật khi có"*.
⇒ Mọi con số "slip" ở đây là **proxy `0,5·(h−l)/c`** — đo **biến động**, **KHÔNG** đo **tác động thị trường**
(tác động thật còn phụ thuộc **size lệnh**; ở đây size ≈ `BASE_BUDGET ≈ 700–5 000 USDT` trên coin có
2e4–3e6 USDT/phút ⇒ impact thật thường **nhỏ hơn proxy nhiều**). **Không được** dùng proxy này làm "slip thực".

---

## 5. Giới hạn + việc nên làm tiếp (không tự ý làm)

1. **Chưa có fill thật** ⇒ không hiệu chỉnh được slip. Việc cần: ghi `orderId` + giá khớp thật từ
   shadow/live vào log, rồi so `giá khớp − giá nến` ⇒ có **slip thật** để thay `SLIPPAGE_RATE` phẳng.
2. **Một run duy nhất** (`X1_GS_T170_2021`) ⇒ decile có **selection bias**. Muốn kết luận về universe cần
   chạy decile trên **nhiều run / nhiều thời kỳ** hoặc trên **pool coin đủ điều kiện** (không qua selector).
3. **Chi phí là "biến ẩn" của mọi kết luận NO-GO trước đây**: các luật quay vòng dùng proxy
   `0,5·range` ⇒ cost 0,19–1,11%/chu kỳ **do proxy**, không do phí. Nếu sau này có slip thật nhỏ hơn,
   **phải chạy lại** các bảng độ nhạy phí đó (`PREREG_*` khác), **không** được hạ chi phí tuỳ ý tại chỗ.
4. **`DumpConfig` in sai 0,010** và `RATE_PROFIT_STOP_MARKET` dễ bị đếm nhầm là chi phí ⇒ nên sửa **dòng in**
   cho khớp `calTp()` (việc sửa code **ngoài phạm vi** lần này — chỉ báo cáo).

---

## 6. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/PREREG_COST_LIQUIDITY.md` | pre-reg, commit **`cd5e758`** |
| `research/analysis/liq_decile_t170.py` | việc (2): đo causal + decile + CI + quét ngưỡng |
| `research/analysis/cost_breakeven.py` | việc (1): kiểm kê hằng số + kiểm chứng đóng kín + hòa vốn |
| `docs/RESULT_COST_LIQUIDITY.md` | file này |
| `/tmp/liq_decide/` | trung gian (`legs.npz`, `anchor_mom15.npz`, `report_liq.txt`, `report_cost.txt`, `diag.json`, `summary.json`) — **dọn sau khi commit** |

**Commit: `cd5e758`** (pre-reg) + commit kết quả (hash ở `git log`, `KHÔNG push`).

---

## 7. Vệ sinh file tạm (sau commit)

`/tmp/liq_decide/` giữ lại **bằng chứng số nhỏ** (60 KB): `report_liq.txt`, `report_cost.txt`,
`final_liq.log`, `final_cost.log`, `summary.json`, `diag.json`.
Đã **xoá** phần trung gian nặng: `legs.npz` (351 KB), `anchor_mom15.npz` (411 KB, bản sao — bản gốc vẫn ở
`/tmp/.trash_mine/range4h_topk_1790096271/`) và các log chạy trùng (`run*.log`).
Hai script tái tạo lại `legs.npz` được từ nguồn: `python3 research/analysis/liq_decile_t170.py` (đọc
`printDone.csv` + `raw/*.f32`), rồi `python3 research/analysis/cost_breakeven.py`.
