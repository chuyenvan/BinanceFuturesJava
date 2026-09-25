# PREREG_MODEL_RULER — THƯỚC ĐÁNH GIÁ **MODEL** (ranker), TÁCH KHỎI thước HỆ THỐNG (sim)

**Ngày chốt:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** CHỐT TRƯỚC — chưa chạy dòng nào
**Vòng:** ARM44 (`7eb4c2b` pre-reg · `48d7c2d` result `GIỮ 45`) → vòng này **KHÔNG** train, **KHÔNG** sim.

---

## 0. CÂU HỎI (nguyên văn chủ dự án, không diễn giải lại)

> *"selector train để scoring theo điểm số ⇒ nó sẽ chính xác nếu coin A được điểm cao thì khi vào mô hình
> hoặc tính bằng 1 thước đo nào sẽ cao hơn coin B ⇒ mình có nên xây cái thước này để thực sự biết tập
> features mới train sẽ tốt hơn không. Còn hiện tại tôi thấy train rồi ghép vào hiện trạng thế thông hiện
> tại (có thể sẽ thay đổi rất nhiều) thì hơi bị thiên kiến — nó ko phản ánh đúng là model tốt hơn, chỉ là
> **hợp hơn** mà hợp với 1 cái chưa tốt hoặc sẽ thay đổi nhiều thì ko hợp lý."*

**Vấn đề đo được ở vòng ARM44:** hai thước **MÂU THUẪN**:
- **SIM** (thước HỆ THỐNG): `A44 ≥ A45` (0 rate ngoài CI; maxDD/UW MTM tốt hơn; PnL +71.250 vs +68.083).
- **THƯỚC XẾP HẠNG** (rank-IC/lift8): `A45 > A44` **ngoài CI** (`ΔIC +0,001965`; `Δlift@8 −0,003075`).

⇒ Vòng này xây **một** thước dùng lại được cho **MODEL**, chốt TRƯỚC định nghĩa + ngưỡng + luật, rồi
**kiểm tra thước bằng cách tự nó có nói lại được kết luận `GIỮ 45` hay không**.

### 0.1 HAI TẦNG (chốt trước — đây là sản phẩm chính)

| tầng | thước | câu hỏi nó trả lời | KHÔNG được hỏi |
|---|---|---|---|
| **A — THƯỚC MODEL (ruler)** | bộ chỉ số ranker offline (mục 2) | *"tập feature mới có phải RANKER tốt hơn không?"* | không nói gì về equity/lệnh/DD |
| **B — SIM** | SIM trên nền KEEPLEG0 | *"sau khi đã qua Tầng A, model đó có làm HỆ THỐNG tốt hơn trong hiện trạng không?"* | không phải thước chọn model |

**Ràng buộc bắt buộc của Tầng B (chốt trước):** SIM **chỉ** được chạy cho model **đã qua Tầng A**, VÀ
**phải RE-CALIBRATE gate theo scale score của model mới**. Lý do đã đo trong repo: `G5_VALUE_LABELS`
(bảng §4 runbook) — đổi phân phối `P(win)` ⇒ đổi multiset ⇒ đổi `dyn_thr` ⇒ đổi số lệnh. So sánh sim
giữa hai model **khác scale score** mà **không** re-calibrate là **vô nghĩa** (đo calibration, không đo skill).

---

## 1. NGUỒN DỮ LIỆU (cố định — chỉ dùng artifact ĐÃ CÓ, không train/sim)

| tên | vai trò | nguồn | chế độ |
|---|---|---|---|
| `45deploy` | MỐC (bản deploy 45 feat) | bins `claudedata/predwf_G015x26/predict_wf_<fold>.bin` + nhãn `/home/ubuntu/label_15m` | **RAW** |
| `A45` | đối chứng **retrain** (45 feat, cùng kernel/seed) | `kaggle_sim/out/a44out/A45_perfold_ticks.parquet` | AGG |
| `A44` | **ỨNG VIÊN 1** (45 − `rvol15m`) | `kaggle_sim/out/a44out/A44_perfold_ticks.parquet` | AGG |
| `V0` | **ỨNG VIÊN 2** (cắt 45 → 21 keeper) | `claudedata/stage2_featvar_out/stage2/V0_perfold_ticks.parquet` | AGG |
| `V5` | đối chứng **NHIỄU cùng NaN-mask** (bẫy OFI) | `claudedata/stage2_featvar_out/stage2/V5_perfold_ticks.parquet` | AGG |
| `V1` | tham chiếu (26 feat, OFI thật) | `.../V1_perfold_ticks.parquet` | AGG |

