# RESULT_FUNDING_TOPK_K13 — MỞ RỘNG K = 1 và K = 3 (họ K ∈ {1,3,5,10,20}) CHO LUẬT QUAY VÒNG 8h: LONG top-K coin có FUNDING FEE NHỎ NHẤT

Ngày: 2026-09-22. Pre-reg: `docs/PREREG_FUNDING_TOPK_K13.md` (**commit `6d1a8fd`**, chốt TRƯỚC khi chạy).
Vòng gốc: `docs/PREREG_FUNDING_TOPK_ROTATE.md` (`55b8280`) + `docs/RESULT_FUNDING_TOPK_ROTATE.md` (`fdf61d7`).
Script dùng lại **nguyên bản**: `research/analysis/funding_topk_rotate.py` (grid + neo MOM15),
`research/analysis/funding_topk_rotate_stats.py` (**chỉ** thêm `TKR_KLIST`/`TKR_KTESTS`/`TKR_REPORT_TAG`
+ ghi `summary_K*.json`; **mặc định giữ nguyên** `5,10,20`/`K_test=3` nên hành vi cũ không đổi).
**Thuần Python**, 0-sim, **không** `claude-run`, **không** chạy Java (Oracle đang có shadow), **không push**,
**không chạm HOLDOUT 2026** (dữ liệu ≤ 2025-12-31). Trung gian ngoài repo: `/tmp/funding_topk_k13/`.

## 0. KẾT LUẬN (một dòng)

> **NO-GO cả 5 giá trị K (1/3/5/10/20)** — luật **bị TỪ CHỐI** (không phải "chưa kết luận") ở **K = 3, 5, 10, 20**
> (CI72h×1.21 **ngoài 0 về phía ÂM**), và ở **K = 1 là KHÔNG PHÂN GIẢI ĐƯỢC** (net **−0,3666%** nhưng CI
> **[−0,7838%, +0,0505%] chứa 0**, |net| **< MDE80 0,50%**, null DEV **p = 0,250**). **Tiên lượng ghi
> trước ĐÚNG**: net(1) < net(5) < net(10) < net(20) và cả hai K=1/K=3 âm; **K nhỏ hơn KHÔNG cứu được luật** —
> nó chỉ **làm chi phí quay vòng lớn hơn** (turnover 54,8% và cost 0,6204%/chu kỳ ở K=1, so với 40,0%/0,1895%
> ở K=20) trong khi **chân giá cũng xấu nhất** (raw −0,3218%/chu kỳ). **Không đề xuất áp dụng.**

**Bảng đầy đủ (DEV 2022–2025 = CHÍNH, phí round-trip 0,10%, mỗi chu kỳ 8h):**

| K | net/chu kỳ (DEV) | CI72h×1.21 | p(>0) | CI-Bonf5 | %chu kỳ dương | TURNOVER (1 chiều) | cost drag | gross (raw−funding) | MDE80 | Kết luận |
|---|---|---|---|---|---|---|---|---|---|---|
| **1** | **−0,3666%** | [−0,7838%, **+0,0505%**] | 0,021 | [−0,8113%, +0,0599%] | **39,6%** | **54,8%** (med 100%) | **0,6204%** (244,5% gross) | +0,2537% | 0,50% | **NO-GO** (không phân giải được) |
| **3** | **−0,2174%** | [−0,4247%, **−0,0100%**] | 0,004 | [−0,4378%, −0,0066%] | **44,9%** | **47,3%** (med 33,3%) | **0,3852%** (229,5% gross) | +0,1678% | 0,50% | **NO-GO** (bác bỏ, chiều âm) |
| **5** | **−0,2223%** | [−0,3774%, −0,0672%] | 0,001 | [−0,3825%, −0,0679%] | **45,8%** | **44,8%** (med 40,0%) | 0,3108% (351,2% gross) | +0,0885% | 0,20% | **NO-GO** (bác bỏ, chiều âm) |
| **10** | **−0,1709%** | [−0,2854%, −0,0564%] | 0,002 | [−0,2944%, −0,0425%] | **47,5%** | **43,0%** (med 50,0%) | 0,2392% (350,2% gross) | +0,0683% | 0,20% | **NO-GO** (bác bỏ, chiều âm) |
| **20** | **−0,1460%** | [−0,2449%, −0,0471%] | 0,002 | [−0,2477%, −0,0364%] | **48,6%** | **40,0%** (med 40,0%) | 0,1895% (435,2% gross) | +0,0435% | 0,20% | **NO-GO** (bác bỏ, chiều âm) |

N = **4 382** chu kỳ DEV / **487** block-72h cho **mọi** K. Quy đổi xấp xỉ (số học, ×3 chu kỳ/ngày):
net −1,10% … −0,44%/ngày; cost 1,86% … 0,57%/ngày; funding **thu** +1,73% … +0,29%/ngày; chân giá
−0,97% … −0,16%/ngày. (Chỉ để thấy bậc độ lớn — không dùng để tuyên bố lợi nhuận.)

