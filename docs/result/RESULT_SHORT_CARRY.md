# RESULT_SHORT_CARRY — luồng MỚI: SHORT-side funding harvest (carry)

Ngày: 2026-09-23. Pre-reg: `docs/prereg/PREREG_SHORT_CARRY.md` (**commit `edd1e70`, chốt TRƯỚC khi đo**;
sau đó **không sửa thiết kế**). Script: `research/analysis/short_carry.py`.
**Thuần Python**, 0-sim, **không** Java trên Oracle (shadow active), **không** `claude-run`, **không push**,
**không chạm 2026** (giá `raw/*.f32` hết ở **2025-12-31 16:59 UTC** ⇒ 2026 **không đo được**).
Trung gian **ngoài repo**: `/home/ubuntu/claudedata/short_carry/` (`report.txt`, `summary.json`;
`grid.npz` tái tạo bằng `python3 research/analysis/short_carry.py build` ≈ 114 s).

## 0. KẾT LUẬN (một dòng)

> **NO-GO cả 3 biến thể.** Carry short **THU funding thật** (top-decile = **+0,0251 %/chu kỳ 8h**,
> 85,0% chu kỳ dương) nhưng **quá nhỏ so với chi phí**: cost **0,1599 %/chu kỳ** ⇒ **cost/gross = 810%**.
> Net **V1 −0,1402 %/chu kỳ**, **V3 −0,1127 %**, **V2 −0,3751 %** — cả ba **CI72h×1,21 NGOÀI 0 về phía ÂM**,
> 40,0–44,6% chu kỳ dương (cổng đòi ≥60%), |net| ≥ MDE80. **Đổi sang phía short KHÔNG lật được kết quả
> long-side**: net vẫn âm (long-side cùng harness: −0,0852 %). **Không đề xuất build** (và engine cũng
> **không có đường SELL**).

## 1. Tuân thủ + kiểm chứng tái lập (harness còn lực)

| Kiểm chứng | Vòng này | Tham chiếu | Khớp |
|---|---|---|---|
| `n_elig`/mốc 8h: median / max | **186 / 588** | `RESULT_FUNDING_TOPK_ROTATE.md` §2: 186 / 588 | ✔ |
| Mốc dùng được (`n_elig ≥ 50`) | **5476 / 5477** | idem: 5476/5477 | ✔ |
| Universe | **627** symbol | idem: 627/627 | ✔ |
| Quy ước dấu | `rate>0` ⇒ long TRẢ / short THU | `RESULT_FUNDING_SIGN.md` §0–§1 (2 tầng độc lập) | ✔ |
| `f_cyc` unconditional (universe EW) | mean **+0,0016 %/chu kỳ**, median +0,0100 % | `RESULT_FUNDING_SIGN.md` §0(5): mean rate ≈ +0,16 bp/kỳ ⇒ cùng bậc | ✔ |
| Long-side cùng harness (L1) | DEV **−0,1354 %/chu kỳ** | `RESULT_FUNDING_TOPK_ROTATE` DEV K=20: **−0,1460 %** | ✔ (cùng dấu, cùng bậc) |

⇒ Bộ đo **tái lập đúng** các vòng trước (cùng nguồn, cùng mốc, cùng bậc độ lớn) ⇒ **không VOID**.

## 2. BƯỚC 0 — coverage

| Mục | Kết quả |
|---|---|
| Funding | Aerospike `test.funding_data` (chỉ đọc), bin `f_data` = Snappy(JSON `{ts_ms: rate}`); **831** symbol / **2 394 587** cặp; ts_max 2026-08-05 (chỉ dùng ≤ 2025-12-31) |
| Giá 1m | `raw/<sym>.f32`, **627** file, **619 082 489** dòng (`int32 epoch_minute` + `float32 O/H/L/C/V`), UTC, [2021-01-01, **2025-12-31 16:59**] |
| Universe | **627** = (có giá) ∩ (có funding); **624/627** có record funding; lọc rác `ts < 2021-01-01` (3 symbol) |
| Mốc 8h | **5477** mốc (00/08/16 UTC); **5476** mốc dùng được (`n_elig ≥ 50`; mốc `2021-01-01 00:00` bị loại — chưa có nến) |
| Ô grid hợp lệ | **1 283 879** / 3 434 079 (giá **và** funding) |
| **Quy ước dấu (chốt)** | **`rate > 0` ⇒ long TRẢ, short THU** (Binance nguyên bản, không đảo dấu — `RESULT_FUNDING_SIGN.md`); `f_cyc = 100×Σ rate` trên `(t_entry, t_exit]` |

