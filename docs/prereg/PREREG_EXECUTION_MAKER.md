# PREREG_EXECUTION_MAKER — execution realism: maker (post-only) vs taker trên 1089 lệnh T170

Ngày: 2026-09-23. Trạng thái: **chốt TRƯỚC khi chạy script kết quả**. Sau khi commit file này
**không sửa thiết kế**; mọi sai khác phải ghi thành "sửa chính tả" tách bạch (như tiền lệ
`RESULT_COST_LIQUIDITY.md` §1).

**Ràng buộc:** thuần Python, **KHÔNG** Java, **KHÔNG** `claude-run`/Claude Code, **KHÔNG push**,
**KHÔNG** chạm HOLDOUT 2026, **KHÔNG** sửa tham số hệ thống, **KHÔNG** đề xuất tune. Chỉ đo
counterfactual trên **dữ liệu ĐÃ CÓ**.

---

## 0. Câu hỏi + cái KHÔNG làm được

**Câu hỏi:** mô hình chi phí của sim (`calTp()`: `RATE_FEE` 0,002×1 chân + `SLIPPAGE_RATE`
0,003×2 chân = **0,800000%** round-trip, phẳng, không phân biệt maker/taker) lệch thực tế ở đâu,
và **nếu chuyển sang maker (post-only) thì net tốt lên bao nhiêu, ở mức xác suất khớp nào thì hòa vốn?**

**KHÔNG đo được `p` thật.** Repo **không có** dữ liệu order book/L2, không có `orderId`/giá khớp thật
(`RESULT_COST_LIQUIDITY.md` §5.1). ⇒ `p` (xác suất khớp maker) là **GIẢ ĐỊNH QUÉT**, không phải số đo.
Kết quả đúng phải đọc là "**hòa vốn ở p = ?**", không phải "maker lãi hơn".

---

## 1. Nguồn + cổng tự-kiểm (G1–G5) — chạy TRƯỚC mọi phép tính

| Cổng | Kỳ vọng |
|---|---|
| **G1** md5 `printDone.csv` | `efb793e2468ca3a7318da0f0ad23d4fc`, n = **1089** |
| **G2** `notional := quantity×entry` | khớp cột `margin` (sai số tương đối < 1e−6) trên 1089/1089 |
| **G3** chi phí sim tái tạo | `gross% − 100·pnl/notional == 0,80 + funding%` đúng 1089/1089 (sai số < 1e−6, suy ra `funding% = chi_phí_thực − 0,80`) |
| **G4** proxy slip có đủ | nến tại **cả** phút vào (`start`) **và** phút ra (`end`) cho 1089/1089 |
| **G5** không có dòng ≥ 2026 | 0 |

Nguồn: `printDone.csv` (run `X1_GS_T170_2021`), nến `/home/ubuntu/claudedata/rvb_1m/raw/<SYM>USDT.f32`
(`ts<i4,o,h,l,c,v>`, ts = phút epoch UTC — như `liq_decile_t170.py`). `start`/`end` là **GMT+7**.

---

## 2. Đơn vị + hằng số (đọc từ CODE, không bịa)

| Đại lượng | Giá trị | Nguồn |
|---|---|---|
| `gross%ᵢ` | `(tp − entry)/entry × 100 × sign(side)` | cột `profit` (khớp 1089/1089, đã kiểm chứng) |
| `notionalᵢ` | `quantity × entry` | cột `margin` |
| `net_sim%ᵢ` | `100·pnlᵢ/notionalᵢ` | đường **tham chiếu bắt buộc** |
| Chi phí sim RT | **0,800000%** = `RATE_FEE` 0,002×1 + `SLIPPAGE_RATE` 0,003×2 | `Configs.java:103,117` |
| `funding%ᵢ` | `= (gross%ᵢ − net_sim%ᵢ) − 0,800000` | **suy ra từ dữ liệu**, giữ **nguyên** ở mọi kịch bản |
| Phí Binance | maker **0,02%/chân**, taker **0,05%/chân** | `PREREG_HARNESS_CONTROL.md:38`, `PREREG_HEDGE_OVERLAY_A.md:117` |

**Slip proxy (per chân, causal tại đúng phút khớp):** `sᵢ = 0,5·(high−low)/close` của **nến tại
phút vào** (chân entry) và của **nến tại phút ra** (chân exit). Đây là **thước đo BIẾN ĐỘNG, KHÔNG
phải tác động thị trường** (`RESULT_COST_LIQUIDITY.md` §5.2). Vì vậy, ngoài bản "proxy đo được",
mỗi kịch bản có slip còn được lặp lại với **2 mốc thay thế**: `0,140%/chân` (mốc "universe" trong
đề bài — sẽ **đo lại độc lập** ở §5) và `0,01%/chân` (1bp, mốc `PREREG_HEDGE_OVERLAY_A.md`).
Đây là **phân tích độ nhạy**, không phải tune.

---

## 3. Ba kịch bản (chốt)

`net_S%ᵢ = gross%ᵢ − fee_S − slip_Sᵢ − funding%ᵢ`

