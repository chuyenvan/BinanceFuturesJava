# PREREG_FLOWOPT4 — Path `BIG_DOWN` / `DCA_LEVEL1` có **MỞ ĐƯỢC TUẦN GATE ĐÓNG** không?

**Ngày:** 2026-09-30 · **Nhánh:** `module` · **Loại:** 0-sim / 0 train (**CHỈ ĐỌC artifact có sẵn**).
**Kế thừa:** `docs/plan/REVIEW_FLOW_OPT.md` `f3573a2e` (mục ④ = H4, và §1 bảng luồng) —
`RESULT_K_DENSITY` (burstiness là thuộc tính GATE) — `RESULT_GDV2_P3` (baseline `G2+FLAT3`) —
`RESULT_OFI_V3_EVENT2` (cùng phương pháp, NO-GO) — `RESULT_SEL_BIGDOWN` / `RESULT_BD_THRESHOLD_FRAGILITY` (ngưỡng brittle).
**Ràng buộc cứng (đề bài):** chỉ đọc + 0-sim · KHÔNG sửa `.java` · KHÔNG chạm `242`/ONNX/LIVE · **KHÔNG push file dữ liệu** ·
DEV ≤ 2025-12-31 (không chạm 2026) · `df -h /` ~95 % ⇒ output nhỏ · **KHÔNG dùng CPU lớn** (có tiến trình khác đang chạy).

> ⚠️ **Trung thực về thời điểm:** bản pre-reg này được **commit TRƯỚC** khi chạy script quyết định
> (`research/analysis/flowopt4_bd_week.py`). Tác giả có liếc **đếm thô ban đầu** (số tuần / số leg) trước khi viết;
> **các LUẬT A1/B1/B2 dưới đây KHÔNG được chọn bởi tác giả** — chúng **kế thừa nguyên văn cổng DỪNG đã chốt trong
> `REVIEW_FLOW_OPT.md` §3-H4** ("<100 event hoặc net ≤ 0 ⇒ bỏ"). Không có ngưỡng nào được chỉnh sau khi thấy số.

---

## 1. CÂU HỎI

`BIG_DOWN` **bypass gate** (`SimulatorMarketLevelTicker1MStopLoss.java:1326`, điều kiện `!levelChange.equals(BIG_DOWN)`)
nên **về mặt code** nó *có thể* nổ ở tuần gate đóng. Vậy:

> **(1)** Path `BIG_DOWN`/`DCA_LEVEL1` có **thực sự fire trong TUẦN GATE ĐÓNG** của `G2` không — bao nhiêu tuần, bao nhiêu leg?
> **(2)** Các leg đó có **NET > 0 NGOÀI CI** (block-72h) không?
> **(3)** Nếu tính là "sự kiện thêm" thì `n` tăng bao nhiêu %, và chất lượng/risk (T3/T1) có bị đẩy vượt trần không?

---

## 2. ĐỐI TƯỢNG + NGUỒN (chốt cứng, ghi hash)

| tên | nguồn | dùng để |
|---|---|---|
| **`G2` (chính)** | `/home/ubuntu/kaggle_sim/out/de-p1` — `storage/printDone.csv` **n 2517**, eq **131 908**, `20210701..20251230`, `profile_hash c47b73f3133521a1`, `jar_sha256 7368be46…` (= `@base` của `RESULT_GDV2_P3`) | định nghĩa **tuần** + đo path |
| **`G2S`** (robustness, `@stress`) | `/home/ubuntu/kaggle_sim/out/gdv2-g2-stress/storage/printDone.csv` (**n 2509**) | kiểm bền vững định nghĩa tuần + kết luận |
| **`G2B`** (robustness, `@base` bản featv1) | `/home/ubuntu/kaggle_sim/out/featv1-b0/storage/printDone.csv` (**n 2517**) | kiểm bền vững |
| **tag path** | cột `level` ∈ {`PREDICT_SYMBOL_TRADE`, `BIG_DOWN`, `DCA_LEVEL1`} (`TraceOrderDone.printOrderTestDone`, `order.marketLevelChange`) | tách nguồn sự kiện |
| **thời gian** | cột `start` (`YYYYMMDD HH:MM` = `timeStart` = **leg-cuối của cụm**) | bin tuần + block-72h |

**Định nghĩa "NET" của 1 leg (chốt trước):**
`net_leg = pnl / margin`, trong đó
- `pnl` = `order.calTp()` = giá − `RATE_FEE` (1 chân) − `SLIPPAGE_RATE×2` − `calFundingFee()` ⇒ **đã net đủ phí + trượt + funding**;
- `margin` = `quantity × priceEntry / leverage` = notional/đòn bẩy.
⇒ `net_leg` là **lợi suất trên margin của leg**, so được giữa các leg khác size (DCA ×6, BD size-adapt).
**KHÔNG** trừ thêm phí (đã nằm trong `calTp`) — khác `OFI_V3_EVENT2` (ở đó `gross` thô nên phải trừ `f=0,006`).

