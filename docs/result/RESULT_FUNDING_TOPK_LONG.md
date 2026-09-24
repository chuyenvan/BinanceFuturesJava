# RESULT_FUNDING_TOPK_LONG — LUONG DOI XUNG: **LONG top-K coin FUNDING CAO**

Ngày: 2026-09-23. Pre-reg: `docs/prereg/PREREG_FUNDING_TOPK_LONG.md` (**commit `da76e41`**, amend nguồn
universe V3 **`1203cf7`** — cả hai **TRƯỚC** khi đo; sau đó **không sửa thiết kế**). Script:
`research/analysis/funding_topk_long.py`. **Thuần Python**, 0-sim, **không** Java trên Oracle (shadow
active), **không** `claude-run`, **không push**, **không chạm 2026** (giá `raw/*.f32` hết ở
**2025-12-31 16:59 UTC** ⇒ 2026 không đo được). Trung gian **ngoài repo**:
`/home/ubuntu/claudedata/funding_topk_long/` (`report.txt`, `summary.json`, `anchor.npz`;
`grid.npz` 134 MB tái tạo bằng `python3 research/analysis/funding_topk_long.py build` ≈ 105 s).

## 0. KẾT LUẬN (một dòng)

> **NO-GO cả 3 biến thể.** LONG top-decile funding CAO **THUA ngay cả ở tầng GROSS** (DEV **−0,0433
> %/chu kỳ** = chân giá **−0,0259%** + **funding PHẢI TRẢ −0,0174%**) rồi cộng thêm chi phí quay vòng
> **0,1368%/chu kỳ** ⇒ net **V1 −0,1801%** (CI72h×1,21 **[−0,2716%, −0,0887%]**) / **V3 −0,1930%** /
> **V2 −0,4002%**; 38,0–49,3% chu kỳ dương (cổng đòi ≥60%); **null: long N coin NGẪU NHIÊN cho
> −0,1781%/chu kỳ ⇒ p(null ≥ thật) = 0,560 — luật funding cao KHÔNG có edge chọn coin**. Neo MOM15
> **tái lập đúng** (+1,6690% DEV @0,10%) ⇒ bộ đo không hỏng. **Không đề xuất build/tích hợp.**

## 1. Tuân thủ + kiểm chứng tái lập

| Kiểm chứng | Vòng này | Tham chiếu | Khớp |
|---|---|---|---|
| `n_elig`/mốc 8h: median / max | **186 / 588** | `RESULT_FUNDING_TOPK_ROTATE.md` §2: 186 / 588 | ✔ |
| Mốc dùng được (`n_elig ≥ 50`) | **5476 / 5477** | idem: 5476/5477 | ✔ |
| Universe | **627** symbol | idem: 627/627 | ✔ |
| Quy ước dấu | `rate>0` ⇒ long TRẢ / short THU | `RESULT_FUNDING_SIGN.md` §0–§1 | ✔ |
| **Neo MOM15** (M-LEVEL k=1, HOLD 24h, @0,10%) | **DEV +1,6690%** (N=7128, N_blk=**301**) · ALL **+2,2622%** | `funding_factor`/`funding_topk_rotate_stats` §0 neo **+1,6690%** (N=7128, N_blk=301); `RESULT_HARNESS_CONTROL.md` §2.1 đo **bộ event khác** (N=3167, +1,2793%) | ✔ **chính xác** |
| `total_rows` cross-section d15 | **619 073 711** | idem | ✔ |
| **S1 = short top-decile** (cùng harness) | **DEV −0,0935%** / ALL **−0,1402%**, CI [−0,2274%, −0,0529%] | `RESULT_SHORT_CARRY.md` §3.2 (**−0,0935%**) | ✔ **chính xác** |
| **L2 = long bottom-decile** (hướng long-side đã thua) | DEV **−0,1354%** | `RESULT_SHORT_CARRY.md` L1 DEV **−0,1354%** | ✔ **chính xác** |

