# RESULT_RANGE4H_TOPK — luật quay vòng 4h: LONG top-K coin có NẾN 4h BIÊN ĐỘ RỘNG NHẤT

Ngày: 2026-09-22. Pre-reg: `docs/prereg/PREREG_RANGE4H_TOPK.md` (**commit `62e01bf`**, chốt TRƯỚC khi chạy;
sau đó **không sửa thiết kế**). Script: `research/analysis/range4h_topk.py` (sinh grid mốc 4h + neo MOM15),
`research/analysis/range4h_topk_stats.py` (thống kê). **Thuần Python**, 0-sim, **không** chạy Java trên
Oracle (job shadow), **không** `claude-run`, **không push**, **không chạm HOLDOUT 2026** (dữ liệu ≤ 2025-12-31).
Trung gian: `/tmp/range4h_topk/` (dọn sau khi commit).

## 0. KẾT LUẬN (một dòng)

> **NO-GO cả 4 giá trị K (1/3/5/10)** — và **không phải "thiếu lực"**: net/chu kỳ **ÂM RẤT MẠNH có ý nghĩa
> thống kê** ở cả 4 K (`CI72h×1.21` **ngoài 0 về phía ÂM**, `CI-Bonf4` cũng vậy, p = 0,000), chỉ
> **37,4–41,9%** chu kỳ dương (cổng đòi ≥60%), `|net|` **vượt MDE80** ở cả 4 K. **Cơ chế đúng như tiên
> lượng trước**: luật chọn **đúng nhóm biến động nhất** ⇒ **slip × turnover giết luật** — `slip/chiều` của
> basket **0,373–0,657%** so với **0,129%** của universe (**×2,9–5,1**), turnover **63,0–84,3%/chu kỳ**
> (≈ **1,3–1,7 book giao dịch mỗi 4 giờ**), ⇒ `cost` **0,45–1,11%/chu kỳ** trong khi **gross chỉ
> +0,02…+0,12%** = **cost/gross 945–2948%**. Tệ hơn: luật **thua cả basket NGẪU NHIÊN cùng cỡ**
> (null −0,347…−0,363%/chu kỳ, p(null ≥ obs) = **1,000**) ⇒ xếp hạng theo biên độ là **anti-signal**, không
> phải "signal yếu". Ở khung 4h **KHÔNG có K nào dương** ⇒ **không** rơi vào nhánh **UNCONFIRMED (post-hoc)**
> ⇒ **không áp dụng, không đề xuất tích hợp.**

| K | net/chu kỳ (DEV) | CI72h×1.21 | %chu kỳ dương | turnover | cost/chu kỳ | cost/gross | null (ngẫu nhiên) | Kết luận |
|---|---|---|---|---|---|---|---|---|
| **1** | **−0,9906%** | [−1,2906%, −0,6907%] | 37,4% | 84,3% | 1,1079% | 945% | −0,3633% | **NO-GO** |
| **3** | **−0,7131%** | [−0,8629%, −0,5633%] | 38,7% | 74,9% | 0,7629% | 1532% | −0,3574% | **NO-GO** |
| **5** | **−0,5933%** | [−0,7007%, −0,4859%] | 39,8% | 69,9% | 0,6141% | 2948% | −0,3550% | **NO-GO** |
| **10** | **−0,4254%** | [−0,5010%, −0,3498%] | 41,9% | 63,0% | 0,4487% | 1924% | −0,3466% | **NO-GO** |

Quy đổi xấp xỉ (số học, ×6 chu kỳ/ngày — chỉ để thấy bậc độ lớn): **net −2,6…−5,9%/ngày**; cost
2,7–6,6%/ngày; slip 2,3–6,1%/ngày; phí exchange 0,38–0,51%/ngày.

## 1. Tuân thủ + kiểm chứng tái tạo (harness còn lực)

