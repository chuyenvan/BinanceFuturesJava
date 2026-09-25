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
