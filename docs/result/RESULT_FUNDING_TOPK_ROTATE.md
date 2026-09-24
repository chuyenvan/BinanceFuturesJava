# RESULT_FUNDING_TOPK_ROTATE — luật quay vòng 8h: LONG top-K coin có FUNDING FEE NHỎ NHẤT

Ngày: 2026-09-22. Pre-reg: `docs/prereg/PREREG_FUNDING_TOPK_ROTATE.md` (**commit `55b8280`**, chốt TRƯỚC khi
chạy; sau đó **không sửa thiết kế**). Script: `research/analysis/funding_topk_rotate.py` (sinh grid mốc 8h
+ neo MOM15), `research/analysis/funding_topk_rotate_stats.py` (thống kê).
**Thuần Python**, 0-sim, **không** chạy Java trên Oracle (job shadow), **không** `claude-run`, **không push**,
**không chạm HOLDOUT 2026** (dữ liệu ≤ 2025-12-31). Trung gian: `/tmp/funding_topk/` (đã dọn sau khi commit).

## 0. KẾT LUẬN (một dòng)

> **NO-GO cả 3 giá trị K (5/10/20)** — và lần này **không phải "thiếu lực"**: net/chu kỳ **ÂM có ý nghĩa
> thống kê** ở cả 3 K (CI72h×1.21 **ngoài 0 về phía ÂM**), chỉ **45,8–48,6%** số chu kỳ dương (cổng đòi
> ≥60%), MDE 0,20%/chu kỳ (K=5: |net| **vượt** MDE; K=10/20: |net| **xấp xỉ** MDE). **Cơ chế đúng như tiên lượng trước**: luật **thu funding thật**
> (chọn đúng nhóm funding âm nhất ⇒ `f_cum` **−0,256%/chu kỳ ở K=5**, tức **thu +0,77%/ngày**), nhưng
> (i) **chân giá âm** (top-K funding nhỏ nhất = nhóm **đang bị bán mạnh nhất**: raw **−0,168%/chu kỳ** so
> với **−0,012%** của universe) và (ii) **chi phí quay vòng 0,31%/chu kỳ** (turnover **44,8%**; **slip chiếm
> 0,266%** vì nhóm được chọn **biến động nhất**: slip/chiều **0,334%** so với **0,139%** của universe) ⇒
> **cost/gross = 351%** ở K=5. Ở khung 8h, **chi phí ăn hết gross** — đúng như tiên lượng. **Không đề xuất áp dụng.**

| K | net/chu kỳ (DEV) | CI72h×1.21 | %chu kỳ dương | turnover | cost/chu kỳ | cost/gross | Kết luận |
|---|---|---|---|---|---|---|---|
| **5** | **−0,2223%** | [−0,3774%, −0,0672%] | 45,8% | 44,8% | 0,3108% | 351% | **NO-GO** |
| **10** | **−0,1709%** | [−0,2854%, −0,0564%] | 47,5% | 43,0% | 0,2392% | 350% | **NO-GO** |
| **20** | **−0,1460%** | [−0,2449%, −0,0471%] | 48,6% | 40,0% | 0,1895% | 435% | **NO-GO** |

Quy đổi xấp xỉ (số học, ×3 chu kỳ/ngày): **net −0,67%/ngày**; cost 0,93%/ngày; funding thu +0,77%/ngày;
chân giá −0,50%/ngày. (Không dùng để tuyên bố lợi nhuận — chỉ để thấy bậc độ lớn.)

## 1. Tuân thủ + kiểm chứng tái tạo (harness còn lực)

| Kiểm chứng | Vòng này | Tham chiếu | Khớp |
|---|---|---|---|
| `total_rows` cross-section `d15` (cache2 vòng trước) | **619 073 711** | `RESULT_HARNESS_CONTROL.md` §1 | ✔ |
| Phút MOM15 (`rd15 < −0,028`, `cnt ≥ 50`) | **13 150** | `RESULT_LEVEL_SENSITIVITY.md` §0b | ✔ |
| M-LEVEL MOM15 `k=1` (ALL) | **11 367** | idem | ✔ |
| M-LEVEL MOM15 `k=1` (DEV) | **7 128** | idem | ✔ |
| MOM15 `k=1` DEV 24h net @0,10% | **+1,6690%** | **+1,6690%** (vòng trước) / +1,6431% (ref cũ) | ✔ |
| MOM15 `k=1` ALL 24h net @0,10% | **+2,2622%** | "+2,26%" (`RESULT_HARNESS_CONTROL.md` §2) | ✔ |
| `N_blk` (block-72h) MOM15 DEV | **301** | 301 | ✔ |