- Cả 6 arm đã kiểm: **140.238 tick, `ts` TRÙNG KHÍT từng dòng** (đo ở vòng này) ⇒ mọi `Δ` ghép cặp được.
- Định dạng bins: `>i8 ts, >i2 sym, >f4 p0` (26 B/rec = 4 giá trị horizon); `p0 = P(win)`, nhãn
  `y_thr = (retEnd_4h > 0,015)`, `THR = 0,015`; chỉ tick có **≥ 2 coin** sau khi join nhãn.
- `retEnd_4h` = `close(t+4h)/close(t) − 1` (`ExportFundingLabel.java:40`) = **GROSS**, KHÔNG trừ chi phí.
- **DEV only**: 16 fold `20220101..20251001`; **KHÔNG** chạm 2026/`HoldoutSeal`.

---

## 2. BỘ CHỈ SỐ (chốt TRƯỚC — 1 dòng/chỉ số)

| # | chỉ số | định nghĩa (1 dòng) | chế độ |
|---|---|---|---|
| M1 | **rank-IC** | Spearman cross-section **trong từng tick** giữa `score` và `retEnd_4h` (chỉ tick ≥ 2 coin) | RAW+AGG |
| M2 | **\|rank-IC\|** | độ lớn của M1 (dùng cho luật; **KHÔNG** dùng một mình để kết luận) | RAW+AGG |
| M3 | **lift@8** | `mean(y_thr)` của **top-8 theo score** trong tick **−** `mean(y_thr)` toàn tick (K = 8 = K selector) | RAW+AGG |
| M4 | **precision@8** | `mean(y_thr)` của top-8 trong tick (chính là `t8`) | RAW+AGG |
| M5 | **AUC (within-tick)** | Mann–Whitney: `P(score_pos > score_neg)` trong 1 tick, gộp theo tick (trung bình) | RAW |
| M6 | **pairwise accuracy** | `P(score_A > score_B \| y_A > y_B)`; đo trong tick ⇒ `= 0,5 + 0,5·Kendall_τ` (đúng câu chủ dự án nói) | RAW |
| M7 | **decile monotonicity** | chia 10 decile theo score trong tick → `mean(retEnd_4h)` mỗi decile → lấy trung bình qua tick → báo `Spearman(decile, mean_y)` + số cặp kề **không giảm** / 9 | RAW |
| M8 | **gross@8** | `mean(retEnd_4h)` của top-8 trong tick (chọn theo score) | RAW |
| M9 | **net@8** | `gross@8 − 0,008` với chi phí round-trip `fee 2×0,002 + slip 2×0,003 = 0,008` (`Configs.java` RATE_FEE/SLIPPAGE_RATE) | RAW |
| M10 | **net_lift@8** | như M3 nhưng trên nhãn **net**: `y_net = (retEnd_4h − 0,008 > 0,015)` | RAW |
| M11 | **drift** | `mean(first 8 fold) − mean(last 8 fold)` của M1 và M3 (mô tả, **không** có luật) | RAW+AGG |
| M12 | **theo FOLD / theo NĂM** | bảng M1/M3 theo từng fold (16) và theo năm (UTC+7h, khớp `TZ=+7h` của trainer) | RAW+AGG |

- **FUNDING — KHAI BÁO RÕ (không che):** công thức net ở M9 **CHƯA** trừ funding (không có chuỗi funding-rate
  local; crawler `HistoricalFundingCrawlerLocal` gọi API ⇒ ngoài phạm vi offline). Đối chứng: sim/WFO của
  repo cũng **mặc định** `APPLY_FUNDING_FEE=false` (comment `Configs.java:130`: tác động ~0,9 % PnL, maxDD
  không đổi). ⇒ Mọi kết luận net ở vòng này là net **"ex-funding"** — ghi rõ, không gọi là net đầy đủ.