**Đọc đúng 3 nhóm K:**
1. **K = 3, 5, 10, 20 — BÁC BỎ theo chiều LỖ:** `CI72h×1.21` và `CI-Bonf5` (p < 0,01) **đều nằm ngoài 0 về
   phía ÂM** ⇒ luật **lỗ có ý nghĩa**, không phải NULL thiếu lực.
2. **K = 1 — KHÔNG PHÂN GIẢI ĐƯỢC:** net âm điểm (**−0,3666%**) nhưng **CI chứa 0** (cận trên **+0,0505%**)
   và |net| **< MDE80 0,50%** ⇒ **không** được tuyên bố "lỗ có ý nghĩa" ở K=1; đồng thời **null DEV
   p = 0,250** ⇒ ở K=1 **xếp hạng theo funding không hơn gì chọn ngẫu nhiên 1 coin** (khác hẳn K ≥ 3).
3. **Không K nào dương** ⇒ **không** rơi vào nhánh "1 K dương, K khác không" ⇒ **không có UNCONFIRMED
   post-hoc** phải ghi; kết luận gọn: **NO-GO cả họ K**.

## 1. Tuân thủ + kiểm chứng tái tạo (harness còn lực) — 7/7 khớp

| Kiểm chứng | Vòng này | Tham chiếu | Khớp |
|---|---|---|---|
| `total_rows` cross-section `d15` (cache2) | **619 073 711** | `RESULT_HARNESS_CONTROL.md` §1 | ✔ |
| Phút MOM15 (`rd15 < −0,028`, `cnt ≥ 50`) | **13 150** | `RESULT_LEVEL_SENSITIVITY.md` §0b | ✔ |
| M-LEVEL MOM15 `k=1` (ALL) | **11 367** | idem | ✔ |
| M-LEVEL MOM15 `k=1` (DEV) | **7 128** | idem | ✔ |
| MOM15 `k=1` DEV 24h net @0,10% | **+1,6690%** | +1,6690% (vòng trước) / +1,6431% (ref cũ) | ✔ |
| MOM15 `k=1` ALL 24h net @0,10% | **+2,2622%** | "+2,26%" | ✔ |
| `N_blk` (block-72h) MOM15 DEV | **301** | 301 | ✔ |

⇒ Bộ đo **tái tạo đúng** ⇒ **không VOID**; kết luận NO-GO ở §0 **không** do harness hỏng (MOM15 vẫn phân
giải được hiệu ứng dương ≳2%/lệnh).

**Kiểm chứng chéo quan trọng — K = 5/10/20 re-run khớp TUYỆT ĐỐI số đã công bố ở `fdf61d7`:**

| Đại lượng | `fdf61d7` (vòng trước) | Re-run vòng này | Khớp |
|---|---|---|---|
| net DEV K=5 / 10 / 20 | −0,2223% / −0,1709% / −0,1460% | −0,2223% / −0,1709% / −0,1460% | ✔ |
| CI72h×1.21 K=5 | [−0,3774%, −0,0672%] | [−0,3774%, −0,0672%] | ✔ |
| turnover 5/10/20 | 44,8% / 43,0% / 40,0% | 44,8% / 43,0% / 40,0% | ✔ |
| cost 5/10/20 | 0,3108% / 0,2392% / 0,1895% | 0,3108% / 0,2392% / 0,1895% | ✔ |
| null DEV (mean, p) K=5 | −0,3811%, p=0,000 | −0,3811%, p=0,000 | ✔ |
| §11 (B) + §12 `MIN_SYM` | như đã in | như đã in | ✔ |

⇒ Hai lần chạy độc lập cho **cùng số** (seed cố định) ⇒ kết quả tất định, không phải may mắn của một lần chạy.

## 2. BƯỚC 0 — coverage dùng cho lần này (dựng lại grid từ đầu; trùng khít vòng trước)

| Mục | Kết quả |
|---|---|
| Nguồn funding | Aerospike `test.funding_data` (chỉ đọc), bin `f_data` = Snappy(JSON `{ts_ms: rate}`), tunnel `127.0.0.1:3222` |
| Nguồn giá | `raw/<sym>.f32` (extract `kline_1m_opt`, 1 nến/phút, UTC), **627** symbol, 2021-01-01..2025-12-31 |
| Universe | **627/627** symbol có **cả** raw **và** funding record |
| Mốc 8h | **5 477** mốc có dữ liệu; **5 476** mốc có `n_elig ≥ 50` (**dùng chính**); bỏ **1** mốc (2021-01-01 00:00) |
| `n_elig`/mốc | min 0 → median **186** → max **588**; trung bình **234,5** |
| Tổng dòng grid | **1 289 338** cặp (mốc, symbol) |
| Cadence funding | **422** symbol 4h / **202** symbol 8h / 0 khác (theo trung vị khoảng cách event) |