⇒ **Bộ đo tái tạo ĐÚNG neo MOM15** (7/7 khớp) ⇒ **không VOID**; mọi so sánh ở đây dùng được cùng harness
với vòng funding-factor/reversal-bounce. Số liệu vào **giống hệt** dòng M-LEVEL của vòng trước (kiểm tra
chéo: N=7 128, net=0,0166897 ở cả hai — xem §11 (i)).

## 2. BƯỚC 0 — coverage dùng cho lần này

| Mục | Kết quả |
|---|---|
| Nguồn funding | Aerospike `test.funding_data` (chỉ đọc), bin `f_data` = Snappy(JSON `{ts_ms: rate}`), host tunnel `127.0.0.1:3222` → `103.157.218.242:3222` |
| Nguồn giá | `raw/<sym>.f32` = bản extract **`kline_1m_opt`** (1 nến/phút, UTC), **627** symbol, 2021-01-01..2025-12-31 |
| Universe | **627/627** symbol có **cả** raw **và** funding record (khớp universe sim ~627 ⇒ không cần map lại) |
| Mốc 8h | **5 477** mốc có dữ liệu (00/08/16 UTC); **5 476** mốc có `n_elig ≥ 50` (**dùng chính**), bỏ **1** mốc (mốc `2021-01-01 00:00` — chưa có symbol nào có nến) |
| `n_elig`/mốc | min 0 → median **186** → max **588**; trung bình **234,5** (universe **lớn dần theo thời gian**: 2021 median 112 → 2025 median 463) |
| Tổng dòng grid | **1 289 338** cặp (mốc, symbol) |
| Cadence funding | **422** symbol 4h, **202** symbol 8h, 3 symbol không phân loại (theo **trung vị khoảng cách event** — xem caveat §11(iv)) |
| Rác | đã lọc `ts ≥ 2021-01-01` (3 symbol `GAIBUSDT`/`GRAMUSDT`/`STPTUSDT`) |

## 3. KẾT QUẢ CHÍNH — net/chu kỳ theo K (DEV = CHÍNH, phí 0,10%)

| K | net/chu kỳ (DEV) | CI72h×1.21 | p(>0) | CI-Bonf3 | %chu kỳ dương | N | N_blk | MDE80 |
|---|---|---|---|---|---|---|---|---|
| **5** | **−0,2223%** | [−0,3774%, −0,0672%] | 0,001 | [−0,3726%, −0,0759%] | **45,8%** | 4 382 | 487 | 0,20% |
| **10** | **−0,1709%** | [−0,2854%, −0,0564%] | 0,002 | [−0,2866%, −0,0487%] | **47,5%** | 4 382 | 487 | 0,20% |
| **20** | **−0,1460%** | [−0,2449%, −0,0471%] | 0,002 | [−0,2426%, −0,0445%] | **48,6%** | 4 382 | 487 | 0,20% |

**Đọc đúng bản chất:** cả 3 K đều **âm có ý nghĩa** — `CI72h×1.21` và `CI-Bonf3` **đều nằm ngoài 0 về
phía ÂM** (tức ta **bác bỏ được** giả thuyết "net = 0", theo chiều **lỗ**). Đây **không phải** NULL kiểu
"không phân giải được": N = 4 382 chu kỳ / 487 block-72h, MDE 0,20%/chu kỳ **< |hiệu ứng| 0,15–0,22%**
⇒ bộ đo **đủ lực** để kết luận net **ÂM**. (Với luật đã khoá, điều kiện GO cần net **> 0** ⇒ **KHÔNG đạt**.)

## 4. TURNOVER + COST DRAG — phần **quyết định** (DEV, phí 0,10%)