- **"ngoài CI" của vòng này:** ngoài **CẢ HAI** độ rộng (xem §3).

---

## 3. CI (KHÔNG bịa hệ số — dùng lại hằng số có sẵn)

- Máy: **block-72h bootstrap, NREP = 2000, seed = 20260905** — import `c3_rates` (BLOCK_H/NREP/SEED) qua
  `stage2_score.block_boot_mean`; **ghép cặp theo `ts`** cho mọi `Δ` (chỉ tick chung).
- **`k`** = số ỨNG VIÊN của vòng. Vòng này có **2 ứng viên** ở **2 họ khác nhau** (`A44` bỏ-cột · `V0`
  cắt-về-21), mỗi ứng viên so trong **họ của nó** ⇒ mỗi phép so có `k = 1` ⇒ in
  **`inflate(1) = 1,0`** (CI gốc, không nở).
- **Độ rộng QUYẾT ĐỊNH = `1.21`** = `gd92xexit_score.LEGACY` (**hằng số có sẵn trong repo**, không phải hệ
  số mới). "Ngoài CI" = ngoài **CẢ HAI** (tức ngoài 1.21).

---

## 4. HAI ĐỐI CHỨNG BẮT BUỘC (mọi kết luận là `Δ` so với CẢ HAI)

| đối chứng | là gì | trừ được cái gì |
|---|---|---|
| **C1 = retrain control** | cùng feature set, train lại: `A44` ↔ `A45` (cùng kernel/seed/matrix) | **nền nhiễu retrain** (bài học: train lại cùng config đã đẩy 1 rate ra ngoài CI) |
| **C2 = noise control cùng NaN-mask** | `V5` (5 cột nhiễu, NaN-mask y hệt 5 cột OI thật) cho họ `V*` | **bẫy OFI** (nhiễu "thắng" y như feature thật) |

- Ứng viên **A44**: so với **`45deploy` (MỐC)** và **`A45` (C1)**.
- Ứng viên **V0**: so với **`45deploy` (MỐC)** và **`V5` (C2)**.
- Tham chiếu thêm (không quyết định): `A45 − 45deploy` (nền nhiễu deploy-vs-retrain), `V5 − V0`, `V1 − V0`.

---

## 5. LUẬT QUYẾT ĐỊNH (chốt TRƯỚC)

**Chỉ số CHÍNH = `lift@8` (M3); chỉ số PHỤ BẮT BUỘC = `|rank-IC|` (M2).**

Ứng viên `X` **ĐỔI ĐƯỢC MỐC** (ruler nói "feature set mới tốt hơn") khi **đồng thời**:
1. **`Δlift@8(X − control) > 0` NGOÀI CI** (độ rộng 1.21) so với **CẢ HAI** đối chứng; **VÀ**
2. **`Δ|rank-IC|` KHÔNG bất lợi ngoài CI** so với **CẢ HAI** (CI của `Δ|IC|` **không** nằm trọn âm); **VÀ**
3. `precision@8` (M4) không xấu hơn, và (`AUC`/`pairwise`/`decile` — nếu có RAW) cùng hướng.

Không thoả ⇒ **KEEP (NULL)** = "chưa chứng minh được feature set mới là RANKER tốt hơn ⇒ **KHÔNG đổi**".

- **Sign convention (ghi rõ, KHÔNG giấu):** `rank-IC` của **mọi** arm vòng ARM44 **ÂM** (đã công bố ở
  `RESULT_ARM44` §7). Luật dùng **`|IC|`** để không phụ thuộc dấu; nếu arm nào **LẬT DẤU** IC mà không
  tăng `lift@8` ⇒ **ghi rõ là bất thường**, không tự động coi là tốt.
- **KHÔNG** dùng equity/`n`/PnL làm tiêu chí (đó là Tầng B).

---

## 6. TỰ KIỂM THƯỚC (bắt buộc — thước phải chứng minh nó CÓ phân biệt được, và phân biệt ĐÚNG)