Số coverage **giống hệt** `RESULT_FUNDING_TOPK_ROTATE.md` §2 ⇒ cùng đầu vào, chỉ khác K được đo.

## 3. KẾT QUẢ CHÍNH — net/chu kỳ theo K (DEV = CHÍNH, phí 0,10%)

| K | net/chu kỳ (DEV) | CI72h×1.21 | p(>0) | CI-Bonf5 (p<0,01) | %chu kỳ dương | N | N_blk | MDE80 |
|---|---|---|---|---|---|---|---|---|
| **1** | **−0,3666%** | [−0,7838%, +0,0505%] | 0,021 | [−0,8113%, +0,0599%] | **39,6%** | 4 382 | 487 | 0,50% |
| **3** | **−0,2174%** | [−0,4247%, −0,0100%] | 0,004 | [−0,4378%, −0,0066%] | **44,9%** | 4 382 | 487 | 0,50% |
| **5** | **−0,2223%** | [−0,3774%, −0,0672%] | 0,001 | [−0,3825%, −0,0679%] | **45,8%** | 4 382 | 487 | 0,20% |
| **10** | **−0,1709%** | [−0,2854%, −0,0564%] | 0,002 | [−0,2944%, −0,0425%] | **47,5%** | 4 382 | 487 | 0,20% |
| **20** | **−0,1460%** | [−0,2449%, −0,0471%] | 0,002 | [−0,2477%, −0,0364%] | **48,6%** | 4 382 | 487 | 0,20% |

- **K = 3/5/10/20:** CI (cả bản x1.21 và bản Bonferroni siết p<0,01) **ngoài 0 về phía âm** ⇒ **bác bỏ
  H0 theo chiều LỖ**. **K=3 chỉ vừa đủ** để ngoài 0 (cận dưới −0,0100%); ở phí 0,05% CI **chứa 0** (xem §5).
- **K = 1:** CI **chứa 0** ⇒ **không phân giải được** (không được đọc thành "lỗ có ý nghĩa"). Đây là
  **nhánh NULL** của pre-reg §4, không phải nhánh bác bỏ.
- Ghi chú multiplicity: vòng trước dùng `K_test=3` (p<0,016667) cho K=5/10/20; vòng này **siết** lên
  `K_test=5` (p<0,01). CI-Bonf5 của K=5/10/20 vẫn ngoài 0 ⇒ **không** có ô nào "sống nhờ nới lỏng cổng".

## 4. TURNOVER + COST DRAG — phần **quyết định** (DEV, phí 0,10%)

| K | turnover/chu kỳ (1 chiều) | giao dịch/chu kỳ | chân giá `raw` | funding `f_cum` (âm = THU) | phí | **slip** | **cost tổng** | net | **cost/gross** |
|---|---|---|---|---|---|---|---|---|---|
| **1** | **54,8%** (med **100,0%**, p90 100%) | **1,10 book** | **−0,3218%** | **−0,5755%** | 0,0548% | **0,5656%** | **0,6204%** | **−0,3666%** | **244,5%** |
| **3** | **47,3%** (med 33,3%, p90 100%) | 0,95 book | −0,1767% | −0,3446% | 0,0473% | 0,3380% | **0,3852%** | **−0,2174%** | **229,5%** |
| **5** | **44,8%** (med 40,0%, p90 80%) | 0,90 book | −0,1677% | −0,2562% | 0,0448% | 0,2660% | 0,3108% | **−0,2223%** | 351,2% |
| **10** | **43,0%** (med 50,0%, p90 70%) | 0,86 book | −0,0937% | −0,1620% | 0,0430% | 0,1962% | 0,2392% | **−0,1709%** | 350,2% |
| **20** | **40,0%** (med 40,0%, p90 60%) | 0,80 book | −0,0519% | −0,0954% | 0,0400% | 0,1495% | 0,1895% | **−0,1460%** | 435,2% |

**Ba con số phải nhớ (đã bổ sung K=1/K=3):**

1. **K càng nhỏ ⇒ turnover càng cao**: 54,8% (K=1) → 40,0% (K=20). Ở **K=1 trung vị turnover = 100%** ⇒
   luật **đổi coin mỗi 2 chu kỳ một lần** (bán hết + mua hết, 1,10 book giao dịch/chu kỳ ≈ 3,3 book/ngày).
2. **Cost drag tuyệt đối lớn nhất ở K=1** (0,6204%/chu kỳ, gấp **3,3 lần** K=20) — **slip 0,5656%** chiếm
   **91%** cost, phí exchange chỉ 0,0548%. Ở **mọi K, slip > phí 5–10 lần** (basket là nhóm **biến động nhất**:
   slip/chiều trên slot được chọn = **0,529% / 0,380% / 0,323% / 0,259% / 0,214%** (K=1/3/5/10/20) so với
   **0,140%** của trung bình universe eligible ⇒ **×1,5–3,8**). *(Định nghĩa: trung bình `slip` trên các
   slot được chọn, mọi chu kỳ DEV; vòng trước in 0,334/0,260/0,207% theo cách gộp hơi khác — chênh < 0,02pp,
   không đổi kết luận.)*