**Tín hiệu causal đã dùng:** `f_sig(r)` = rate của event cuối cùng có `ts ≤ t_entry` (rate **đã settle**,
KHÔNG nhìn tương lai) — cùng định nghĩa `f_entry` của `funding_factor.py`.

## 3. KẾT QUẢ CHÍNH — 3 biến thể + 2 đối chứng (chi phí chính: taker 0,05%/chân + slip proxy `0,5×(h−l)/c`/chân)

### 3.1 ALL 2021-2025

| Var | N chu kỳ | **net/chu kỳ** | **CI72h×1,21** | %chu kỳ dương | gross | (funding) | cost | turnover (1 vế) | cost/gross | **KL** |
|---|---|---|---|---|---|---|---|---|---|---|
| **V1** pure carry | 5476 | **−0,1402%** | **[−0,2274%, −0,0529%]** | 44,6% | +0,0197% | +0,0251% | 0,1599% | 34,36% | **810%** | **NO-GO** |
| **V2** carry+filter | 3447 | **−0,3751%** | **[−0,5353%, −0,2148%]** | 40,0% | −0,0004% | +0,0434% | 0,3746% | 64,43% | (gross≈0) | **NO-GO** |
| **V3** dollar-neutral | 5476 | **−0,1127%** | **[−0,1358%, −0,0895%]** | 41,7% | +0,0539% | +0,0402% | 0,1666% | 36,23% | **309%** | **NO-GO** |
| U đối chứng: short universe EW | 5476 | −0,0305% | [−0,1167%, +0,0557%] | 45,7% | −0,0299% | +0,0070% | 0,0006% | 0,11% | — | (chứa 0) |
| L1 đối chứng: long bottom-decile (hướng long-side đã thua) | 5476 | −0,0852% | [−0,1799%, +0,0095%] | 50,3% | +0,0882% | +0,0552% | 0,1734% | 38,10% | 197% | (chứa 0) |

### 3.2 DEV 2022-2025 (CHÍNH) — cùng W, chỉ đổi cửa sổ

| Var | N | net/chu kỳ | CI72h×1,21 | %dương | gross | (funding) | cost |
|---|---|---|---|---|---|---|---|
| **V1** | 4382 | **−0,0935%** | [−0,1834%, −0,0037%] | 45,3% | +0,0433% | +0,0174% | 0,1368% |
| **V2** | 2692 | **−0,3542%** | [−0,5229%, −0,1854%] | 39,9% | −0,0165% | +0,0353% | 0,3377% |
| **V3** | 4382 | **−0,1145%** | [−0,1392%, −0,0898%] | 40,7% | +0,0374% | +0,0420% | 0,1518% |
| U | 4382 | +0,0135% | [−0,0742%, +0,1012%] | 46,7% | +0,0141% | −0,0002% | 0,0006% |
| L1 | 4382 | −0,1354% | [−0,2341%, −0,0368%] | 49,4% | +0,0314% | +0,0667% | 0,1668% |

### 3.3 Theo năm (V1, chi phí chính — %/chu kỳ)

| 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|
| −0,3269 | **+0,0405** | −0,1731 | −0,1567 | −0,0846 |

⇒ **1/5 năm dương** (2022) và chỉ nhẹ; không có năm nào đủ để bù các năm còn lại.
**Thêm (độ bền của mean):** median **gross** V1 = **−0,1138 %/chu kỳ** (mean +0,0197 % bị kéo lên bởi
vài chu kỳ đuôi may) ⇒ chu kỳ **điển hình** còn âm hơn cả mean.

### 3.4 Phân rã V1 — bài học "slip × turnover" tái diễn

| Hạng mục | Giá trị |
|---|---|
| Chân giá (short) | **−0,0054 %/chu kỳ** (≈ 0 — short nhóm funding cao **không** được lợi từ giá) |
| **Funding THU** | **+0,0251 %/chu kỳ** (≈ +0,075 %/ngày) |
| Gross | +0,0197 %/chu kỳ — **NHƯNG median gross = −0,1138 %** (mean bị kéo lên bởi vài chu kỳ may) |
| **Cost** | **−0,1599 %/chu kỳ** (turnover 34,36%/chu kỳ; slip chiếm phần lớn) |
| **Net** | **−0,1402 %/chu kỳ** (DEV −0,0935%) |
| **Cost/gross** | **810 %** ← chi phí gấp **8,1×** gross |