---

## 3. ĐỊNH NGHĨA (chốt trước, không đổi)

- **Tuần**: bin 7 ngày kể từ `W0 = 2021-07-01` (giống `PREREG_OFI_V3_EVENT2` §2).
- **`PATH`** = leg có `level` ∈ {`BIG_DOWN`, `DCA_LEVEL1`} (2 nguồn **bypass gate**).
- **TUẦN GATE ĐÓNG — `D1` (định nghĩa CHÍNH)**: tuần có **0 leg `PREDICT_SYMBOL_TRADE`**
  (⇒ cổng đã chặn toàn bộ selector; mọi leg còn lại trong tuần đó buộc phải đến từ nhánh bypass).
- **TUẦN GATE ĐÓNG — `D2` (đối chiếu, giống `OFI_V3_EVENT2`)**: tuần có **0 leg G2** (bất kỳ level).
- **`m`** = số leg `PATH` rơi vào các tuần `D1`.
- **CI**: block **72 h** bootstrap (resample **block**, không phải leg), NREP **2000**, seed **20260919**,
  nhân `inflate(k=2) = √(2·ln 2) = 1,177410` (kế thừa `c3_rates`/`stage2_score`, **không viết lại**).
- **Placebo `perm`** (đối chứng ngẫu nhiên): bốc **`m` leg ngẫu nhiên không hoàn lại từ toàn bộ n leg của G2**,
  2000 lần, seed **20260930** ⇒ phân phối null của `net_leg` trung bình + p 2 phía. (Đây là **null đúng**: nhãn level
  là hoán vị được trong cùng quần thể leg — tựa `random` của `OFI_V3_EVENT2`.)
- **Đối chiếu nội bộ `B3`**: `PATH` trong tuần `D1` **vs** `PATH` trong tuần gate **MỞ** (giống `OFI` B3: "tuần đóng có bị bào mòn không").

---

## 4. LUẬT KẾT LUẬN (kế thừa `REVIEW_FLOW_OPT` §3-H4 — KHÔNG tune)

| mã | tiêu chí | ngưỡng |
|---|---|---|
| **A1** (đủ sự kiện) | `m` = số leg `PATH` trong tuần `D1` | **≥ 100** |
| **A2** (phủ) | số tuần `D1` có ≥ 1 leg `PATH` / tổng tuần `D1` | báo cáo số (mô tả) |
| **B1** (chất lượng) | `net_ev` = `mean(net_leg)` của `PATH` trong tuần `D1` | phải **> 0** |
| **B2** (ngoài CI) | CI95×`k2` của `B1` | **không chứa 0** và **DƯƠNG** |
| **B3** (mô tả) | `net_ev(D1)` − `net_ev(tuần mở)`; placebo `perm` p-value | báo cáo (không tự đủ để GO) |

**VERDICT**: **GO** ⟺ **A1 ∧ B1 ∧ B2**. Ngược lại ⇒ **NO-GO / NULL** (nói thẳng).
**A2/B3 + `Δn %` + phát biểu T3/T1** là số **mô tả**, không tự đủ để GO.

**Phát biểu T3/T1 (chốt trước, để không over-claim):** các leg `PATH` **ĐÃ NẰM TRONG n của `G2`** (n 2517 = baseline
PASS 4 tầng). Vì vậy phép đo này **KHÔNG thể** "thêm" sự kiện so với `G2`; nó chỉ trả lời *"path bypass có chạm được
tuần đóng không, và các leg đó tốt/xấu thế nào"*. `UW`/`dd` **không đo lại được** bằng 0-sim ⇒ chỉ **báo cáo đóng góp PnL**
của tập `PATH` như cận trên thô về tác động tài khoản, **không** tuyên bố về T1/T3.

---

## 5. KHÔNG làm (chốt trước)

KHÔNG sim/Java/`claude-run`/build · KHÔNG sửa `.java` · KHÔNG train/kernel · KHÔNG chạm `242`/ONNX/LIVE/2026/`HoldoutSeal` ·
KHÔNG đổi `K`/phí/window/ngưỡng · KHÔNG push `.parquet`/CSV dữ liệu · KHÔNG đổi luật sau khi thấy số.

## 6. FILE

- Code: `research/analysis/flowopt4_bd_week.py`
- Số thô: `docs/result/flowopt4.json`
- Kết quả: `docs/result/RESULT_FLOWOPT4.md`