3. **Gross dương ở MỌI K và TĂNG khi K nhỏ** (K=1 **+0,2537%** → K=20 **+0,0435%**), nhưng **cost tăng
   nhanh hơn** (0,6204% → 0,1895%) ⇒ net vẫn âm ở mọi K. **Ở phí 0,00%**, cost = slip (0,5656% ở K=1;
   0,2660% ở K=5) **vẫn lớn hơn gross** (0,2537%; 0,0885%) ⇒ **bỏ phí exchange hoàn toàn cũng không cứu được**:
   nút thắt là **slip × turnover** (nhóm funding âm nhất **chính là** nhóm biến động nhất).

## 5. Độ nhạy phí + biến thể full-churn (DEV)

| K | 0,05% | 0,10% (chính) | 0,15% | full-churn @0,10% (cận trên chi phí) |
|---|---|---|---|---|
| **1** | −0,3393% [−0,7565%, **+0,0779%**] | −0,3666% [−0,7838%, **+0,0505%**] | −0,3940% [−0,8111%, +0,0230%] | −0,9747% [−1,3914%, −0,5579%] |
| **3** | −0,1938% [−0,4015%, **+0,0139%**] | −0,2174% [−0,4247%, −0,0100%] | −0,2410% [−0,4480%, −0,0340%] | −0,7299% [−0,9376%, −0,5221%] |
| **5** | −0,1999% [−0,3547%, −0,0451%] | −0,2223% [−0,3774%, −0,0672%] | −0,2447% [−0,3996%, −0,0897%] | −0,6799% [−0,8336%, −0,5263%] |
| **10** | −0,1494% [−0,2640%, −0,0348%] | −0,1709% [−0,2854%, −0,0564%] | −0,1924% [−0,3068%, −0,0780%] | −0,5519% [−0,6678%, −0,4360%] |
| **20** | −0,1260% [−0,2247%, −0,0272%] | −0,1460% [−0,2449%, −0,0471%] | −0,1660% [−0,2650%, −0,0670%] | −0,4705% [−0,5680%, −0,3730%] |

⇒ **Âm ở MỌI mức phí và MỌI K** (net âm điểm ở cả 15 ô). Ở **K=1 và K=3 (phí 0,05%)** CI **chứa 0**
⇒ các ô đó **chưa bác bỏ được**; còn K=5/10/20 bác bỏ ở cả 3 mức phí. Full-churn (quay vòng toàn bộ book
mỗi chu kỳ) chỉ **làm tệ thêm** (−0,47% → −0,97%/chu kỳ) ⇒ kết luận **không** phụ thuộc cách tính turnover.

## 6. ALL (2021–2025, PHỤ — dán nhãn rõ) — phí 0,10%

| K | net/chu kỳ (ALL) | CI72h×1.21 | p(>0) | %chu kỳ dương | N | N_blk |
|---|---|---|---|---|---|---|
| **1** | **−0,2628%** | [−0,6154%, +0,0899%] | 0,039 | **40,8%** | 5 476 | 609 |
| **3** | **−0,1315%** | [−0,3034%, +0,0405%] | 0,035 | **45,9%** | 5 476 | 609 |
| **5** | **−0,1539%** | [−0,2867%, −0,0210%] | 0,004 | **46,8%** | 5 476 | 609 |
| **10** | **−0,1069%** | [−0,2128%, −0,0011%] | 0,005 | **49,0%** | 5 476 | 609 |
| **20** | **−0,0759%** | [−0,1693%, +0,0176%] | 0,021 | **50,2%** | 5 476 | 609 |

⇒ ALL **cùng dấu âm ở mọi K** (cổng (6) "không đổi dấu ALL" **không** đạt) nhưng **nhẹ hơn DEV** vì
**2021 là bull/alt-season**. K=1/K=3/K=20 CI ALL **chứa 0** (cửa sổ **PHỤ**, không dùng để tuyên bố).

## 7. Net/chu kỳ theo NĂM (GMT+7) — phí 0,10%

| K | 2021 (phụ) | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| **1** | +0,158% (n=1 093, 45%+) | −0,207% (n=1 095, 43%+) | −0,355% (n=1 095, 44%+) | −0,230% (n=1 098, 39%+) | **−0,679%** (n=1 095, **32%+**) |
| **3** | +0,217% (n=1 093, 50%+) | −0,192% (n=1 095, 46%+) | −0,135% (n=1 095, 47%+) | −0,180% (n=1 098, 44%+) | −0,365% (n=1 095, 41%+) |
| **5** | +0,124% (n=1 093, 51%+) | −0,223% (n=1 095, 47%+) | −0,105% (n=1 095, 47%+) | −0,226% (n=1 098, 46%+) | −0,339% (n=1 095, 43%+) |
| **10** | +0,153% (n=1 093, 55%+) | −0,195% (n=1 095, 48%+) | −0,073% (n=1 095, 49%+) | −0,159% (n=1 098, 47%+) | −0,260% (n=1 095, 45%+) |
| **20** | +0,209% (n=1 093, 57%+) | −0,178% (n=1 095, 51%+) | −0,042% (n=1 095, 49%+) | −0,165% (n=1 098, 49%+) | −0,203% (n=1 095, 45%+) |