## 4. Độ bền theo CHI PHÍ (V1) — "chết vì slip", không vì chọn sai nhóm

| Biến thể chi phí | net/chu kỳ | CI72h×1,21 | %dương |
|---|---|---|---|
| taker 0,05 + slip proxy | **−0,1402%** | [−0,2274%, −0,0529%] | 44,6% |
| maker 0,02 + slip proxy | −0,1196% | [−0,2071%, −0,0320%] | 45,2% |
| taker 0,05 + slip phẳng 0,140%/chân | −0,1108% | [−0,1970%, −0,0247%] | 44,8% |
| taker 0,05 + slip nến-ra | −0,1387% | [−0,2255%, −0,0518%] | 44,7% |
| taker 0,05 + slip **1 bp/chân** (lạc quan phi thực tế) | **−0,0215%** | [−0,1075%, **+0,0645%**] | 46,8% |
| taker 0,05 + **round-trip toàn sổ mỗi chu kỳ** (cận trên) | −0,4150% | [−0,5030%, −0,3269%] | 39,0% |

⇒ **Ngay cả khi slip chỉ 1 bp/chân** (bất khả thi với taker trên perp), net ≈ 0 và **CI chứa 0** ⇒ **không có
"vùng tham số" nào cho carry short dương có ý nghĩa**. Ở biến thể maker (0,02%) vẫn âm rõ.

## 5. RỦI RO SHORT — max adverse excursion (drawup trong `(r, r+480]`) + squeeze

| Var | n vị thế | MAE p50 | p90 | **p99** | max | MFE p50 | **%squeeze >+20%** |
|---|---|---|---|---|---|---|---|
| **V1** | 128 333 | +1,59% | +6,04% | **+20,38%** | **+602,21%** | −1,76% | **1,04%** |
| V2 | 28 206 | +1,81% | +8,87% | +31,48% | +441,00% | −2,20% | 2,56% |
| V3 | 128 333 | +1,59% | +6,04% | +20,38% | +602,21% | −1,76% | 1,04% |
| U | 1 283 879 | +1,61% | +5,67% | +16,44% | +1 302,13% | −1,79% | 0,62% |

Worst 5 (V1): `ALPACAUSDT` 2025-04-30 **+602,21%** (f_cyc +7,65%) · `PEOPLEUSDT` 2024-01-03 +441,00% ·
`HIFIUSDT` 2025-09-12 +401,14% · `HIPPOUSDT` 2025-11-06 +390,90% · `BLESSUSDT` 2025-10-15 +388,05%.

**Đọc:** ~1% vị thế bị **+20% ngược chiều trong 1 chu kỳ 8h**, đuôi tới **+400…+600%** — trong khi gross
kỳ vọng của cả chu kỳ chỉ **+0,02%**. ⇒ **rủi ro squeeze lớn hơn lợi nhuận kỳ vọng ~10^4 lần**; một vị thế
như ALPACA (2025-04-30) **xoá sạch** thành quả của ~30 000 chu kỳ. (Chưa mô hình hoá margin/liquidation.)

## 6. NULL + MDE (không thể "ăn may")

| Var | Null (N coin ngẫu nhiên cùng số lượng, 300 rep, seed 20260905) | p(null ≥ thật) |
|---|---|---|
| V1 | mean **−0,2374%** (p05 −0,2530%, p95 −0,2220%) | **0,000** |
| V2 | mean −0,2546% (p05 −0,2740%, p95 −0,2329%) | 1,000 |

- **MDE80**: V1 **0,10 %/chu kỳ**; V2 0,20%; V3 **0,05%** (V3 có CI hẹp nhất ⇒ lực đo cao nhất).
  |net| của cả 3 biến thể **≥ MDE80** ⇒ kết luận **âm** có **lực thống kê**, không phải "thiếu mẫu".
- V1 "thắng" null (đúng hơn ngẫu nhiên 0,10%/chu kỳ) — nhưng **cả hai đều âm**: chọn đúng nhóm funding
  **không** đủ để bù chi phí.

## 7. ĐỐI CHIẾU — đổi phía có lật không?

| | net/chu kỳ (DEV) | CI | %dương |
|---|---|---|---|
| Long top-K funding nhỏ nhất (vòng trước, `RESULT_FUNDING_TOPK_ROTATE` DEV K=20) | −0,1460% | âm | 48,6% |
| **L1 long bottom-decile (cùng harness, DEV)** | **−0,1354%** | [−0,2341%, −0,0368%] | 49,4% |
| **V1 short top-decile (DEV)** | **−0,0935%** | [−0,1834%, −0,0037%] | 45,3% |
| U short universe EW (DEV) | +0,0135% | [−0,0742%, +0,1012%] | 46,7% |