| Kiểm chứng | Vòng này | Tham chiếu | Khớp |
|---|---|---|---|
| `total_rows` cross-section `d15` (cache2 vòng trước) | **619 073 711** | `RESULT_HARNESS_CONTROL.md` §1 | ✔ |
| Phút MOM15 (`rd15 < −0,028`, `cnt ≥ 50`) | **13 150** | `RESULT_LEVEL_SENSITIVITY.md` §0b | ✔ |
| M-LEVEL MOM15 `k=1` (ALL) | **11 367** | idem | ✔ |
| M-LEVEL MOM15 `k=1` (DEV) | **7 128** | idem | ✔ |
| MOM15 `k=1` DEV 24h net @0,10% | **+1,6690%** | +1,6690% (vòng trước) | ✔ |
| MOM15 `k=1` ALL 24h net @0,10% | **+2,2622%** | +2,2622% | ✔ |
| `N_blk` (block-72h) MOM15 DEV | **301** | 301 | ✔ |

⇒ **Bộ đo tái tạo ĐÚNG neo MOM15 (7/7)** ⇒ **không VOID**; so sánh được với 2 vòng funding trước ở cùng harness.

## 2. BUOC 0 — coverage dùng cho lần này

| Mục | Kết quả |
|---|---|
| Nguồn giá | `raw/<sym>.f32` = bản extract **`kline_1m_opt`** (1 nến 1 phút, UTC), **627** symbol, 2021-01-01..2025-12-31 |
| Nguồn funding | Aerospike `test.funding_data` (chỉ đọc), bin `f_data` = Snappy(JSON `{ts_ms: rate}`) |
| Universe | **627/627** symbol có **cả** raw **và** funding record (khớp 2 vòng trước) |
| Mốc 4h (00/04/08/12/16/20 UTC) | **10 955** mốc sinh được; **10 949** mốc có dữ liệu; **10 947** mốc có `n_elig ≥ 50` (**dùng chính**), bỏ **2** mốc |
| `n_elig`/mốc | min **13** → median **187** → max **588**; trung bình **235,2** trên mốc dùng |
| Tổng dòng grid | **2 575 168** cặp (mốc, symbol) |
| Chẩn đoán sinh grid (toàn universe × 10 955 mốc = 6 868 785 dòng) | không có nến tại mốc **4 289 247** (symbol chưa list / hết dữ liệu); cửa sổ nến khuyết (`<200/240` phút **hoặc** thiếu nến open) **4 289 726**; **eligible (đủ exit HOLD 240 + f_cum hữu hạn) = 2 575 168** |
| `short_delist` | **0** (không có exit sớm ⇒ không phải nguồn nhiễu) |
| Rác | đã lọc `ts ≥ 2021-01-01` (3 symbol `GAIBUSDT`/`GRAMUSDT`/`STPTUSDT`) |

## 3. KẾT QUẢ CHÍNH — net/chu kỳ theo K (DEV = CHÍNH, phí 0,10%)

| K | net/chu kỳ (DEV) | CI72h×1.21 | p(>0) | CI-Bonf4 | %chu kỳ dương | N | N_blk | MDE80 |
|---|---|---|---|---|---|---|---|---|
| **1** | **−0,9906%** | [−1,2906%, −0,6907%] | 0,000 | [−1,2884%, −0,6741%] | **37,4%** | 8 758 | 487 | 0,50% |
| **3** | **−0,7131%** | [−0,8629%, −0,5633%] | 0,000 | [−0,8745%, −0,5473%] | **38,7%** | 8 758 | 487 | 0,20% |
| **5** | **−0,5933%** | [−0,7007%, −0,4859%] | 0,000 | [−0,7082%, −0,4739%] | **39,8%** | 8 758 | 487 | 0,20% |
| **10** | **−0,4254%** | [−0,5010%, −0,3498%] | 0,000 | [−0,5057%, −0,3449%] | **41,9%** | 8 758 | 487 | 0,10% |