⇒ **Dương DUY NHẤT ở 2021** (bull), **âm cả 4 năm DEV ở mọi K**; **K=1 tệ nhất và xấu đi nhanh nhất**
(2025: −0,679%, chỉ **32% chu kỳ dương**). Tỷ lệ chu kỳ dương **< 60% ở mọi năm DEV, mọi K**.

## 8. Null test — long K coin NGẪU NHIÊN (cùng số lượng, cùng mô hình chi phí, 300 rep)

| K | null mean/chu kỳ (DEV) | null sd | p(null ≥ obs) | obs | rep |
|---|---|---|---|---|---|
| **1** | −0,3932% | 0,0420% | **0,250** | −0,3666% | 300 |
| **3** | −0,3812% | 0,0232% | **0,000** | −0,2174% | 300 |
| **5** | −0,3811% | 0,0193% | **0,000** | −0,2223% | 300 |
| **10** | −0,3712% | 0,0126% | **0,000** | −0,1709% | 300 |
| **20** | −0,3543% | 0,0092% | **0,000** | −0,1460% | 300 |

(null ALL: K=1 −0,3853% p=0,000; K=3 −0,3729% p=0,000; K=5 −0,3712% p=0,000; K=10 −0,3582% p=0,000;
K=20 −0,3332% p=0,000)

**Đọc đúng bản chất (có điểm MỚI ở K=1 — rất quan trọng):**

- **K ≥ 3:** basket ngẫu nhiên lỗ **−0,37…−0,38%/chu kỳ**, basket top-K funding lỗ **−0,15…−0,22%** ⇒
  **xếp hạng theo funding CÓ giá trị so với random** (p = 0,000) nhờ (a) **thu** funding thay vì **trả**, và
  (b) **turnover thấp hơn** (~100% của random). **Nhưng "+0,16…+0,21%/chu kỳ so với random" ≠ "có lãi"**:
  cả hai đều **âm tuyệt đối**, luật cần **> 0** mới dùng được.
- **K = 1 (MỚI):** **p = 0,250 ở DEV** ⇒ chọn **1 coin funding âm nhất** **không** tốt hơn chọn ngẫu nhiên
  1 coin ⇒ **ở K=1, tiêu chí funding mất hẳn giá trị xếp hạng** trong cửa sổ DEV (trong ALL p=0,000, nhưng
  đó là do **2021**: nhóm funding âm nhất ở 2021 là nhóm được pump mạnh). Đây là **lý do kỹ thuật** để
  **không** đọc "K=1 gần hoà vốn" như một tia hy vọng: K=1 vừa **thiếu lực** vừa **thiếu thông tin xếp hạng**.

## 9. ICC + đặc trưng basket + MDE

| K | ICC(ngày) | ICC(block-72h) | N | N_blk |
|---|---|---|---|---|
| 1 | 0,1291 | 0,0826 | 4 382 | 487 |
| 3 | 0,1231 | 0,0559 | 4 382 | 487 |
| 5 | 0,1060 | 0,0451 | 4 382 | 487 |
| 10 | 0,0759 | 0,0315 | 4 382 | 487 |
| 20 | 0,0443 | 0,0196 | 4 382 | 487 |

| K | `f_entry` mean (%/chu kỳ) | median | min | max | %tên `f≤0` | %tên `f=0` | tỷ lệ dòng `short_delist` |
|---|---|---|---|---|---|---|---|
| 1 | **−0,525%** | −0,2868% | **−3,000%** | +0,010% | **96,7%** | 0,5% | 0,0000 |
| 3 | −0,304% | −0,1241% | −3,000% | +0,010% | 92,5% | 0,8% | 0,0000 |
| 5 | −0,219% | −0,0793% | −3,000% | +0,010% | 88,6% | 1,1% | 0,0000 |
| 10 | −0,133% | −0,0444% | −3,000% | +0,035% | 81,5% | 1,0% | 0,0000 |
| 20 | −0,077% | −0,0224% | −3,000% | +0,066% | 72,9% | 0,9% | 0,0000 |

⇒ K=1 chọn **coin funding âm nhất toàn universe** (mean −0,525%/chu kỳ, 96,7% số tên ≤ 0, có tên chạm
**sàn −3%/chu kỳ**) = nhóm **perp discount mạnh nhất** = nhóm **bị bán mạnh nhất**. `short_delist` = **0**
ở mọi K (không phải nguồn nhiễu).

**MDE80** (lưới {0,01; 0,02; 0,05; 0,10; 0,20; 0,50}%/chu kỳ):