| K | turnover/chu kỳ (1 chiều) | giao dịch/chu kỳ | chân giá `raw` | funding `f_cum` | phí | **slip** | **cost tổng** | net | cost/gross |
|---|---|---|---|---|---|---|---|---|---|
| **5** | **44,8%** (med 40,0%, p90 80,0%) | 0,90 book | −0,1677% | **−0,2562%** | 0,0448% | **0,2660%** | **0,3108%** | **−0,2223%** | **351,2%** |
| **10** | **43,0%** (med 50,0%, p90 70,0%) | 0,86 book | −0,0937% | −0,1620% | 0,0430% | **0,1962%** | **0,2392%** | **−0,1709%** | **350,2%** |
| **20** | **40,0%** (med 40,0%, p90 60,0%) | 0,80 book | −0,0519% | −0,0954% | 0,0400% | **0,1495%** | **0,1895%** | **−0,1460%** | **435,2%** |

**Ba con số phải nhớ:**

1. **Turnover ≈ 40–45%/chu kỳ (1 chiều)** ⇒ **0,8–0,9 book giao dịch mỗi chu kỳ** (≈ **2,4–2,7 book giao dịch/ngày**). Với K nhỏ turnover **cao hơn** (K=5: 44,8%) — đúng cơ học vì top-5 nhạy với nhiễu
   xếp hạng (xem §11(iii)).
2. **Chi phí quay vòng 0,19–0,31%/chu kỳ = 350–435% của gross.** Trong đó **slip (0,15–0,27%) lớn hơn
   phí exchange (0,04%) 3,5–6 lần** — chính vì basket là các coin **biến động nhất** (§11(ii)).
3. **Gross dương rất nhỏ** (raw − funding = **+0,0885% / +0,0683% / +0,0435%** ở K=5/10/20), tức
   luật **có "alpha" thô** nhưng nó chỉ bằng **1/3,5 → 1/4,4** chi phí giao dịch của chính nó.
   **Thậm chí ở phí 0%**, cost slip (0,266% ở K=5) **vẫn lớn hơn gross 0,0885%** ⇒ **giảm phí exchange
   KHÔNG cứu được luật**; nút thắt là **slip × turnover**.

## 5. Độ nhạy phí + biến thể full-churn (DEV)

| K | 0,05% | 0,10% | 0,15% | full-churn @0,10% (cận trên chi phí) |
|---|---|---|---|---|
| **5** | −0,1999% [−0,3547%, −0,0451%] | −0,2223% [−0,3774%, −0,0672%] | −0,2447% [−0,3996%, −0,0897%] | −0,6799% [−0,8336%, −0,5263%] |
| **10** | −0,1494% [−0,2640%, −0,0348%] | −0,1709% [−0,2854%, −0,0564%] | −0,1924% [−0,3068%, −0,0780%] | −0,5519% [−0,6678%, −0,4360%] |
| **20** | −0,1260% [−0,2247%, −0,0272%] | −0,1460% [−0,2449%, −0,0471%] | −0,1660% [−0,2650%, −0,0670%] | −0,4705% [−0,5680%, −0,3730%] |

⇒ **Âm ở MỌI mức phí** (kể cả 0,05%). **Không** có ô nào đổi dấu ⇒ luật không "chết vì phí exchange",
mà chết vì **cấu trúc cost (slip × turnover) + chân giá âm**. Biến thể full-churn chỉ làm tệ thêm
(−0,47% → −0,68%/chu kỳ) — dùng làm **cận trên** để cho thấy kết luận không phụ thuộc cách tính turnover.

## 6. ALL (2021–2025, PHỤ — dán nhãn rõ) — phí 0,10%

| K | net/chu kỳ (ALL) | CI72h×1.21 | p(>0) | %chu kỳ dương | N | N_blk |
|---|---|---|---|---|---|---|
| **5** | **−0,1539%** | [−0,2867%, −0,0210%] | 0,004 | 46,8% | 5 476 | 609 |
| **10** | **−0,1069%** | [−0,2128%, −0,0011%] | 0,005 | 49,0% | 5 476 | 609 |
| **20** | **−0,0759%** | [−0,1693%, +0,0176%] | 0,021 | 50,2% | 5 476 | 609 |

⇒ ALL **cùng dấu âm** (không đổi dấu ⇒ cổng (6) của pre-reg cũng không đạt), nhưng **nhẹ hơn DEV** vì
**2021 là bull/alt-season** (đúng cảnh báo ghi trước ở pre-reg §6: 2021 có thể tạo dương giả). Ở K=20
CI **chứa 0** — nhưng đây là cửa sổ **PHỤ**, không dùng để tuyên bố.

## 7. Net/chu kỳ theo NĂM (GMT+7) — phí 0,10%