**Đọc đúng bản chất:** cả 4 K đều **âm có ý nghĩa** — `CI72h×1.21` **và** `CI-Bonf4` **đều nằm ngoài 0 về
phía ÂM** (bác bỏ "net = 0" theo chiều **lỗ**). N = 8 758 chu kỳ / 487 block-72h, MDE80 0,10–0,50%
**< |hiệu ứng| 0,43–0,99%** ⇒ bộ đo **đủ lực**. Cổng GO cần net **> 0** ⇒ **KHÔNG đạt ở bất kỳ K nào**.

## 4. TURNOVER + COST DRAG — phần **quyết định** (DEV, phí 0,10%)

| K | turnover/chu kỳ (1 chiều) | giao dịch/chu kỳ | raw | f_cum | phí | **slip** | **cost tổng** | net | cost/gross |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **84,3%** (med 100%, p90 100%) | 1,69 book | −0,0283% | −0,1455% | 0,0843% | **1,0236%** | **1,1079%** | **−0,9906%** | **945%** |
| **3** | **74,9%** (med 66,7%, p90 100%) | 1,50 book | −0,0431% | −0,0929% | 0,0749% | **0,6881%** | **0,7629%** | **−0,7131%** | **1532%** |
| **5** | **69,9%** (med 80,0%, p90 100%) | 1,40 book | −0,0504% | −0,0712% | 0,0699% | **0,5442%** | **0,6141%** | **−0,5933%** | **2948%** |
| **10** | **63,0%** (med 60,0%, p90 80%) | 1,26 book | −0,0234% | −0,0467% | 0,0630% | **0,3857%** | **0,4487%** | **−0,4254%** | **1924%** |

**Bốn con số phải nhớ:**

1. **Turnover 63,0–84,3%/chu kỳ (1 chiều)** ⇒ **1,26–1,69 book giao dịch mỗi 4 giờ** ⇒ **≈ 7,6–10,1
   book/ngày**. Ở khung **4h**, turnover **cao hơn hẳn** vòng funding-topk 8h (40–45%): xếp hạng theo
   **biên độ** cực kỳ **không dai** — top-1 đổi tên **100%/chu kỳ (median)**, tức **bán sạch mua sạch mỗi 4h**.
2. **Chi phí 0,45–1,11%/chu kỳ** (≈ **2,7–6,6%/ngày**) — **gấp 9,4× → 29,5× gross**.
3. **Slip là thủ phạm số 1**: `slip/chiều` của basket **0,6573% (K=1) / 0,4565% (K=5) / 0,3726% (K=10)**
   so với **0,1288%** của universe ⇒ **×2,9–5,1**; **phí exchange chỉ 0,063–0,084%/chu kỳ**, tức slip
   **lớn hơn phí 5–12 lần**. **Giảm phí exchange về 0 KHÔNG cứu được luật** (xem §5).
4. **Gross gần như bằng 0** (raw − funding = **+0,1173% / +0,0498% / +0,0208% / +0,0233%**) ⇒ luật có
   **chút "alpha" thô** (và thậm chí **thu funding** nhờ đuôi biến động thường có funding âm:
   `f_cum` = **−0,1455%** ở K=1 = **thu +0,87%/ngày**), nhưng **nhỏ hơn chi phí 9–30 lần**.

## 5. Độ nhạy phí + biến thể full-churn (DEV)