⇒ Bộ đo **tái lập chính xác** cả 3 vòng trước (cùng nguồn, cùng mốc, cùng bậc) ⇒ **không VOID**.
Cột "funding" của S1 (+0,0251%) và L2 (+0,0552%) trùng khít vòng short ⇒ kế toán funding **đối xứng đúng**.

## 2. BƯỚC 0 — coverage

| Mục | Kết quả |
|---|---|
| Funding | Aerospike `test.funding_data` (chỉ đọc), bin `f_data` = Snappy(JSON); dùng ≤ 2025-12-31 |
| Giá 1m | `raw/<sym>.f32`, **627** file, UTC, [2021-01-01, **2025-12-31 16:59**] |
| Ô grid hợp lệ | **1 283 879** / 3 434 079 (giá **và** funding) |
| Universe V3 (proxy hệ thống) | `printDone.csv` của **`X1_GS_T170_2021_SEL_DROP_TOP8`** (đúng run `SELECTOR_RANK_TOPK=8`): **365/365** tên khớp `raw`, causal (mở rộng dần theo `start` đọc là UTC) |
| MOM15-active | **2052 / 5476** mốc dùng được (**37,5%**) có ≥1 phút MOM15 fire trong 24h trước |
| **Quy ước dấu** | `rate > 0` ⇒ **long TRẢ** ⇒ `funding = −f_cyc` (chi phí). DEV: **70,9%** ô hợp lệ có `f_cyc > 0` |

**Basket V1 (DEV):** `f_sig` top-decile mean **+4,15 bp**, med **+1,00 bp**, **100% > 0** (decile cao =
toàn bộ rate dương — chạm cả mức sàn 1 bp) · `f_cyc` top-decile mean **+0,0240%**, **76,6%** ô > 0
(⇒ đúng 76,6% chỗ đứng là **trả tiền**).

## 3. KẾT QUẢ CHÍNH — 3 biến thể + 4 đối chứng (chi phí chính: taker 0,05%/chân + slip proxy `0,5×(h−l)/c`/chân)

### 3.1 ALL 2021-2025 (%/chu kỳ 8h; funding ghi riêng **dấu THỰC** — âm = phải trả)

| Var | N chu kỳ | **net/chu kỳ** | **CI72h×1,21** | %dương | gross | (chân giá) | (**funding TRẢ**) | cost | turnover (1 vế) | cost/gross | **KL** |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **V1** pure | 5476 | **−0,1797%** | **[−0,2670%, −0,0923%]** | 49,7% | **−0,0197%** | +0,0054% | **−0,0251%** | 0,1599% | 34,36% | **810%** | **NO-GO** |
| **V2** + momentum | 3388 | **−0,3967%** | [−0,5526%, −0,2409%] | 38,7% | −0,0468% | −0,0020% | −0,0448% | 0,3500% | 67,06% | 749% | **NO-GO** |
| **V3** universe hệ thống | 4172 | **−0,1940%** | [−0,2925%, −0,0955%] | 48,6% | −0,0267% | −0,0101% | −0,0166% | 0,1673% | 39,75% | 627% | **NO-GO** |
| U: long universe EW | 5476 | +0,0292% | [−0,0574%, +0,1159%] | 54,2% | +0,0299% | +0,0369% | −0,0070% | 0,0006% | 0,11% | 2% | (chứa 0) |
| L2: long bottom-decile | 5476 | −0,0852% | [−0,1799%, +0,0095%] | 50,3% | **+0,0882%** | +0,0329% | **+0,0552%** | 0,1734% | 38,10% | 197% | (chứa 0) |
| S1: short top-decile | 5476 | −0,1402% | [−0,2274%, −0,0529%] | 44,6% | +0,0197% | −0,0054% | **+0,0251%** | 0,1599% | 34,36% | 810% | **NO-GO** |

### 3.2 DEV 2022-2025 (CHÍNH)