| K | MDE80 | p50 half-width | p80 | p95 |
|---|---|---|---|---|
| 1 | **0,50%** (chạm trần lưới) | 0,4064% | 0,4525% | 0,4999% |
| 3 | **0,50%** | 0,1989% | 0,2227% | 0,2466% |
| 5 | **0,20%** | 0,1475% | 0,1637% | 0,1808% |
| 10 | **0,20%** | 0,1134% | 0,1235% | 0,1328% |
| 20 | **0,20%** | 0,0958% | 0,1035% | 0,1117% |

⇒ **K=1: MDE80 = 0,50% > |net| 0,3666%** ⇒ **không phân giải được ở thang 0,5%/chu kỳ** (đúng như
pre-reg §3.4 đã khoá trước). **K=3: MDE80 = 0,50% > |net| 0,2174%** ⇒ theo **cổng (5)** là "chưa phân giải
ở thang 0,5%", **nhưng** CI72h×1.21 (nửa-độ-rộng 0,207%) **đã ra ngoài 0** ⇒ ta **bác bỏ được net = 0**
theo chiều âm, chỉ là **độ lớn** nhỏ hơn ngưỡng lưới MDE. Ghi cả hai, không chọn cái có lợi.

## 10. CÁCH PHỤ (B) + độ nhạy `MIN_SYM` (descriptive — KHÔNG dùng để tuyên bố)

**B — universe CHỈ symbol cadence 8h** (**202/627** symbol; `n_elig` median 165; 5 473 mốc):

| K | net/chu kỳ (DEV) | CI72h×1.21 | %chu kỳ dương | N | N_blk | turnover |
|---|---|---|---|---|---|---|
| **1** | **−0,3975%** | [−0,6860%, −0,1090%] | 40,7% | 4 379 | 487 | 50,4% |
| **3** | **−0,2169%** | [−0,3829%, −0,0509%] | 45,2% | 4 379 | 487 | 43,6% |
| **5** | **−0,1837%** | [−0,3123%, −0,0552%] | 46,2% | 4 379 | 487 | 42,2% |
| **10** | **−0,1438%** | [−0,2451%, −0,0425%] | 47,5% | 4 379 | 487 | 40,1% |
| **20** | **−0,1220%** | [−0,2129%, −0,0311%] | 49,8% | 4 379 | 487 | 36,7% |

⇒ **Cùng kết luận** (âm ở mọi K; ở cách B thì **cả K=1 cũng ngoài 0 về phía âm** — lưu ý K=1 ở cách A
chứa 0, tức K=1 **nhạy với thành phần universe**, thêm một lý do để **không** tin K=1) ⇒ (A) **không**
phải artefact của việc trộn 2 cadence.

**Độ nhạy `MIN_SYM`** (DEV, phí 0,10%) — thay đổi **< 0,001pp**:

| MIN_SYM | số mốc dùng | K=1 | K=3 | K=5 | K=10 | K=20 |
|---|---|---|---|---|---|---|
| 50 | 5 476 | −0,3666% [−0,7838%, +0,0505%] | −0,2174% [−0,4247%, −0,0100%] | −0,2223% | −0,1709% | −0,1460% |
| 100 | 5 213 | −0,3670% [−0,7848%, +0,0507%] | −0,2178% [−0,4249%, −0,0106%] | −0,2224% | −0,1710% | −0,1457% |

## 11. Đối chứng

### 11a. Trung bình universe cùng kỳ (long TOÀN BỘ eligible, equal-weight, cùng mô hình chi phí)

| | net/chu kỳ DEV | CI72h×1.21 | %chu kỳ dương | turnover | funding |
|---|---|---|---|---|---|
| universe (234 tên/mốc trung bình) | **−0,0129%** | [−0,1006%, +0,0748%] | 53,2% | 0,08% | +0,0002% |

- K=1 vs universe: −0,3666% vs −0,0129% ⇒ top-K **kém universe 0,354%/chu kỳ**;
- K=3 kém 0,204%; K=5 kém 0,209%; K=10 kém 0,158%; K=20 kém 0,133%.
- ⚠️ Universe equal-weight (turnover ~0, chi phí ~0) **≈ 0, CI chứa 0** ⇒ baseline 2022–2025 ≈ 0; luật top-K
  **biến baseline 0 thành −0,15…−0,37%**, và **K càng nhỏ càng kém hơn baseline**.

### 11b. Neo MOM15 (xem §1)

`MOM15 k=1` DEV 24h net @0,10% = **+1,6690%** (CI72h×1.21 [+0,0455%, +3,2925%], N=7 128, N_blk=301) —
**tái tạo đúng** ⇒ bộ đo còn phân giải được hiệu ứng **dương** cỡ ≳2%/lệnh ⇒ kết luận âm ở trên **không**
do bộ đo hỏng.

### 11c. Dẫn chiếu H2 vòng trước (`RESULT_FUNDING_FACTOR` `5b548e4`: D1 net 24h −0,1913%, CI chứa 0, IC +0,0009)