| K | 0,05% | 0,10% | 0,15% | full-churn @0,10% (cận trên chi phí) |
|---|---|---|---|---|
| **1** | −0,9485% [−1,2485%, −0,6484%] | −0,9906% [−1,2906%, −0,6907%] | −1,0328% [−1,3327%, −0,7330%] | −1,2973% [−1,5984%, −0,9962%] |
| **3** | −0,6757% [−0,8254%, −0,5260%] | −0,7131% [−0,8629%, −0,5633%] | −0,7506% [−0,9003%, −0,6008%] | −1,0978% [−1,2517%, −0,9439%] |
| **5** | −0,5583% [−0,6659%, −0,4507%] | −0,5933% [−0,7007%, −0,4859%] | −0,6283% [−0,7355%, −0,5210%] | −0,9923% [−1,1069%, −0,8776%] |
| **10** | −0,3939% [−0,4696%, −0,3182%] | −0,4254% [−0,5010%, −0,3498%] | −0,4569% [−0,5325%, −0,3812%] | −0,8218% [−0,9023%, −0,7414%] |

⇒ **Âm ở MỌI mức phí** (kể cả 0,05%) và **mọi K** ⇒ **không** có ô nào đổi dấu ⇒ luật **không chết vì phí
exchange** mà chết vì **slip × turnover**. Full-churn làm tệ thêm (−0,82% → −1,30%).

## 6. ALL (2021–2025, PHỤ — dán nhãn rõ) — phí 0,10%

| K | net/chu kỳ (ALL) | CI72h×1.21 | p(>0) | %chu kỳ dương | N | N_blk |
|---|---|---|---|---|---|---|
| **1** | **−0,9002%** | [−1,1474%, −0,6529%] | 0,000 | 37,8% | 10 947 | 609 |
| **3** | **−0,6683%** | [−0,7952%, −0,5415%] | 0,000 | 39,4% | 10 947 | 609 |
| **5** | **−0,5624%** | [−0,6608%, −0,4639%] | 0,000 | 40,5% | 10 947 | 609 |
| **10** | **−0,4081%** | [−0,4778%, −0,3384%] | 0,000 | 42,7% | 10 947 | 609 |

⇒ ALL **cùng dấu âm**, CI **ngoài 0 về phía âm** ở cả 4 K (cổng (6) không đạt). **Kể cả 2021 (bull) cũng âm**.

## 7. Net/chu kỳ theo NĂM (GMT+7) — phí 0,10%

| K | 2021 (phụ) | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| **1** | −0,538% (n=2 186, 40%+) | −0,665% (2 190, 37%+) | −0,920% (2 190, 36%+) | **−1,222%** (2 196, 38%+) | −1,156% (2 185, 38%+) |
| **3** | −0,488% (2 186, 42%+) | −0,582% (2 190, 39%+) | −0,519% (2 190, 38%+) | −0,785% (2 196, 39%+) | −0,968% (2 185, 39%+) |
| **5** | −0,437% (2 186, 43%+) | −0,534% (2 190, 40%+) | −0,407% (2 190, 40%+) | −0,632% (2 196, 40%+) | −0,802% (2 185, 39%+) |
| **10** | −0,338% (2 186, 46%+) | −0,432% (2 190, 42%+) | −0,266% (2 190, 43%+) | −0,436% (2 196, 42%+) | −0,569% (2 185, 41%+) |

⇒ **ÂM Ở MỌI NĂM, kể cả 2021** (khác vòng funding-topk 8h, nơi 2021 **dương**); lỗ **sâu nhất 2024–2025**;
tỷ lệ chu kỳ dương **≤46% ở mọi ô**. Không có "năm cứu" nào.

## 8. Đối chứng

### 8a. Trung bình universe cùng kỳ (long TOÀN BỘ eligible, equal-weight, cùng mô hình chi phí)

| | net/chu kỳ DEV | CI72h×1.21 | %chu kỳ dương | turnover | funding |
|---|---|---|---|---|---|
| universe (235 tên/mốc trung bình) | **−0,0062%** | [−0,0500%, +0,0375%] | 52,7% | 0,05% | +0,0001% |