| Var | N | net/chu kỳ | CI72h×1,21 | %dương | gross | (chân giá) | (funding) | cost |
|---|---|---|---|---|---|---|---|---|
| **V1** | 4382 | **−0,1801%** | **[−0,2716%, −0,0887%]** | 49,3% | **−0,0433%** | **−0,0259%** | **−0,0174%** | 0,1368% |
| **V2** | 2647 | **−0,4002%** | [−0,5820%, −0,2183%] | 38,0% | −0,0672% | −0,0291% | −0,0381% | 0,3330% |
| **V3** | 3874 | **−0,1930%** | [−0,2947%, −0,0912%] | 48,7% | −0,0388% | −0,0232% | −0,0157% | 0,1541% |
| U | 4382 | −0,0148% | [−0,1025%, +0,0730%] | 53,2% | −0,0141% | −0,0144% | +0,0002% | 0,0006% |
| L2 | 4382 | −0,1354% | [−0,2341%, −0,0368%] | 49,4% | +0,0314% | −0,0352% | +0,0667% | 0,1668% |
| S1 | 4382 | −0,0935% | [−0,1834%, −0,0037%] | 45,3% | +0,0433% | +0,0259% | +0,0174% | 0,1368% |

> **Đối xứng tuyệt đối (bằng chứng dấu đúng):** V1 (long top) và S1 (short top) là **ảnh gương từng
> con số**: chân giá ±0,0054% (ALL), funding ∓0,0251%, cost y hệt 0,1599%, turnover y hệt 34,36%.
> Chỉ khác **vế nào trả/nhận funding** ⇒ V1 = S1 − 2×0,0251% ≈ **−0,19%** vs −0,14%. Kế toán chuẩn.

### 3.3 Theo năm (net/chu kỳ, chi phí chính)

| Var | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| **V1** | −0,1777 | **−0,2840** | −0,0749 | −0,1527 | −0,2091 |
| V2 | −0,3844 | −0,5351 | −0,1813 | −0,3634 | −0,5064 |
| V3 | −0,2069 | −0,3845 | −0,0597 | −0,1183 | −0,2395 |
| U | +0,2056 | −0,1068 | +0,0807 | +0,0285 | −0,0617 |
| L2 | +0,1159 | −0,1926 | −0,0362 | −0,1355 | −0,1774 |
| S1 | −0,3269 | **+0,0405** | −0,1731 | −0,1567 | −0,0846 |

⇒ **V1/V2/V3 âm ở CẢ 5/5 năm** (không năm nào dương) — khác hẳn S1 (1/5 năm dương, 2022).

## 4. Độ bền theo CHI PHÍ (V1, DEV) — "chết trước cả khi tính phí"

| Biến thể chi phí | net/chu kỳ | CI72h×1,21 | %dương |
|---|---|---|---|
| taker 0,05 + slip proxy (CHÍNH) | **−0,1801%** | [−0,2716%, −0,0887%] | 49,3% |
| maker 0,02 + slip proxy | −0,1603% | [−0,2518%, −0,0689%] | 49,7% |
| taker 0,05 + slip phẳng 0,140%/chân | −0,1687% | [−0,2592%, −0,0782%] | 49,4% |
| taker 0,05 + slip nến-ra | −0,1789% | [−0,2703%, −0,0876%] | 49,5% |
| taker 0,05 + slip **1 bp/chân** (lạc quan phi thực tế) | **−0,0829%** | [−0,1731%, **+0,0073%**] | 51,0% |
| taker 0,05 + **round-trip toàn sổ/chu kỳ** (cận trên) | −0,4341% | [−0,5242%, −0,3441%] | 43,0% |

**Quan trọng hơn cả bảng phí:** **gross DEV đã ÂM (−0,0433%)** và **gross ALL cũng ÂM (−0,0197%)**
⇒ ngay khi **bỏ hết chi phí**, luật này vẫn lỗ, vì (i) chân giá của nhóm funding cao **≈ 0 / hơi âm**
(DEV −0,0259%) và (ii) **funding phải TRẢ** (−0,0174%/chu kỳ DEV). Chi phí quay vòng chỉ **nhân lỗ lên
3–8×**, không phải nguyên nhân duy nhất. (Khác vòng short: ở đó gross **+0,0197%** ⇒ short "chết vì phí";
long "chết ngay ở gross".)

