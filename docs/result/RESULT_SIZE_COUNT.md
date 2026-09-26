# RESULT_SIZE_COUNT — Trục "GIẢM MARGIN / TĂNG SỐ LỆNH" dưới trần gross 70 % CỨNG

**Ngày:** 2026-09-27 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG · **KHÔNG push**
**Pre-reg:** `docs/prereg/PREREG_SIZE_COUNT_HARNESS.md` (commit `98b5c97`) — chốt **TRƯỚC** khi đọc số.
**Harness (tái sử dụng):** `research/analysis/size_count_run.py` (`b1b77d6`) · `research/analysis/size_count_score.py` (`b1b77d6`).
**Số thô:** `docs/result/size_count_score.json`. **KHÔNG** sửa code Java (knob `SIM_F_BASE` + `SELECTOR_RANK_TOPK` đã có sẵn).
**Chi phí:** 5 chặn Kaggle CPU, **0** (không chạy sim trên Oracle). DEV only ≤ 2025-12-31 (holdout 2026 nguyên vẹn).

---

## 0. PARITY / CỔNG KNOB (bắt buộc trước khi tin số)

- **Không sửa code Java** ⇒ không cần parity lại 2 md5 cũ. Thay vào đó: **cổng knob** `sc-par`
  (= `KEEPLEG0` + `SIM_ENTRY_SAMPLE_MIN=15` + `SIM_F_BASE=0,03` **khai tường minh** + `SELECTOR_RANK_TOPK=8` **khai tường minh**)
  ⇒ md5 `printDone.csv` = **`1317191624d316d955223311ae693228`** = **đúng bằng** `cd-sel15` (n=744, eq=71.718)
  ⇒ **2 knob ở giá trị default VÔ HẠI** ⇒ "TẮT = y nguyên" ĐẠT.

## 1. BẢNG ARM (chốt trước; base = `cd-sel15`)

| arm | size | K | n | entry/tháng | gross TB% | gross MAX% | conc%/coin | coin đồng thời (max/TB) | CAGR% | maxDD% | UW | qmin% | %top-1 | TF50 (USDT) | q*% | mean\|lỗ\|/mean lãi | sign% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **B0** `cd-sel15` | ×1 | 8 | **744** | 13,77 | 1,7 | 49,5 | **6,77** | 24 / 0,5 | **+17,29** | −6,27 | 166 | −3,36 | **19,13** | **−17.551** | 21,2 | **3,38** | 88,44 |
| **B1** `sc-b1` | ×0,5 | 8 | 745 | 13,79 | 1,0 | 34,4 | 4,10 | 23 / 0,5 | +11,22 | **−3,90** | 164 | −1,56 | 18,69 | −7.657 | 25,1 | 3,02 | 88,19 |
| **B2** `sc-b2` | ×0,5 | 16 | 1152 | 21,33 | 1,4 | 44,2 | **3,74** | 34 / 0,9 | +15,06 | −5,48 | 164 | −1,36 | 15,83 | −10.396 | 25,5 | 3,09 | 88,80 |
| **B3** `sc-b3` | ×0,25 | 32 | 1885 | 34,90 | 1,3 | 39,6 | **2,12** | 57 / 1,6 | +12,65 | −5,00 | **278** | −0,78 | 15,23 | −8.098 | 26,0 | 2,78 | 87,85 |
| **B4** `sc-b4` | ×0,5 | 32 | 1878 | 34,77 | 2,0 | 53,5 | 3,49 | 57 / 1,6 | **+18,43** | **−7,04** | **277** | −2,27 | 16,80 | −16.679 | 22,2 | 2,93 | 87,86 |

(B1: n gần như **không đổi** 745 vs 744 — giảm margin nhưng giữ `K=8` ⇒ **không thêm lệnh**, chỉ nửa size ⇒ gross ≈ nửa.
B3/B4: `UW` **tổng chuỗi 278/277 > 250**, nhưng theo **từng năm ≤ 164** — drawdown dài **vắt qua mốc năm**.)

## 2. RÀO + 2 SỰ THẬT TOÁN HỌC

| arm | (a) `%top-1 ≤15` | (b′) `bỏ-50% > 0` | rào CŨ (appetite latest) | gross≤70 TB / MAX |
|---|---|---|---|---|
| B0 `cd-sel15` | **FAIL** 19,13 | **FAIL** −17.551 | PASS (DD −6,27 · UW 166 · qmin −3,36 · conc 6,77 · 0 năm âm) | PASS / PASS |
| B1 `sc-b1` | **FAIL** 18,69 | **FAIL** −7.657 | **PASS** (DD −3,90 · UW 164 · qmin −1,56 · conc 4,10) | PASS / PASS |
| B2 `sc-b2` | **FAIL** 15,83 | **FAIL** −10.396 | **PASS** (DD −5,48 · UW 164 · qmin −1,36 · conc 3,74) | PASS / PASS |
| B3 `sc-b3` | **FAIL** 15,23 | **FAIL** −8.098 | **FAIL** (UW tổng **278** > 250) | PASS / PASS |
| B4 `sc-b4` | **FAIL** 16,80 | **FAIL** −16.679 | **FAIL** (UW tổng **277** > 250) | PASS / PASS |