- K=1 **kém universe 0,9844%/chu kỳ**; K=3 kém 0,7069%; K=5 kém 0,5871%; K=10 kém 0,4192%.
- ⚠️ **Baseline 2022–2025 ≈ 0** (universe turnover ~0 ⇒ cost ~0, CI chứa 0). Luật top-K biến
  **baseline 0 thành −0,43…−0,99%/chu kỳ** ⇒ thiệt hại **hoàn toàn do chính sách chọn tên + chi phí quay
  vòng của nó**, không phải do "thị trường xấu".

### 8b. Neo MOM15 (xem §1)

`MOM15 k=1` DEV 24h net @0,10% = **+1,6690%** (CI72h×1.21 [+0,0455%, +3,2925%], N=7 128, N_blk=301),
ALL = **+2,2622%** ⇒ neo **tái tạo đúng** ⇒ kết luận NO-GO **không** do bộ đo hỏng.

### 8c. Dẫn chiếu vòng trước (cùng họ "quay vòng đuôi")

| | Vòng này (4h, **biên độ rộng nhất**) | Vòng funding-topk (8h, **funding nhỏ nhất**) |
|---|---|---|
| K=5 net DEV | **−0,5933%/chu kỳ** | −0,2223%/chu kỳ |
| turnover | **69,9%** | 44,8% |
| slip/chiều basket vs universe | **0,4565% vs 0,1288% (×3,5)** | 0,334% vs 0,139% (×2,4) |
| cost/gross | **2948%** | 351% |
| null (ngẫu nhiên) | **−0,3550%, p = 1,000** (luật **thua** random) | −0,3811%, p = 0,000 (luật **thắng** random) |
| Kết luận | **NO-GO** | **NO-GO** |

⇒ **Nhất quán** với kết luận vòng trước và **tiên lượng ghi trước** (§0 pre-reg): chi phí quay vòng giết
luật. **Định lượng mới**: khi biến xếp hạng là **biến động** (thay vì funding), (i) turnover **cao hơn
~1,6×**, (ii) slip/chiều **cao hơn ~1,4×**, (iii) và **giá trị xếp hạng so với random chuyển từ DƯƠNG
(+0,13…+0,16% ở vòng funding) sang ÂM (−0,08…−0,63%)** ⇒ đây là **anti-signal**. Nhất quán tiền lệ
`docs/analysis/SURVEY_OLDCODE_SIGNALS.md` (các rule momentum/breakout ngắn hạn không sống qua chi phí).

## 9. Null test — long K coin NGẪU NHIÊN (cùng số lượng, cùng mô hình chi phí)

| K | null mean/chu kỳ (DEV) | null sd | p(null ≥ obs) | obs | luật − null | rep |
|---|---|---|---|---|---|---|
| **1** | **−0,3633%** | 0,0202% | **1,000** | −0,9906% | **−0,6273%** | 300 |
| **3** | **−0,3574%** | 0,0118% | **1,000** | −0,7131% | **−0,3557%** | 300 |
| **5** | **−0,3550%** | 0,0087% | **1,000** | −0,5933% | **−0,2383%** | 300 |
| **10** | **−0,3466%** | 0,0062% | **1,000** | −0,4254% | **−0,0788%** | 300 |

(null ALL: K=1 −0,3758% p=1,000; K=3 −0,3685%; K=5 −0,3648%; K=10 −0,3532% — tất cả p=1,000.)

**Đọc đúng bản chất (rất quan trọng):** basket **ngẫu nhiên** lỗ **−0,35%/chu kỳ** (vì random cũng phải
trả slip ~0,13–0,65% × turnover ~100%), nhưng basket **top-K biên độ** lỗ **−0,43…−0,99%/chu kỳ** ⇒
**xếp hạng theo biên độ LÀM TỆ ĐI so với random**, `p(null ≥ obs) = 1,000` ở cả 4 K. Đây **không** phải
"signal yếu" mà là **chọn ngược**: mua đúng tên vừa có nến rộng nhất = **mua đỉnh biến động** rồi trả slip
lớn nhất. Khác hẳn vòng funding (nơi ranking **thắng** random +0,13…+0,16%/chu kỳ nhưng level vẫn âm).