| K | Vòng này (8h, quay vòng) | Nhất quán với D1? |
|---|---|---|
| 1 | −0,3666% [−0,7838%, +0,0505%] (CI chứa 0 — như D1) | **NHẤT QUÁN** (âm, chưa phân giải) |
| 3 | −0,2174% [−0,4247%, −0,0100%] | **NHẤT QUÁN + mạnh hơn** (bác bỏ chiều âm) |
| 5 | −0,2223% [−0,3774%, −0,0672%] | idem |
| 10 | −0,1709% [−0,2854%, −0,0564%] | idem |
| 20 | −0,1460% [−0,2449%, −0,0471%] | idem |

Tiền lệ xa: `docs/SURVEY_OLDCODE_SIGNALS.md` — rule `FUNDING_FEE_BUY` → ML `funding_selector` → **FAIL
(WFE med 0,098)**. Vòng này **không mâu thuẫn** tiền lệ; nó **đóng nốt rìa trái** của họ K: kể cả
**K=1 (harvest funding lớn nhất)** cũng **không** tạo được GO. **Không đề xuất áp dụng.**

## 12. VÌ SAO LỖ — cơ chế bằng số (không suy diễn)

(i) **Chân giá âm, xấu nhất ở K nhỏ:** `raw` = **−0,3218% / −0,1767% / −0,1677% / −0,0937% / −0,0519%**
(K=1/3/5/10/20) so với **−0,012%** của universe ⇒ "chọn funding nhỏ nhất = chọn nhóm đang rơi".
(2021 ngược lại: raw basket **+0,394% / +0,426% / +0,335% / +0,358% / +0,392%** (K=1/3/5/10/20) ⇒ 2021 là năm dương duy nhất.)

(ii) **Slip bị thổi lên bởi chính tiêu chí chọn:** slip/chiều trên slot được chọn **0,529% / 0,380% /
0,323% / 0,259% / 0,214%** so với **0,140%** của universe eligible ⇒ **×1,5–3,8**, và **lớn nhất ở K=1**.
Nhóm funding âm nhất là nhóm **biến động/thanh khoản mỏng nhất**: "mua rẻ funding" = **"mua đắt slip"**.

(iii) **Turnover:** 40,0–54,8%/chu kỳ; K càng nhỏ turnover càng cao (nhiễu xếp hạng ở đuôi) ⇒ cost drag
**lớn hơn ở K nhỏ** ⇒ net **xấu hơn ở K nhỏ** (**−0,367%** ở K=1 vs **−0,146%** ở K=20) — **ngược** chiều
kỳ vọng "harvest funding lớn hơn ở K nhỏ".

(iv) **Thu funding là thật và TĂNG khi K nhỏ — nhưng không đủ:** `f_cum` = **−0,5755% / −0,3446% /
−0,2562% / −0,1620% / −0,0954%** (âm = **thu**, đúng dấu mong đợi) ⇒ K=1 thu **+1,73%/ngày** tiền funding,
nhưng **chi phí giao dịch 1,86%/ngày** + **chân giá −0,97%/ngày** ăn hết và hơn. Luật **làm đúng việc nó
tuyên bố** (thu funding nhiều nhất ở K=1) mà **vẫn lỗ** ⇒ **không phải lỗi cài đặt**, là **cấu trúc chi phí**.

**Caveat kỹ thuật** (ghi để trung thực): (a) phân loại cadence 4h/8h theo trung vị khoảng cách event trên
cả 2021–2025 ⇒ chỉ ảnh hưởng **cách PHỤ (B)**; (b) `MIN_SYM=50` khiến gần như mọi mốc được dùng;
(c) **K=1 ở cách A chứa 0 nhưng ở cách B lại ngoài 0** ⇒ K=1 nhạy với thành phần universe (đã ghi ở §10).

## 13. CỔNG KẾT LUẬN (đã khoá; **K_test = 5**, Bonferroni **p < 0,01**)

Cột (2) là "cận dưới CI72h×1.21 > 0" (điều kiện GO). *Lưu ý: với K=3/5/10/20 CI **có** nằm ngoài 0,
chỉ là **ngoài về phía ÂM** ⇒ bác bỏ theo chiều lỗ; với K=1 CI **chứa 0** ⇒ không phân giải được.*