## 5. RỦI RO LONG — drawdown trong `(r, r+480]` (adverse) + MFE

| Var | n vị thế | DD p50 | p10 | p05 | **p01** | **min** | MFE p50 | MFE p90 | **%DD>20%** |
|---|---|---|---|---|---|---|---|---|---|
| **V1** | 128 333 | −1,76% | −6,29% | −8,74% | **−16,93%** | **−93,46%** | +1,59% | +6,04% | **0,65%** |
| V2 | 21 185 | −2,52% | −8,56% | −11,76% | **−23,95%** | −93,22% | +2,32% | +8,24% | **1,54%** |
| V3 | 74 983 | −1,72% | −5,76% | −7,86% | −14,95% | −93,46% | +1,57% | +5,48% | 0,51% |
| U | 1 283 879 | −1,79% | −5,81% | −7,86% | −14,20% | −97,57% | +1,61% | +5,67% | 0,43% |

Worst (V1): `NAORISUSDT` 2025-10-10 −93,46% · `SOLVUSDT` 2025-10-10 −93,22% · `TANSSIUSDT` 2025-10-10
−88,61% · `PIPPINUSDT` 2025-10-10 −88,42% · `DYMUSDT` 2025-10-10 −85,42% · `FARTCOINUSDT` 2025-10-10
−84,77% (ngày thanh lý toàn thị trường 10-10-2025) · `PORT3USDT` 2025-11-22 −82,23% · `TACUSDT` 2025-10-10 −82,15%.

**Đọc:** ~0,65% vị thế long **mất >20% trong 1 chu kỳ 8h**, đuôi tới **−85…−93%** — trong khi gross kỳ
vọng của cả chu kỳ chỉ là **−0,04%**. Rủi ro đuôi **lớn hơn lợi nhuận kỳ vọng ~10³–10⁴ lần** và
**cùng chiều với lỗ** (long coin funding cao = mua đuôi pump). Đối chiếu vòng short: nhóm coin này khi
long còn **nguy hiểm hơn** khi short (DD p01 −16,9% vs drawup p01 +20,4%). Chưa mô hình hoá
margin/liquidation.

## 6. NULL + MDE

| Var | Null (long N coin ngẫu nhiên cùng số lượng, 300 rep, seed 20260905) | p(null ≥ thật) |
|---|---|---|
| **V1** | mean **−0,1781%** (p05 −0,1946%, p95 −0,1627%) | **0,560** |
| V2 | mean −0,1622% (p05 −0,1843%, p95 −0,1421%) | 1,000 |
| V3 | mean −0,2058% (p05 −0,2217%, p95 −0,1912%) | 0,090 |

- **V1 KHÔNG thắng null**: chọn đúng decile funding cao (−0,1797%) **không tốt hơn** long N coin ngẫu
  nhiên (−0,1781%) — thậm chí nhích kém hơn. ⇒ **luật funding không có edge chọn coin ở phía long**;
  phần chênh so với "long universe EW" (U −0,0148%) là do **phải quay vòng** (U turnover 0,11% ⇒ cost
  ~0), không phải do chọn sai/đúng nhóm.
- **MDE80**: V1 **0,10 %/chu kỳ**; V2/V3 **0,20%**. |net| của cả 3 biến thể **≥ MDE80** ⇒ kết luận **âm
  có lực thống kê**, không phải "thiếu mẫu".

## 7. ĐỐI CHIẾU — đổi phía có lật không? (trả lời trực tiếp câu hỏi chủ dự án)