## 10. ICC + đặc trưng basket + MDE

| K | ICC(ngày) | ICC(block-72h) | N | N_blk |
|---|---|---|---|---|
| 1 | 0,0624 | 0,0210 | 8 758 | 487 |
| 3 | 0,0339 | 0,0188 | 8 758 | 487 |
| 5 | 0,0234 | 0,0113 | 8 758 | 487 |
| 10 | 0,0189 | 0,0065 | 8 758 | 487 |

| K | range4h basket mean | median | min | max | phân vị trung bình trong pool |
|---|---|---|---|---|---|
| 1 | **22,48%** | 16,36% | 2,92% | 1078,39% | **0,9977** |
| 3 | 16,79% | 13,19% | 2,76% | 521,65% | 0,9930 |
| 5 | 14,37% | 11,59% | 2,60% | 344,15% | 0,9884 |
| 10 | 11,47% | 9,51% | 2,23% | 195,96% | 0,9768 |

⇒ Basket là **đuôi biến động tuyệt đối** (phân vị trung bình **0,98–0,998**), biên độ **trung bình 22,5%/4h
ở K=1** so với **3,82%/4h** của pool trung bình ⇒ **×5,9**. Đây đúng là nhóm **thanh khoản mỏng nhất**
⇒ **slip cao nhất**. (`max` cực đại do vài nến 1m có print xấu — xem caveat §11.)

**MDE80** (lưới {0,01; 0,02; 0,05; 0,10; 0,20; 0,50}%/chu kỳ):

| K | MDE80 | p50 half-width | p80 | p95 | power@0,20% |
|---|---|---|---|---|---|
| 1 | **0,50%** | 0,2863% | 0,3171% | 0,3485% | 0,0015 |
| 3 | **0,20%** | 0,1438% | 0,1574% | 0,1702% | 0,999 |
| 5 | **0,20%** | 0,1062% | 0,1151% | 0,1242% | 1,000 |
| 10 | **0,10%** | 0,0751% | 0,0813% | 0,0868% | 1,000 |

⇒ Ở khung 4h, nửa-độ-rộng CI **0,075–0,286%** và MDE80 **0,10–0,50%** ⇒ |net| **0,43–0,99% vượt MDE ở cả
4 K** ⇒ hiệu ứng âm **được phân giải rõ**, không phải "không phân giải được".

## 11. VÌ SAO LỖ — cơ chế (giải thích bằng số, không suy diễn)

(i) **Chọn đúng đuôi biến động ⇒ chọn đúng đuôi slip.** `range4h` của basket **22,5/16,8/14,4/11,5%**
(K=1/3/5/10) so với universe **3,82%**; `slip/chiều` **0,657/0,457/0,373%** so với **0,129%** ⇒ chi phí
vào/ra **bằng chính biên độ của nến vừa rộng nhất** — luật **tự đặt giá mua đắt nhất**.
(ii) **Turnover ~1,26–1,69 book/4h.** Xếp hạng biên độ **không dai**: K=1 đổi tên **100%** số chu kỳ
(median), K=10 vẫn 60%. ⇒ cost drag **lớn hơn ở K nhỏ** ⇒ net **xấu hơn ở K nhỏ** (−0,99% ở K=1 vs
−0,43% ở K=10) — **ngược** chiều cảm giác "top-1 sắc nhất".
(iii) **Chân giá ≈ 0 nhưng âm nhẹ**: raw = **−0,028…−0,050%/chu kỳ** ⇒ **không có edge giá ngắn hạn**
(phù hợp "reversal sau nến rộng" + neo MOM15 ngược dấu). Ngay cả **gross** (raw − funding) chỉ
**+0,0208…+0,1173%** — **nhỏ hơn slip một mình** (0,386–1,024%).
(iv) **Thu funding là "phụ lộc"** của đuôi biến động (`f_cum` **−0,047…−0,146%/chu kỳ** = thu
+0,28…+0,87%/ngày) — **thú vị nhưng vô nghĩa** so với cost 0,45–1,11%/chu kỳ. **Luật không thể sống bằng
funding khi phải quay 1,3–1,7 book mỗi 4 giờ.**