| K | (1) net>0 | (2) cận dưới CI >0 | (3) CI-Bonf5 >0 | (4) ≥60% chu kỳ dương | (5) \|net\|≥MDE | (6) không đổi dấu ALL | (7) không đổi dấu phí 0,15% | **GO?** |
|---|---|---|---|---|---|---|---|---|
| **1** | KHÔNG (−0,3666%) | KHÔNG (CI chứa 0) | KHÔNG | KHÔNG (39,6%) | KHÔNG (0,50% > 0,367%) | KHÔNG | KHÔNG (−0,3940%) | **NO-GO** |
| **3** | KHÔNG (−0,2174%) | KHÔNG (CI âm) | KHÔNG (âm) | KHÔNG (44,9%) | KHÔNG (0,50% > 0,217%) | KHÔNG | KHÔNG (−0,2410%) | **NO-GO** |
| **5** | KHÔNG (−0,2223%) | KHÔNG (CI âm) | KHÔNG (âm) | KHÔNG (45,8%) | ĐẠT | KHÔNG | KHÔNG (−0,2447%) | **NO-GO** |
| **10** | KHÔNG (−0,1709%) | KHÔNG (CI âm) | KHÔNG (âm) | KHÔNG (47,5%) | KHÔNG | KHÔNG | KHÔNG (−0,1924%) | **NO-GO** |
| **20** | KHÔNG (−0,1460%) | KHÔNG (CI âm) | KHÔNG (âm) | KHÔNG (48,6%) | KHÔNG | KHÔNG | KHÔNG (−0,1660%) | **NO-GO** |

> **KẾT LUẬN CUỐI: NO-GO cả 5 K (1/3/5/10/20).**
> - K = 3/5/10/20: **BÁC BỎ** (lỗ có ý nghĩa; CI ngoài 0 phía âm; ≥2 rate ngoài CI không đạt theo hướng dương).
> - K = 1: **KHÔNG PHÂN GIẢI ĐƯỢC** (CI chứa 0, |net| < MDE, null DEV p=0,250) — **không** được đọc thành
>   "lỗ có ý nghĩa", cũng **không** được đọc thành "gần hoà vốn".
> - **Không K nào dương** ⇒ **không** có UNCONFIRMED post-hoc; **không đề xuất áp dụng, không tích hợp,
>   không đề xuất feature.** Họ K đã **đóng** ở cả hai rìa.

## 14. Kiểm tra tiên lượng ghi trước (trung thực, không diễn giải lại)

| Tiên lượng ở `PREREG_FUNDING_TOPK_K13.md` §0 | Thực tế | Đúng/Sai |
|---|---|---|
| **NO-GO cả K=1 và K=3** | NO-GO cả 5 K | **ĐÚNG** |
| net(K=1) **≤** net(K=5) | −0,3666% ≤ −0,2223% | **ĐÚNG** |
| net(K=5) ≤ net(K=10) ≤ net(K=20) | −0,2223% ≤ −0,1709% ≤ −0,1460% | **ĐÚNG** |
| net(K=1) ∈ [−0,20%, −0,60%] | −0,3666% | **ĐÚNG** |
| net(K=3) ∈ [−0,20%, −0,35%] | −0,2174% | **ĐÚNG** (sát mép tốt nhất của khoảng) |
| Nói chung "net đơn điệu tăng theo K" | **SAI một cặp**: net(K=3) = −0,2174% **>** net(K=5) = −0,2223% (chênh **0,005pp**, trong nhiễu; không đổi kết luận) | **SAI (nhỏ, đã ghi)** |

Điểm **chưa** tiên lượng được (và học được từ vòng này): **K=1 mất hẳn giá trị xếp hạng** (null p=0,250 ở DEV)
và **K=1 nhạy thành phần universe** (cách A chứa 0, cách B ngoài 0) — pre-reg chỉ nói "K=1 có CI rộng nhất",
chưa nói "K=1 có thể mất tín hiệu".

## 15. Artifacts + vệ sinh + ghi chú kỷ luật

- Pre-reg: `docs/PREREG_FUNDING_TOPK_K13.md` — commit **`6d1a8fd`** (commit **TRƯỚC** khi chạy).
- Script: `research/analysis/funding_topk_rotate.py` (không đổi) + `research/analysis/funding_topk_rotate_stats.py`
  (**thay đổi DUY NHẤT**: `TKR_KLIST`/`TKR_KTESTS`/`TKR_REPORT_TAG` + ghi `summary_K*.json` + các nhãn bảng
  động theo `K_TESTS`; **mặc định giữ nguyên** `5,10,20`/`K_test=3`/`report.txt` như vòng trước, đã **kiểm
  chứng bằng re-run khớp tuyệt đối** — §1). Không đổi: mốc, ranking, HOLD, cost, CI, seed, null, MDE, cổng.
- Trung gian **ngoài repo** (resume được, ghi sau **từng K**): `/tmp/funding_topk_k13/{mark_grid.npz,
  anchor_mom15.npz, partial.npz, report_K1.txt, report_K3.txt, report_full.txt, summary_K1.json,
  summary_K3.json, summary_K5.json, summary_K10.json, summary_K20.json, *.log}` — dọn sau khi commit.
- **Không** chạy Java, **không** `claude-run`, **không** đụng 2026, **không** push.
- Ghi chú quy trình: chạy **từng K một** (K=1, rồi K=3) để có checkpoint, sau đó chạy **một lượt đủ 5 K**
  cho bảng so sánh chéo; **hai lượt chạy độc lập cho cùng số** (seed cố định) ⇒ tất định.