| # | test | PASS khi |
|---|---|---|
| **T1 — null/sensitivity** | xáo score **trong từng tick** (permutation, seed cố định 20260905) trên `45deploy` | `lift@8 ≈ 0` và `\|IC\| ≈ 0`, `Δ` vs `45deploy` **ngoài CI theo hướng XẤU** ⇒ thước **thấy được** khi mất tín hiệu |
| **T2 — bất biến theo RANK (tách khỏi calibration)** | biến đổi score của `45deploy` bằng hàm **tăng nghiêm ngặt** (quantile→uniform và `logit`) | **mọi** chỉ số M1–M10 **giống nhau** (sai số < 1e-9) ⇒ thước đo **THỨ TỰ**, **KHÔNG** đo scale ⇒ đúng thứ cần để tách Tầng A khỏi việc re-calibrate gate ở Tầng B |
| **T3 — coverage/provenance** | `n_tick`, `n_coin`, số tick `n8 = 8`, `ts` khớp `45deploy` | khớp khít; lệch ⇒ DỪNG, báo rõ |

---

## 7. VALIDATE THƯỚC (việc quan trọng nhất): ruler có TỰ NÓI LẠI được `GIỮ 45`?

Câu hỏi: **chạy ruler trên 5 arm — `45deploy`(MỐC) · `A45` · `A44` · `V0` · `V5` — thì ruler có tự kết
luận "KHÔNG đổi model" (= `GIỮ 45`) hay không?** Nếu **KHÔNG** ⇒ **thước chưa dùng được**, phải nói RÕ
chỗ sai. Cách kiểm (chốt trước):

| mã | kiểm | "tự nói lại được `GIỮ 45`" khi |
|---|---|---|
| **V-A** | `A44` vs {`45deploy`, `A45`} theo luật §5 | **KHÔNG** ĐỔI ĐƯỢC ⇒ KEEP |
| **V-B** | `V0` vs {`45deploy`, `V5`} theo luật §5 | **KHÔNG** ĐỔI ĐƯỢC ⇒ KEEP |
| **V-C** | bẫy OFI: ruler có tuyên `V5` (nhiễu) tốt hơn `V0` ngoài CI không? | **KHÔNG** (nếu CÓ ⇒ thước dính bẫy OFI ⇒ FAIL) |
| **V-D** | nền nhiễu retrain: `A45 − 45deploy` | báo cáo (không đặt ngưỡng) |
| **V-E** | T1 + T2 (§6) | cả hai PASS |

**Kết luận tổng:** `GIỮ 45` được **tự nói lại** ⟺ **V-A PASS ∧ V-B PASS ∧ V-C PASS ∧ V-E PASS**.
Ngược lại ⇒ ghi rõ là thước **chưa dùng được** ở mục nào (không nới luật sau khi xem số).

---

## 8. GIỚI HẠN ĐÃ BIẾT TRƯỚC (ghi trước, không phải "phát hiện" sau)

1. **RAW chỉ có cho `45deploy`** (bins giá trị). 4 arm retrain không giữ bins ⇒ **M5/M6/M7/M8/M9/M10 chỉ
   chạy được trên `45deploy`**; `Δ` giữa các arm chỉ có **AGG** (M1–M4). Đây là **khoảng trống của hạ tầng
   kernel** (không tải 5 GB bins), **không** phải lỗi của thước.
2. **Funding chưa tính** trong M9 (mục 2) — ngoài phạm vi offline.
3. **`45deploy` chỉ 16 fold 2022+** giống các arm khác (2 fold 2021 giống nhau tuyệt đối) ⇒ mọi so sánh
   chỉ nói về **16 fold OOS 2022+**.
4. Ruler **KHÔNG** thay SIM: nó là **cổng trước** (Tầng A). Model qua Tầng A **vẫn** phải sim (Tầng B),
   và sim đó **phải re-calibrate gate**.

---

## 9. DỰ ĐOÁN KHOÁ TRƯỚC