**Caveat kỹ thuật (ghi để trung thực, không đổi thiết kế):**
(a) Trong grid có **113 dòng** (0,0044%) biên độ **> 100%** (print 1m xấu/rất thưa). Kiểm tra **hậu
nghiệm** (descriptive, không phải test): bỏ **97 chu kỳ** (0,9%) có tên biên độ >100% ⇒ net **gần như
không đổi** (K=1: −0,9906% → −0,9923%; K=5: −0,5933% → −0,6012%; K=10: −0,4254% → −0,4259%) ⇒ kết luận
**không** phụ thuộc outlier.
(b) Điều kiện cửa sổ nến (≥200/240 phút **và** có nến open tại `r−240`) loại **4 289 726** dòng
(symbol chưa list/hết dữ liệu là chính); không có symbol nào bị loại vì thiếu funding.
(c) `MIN_SYM=50` chỉ bỏ **2 mốc** ⇒ độ nhạy `MIN_SYM` 50 vs 100 **gần như bằng 0** (§13).
(d) Nến mốc `r` dùng giá `close(r)` (nến đã đóng, biết ở `r+1` phút) — **cùng convention** 2 vòng trước
(1 phút trễ kỹ thuật, đã khoá trong pre-reg §3).

## 12. CÁCH PHỤ — HOLD 24h (mốc 00 UTC, `r % 1440 == 0`; dán nhãn, KHÔNG để tuyên bố)

| K | net/24h (DEV) | CI72h×1.21 | %chu kỳ dương | N | N_blk | turnover/24h | cost/24h |
|---|---|---|---|---|---|---|---|
| **1** | **−0,8165%** | [−2,3270%, +0,6940%] | 36,9% | 1 460 | 487 | 90,9% | 1,4183% |
| **3** | −0,6815% | [−1,4688%, +0,1058%] | 40,4% | 1 460 | 487 | 84,3% | 1,0478% |
| **5** | −0,5235% | [−1,1601%, +0,1130%] | 42,7% | 1 460 | 487 | 81,3% | 0,8719% |
| **10** | −0,5247% | [−0,9936%, −0,0558%] | 45,1% | 1 460 | 487 | 75,1% | 0,6617% |

⇒ Kéo dài HOLD lên 24h **không cứu** (vẫn âm, N nhỏ hơn ⇒ K=1/3/5 CI **chứa 0**, K=10 CI ngoài 0 phía âm);
**turnover vẫn 75–91%/24h** vì tên biên độ rộng nhất đổi liên tục.

## 13. Độ nhạy `MIN_SYM` (descriptive)

| MIN_SYM | số mốc dùng | K=1 | K=3 | K=5 | K=10 |
|---|---|---|---|---|---|
| 50 | 10 947 | −0,9906% [−1,2906%, −0,6907%] | −0,7131% [−0,8629%, −0,5633%] | −0,5933% [−0,7007%, −0,4859%] | −0,4254% [−0,5010%, −0,3498%] |
| 100 | 10 450 | −0,9953% [−1,2932%, −0,6973%] | −0,7126% [−0,8628%, −0,5624%] | −0,5931% [−0,7003%, −0,4858%] | −0,4253% [−0,5009%, −0,3497%] |

⇒ Không đổi (chênh <0,005pp) ⇒ kết quả **không** do lựa chọn ngưỡng universe.

## 14. CỔNG KẾT LUẬN (đã khoá, K_test = 4, Bonferroni p < 0,0125)