- **Fact #1 (scale đều KHÔNG đổi dấu (b′)) — XÁC NHẬN.** Cùng `K=8`: `TF50` −17.551 (×1) → −7.657 (×0,5) ⇒ **cùng dấu ÂM**, độ lớn ≈ ×0,44.
  Cùng `K=32`: −16.679 (×0,5) → −8.098 (×0,25) ⇒ tỷ số 0,486 ⇒ **giảm margin KHÔNG THỂ cứu (b′)**.
- **Fact #2 (tăng `n` làm `TF50` ÂM THÊM) — XÁC NHẬN** khi **cùng size ×0,5**: `n` 745 → 1152 → 1878 ⇒ `TF50` −7.657 → −10.396 → **−16.679** (**đơn điệu âm thêm**).
  Lưu ý trung thực: `mean(nửa dưới)` **tự nó bớt âm** khi thêm `n` (−20,5 → −18,1 → −17,8) nhưng **không đủ lật dấu** ⇒ `TF50=(n/2)·mean` vẫn âm thêm.

## 3. TRẢ LỜI 6 CÂU (bắt buộc)

**(1) `gross` thực tế từng arm — có giữ ≤70 % (cả 2 cách)? → CÓ, ở MỌI arm; trần 70 % KHÔNG bind.**
`gross TB` 1,0–2,0 %; `gross MAX` 34,4–53,5 % — đều < 70 % **và** < `U_MAX=0,60` (`Configs.java:156`). Sim đã tự chặn
`margin/equity ≥ U_MAX` (`TradeManager` throttle + trả `null`) ⇒ **trần 70 % không bao giờ là ràng buộc thực tế**;
hệ số bù `70/gross_MAX` = **1,000** ở cả 5 arm (không phải giảm size thêm). *(gross đo hậu kiểm từ `margin`+`start`/`end`+equity ngày — KHAI RÕ; equity nội ngày chưa mô hình hoá.)*

**(2) `conc 1 coin` + số coin đồng thời → giảm size/tăng K làm giảm tập trung & tăng phân tán.**
`conc/coin` 6,77 % (B0) → 4,10 (B1) → **3,74** (B2) → **2,12** (B3) → 3,49 (B4) — **tất cả ≤15 % CỨNG PASS**.
Số coin đồng thời (max): 24 → 34 → **57**; TB: 0,5 → 0,9 → 1,6. ⇒ đúng kênh kỳ vọng (nhiều vị thế nhỏ hơn, phân tán hơn).

**(3) `maxDD` · `UW` · quý xấu nhất cải thiện bao nhiêu?**
- `maxDD` (năm): −6,27 → **−3,90** (B1, **giảm 2,37 pp = −38 %**), −5,48 (B2), −5,00 (B3); **B4 xấu hơn** −7,04.
- `UW` (tổng chuỗi): 166 → 164 (B1/B2, **giảm 2 ngày**); **B3/B4 XẤU HƠN: 278/277 (+112/+111 > trần 250)**.
- `qmin` (quý): −3,36 → −1,56 (B1) · −1,36 (B2) · **−0,78** (B3) · −2,27 (B4) — **tốt hơn ở mọi arm**.
⇒ **giảm size nhẹ + tăng K vừa (B2) cải thiện CẢ ĐỘ SÂU và ĐỘ DÀI drawdown**; đẩy `K=32` (B3/B4) làm drawdown **NÔNG hơn nhưng KÉO DÀI hơn** (đúng như `RESULT_2X_HALFSIZE`).

**(4) Rào (a)/(b′) PASS/FAIL + `TF50` âm/dương ⇒ có xác nhận 2 sự thật?**
**(a) FAIL 5/5** (18,69 · 15,83 · 15,23 · 16,80 vs trần 15 — **B2/B3 rất sát, chỉ vượt 0,23–0,83 pp**).
**(b′) FAIL 5/5**, `TF50` **ÂM ở mọi arm** (−7.657 … −16.679). **Xác nhận CẢ 2 sự thật** (mục 2).

**(5) `TF50/(n/2)` = mean nửa dưới ⇒ tăng `n` làm nó âm thêm?**
`mean nửa dưới` = −47,18 (B0) · −20,53 (B1) · −18,05 (B2) · −8,59 (B3) · −17,76 (B4) — **ÂM ở 5/5**.
Đúng dự đoán ở nhánh **cùng size ×0,5** (B1→B2→B4: `TF50` −7.657→−10.396→−16.679 âm thêm). `mean` **tự nó bớt âm** khi `K` tăng (leg thêm chất lượng không tệ) nhưng **không lật được dấu** ⇒ bất đối xứng lỗ/lãi vẫn còn (`asym` 2,78–3,38 vs nền 3,38).