| # | dự đoán | cách kiểm |
|---|---|---|
| **Q1** | `T2` PASS tuyệt đối (M1–M10 bất biến rank, sai số < 1e-9) | §6 |
| **Q2** | `T1` PASS: `lift@8` shuffled ≈ 0 (trong ±0,005) và ngoài CI vs `45deploy` | §6 |
| **Q3** | `V-A KEEP`: `Δlift@8(A44−A45) < 0` ngoài CI (tái lập `−0,003075`) ⇒ ruler **tự nói lại** `GIỮ 45` | §7 |
| **Q4** | `V-B KEEP`: `Δlift@8(V0−V5) ≤ 0` và CI phủ 0 (khớp NULL Stage 3) | §7 |
| **Q5** | `V-C PASS`: `V5` KHÔNG tốt hơn `V0` ngoài CI | §7 |
| **Q6** | `A45 − 45deploy` ≈ 0 (nền nhiễu retrain nhỏ) | §7 |
| **Q7** | `net@8 < gross@8` đúng bằng ≈ 0,008 và `net_lift@8 < lift@8`; **nhưng** dấu/kết luận **không đổi** (chi phí là hằng số trên mọi coin) ⇒ ruler kết luận giống nhau ở gross và net | §2/§5 |

- **Nếu Q3 hoặc Q5 SAI** ⇒ thước **chưa tự nói lại được** kết luận cũ ⇒ **DỪNG kết luận `GIỮ 45`**, ghi rõ
  chỗ sai và sửa luật/thước **trong doc này** (không sửa sau khi xem số ở vòng sau mà không khai báo).

---

## 10. ĐỀ XUẤT RUNBOOK (đề xuất — chỉ sửa nếu chắc chắn, kèm commit riêng)

Thêm vào `docs/runbooks/AGENT_RUNBOOK.md`: **"thước CHỌN MODEL = model ruler (Tầng A, offline, rank-only);
SIM = kiểm HỆ THỐNG và CHỈ chạy sau khi model đã qua Tầng A + đã re-calibrate gate theo scale score mới."**
Mọi kết luận kiểu "A44 tốt hơn" (PnL/DD thuộc Tầng B) **không** được dùng để chọn feature set.

---

## 11. SẢN PHẨM

`research/analysis/model_ruler.py` · `docs/result/RESULT_MODEL_RULER.md` · commit (**KHÔNG push**).

---

# 12. AMEND — điều chỉnh **TRƯỚC khi đọc số** các chỉ số MỚI (CHỐT CỦA OWNER, 2026-09-25 08:59)

> Chủ dự án chốt lại **bộ chỉ số chính + luật GO** cho CÙNG vòng này. Mục §0–§11 ở trên **GIỮ NGUYÊN**
> (không xoá, không sửa) — đây là bản **amend**, đọc kèm.

## 12.0 KHAI BÁO TRUNG THỰC (không che)

- Bộ chỉ số/luật dưới đây do **owner chốt lúc 08:59 2026-09-25**, trước khi **bất kỳ số nào của bộ mới**
  được tính. Commit amend này là commit **đầu tiên** chứa định nghĩa bộ mới.
- **Nói rõ để không tự lừa:** vòng v1 (§0–§11) **đã chạy và đã đọc số** (commit `999e6c6`) theo bộ chỉ số
  CŨ. Vì vậy amend này **không** phải "chưa từng thấy số". Phân loại rõ:
  - **Đã thấy (dưới spec cũ, báo nguyên trạng, KHÔNG tính lại để chọn):** `AUC` whole-tick (0,6685),
    `lift@8`, `decile ρ` **trên `retEnd` liên tục**, `gross@8`/`net@8`, `rank-IC`, `pacc`.
  - **CHƯA từng thấy (bộ mới ⇒ chạy mù):** **`AUC@top8` (M1)**, **`lift@12`/`lift@16` (M2)**,
    **`decile ρ` + đường decile GỘP trên NHÃN TRAIN (M3)**, **Δ theo luật GO 3 chỉ số**, và **toàn bộ h=72h**.
- Không đổi ngưỡng/luật sau khi xem số. Nếu chạy xong thấy luật có lỗ hổng ⇒ ghi RÕ như đã làm ở §5.2 v1,
  **không** sửa lén.