| K | (1) net>0 | (2) cận dưới CI×1.21 > 0 | (3) cận dưới CI-Bonf4 > 0 | (4) ≥60% chu kỳ dương | (5) \|net\|≥MDE | (6) không đổi dấu ALL | (7) không đổi dấu phí 0,15% | **GO?** |
|---|---|---|---|---|---|---|---|---|
| **1** | KHÔNG | KHÔNG | KHÔNG | KHÔNG (37,4%) | ĐẠT (0,99 ≥ 0,50) | KHÔNG (−0,9002%) | KHÔNG (−1,0328%) | **NO-GO** |
| **3** | KHÔNG | KHÔNG | KHÔNG | KHÔNG (38,7%) | ĐẠT (0,71 ≥ 0,20) | KHÔNG (−0,6683%) | KHÔNG (−0,7506%) | **NO-GO** |
| **5** | KHÔNG | KHÔNG | KHÔNG | KHÔNG (39,8%) | ĐẠT (0,59 ≥ 0,20) | KHÔNG (−0,5624%) | KHÔNG (−0,6283%) | **NO-GO** |
| **10** | KHÔNG | KHÔNG | KHÔNG | KHÔNG (41,9%) | ĐẠT (0,43 ≥ 0,10) | KHÔNG (−0,4081%) | KHÔNG (−0,4569%) | **NO-GO** |

> **KẾT LUẬN CUỐI: NO-GO cả 4 K — luật bị TỪ CHỐI (không phải "chưa kết luận").**
> Không có K nào dương ⇒ **không** rơi vào nhánh "một số K đạt, K khác không" ⇒ **không có UNCONFIRMED
> (post-hoc)** cần ghi. **Không áp dụng, không tích hợp, không đề xuất feature.**
> Nếu muốn theo tiếp họ này: **cửa duy nhất còn lý thuyết** là chi phí (slip/thanh khoản), **không phải**
> biến xếp hạng — và bằng chứng null (§9) cho thấy **xếp hạng theo biên độ còn tệ hơn random**, nên
> hướng này **không đáng đầu tư thêm** ở khung 4h.

## 15. Artifacts + vệ sinh + ghi chú kỷ luật

- Script (commit cùng file này): `research/analysis/range4h_topk.py`, `research/analysis/range4h_topk_stats.py`.
  Chỉ **ĐỌC** `raw/*.f32` + Aerospike `test.funding_data`. **Thuần Python, 0-sim, không Java, không push.**
- Trung gian (ngoài repo, resume được): `/tmp/range4h_topk/{mark_grid4h.npz,anchor_mom15.npz,checkpoint_K*.json,
  numbers4h.json,report4h.txt,*.log}` — **đã dọn file tạm sau khi commit** (theo pre-reg §8).
- **Ghi chú cài đặt (TRƯỚC khi chốt số, không đổi thiết kế/cổng/K/cửa sổ):** code checkpoint `partial.npz`
  (tiện ích resume) bị lỗi trục khi ghép mảng neo MOM15 (`concatenate` axis 0 thay vì 1) ⇒ ghi cảnh báo
  `checkpoint fail` trong log; **không ảnh hưởng số** vì grid cuối được ghi **trong một lượt** và
  `mark_grid4h.npz`/`anchor_mom15.npz` đầy đủ (2 575 168 dòng / 11 367 dòng neo). Đã sửa `axis` cho lần sau.
- Đối chiếu **nghi vấn ban đầu** của pre-reg §0: **đúng** cả 2 vế — (a) chi phí (slip × turnover) **giết**
  luật (**cost/gross 945–2948%**), (b) `raw` ∈ [−0,05%, −0,03%] như tiên lượng ≈0/âm nhẹ. **Chưa** tiên
  lượng được: turnover **cao hơn** dự kiến (63–84% thay vì ~40–45%) và luật **thua cả random** (p=1,000) —
  tức **anti-signal**, mạnh hơn kết luận "chỉ là NULL".