| K | 2021 (phụ) | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| **5** | +0,124% (n=1 093, 51%+) | −0,223% (n=1 095, 47%+) | −0,105% (n=1 095, 47%+) | −0,226% (n=1 098, 46%+) | −0,339% (n=1 095, 43%+) |
| **10** | +0,153% (n=1 093, 55%+) | −0,195% (n=1 095, 48%+) | −0,073% (n=1 095, 49%+) | −0,159% (n=1 098, 47%+) | −0,260% (n=1 095, 45%+) |
| **20** | +0,209% (n=1 093, 57%+) | −0,178% (n=1 095, 51%+) | −0,042% (n=1 095, 49%+) | −0,165% (n=1 098, 49%+) | −0,203% (n=1 095, 45%+) |

⇒ **Dương DUY NHẤT ở 2021** (bull), **âm cả 4 năm DEV** và **xấu dần về cuối** (2025 xấu nhất ở mọi K).
Đây là **dấu hiệu phản chỉ báo mạnh**: càng về sau (khi universe mở rộng, nhiều altcoin yếu) luật càng lỗ.
Tỷ lệ chu kỳ dương **< 60% ở mọi năm DEV** (kể cả 2021: 51–57%).

## 8. Đối chứng

### 8a. Trung bình universe cùng kỳ (long TOÀN BỘ eligible, equal-weight, **cùng mô hình chi phí**)

| | net/chu kỳ DEV | CI72h×1.21 | %chu kỳ dương | turnover | funding |
|---|---|---|---|---|---|
| universe (234 tên/mốc trung bình) | **−0,0129%** | [−0,1006%, +0,0748%] | 53,2% | 0,08% | +0,0002% |

- K=5 vs universe: **−0,2223%** vs −0,0129% ⇒ **top-K lowest-funding KÉM universe 0,209%/chu kỳ**;
  K=10 kém 0,158%; K=20 kém 0,133%.
- ⚠️ **Kết quả này phản trực giác và quan trọng**: "funding nhỏ nhất" **KHÔNG** phải "rẻ hơn" theo nghĩa
  tổng — nó là **tín hiệu về phía bán** (perp discount = phe short đang trả/đang thắng). Universe
  equal-weight (turnover ~0, chi phí ~0) cũng chỉ **−0,013%/chu kỳ, CI chứa 0** ⇒ baseline 2022–2025 ≈ 0;
  luật top-K **biến baseline 0 thành −0,22%**.

### 8b. Neo MOM15 (xem §1)

`MOM15 k=1` DEV 24h net @0,10% = **+1,6690%** (CI72h×1.21 [+0,0455%, +3,2925%], N=7 128, N_blk=301) —
**tái tạo đúng**, bộ đo còn phân giải được hiệu ứng dương cỡ ≳2%/lệnh ⇒ kết luận **NO-GO** ở trên **không**
do bộ đo hỏng.

### 8c. Dẫn chiếu H2 vòng trước

Vòng `RESULT_FUNDING_FACTOR.md` (commit `5b548e4`) đo **cùng hướng** ở dạng tĩnh (decile/portfolio 24h):
**D1 (funding thấp nhất) net 24h = −0,1913%, CI chứa 0**, IC cross-section **+0,0009** ≈ 0.

| | Vòng này (khung 8h, quay vòng, ALL/DEV) | Vòng trước (tĩnh 24h) | Nhất quán? |
|---|---|---|---|
| Dấu | **ÂM** (K=5: −0,2223% DEV / −0,1539% ALL) | **ÂM** (−0,1913%, CI chứa 0) | **NHẤT QUÁN** |
| Độ phân giải | CI **ngoài 0** (âm); 4 382 chu kỳ DEV / **487** block-72h; nửa-độ-rộng CI K=5 = **0,155%** ⇒ |eff| **vượt MDE 0,20%** ở K=5 | CI **chứa 0** (chưa phân giải được) | Vòng này **mạnh hơn**: **lật** từ "chưa kết luận được" sang "**kết luận ÂM**" |
| Cơ chế | funding thu **+0,256%/chu kỳ** nhưng chân giá **−0,168%** + cost **0,311%** | cùng hướng, biên độ 24h | nhất quán |