## 12.1 BỘ CHỈ SỐ CHÍNH (bỏ `rank-IC` khỏi CHÍNH; vẫn báo như thông tin PHỤ)

| # | chỉ số | định nghĩa chốt trước |
|---|---|---|
| **M1** | **AUC@top8** | AUC **pairwise TRONG TICK**, **chỉ xét cặp có ≥1 coin nằm trong top-8** (theo điểm). Công thức chính xác: `T` = 8 coin điểm cao nhất (đúng quy ước `sort p desc, head(8)` của kernel); `P`=nhãn 1, `N`=nhãn 0; `AUC8 = (A+B)/(\|P∩T\|·\|N\| + \|P\\T\|·\|N∩T\|)`; `A = Σ_{p∈P∩T}[#N(s<s_p)+0,5·#N(s=s_p)]`; `B = Σ_{n∈N∩T}[#P(s>s_n)+0,5·#P(s=s_n)]`. Tick thiếu `P` hoặc `N` ⇒ bỏ. Đọc: **>0,5 = tốt**; chỉ dùng dạng **Δ** (không đặt ngưỡng tuyệt đối). |
| **M2** | **lift@K, K ∈ {8,12,16}** | `lift_K(tick) = mean(y_lab)(top-K) − mean(y_lab)(tick)`. **M2 PASS ⟺ với MỖI K** `Δlift_K > 0` **ngoài CI so với CẢ HAI** đối chứng. **1 mức K fail ⇒ M2 FAIL** (kiểm tín hiệu không chỉ nhọn ở đúng 8). |
| **M3** | **decile monotonicity** | `D1` = decile điểm **THẤP nhất** … `D10` = **CAO nhất** (decile theo hạng score trong tick, `floor(10r/(n+1))`). **Hai phần BẮT BUỘC:** (a) TUYỆT ĐỐI — trên **nhãn train**, đường decile **GỘP** (row-weighted toàn bộ tick) có `Spearman(D, mean_y) > 0,8` **VÀ** dốc `mean_y[D10] − mean_y[D1]` **cùng dấu KỲ VỌNG = DƯƠNG**; (b) SO SÁNH — `Δ` của `mean per-tick ρ(D, mean_y_lab)` `> 0` **ngoài CI vs CẢ HAI**. **M3 PASS ⟺ (a) ∧ (b)**. |
| phụ | `rank-IC`, `\|rank-IC\|`, `precision@K`, `AUC` whole-tick, `pacc`, `gross@8`, `net@8`, `net_lift@8`, `drift` | **BÁO CÁO như thông tin phụ — KHÔNG dùng cho luật GO** |

## 12.2 NHÃN + HORIZON

- **Cổng xếp hạng**: dùng **nhãn train** `y_h = (retEnd_h > 0,015)`. **h ∈ {4h, 72h}**; **BỎ h = 1h**.
- **Kinh tế (BẮT BUỘC báo kèm, không dùng cho GO)**: `gross_h = retEnd_h`; `net_h = retEnd_h − 0,008`
  (`fee 0,002` + `slip 0,003×2`; theo code `Configs.java`), **cùng horizon**.
- 72h: join `retEnd_72h` notna (cùng quy ước `notna` như 4h), tick ≥ 2 coin.

## 12.3 LUẬT GO (chốt trước)

`GO(ứng viên)` ⟺ **(i) h=4h**: **≥ 2/3** chỉ số chính `{M1,M2,M3}` có `Δ > 0` **NGOÀI CI so với CẢ
retrain-control VÀ noise-control**; **VÀ (ii) h=72h**: **KHÔNG** chỉ số chính nào có `Δ < 0` ngoài CI
(không đòi tốt hơn — chỉ không được xấu đi).
Không thoả ⇒ **NOT GO (giữ nguyên model)**.
**Khai báo trước:** chỉ số **KHÔNG TÍNH ĐƯỢC** ⇒ **KHÔNG** được tính là PASS (thiếu bằng chứng không cộng
vào 2/3). Áp dụng nguyên văn.