**(6) 5 rate + CI vs B0 + kết luận.**
`win%` và `TSloss%` (2 rate **không phụ thuộc size**) **TRONG CI ở 5/5 arm** ⇒ **không có thay đổi chất lượng thật**.
`mP|SM` (−41…−68) · `mP|SL` (+163…+259) · `meanP` · `mMargin` **ngoài CI** ở 5/5 — nhưng **là hiệu ứng NHÂN SIZE** (đơn vị USDT, nhân theo size), **không phải chất lượng**.
Theo **luật siết §10.2** (bỏ `meanP`/`mMargin`; tối đa 1 rate nhóm tần suất): chỉ còn **1 rate** (`mP|SL`, lại là artifact size) ⇒ **KHÔNG đạt "≥2 rate ngoài CI cùng hướng TỐT"**.
**⇒ Trục này KHÔNG cho bằng chứng-chất-lượng ngoài CI nào để giữ arm.**

## 4. KẾT LUẬN + "để đạt (b′) phải đổi CÁI GÌ"

- **Trục giữ được gì?** **Đúng như kỳ vọng ghi trước**: cải thiện **rủi ro cấp danh mục** — `maxDD` (B1 −38 %; B2/B3 nông hơn), `qmin` (tốt hơn mọi arm), **`conc/coin` giảm mạnh** (6,77 → 2,12–3,74 %), và **số coin đồng thời tăng** (24 → 57). `gross` **luôn ≤70 %** (không cần cưỡng chế). **B2 là ứng viên tốt nhất** (n +55 %, risk tốt hơn B0 toàn diện, CAGR chỉ −2,2 pp, (a) 15,83 sát trần) — nhưng **không đạt luật bằng chứng** (0–1 rate, lại là artifact size) và **vẫn FAIL (a)/(b′)**.
- **Trục KHÔNG cứu được (a)/(b′)**: 5/5 FAIL cả hai. `TF50` âm ở 5/5; `asym ≈ 3×` vẫn nguyên ⇒ **bất đối xứng lỗ/lãi là vấn đề CẤU TRÚC**, không phải quy mô.
- **Để đạt (b′) phải đổi CÁI GÌ (theo số, ngắn):** phải **đổi CẤU TRÚC LÃI**, không phải size/`K` — cụ thể kéo **`asym = mean|lỗ|/mean lãi` từ ~3,0–3,4 về < 1** (⟺ làm `mean(nửa dưới) ≥ 0` / lệnh trung vị có lãi), tức **cắt lỗ ngắn hơn & để lãi chạy / nâng chất lượng nhóm thắng** — đúng trục duy nhất có tín hiệu ở `RESULT_TAIL_ROBUST_RULERS` (`loss_mean`/`wl_ratio`). Đổi size hay `K` chỉ **scale** kết quả, không đổi dấu.
- **Khuyến nghị giữ:** KHÔNG giữ arm nào theo luật (B3/B4 vi phạm `UW` trần 250 tổng chuỗi; B1/B2 thiếu bằng chứng rate). **B2** đáng **ghi nhận như "giảm rủi ro danh mục, giá −2,2 pp CAGR"** nếu owner muốn ưu tiên "nhiều lệnh nhỏ để ổn định" (`RISK_APPETITE` §7) — nhưng **chưa go-live được** (vẫn FAIL (a)/(b′)).

## 5. HẠN CHẾ / GHI ĐỂ TÁI LẬP

- Không sửa Java; knob `SIM_F_BASE` áp **TRƯỚC throttle** ⇒ "giảm margin" **tương tác throttle** (không phải scale tuyệt đối thuần) — chính là kênh cho phép thêm vị thế đồng thời. B1 cho thấy khi giữ `K`, số lệnh **không tăng**.
- `gross` **hậu kiểm** (Kaggle sim không enforce trần gross/tick); đo từ ledger + equity **ngày** (chưa mô hình hoá nội ngày, DCA nhiều chân, funding). `UW`/`maxDD` theo **năm** (`gd92xexit_score.yearly_detail`).
- Rate CI: `mP|SM`/`mP|SL`/`mMargin` **nhân theo size** ⇒ chênh vs B0 phần lớn là **artifact**; chỉ `win%`/`TSloss%` là so sánh sạch (đều trong CI).
- Tái lập: `python3 research/analysis/size_count_run.py arms` rồi `python3 research/analysis/size_count_score.py sc-b1 sc-b2 sc-b3 sc-b4 --base cd-sel15 --k 4`.