⇒ Kết quả này **củng cố và định lượng** kết luận H2 vòng trước: hướng "funding thấp ⇒ long" **không** chỉ
là NULL thiếu lực, mà ở khung 8h có **thể bác bỏ theo chiều lỗ**. **Nhất quán với tiền lệ**
`docs/analysis/SURVEY_OLDCODE_SIGNALS.md`: rule `FUNDING_FEE_BUY` → ML `funding_selector` → **FAIL (WFE med 0,098)**.
Vòng này **không** mâu thuẫn tiền lệ; nó thêm một bậc: kể cả khi **thu được funding thật**, **chi phí giao dịch
+ chân giá** vẫn khiến luật lỗ. **Không đề xuất áp dụng.**

## 9. Null test — long K coin NGẪU NHIÊN (cùng số lượng, cùng mô hình chi phí)

| K | null mean/chu kỳ (DEV) | null sd | p(null ≥ obs) | obs | rep |
|---|---|---|---|---|---|
| **5** | **−0,3811%** | 0,0193% | **0,000** | −0,2223% | 300 |
| **10** | **−0,3712%** | 0,0126% | **0,000** | −0,1709% | 300 |
| **20** | **−0,3543%** | 0,0092% | **0,000** | −0,1460% | 300 |

(null ALL: K=5 mean −0,3712% p=0,000; K=10 −0,3582% p=0,000; K=20 −0,3332% p=0,000)

**Đọc đúng bản chất (rất quan trọng):** basket **ngẫu nhiên** lỗ **−0,35…−0,38%/chu kỳ**; basket top-K
funding lỗ **−0,15…−0,22%/chu kỳ** ⇒ **xếp hạng theo funding CÓ giá trị so với random (+0,16…+0,21%/chu kỳ,
p = 0,000)** nhờ (a) **thu funding** thay vì **trả** funding, và (b) **turnover thấp hơn** (40–45% so với
~100% của random). **Nhưng "+0,2% so với random" ≠ "có lãi"**: cả hai đều **âm tuyệt đối**, và luật cần
**> 0** mới dùng được. Đây là ví dụ rõ của "**signal đúng hướng, level vẫn lỗ**".

## 10. ICC + đặc trưng basket + MDE

| K | ICC(ngày) | ICC(block-72h) | N | N_blk |
|---|---|---|---|---|
| 5 | 0,1060 | 0,0451 | 4 382 | 487 |
| 10 | 0,0759 | 0,0315 | 4 382 | 487 |
| 20 | 0,0443 | 0,0196 | 4 382 | 487 |

| K | `f_entry` mean (%/chu kỳ) | median | min | max | %tên `f≤0` | %tên `f=0` | tỷ lệ dòng `short_delist` |
|---|---|---|---|---|---|---|---|
| 5 | **−0,219%** | −0,0793% | **−3,000%** | +0,010% | **88,6%** | 1,1% | 0,0000 |
| 10 | −0,133% | −0,0444% | −3,000% | +0,035% | 81,5% | 1,0% | 0,0000 |
| 20 | −0,077% | −0,0224% | −3,000% | +0,066% | 72,9% | 0,9% | 0,0000 |

⇒ Basket là nhóm **funding rất âm** (trung bình −0,22%/chu kỳ ở K=5, có tên chạm **sàn −3%/chu kỳ**) ⇒
đúng cơ chế "perp discount mạnh" = nhóm **bị bán mạnh**. `short_delist` = **0** ở mọi K (không có delist
trong 8h của nhóm này — không phải nguồn nhiễu). ICC theo ngày 0,044–0,106 ⇒ có cụm theo ngày nhưng
không phá CI (N_eff 487 block vẫn lớn).

**MDE80** (lưới {0,01; 0,02; 0,05; 0,10; 0,20; 0,50}%/chu kỳ; nửa-độ-rộng p50 = 0,0958–0,1475%):

| K | MDE80 | p50 half-width | p80 | p95 |
|---|---|---|---|---|
| 5 | **0,20%** | 0,1475% | 0,1637% | 0,1808% |
| 10 | **0,20%** | 0,1134% | 0,1235% | 0,1328% |
| 20 | **0,20%** | 0,0958% | 0,1035% | 0,1117% |