| # | Kịch bản | fee (RT) | slip (RT) |
|---|---|---|---|
| **S** | sim hiện tại (đối chứng) | 0,20% (0,002×1 chân) | 0,60% (0,30×2) |
| **A** | **taker thật** | 0,10% (0,05×2) | `s_entryᵢ + s_exitᵢ` (proxy) · nhạy: 0,28% · 0,02% |
| **B** | **entry MAKER / exit TAKER** | 0,07% (0,02 + 0,05) | `s_exitᵢ` (entry slip = 0) |
| **C** | **cả hai MAKER** (trần trên lạc quan) | 0,04% (0,02×2) | 0% |

`S` **phải** tái tạo `net_sim%` (G3) — nếu không, dừng.

### 3.1 Xác suất khớp maker `p` (chỉ áp cho B, C)

Quét `p ∈ {0,2; 0,4; 0,6; 0,8; 1,0}` trên **chân entry maker**. Nếu **không khớp ⇒ BỎ lệnh**
(không tính 0 PnL cho lệnh bỏ; lệnh biến mất khỏi tập). Metric **tính lại trên tập còn lại**.

Hai mô hình khớp (cả hai đều pre-reg):
- **(i) i.i.d. ngẫu nhiên** (CHÍNH): mỗi lệnh khớp độc lập xác suất `p`, **không phụ thuộc kết quả
  lệnh**; R = 200 lần rút, seed `20260923` → mô tả mean + CI bootstrap block-72h (như tiền lệ).
- **(ii) bất lợi chọn lọc (adverse selection) — STRESS/CHẶN DƯỚI:** tập còn lại = `round(p·n)` lệnh
  có `net` **XẤU NHẤT** trước (mô hình hoá việc lệnh maker chỉ khớp khi giá đi ngược). Đây là
  **biên dưới**; (i) là **biên trên** ⇒ khoảng chứa giá trị thật.

### 3.2 Chỉ số (mỗi kịch bản × mỗi `p`)

1. `n` lệnh còn lại, `Σnotional`, `Σnet` (USDT)
2. **`meanP/notional`** = mean của `net%ᵢ` (đơn giản, theo lệnh) — và **`agg`** = `Σnet/Σnotional` (theo notional, khớp cách bảng decile cũ)
3. **`win%`** = tỉ lệ `net%ᵢ > 0`
4. **chi phí/lệnh** = `fee_S + mean(slip_Sᵢ) + mean(funding%ᵢ)` (%/lệnh)

### 3.3 ⛳ Hòa vốn `p`

- **Theo LỆNH (per-order):** B/C rẻ hơn A ⇒ `net` mỗi lệnh của B/C ≥ A với **mọi** `p`; chỉ số
  per-order **không phụ thuộc `p`** dưới mô hình (i) (rút i.i.d. ⇒ tập con cùng phân phối). ⇒
  hòa vốn per-order là **tầm thường**; ghi rõ để không đọc sai.
- **Theo TỔNG (bắt buộc):** vì bỏ lệnh làm mất lệnh, định nghĩa
  `Σnet_B(p) = p · Σnet_B(toàn bộ)` (mô hình (i)) ⇒
  **`p*_B = Σnet_A / Σnet_B`** (tương tự cho C). Với mô hình (ii), `p*` = `p` nhỏ nhất sao cho
  tổng net của tập xấu-nhất-trước ≥ tổng net của A. Báo **cả hai** `p*`.
- Lặp `p*` cho **3 mốc slip** (proxy đo được / 0,140% / 0,01%) ⇒ khoảng hòa vốn.

---

## 4. Luật kết luận (chốt trước)

- Báo bảng **3 kịch bản × các `p`**, kết luận bằng **"hòa vốn ở p = ?"** và trả lời thẳng:
  **có đáng theo dõi sang maker không**.
- Nếu net **tăng nhưng `win%` và hình dạng phân phối không đổi** ⇒ ghi rõ **"chỉ đổi thang đo"**
  (bài học SIZING), KHÔNG gọi là "cải thiện chất lượng".
- Nếu kết luận phụ thuộc mốc slip ⇒ ghi rõ **kết luận không bền theo giả định slip**.
- **KHÔNG đề xuất áp dụng.** Mọi thay đổi cần pre-reg riêng + xác nhận live.

---

## 5. Đo lại mốc "universe 0,140%" (kiểm chứng đề bài)

Để không nhận số từ đề bài mà không kiểm: đo **median của `0,5·(h−l)/c` trên TOÀN BỘ nến 1m** của
627 coin có mặt trong 1089 lệnh (không chỉ nến vào lệnh), và **decile biến động cao nhất**. Mục đích:
phân biệt "proxy toàn cục" với "proxy tại đúng phút khớp lệnh" (chọn mẫu theo biến động).
Số này chỉ dùng để **đối chiếu/đặt độ nhạy**, không đổi thiết kế §3.

---

## 6. Sản phẩm + vệ sinh

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_EXECUTION_MAKER.md` | file này (commit TRƯỚC khi chạy) |
| `research/analysis/exec_maker_t170.py` | script counterfactual thuần Python |
| `docs/result/RESULT_EXECUTION_MAKER.md` | kết quả + kết luận |
| `/tmp/exec_maker/` | trung gian — **dọn sau khi commit** |

**Commit, KHÔNG push.**