| Hướng | Luật | net/chu kỳ (DEV) | CI72h×1,21 | %dương | funding |
|---|---|---|---|---|---|
| LONG funding **thấp nhất** (vòng trước, `RESULT_FUNDING_TOPK_ROTATE` DEV K=20) | long bottom | −0,1460% | âm | 48,6% | **TRẢ** |
| **L2** long bottom-decile (cùng harness) | long bottom | −0,1354% | [−0,2341%, −0,0368%] | 49,4% | **TRẢ +0,0667% → tức −0,0667% cho long** |
| **S1** SHORT top-decile funding cao (vòng short) | short top | −0,0935% | [−0,1834%, −0,0037%] | 45,3% | **THU** |
| **V1** **LONG top-decile funding cao (vòng này)** | long top | **−0,1801%** | [−0,2716%, −0,0887%] | 49,3% | **TRẢ** |
| U long toàn universe EW (baseline "funding trung bình") | long all | −0,0148% | [−0,1025%, +0,0730%] | 53,2% | ≈0 |
| **Neo MOM15** (market timing, 24h) | long, timing | **+1,6690%/lệnh** | [+0,1455%, +3,3925%]¹ | — | — |

**Trả lời:** **BUY coin funding cao KHÔNG hoạt động — và tệ HƠN cả short.** Cả 4 góc
(long-thấp / short-cao / long-cao / long-universe) đều **âm hoặc ≈0**:
- chân giá của nhóm funding cao **≈ 0** (đối xứng hoàn hảo ±0,0054% ALL) ⇒ momentum có thật nhưng
  **cỡ bằng 0** ở khung 8h, không đủ trả phí;
- đổi phía chỉ đổi **ai trả funding**: long trả −0,0251%, short thu +0,0251% ⇒ **long cao = short cao −
  2×funding**, tức **luôn xấu hơn short** với cùng rổ (V1 −0,1801% < S1 −0,0935%);
- **long universe EW (U)** ≈ 0 (CI chứa 0) ⇒ "mua rổ" không lỗ, nhưng **luật top-K funding cao làm nó
  lỗ** vì cộng thêm 0,16%/chu kỳ quay vòng mà **không** mua được chân giá nào.

¹ CI in ở bảng trên là của chuỗi net **trước** khi trừ phí neo 0,10%; số neo **+1,6690%** là **sau** khi
trừ phí neo (đúng quy ước `funding_topk_rotate_stats` §0).

## 8. ĐỐI CHIẾU MOM15 (trùng lặp?) — theo §7 pre-reg

| Var | net trên mốc **MOM15-ACTIVE** (n=2052) | net trên mốc **MOM15-QUIET** (n=3424) | CI72h×1,21 (quiet) |
|---|---|---|---|
| **V1** | −0,1438% | **−0,2011%** | [−0,2964%, −0,1058%] |
| V2 | −0,3012% | −0,4682% | [−0,6674%, −0,2689%] |
| V3 | −0,1716% | −0,2055% | [−0,3141%, −0,0970%] |

- **Không có phần dương nào để "trùng"**: net âm ở **cả** MOM15-active **và** MOM15-quiet (quiet thậm
  chí âm hơn). Nghịch với pattern "edge MOM15 chủ yếu là hiệu ứng THỜI ĐIỂM" — luật này **không** có
  edge thời điểm để mượn.
- **Khác MOM15 về bản chất và về cỡ:** MOM15 = tín hiệu **market-timing** (fire cụm khi bán tháo),
  **+1,6690%/lệnh 24h DEV**; V1 = luật **cross-section funding** mỗi 8h, **−0,1801%/chu kỳ** (≈ −0,54%/ngày).
  Không trùng, không thay thế được MOM15 — và cũng **không** dương.
- **Neo MOM15 vẫn tái lập đúng** (mục §1) ⇒ "không trùng MOM15" là kết luận **có bộ đo kiểm chứng**,
  không phải do harness hỏng.

## 9. KẾT LUẬN theo cổng đã khoá (§7 pre-reg)