⇒ Khung 8h cho **CI rất hẹp theo đơn vị %/chu kỳ** (0,10–0,15% nửa-độ-rộng) nhưng **MDE80 chạm sàn lưới
0,20%** ở cả 3 K (power ≥ 80% chỉ đạt ở mức 0,20%) ⇒ net −0,146…−0,222% **vượt MDE ở K=5** và **xấp xỉ
MDE ở K=10/20** ⇒ kết luận âm **có lực**, không phải "không phân giải được".

## 11. VÌ SAO LỖ — cơ chế (giải thích bằng số, không suy diễn)

Đây là phần trả lời trực tiếp "nếu turnover/chi phí giết luật ⇒ nói rõ bằng số":

(i) **Chân giá âm**: top-K funding nhỏ nhất có `raw` = **−0,1677%/−0,0937%/−0,0519%** (K=5/10/20) so với
**−0,0121%** của universe DEV ⇒ **chọn funding nhỏ nhất = chọn nhóm đang rơi**. (2021 ngược lại: raw basket
**+0,33…+0,39%/chu kỳ** — vì thế 2021 là năm dương duy nhất.)
(ii) **Slip bị thổi lên bởi chính tiêu chí chọn**: slip/chiều của basket = **0,334%/0,260%/0,207%**
(K=5/10/20) so với **0,139%** của universe ⇒ **×1,5–2,4**. Nhóm funding âm nhất là nhóm **biến động/thanh
khoản mỏng nhất**; "mua rẻ funding" = "mua đắt slip".
(iii) **Turnover**: 40–45%/chu kỳ; K càng nhỏ turnover càng cao (nhiễu xếp hạng ở đuôi) ⇒ cost drag **lớn
hơn ở K nhỏ** ⇒ net **xấu hơn ở K nhỏ** (−0,222% ở K=5 vs −0,146% ở K=20) — **ngược** chiều với "mong đợi
funding harvest lớn hơn ở K nhỏ".
(iv) **Thu funding là thật nhưng không đủ**: `f_cum` = **−0,256%/−0,162%/−0,095%** (âm = **thu**, đúng dấu
mong đợi của quy tắc) ⇒ quy tắc **làm đúng việc nó tuyên bố**, chỉ là **+0,77%/ngày tiền funding** bị
**0,93%/ngày chi phí giao dịch** + **0,50%/ngày chân giá âm** ăn hết.

**Caveat kỹ thuật** (ghi để trung thực, không đổi thiết kế): (a) phân loại cadence 4h/8h theo **trung vị
khoảng cách event trên cả 2021–2025**, nên symbol **đổi cadence giữa đời** có thể bị xếp lệch — điều này
chỉ ảnh hưởng **cách PHỤ (B)**, không ảnh hưởng cách chính (A); (b) `MIN_SYM=50` khiến **gần như mọi mốc**
được dùng (5 476/5 477) ⇒ cách phụ dùng **5 473/5 477** mốc — độ nhạy `MIN_SYM` 50 vs 100 **gần như bằng 0**
(−0,2224% vs −0,2223% ở K=5).

## 12. CÁCH PHỤ (B) + độ nhạy (descriptive — KHÔNG dùng để tuyên bố)

**B — universe CHỈ symbol cadence 8h** (202/627 symbol; `n_elig` median 165; 5 473 mốc):

| K | net/chu kỳ (DEV) | CI72h×1.21 | %chu kỳ dương | N | N_blk | turnover |
|---|---|---|---|---|---|---|
| **5** | −0,1837% | [−0,3123%, −0,0552%] | 46,2% | 4 379 | 487 | 42,2% |
| **10** | −0,1438% | [−0,2451%, −0,0425%] | 47,5% | 4 379 | 487 | 40,1% |
| **20** | −0,1220% | [−0,2129%, −0,0311%] | 49,8% | 4 379 | 487 | 36,7% |

⇒ **Cùng kết luận** (âm, CI ngoài 0 về phía âm, nhẹ hơn chút) ⇒ kết quả (A) **không** phải artefact của
việc trộn 2 cadence.

**Độ nhạy `MIN_SYM`** (DEV, phí 0,10%):

| MIN_SYM | số mốc dùng | K=5 | K=10 | K=20 |
|---|---|---|---|---|
| 50 | 5 476 | −0,2223% [−0,3774%, −0,0672%] | −0,1709% [−0,2854%, −0,0564%] | −0,1460% [−0,2449%, −0,0471%] |
| 100 | 5 213 | −0,2224% [−0,3774%, −0,0674%] | −0,1710% [−0,2855%, −0,0565%] | −0,1457% [−0,2445%, −0,0469%] |