## 12.4 CI (không hardcode hệ số)

- block **theo tick**, khối **72h**, **2000 rep**, seed **20260905** (không đổi).
- Hệ số = `c3_rates.inflate(k)` = `sqrt(2 ln k)`, `inflate(1)=1,0` (`docs/audit/AUDIT_CI_INFLATE_STANDARDIZATION.md`).
  **k = số ỨNG VIÊN của round = 2** (`A44`, `V0`) ⇒ **`inflate(2) = 1,177410`**; truyền qua `--k`, **không hardcode**.
  Hằng số `1,21` (≈ k=2,079) **đã bị gỡ** ⇒ chỉ in như **tham chiếu**, không dùng để quyết định.
- "Ngoài CI" = ngoài **CẢ** `raw` **VÀ** `inflate(k)`.

## 12.5 TẦNG A KHÔNG NHÌN PnL/EQUITY

(budget · DCA · trailing · impact của luồng tín hiệu khác) ⇒ **NGOÀI PHẠM VI Tầng A** (giữ nguyên v1 §0.1).

## 12.6 GIỮ NGUYÊN

2 đối chứng **BẮT BUỘC** (retrain `A45` · noise `V5` cùng NaN-mask) · cross-section **TRONG TICK** ·
**scale-invariant** (T2) · bước **validate: thước có tự nói lại `GIỮ 45` trên 5 arm đã có**
(`45deploy`, `A45`, `A44`, `V0`, `V5`).

## 12.7 KHOẢNG TRỐNG DỮ LIỆU — KHAI BÁO TRƯỚC (không phải "phát hiện" sau)

- **G-1:** 4 arm retrain chỉ có per-tick parquet 4h với cột `{ic, base, t8, n8, n_coin, lift8, fold}`
  ⇒ **KHÔNG có điểm/nhãn thô** ⇒ **M1 và M3 KHÔNG tính được** cho `A45/A44/V0/V5`; và **`lift@12/16`
  cũng không có** ⇒ **M2 chỉ đo được ở K=8**.
- **G-2:** **không có artifact 72h cho arm nào ngoài `45deploy`** ⇒ điều kiện **(ii)** của luật GO
  **KHÔNG đánh giá được** cho `A44`/`V0`.
- **Hệ quả khai báo trước:** nếu `K=8` của M2 fail thì **M2 fail bất kể K=12/16**; và **GO không thể được
  cấp** khi thiếu bằng chứng cho M1/M3. ⇒ Dự kiến round này = **NOT GO** cho **cả 2** ứng viên, với lý do
  **vừa là số đo, vừa là thiếu hạ tầng**. **Việc mở khoá:** kernel xuất thêm parquet per-`(tick,coin)`
  `(ts, sym, p, retEnd_4h, retEnd_72h)`.

## 12.8 DỰ ĐOÁN KHOÁ TRƯỚC (bộ mới)

| # | dự đoán |
|---|---|
| **Q8** | `AUC@top8(45deploy)` nằm trong **0,55–0,80**; **KHÔNG** hứa cao hơn `AUC` whole-tick (mẫu số của M1 đặt trọng số lớn vào các cặp `P\\T` vs `N∩T` = đúng vùng model sai) |
| **Q9** | `lift@8 ≥ lift@12 ≥ lift@16` cho `45deploy` (lift giảm khi K tăng) |
| **Q10** | `45deploy` **PASS (a)** của M3 trên **nhãn train** (`ρ_gộp > 0,8`, dốc `> 0`) **NHƯNG** nếu đo trên `retEnd` liên tục thì ρ **âm** ⇒ tách bạch "nhãn nhị phân xếp được" vs "độ lớn kết quả không xếp được" |
| **Q11** | `A44` và `V0` **fail `K=8` của M2** (`Δlift8 < 0` ngoài CI vs **cả hai**) — tái lập v1 |
| **Q12** | **NOT GO** cho cả `A44` và `V0` |
| **Q13** | Ở `45deploy`: `lift@8(72h) > 0` nhưng **nhỏ hơn** `lift@8(4h)` (base rate 72h cao hơn ⇒ lift nhỏ hơn) |