| Cổng | V1 | V2 | V3 |
|---|---|---|---|
| net > 0 sau TẤT CẢ chi phí (kể cả funding TRẢ) | ✗ (−0,1801%) | ✗ (−0,4002%) | ✗ (−0,1930%) |
| CI72h×1,21 ngoài 0 | ✗ (ngoài 0 **về phía ÂM**) | ✗ (ÂM) | ✗ (ÂM) |
| ≥60% chu kỳ dương | ✗ (49,3%) | ✗ (38,0%) | ✗ (48,7%) |
| Bền vững qua biến thể | ✗ (âm cả 5/5 năm; **gross đã âm**; mọi biến thể phí đều âm) | ✗ | ✗ |
| Không trùng MOM15 + không âm ở biến thể phí bảo thủ | ✗ (âm ở cả active/quiet; round-trip −0,4341%) | ✗ | ✗ |

> ### **KẾT LUẬN: NO-GO (không NULL, mà là ÂM có ý nghĩa).**
> Không biến thể nào dương ⇒ **không có UNCONFIRMED/post-hoc** nào cần xử lý. Riêng **edge chọn coin**
> thì đúng là **NULL** (p=0,560) — cần nói rõ cả hai: *chiến lược âm*, và *luật xếp hạng funding không
> mang thêm thông tin gì ở phía long*.
> **KHÔNG đề xuất build/tích hợp.** (Engine cũng chưa có đường long đặc thù cho funding; đây là đo
> counterfactual offline.)

**Trả lời câu hỏi owner (1 câu):** *"BUY coin funding cao"* **thất bại** — và thất bại **nặng hơn**
short: chân giá của nhóm này ở khung 8h **bằng 0** (đúng như ảnh gương của vòng short ±0,0054%), nên
long chỉ khác short ở chỗ **đảo dấu funding từ THU (+0,0251%) thành TRẢ (−0,0251%)**, kết quả
−0,1801% (DEV) với CI âm, 0/5 năm dương, thua cả "long universe EW" (≈0). **Đây là kết cục tất yếu
của một luật có cỡ tín hiệu (bp) nhỏ hơn chi phí (hàng chục bp) — không phải vấn đề tham số.**

## 10. GIỚI HẠN (nói rõ)

(i) Không có **dữ liệu fill thật** ⇒ chi phí là **mô hình**; ở đây kết luận **không phụ thuộc** chi phí
vì **gross đã âm**. (ii) `f_sig` là rate **đã settle** (trễ ≤ 1 chu kỳ) — causal đúng, không phải
"rate kỳ tới". (iii) Cadence 4h/8h hỗn hợp: 1 chu kỳ 8h tính **đủ mọi event settle** trong cửa sổ.
(iv) Không mô hình **margin/liquidation** ⇒ drawdown chỉ là **cảnh báo**. (v) Decile phụ thuộc #symbol
theo thời gian. (vi) **Universe V3 là proxy** từ `printDone.csv` (`SEL_DROP_TOP8`), symbol chỉ vào
universe **sau** lệnh đầu tiên ⇒ muộn hơn thực tế (bảo thủ); N V3 = 4172/5476 mốc. (vii) Neo MOM15
dùng `cache2.npz` do **vòng trước** sinh từ cùng nguồn `kline_1m_opt` — tái lập ở đây kiểm **chuỗi +
bộ đo**, không sinh lại từ đầu. (viii) Decile "top" của funding cao phần lớn là coin **mới/thanh khoản
mỏng** (med f_sig = 1 bp = mức sàn) ⇒ cẩn trọng về khả năng giao dịch thật (thêm bất lợi, cùng chiều).

## 11. SẢN PHẨM

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_FUNDING_TOPK_LONG.md` | chốt trước (commit `da76e41`; amend `1203cf7`) |
| `docs/result/RESULT_FUNDING_TOPK_LONG.md` | file này |
| `research/analysis/funding_topk_long.py` | script thuần Python (build grid + neo MOM15 + thống kê) |
| `/home/ubuntu/claudedata/funding_topk_long/{report.txt,summary.json,anchor.npz}` | log + số tổng hợp (**ngoài repo**) |

`grid.npz` (134 MB) **đã dọn** sau commit — tái tạo: `python3 research/analysis/funding_topk_long.py build`
(≈105 s) rồi `... stats` (≈13 phút, gồm 300 rep null × 3 + MDE lồng cho 6 cấu hình).