## 13. CỔNG KẾT LUẬN (đã khoá, K_test = 3, Bonferroni p < 0,016667)

Cột (2) là "**cận dưới CI72h×1.21 > 0**" (điều kiện GO); *lưu ý CI **có** nằm ngoài 0, chỉ là **ngoài về
phía ÂM** ⇒ luật bị **bác bỏ theo chiều lỗ**, không phải "chưa phân giải được".

| K | (1) net>0 | (2) cận dưới CI >0 | (3) CI-Bonf3 >0 | (4) ≥60% chu kỳ dương | (5) \|net\|≥MDE | (6) không đổi dấu ALL | (7) không đổi dấu phí 0,15% | **GO?** |
|---|---|---|---|---|---|---|---|---|
| **5** | KHÔNG | KHÔNG | KHÔNG | KHÔNG (45,8%) | ĐẠT | KHÔNG | KHÔNG (−0,2447%) | **NO-GO** |
| **10** | KHÔNG | KHÔNG | KHÔNG | KHÔNG (47,5%) | KHÔNG | KHÔNG | KHÔNG (−0,1924%) | **NO-GO** |
| **20** | KHÔNG | KHÔNG | KHÔNG | KHÔNG (48,6%) | KHÔNG | KHÔNG | KHÔNG (−0,1660%) | **NO-GO** |

> **KẾT LUẬN CUỐI: NO-GO cả 3 K — luật bị TỪ CHỐI (không chỉ "chưa kết luận").**
> Không có K nào dương ⇒ **không** rơi vào nhánh "một K dương, K khác không" ⇒ **không có** UNCONFIRMED
> post-hoc cần ghi. **Không đề xuất áp dụng, không tích hợp, không đề xuất feature.**

## 14. Artifacts + vệ sinh + ghi chú kỷ luật

- Script (commit cùng file này): `research/analysis/funding_topk_rotate.py`,
  `research/analysis/funding_topk_rotate_stats.py`. Chỉ **ĐỌC** `raw/*.f32` + Aerospike `test.funding_data`.
- Trung gian (ngoài repo, resume được): `/tmp/funding_topk/{mark_grid.npz,anchor_mom15.npz,partial.npz,*.log,report.txt}`
  — **đã dọn file tạm sau khi commit** (theo pre-reg §9).
- **Hai lỗi cài đặt phát hiện & sửa TRƯỚC khi chốt số** (ghi để truy vết; **không** đổi thiết kế, cổng,
  K, cửa sổ hay tham số nào):
  1. **Index sai mảng cumsum**: bản nháp đầu dùng `cumsum[row_idx]` để lấy giá trị từng dòng ⇒ net bị
     **thổi lên ~16 200%/chu kỳ** (vô lý). Phát hiện ngay ở lần chạy smoke đầu tiên; sửa thành **index
     thẳng mảng giá trị đã sắp** rồi chạy lại **từ đầu**; số cũ **bị huỷ**, không dùng.
  2. **Block-72h lệch pha**: `BASE=26 824 320` **không** chia hết cho 4 320 ⇒ block theo *phút tương đối*
     cho **306** block, theo *phút epoch* (đúng như vòng trước) cho **301**. Đã chuyển về **phút epoch**
     để khớp harness (neo MOM15 §1: 301 ✔).
  - **(Fix định dạng)**: một số chuỗi in có `%%` thừa trong báo cáo text (chỉ ảnh hưởng **hiển thị**,
    không ảnh hưởng số). Số trong tài liệu này là số đã in đúng.
- Kiểm tra chéo độc lập: dòng M-LEVEL MOM15 của vòng này **trùng khít** `pools.npz` vòng trước
  (N=7 128, mean net = 0,0166897, khoảng phút lệch **0**) ⇒ đầu vào giống hệt, chỉ khác phép đo.
- Đối chiếu **nghi vấn ban đầu** của pre-reg §0: **đúng** — (a) hướng "funding thấp" âm như H2 vòng trước,
  (b) chi phí quay vòng **giết** luật (**cost/gross 350–435%**). Điều **chưa** tiên lượng được chính xác:
  luật **thu funding thật và đáng kể** (+0,77%/ngày) và **thắng random rõ rệt** (p=0,000) — nhưng **level
  vẫn lỗ**.