**Dấu funding ĐỔI thật**: bottom-decile **TRẢ** −0,0552 %/chu kỳ, top-decile **THU** +0,0251 %/chu kỳ
(chênh 0,080 %/chu kỳ ≈ **0,24 %/ngày** — "carry spread" có thật). **Nhưng kết quả KHÔNG lật**: cả hai
phía đều **âm** vì (i) chân giá ≈ 0 ở cả hai phía, (ii) chi phí quay vòng (0,14–0,17%/chu kỳ) ăn hết.
⇒ **Bất đối xứng funding là thật nhưng quá nhỏ so với chi phí/h (8h)** — đúng như tiên lượng ghi trước ở
`PREREG_SHORT_CARRY.md` §0.

## 8. KẾT LUẬN theo cổng đã khoá (§7 pre-reg)

| Cổng | V1 | V2 | V3 |
|---|---|---|---|
| net > 0 sau TẤT CẢ chi phí | ✗ (−0,1402%) | ✗ (−0,3751%) | ✗ (−0,1127%) |
| CI72h×1,21 ngoài 0 | ✗ (ngoài 0 **về phía ÂM**) | ✗ (ÂM) | ✗ (ÂM) |
| ≥60% chu kỳ dương | ✗ (44,6%) | ✗ (40,0%) | ✗ (41,7%) |
| Bền vững qua biến thể | ✗ (mọi biến thể chi phí đều âm; 1bp slip ⇒ CI chứa 0) | ✗ | ✗ |
| Squeeze không quá lớn | ✗ (p99 +20,4%; max +602%) | ✗ (p99 +31,5%) | ✗ (p99 +20,4%) |

> ### **KẾT LUẬN: NO-GO (không NULL, mà là ÂM có ý nghĩa).**
> Không biến thể nào dương ⇒ **không có UNCONFIRMED/post-hoc** nào cần xử lý. **Không đề xuất build/tích hợp.**

**Carry short có đáng build không?** **KHÔNG** trong điều kiện hiện tại: để hoà vốn ở khung 8h với turnover
34%/chu kỳ, funding phải **≈ 0,165 %/chu kỳ** (≈ **6,6× mức thực +0,0251%**), tức cần **coin có funding
"carry-like" bền (dương cao kéo dài)** chứ không phải đuôi squeeze nhất thời — và ngay cả khi có, mức đó
tương đương **~0,5 %/ngày**, hiếm khi tồn tại ngoài các episode sụp; cộng thêm **rủi ro squeeze đuôi +400%**
và **engine không có đường SELL** ⇒ chi phí build (viết lại ENTRY short + margin/liquidation) **không có
cơ sở hoàn vốn** từ bằng chứng này.

## 9. GIỚI HẠN (nói rõ)

(i) Không có **dữ liệu fill thật** ⇒ chi phí là **mô hình**; kết luận "âm" mạnh ở biến thể 1 bp slip ⇒
độ nhạy chi phí cao. (ii) `f_sig` là rate **đã settle** (trễ ≤ 1 chu kỳ) — causal đúng nhưng **không** phải
"rate kỳ tới". (iii) Cadence 4h/8h hỗn hợp: 1 chu kỳ 8h tính **đủ mọi event settle** trong cửa sổ.
(iv) Không mô hình **margin/liquidation/borrow** ⇒ MAE là **cảnh báo**, không phải mô phỏng thanh lý.
(v) Decile cross-section **phụ thuộc #symbol** theo thời gian (2021 ít coin hơn 2025). (vi) V3 dùng
**cùng** danh sách đủ điều kiện cho cả 2 chân (không khớp lệch danh sách).

## 10. SẢN PHẨM

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_CARRY.md` | chốt trước (commit `edd1e70`) |
| `docs/result/RESULT_SHORT_CARRY.md` | file này |
| `research/analysis/short_carry.py` | script thuần Python (build grid + thống kê) |
| `/home/ubuntu/claudedata/short_carry/report.txt`, `summary.json` | log + số tổng hợp (**ngoài repo**) |

`grid.npz` (130 MB) **đã dọn** sau commit — tái tạo: `python3 research/analysis/short_carry.py build` (≈114 s)
rồi `... stats` (≈15 phút, gồm 300 rep null + MDE lồng cho 5 cấu hình).
