# PREREG_BAR_A_CALIBRATION — HIỆU CHỈNH RÀO (a) `share top-1 % ≤ 15 %`

Ngày: **2026-09-28**. File này **chốt TRƯỚC** mọi số của vòng này (sau đó **không sửa thiết kế**;
mọi lệch phải khai riêng như mọi pre-reg khác).

**Câu hỏi.** Rào (a) `%PnL đến từ top-1 % **lệnh** ≤ 15 %` là **NGƯỠNG LỌC CÓ NGHĨA**, hay là
**ĐIỀU KIỆN KHÔNG THỂ ĐẠT** với mọi chiến lược thật? Nếu bất khả thi ⇒ **đề xuất mức thay thế có cơ sở**.

**Vì sao phải hiệu chỉnh.** Ba vòng trước đều cho cùng tín hiệu:
- `RESULT_RULERS_UNIT` (`afe398b`): ở **đơn vị đúng** (U1 = cấp vị thế) Track B `share top-1 %` = **264,94 %**
  (rào (a) `≤ 15 %` ⇒ vượt **17,7×**); ở cấp NGÀY = 40,49 % ⇒ **FAIL cả 2 đơn vị**.
- `RESULT_TAIL50_RULER_REDUNDANCY` (`76cc051`): **1/8** biến thể arm PASS (a) (`kg0-q998-15m` 12,91 %).
- `RESULT_GROSS_ASYMMAP` (`42a48cd`): quét **461 run** ⇒ PASS (a) = **3/461**.

⇒ Cần biết **phân bố** `share top-1 %` trên **toàn bộ đối tượng đã đo**, xem mức nào **đạt được**,
và liệu có đối tượng nào **vừa PASS (a) vừa PnL dương bền** (CI ngoài 0) + qua **rào (b′)** hay không.

---

## 1. ĐƠN VỊ ĐO — CHỐT: **U1 = CẤP “LỆNH” (1 leg = 1 lệnh/vị thế)**

Theo `PREREG_RULERS_UNIT` §2 (đơn vị gốc của rào là **“LỆNH”**). Vòng này **chỉ dùng đơn vị lệnh**:
- **Book cross-section (Track B):** 1 leg = PnL **ròng** của **một vị thế `(coin i, ngày t)`** (đúng U1
  của `rulers_unit.json`). **KHÔNG** dùng cấp NGÀY (U2). **KHÔNG** dùng U0 (tái lập cũ).
- **Mọi nguồn khác (arm sim / tick-score):** 1 leg = **1 lệnh** hoàn tất (1 dòng ledger `printDone.csv`),
  hoặc **1 tick vào lệnh** với nguồn tick-level (pool P32 / ext). Ghi rõ nguồn nào ở cột `unit`.

## 2. CHỈ SỐ (định nghĩa GIỐNG NHAU cho mọi đối tượng; KHÔNG đổi sau khi thấy số)

`o = sort(legs, giảm dần)`, `Σ = Σ legs` (**phải `> 0`** để (a) có nghĩa; `Σ ≤ 0` ⇒ **(a) = N/A**, ghi rõ, KHÔNG đọc thành PASS).

| chỉ số | công thức |
|---|---|
| `share_top1 %` (rào a) | `Σ o[:⌈1 %·n⌉] / Σ × 100` |
| `share_top5 %` | `Σ o[:⌈5 %·n⌉] / Σ × 100` |
| `share_top25 %` | `Σ o[:⌈25 %·n⌉] / Σ × 100` |
| `drop_q` (rào b′) | `Σ o[⌈q %·n⌉:]` với `q = 25` |
| `winrate` | tỷ lệ leg `> 0` |
| `asym` | `mean(|leg âm|) / mean(leg dương)` |
| `median` | trung vị leg |
| `freq` | số leg / năm (dùng để so độ dày lệnh) |

## 3. CI — CHỐT

Bootstrap **theo khối 72 h**, khối neo **ANCHOR = 2021-07-01** (`blk2 = (ts−ANCHOR)//72h`),
**2000 rep**, **seed 20260905**, nở rộng **`inflate(k)`, `k = 8`** (`sqrt(2 ln 8)`) — **Y HỆT**
`size_count_score.py` / `gd92xexit_score.py`. Báo `CI95` cho `share_top1 %` và cho **Σ drop_q**.
`PnL dương bền` ⇔ **`Σ` (hay `drop_q`) CI95 KHÔNG chứa 0** (theo chiều dương).

## 4. ĐỐI TƯỢNG ĐO (chốt trước — **báo HẾT, không chọn cái đẹp**)

| nhóm | đối tượng | nguồn |
|---|---|---|
| **G-A book (U1, đơn vị đúng)** | `BOOK_EW`, `funding`, `dOI`, `vol`, `reversal` | `docs/result/rulers_unit.json` |
| **G-B tick-score (pool P32/ext)** | `45deploy`, `A44`, `A45`, `MRA4`, `MRB8`, `MRB32`, `S1`, `ofi_candidate`, `ofi_baseline_fresh`, `ofi_noise` | `docs/result/tail_robust_rulers.json` |
| **G-C arm sim (ledger)** | **toàn bộ 461 run** của `gross_asymmap.json` (gồm 8 biến thể `KEEPLEG0`/`T100`/`GD92`/`kg0-q995`/`kg0-q998`/`kg0-q999`/`T170`/`kg0-q998-15m`) | `docs/result/gross_asymmap.json` + `TAIL50_RULER_REDUNDANCY.json` |
| **G-D vòng exit/shape/family2/size_count** | 4 arm mỗi vòng (`A0..A3`, `sh1-*`, `tp-n*`, `sc-b*`) | `RESULT_EXIT_STRUCT.json`, `shape1_early_cut.json`, `family2_tp_sl.json`, `size_count_score.json` |

**Ghi chú nguồn:** G-B (`tail_robust`) là **tick/score-level của pool P32** (`conc_1` × 100 = `share_top1 %`);
G-C/G-D là **ledger cấp lệnh** thật. Cả hai đều là “1 lệnh/cơ hội vào lệnh = 1 leg”.
**Không trộn** G-A (book) với G-C (arm) trong cùng một con số PASS/FAIL — báo **song song**.

## 5. MỨC SO SÁNH + LUẬT KẾT LUẬN (chốt trước)

Mức so sánh: **`T ∈ {15, 25, 50, 100}` %** (15 = mức hiện hành; 25 = mức (b′) hiện hành).

- `PASS_a(T)` = đối tượng **hợp lệ** (`Σ>0`) và `share_top1 % ≤ T`.
- `PASS_b′(25)` = `Σ o[⌈25 %·n⌉:] > 0` (điểm; kèm CI).
- `PASS_both(T)` = `PASS_a(T)` **và** `PASS_b′(25)`.

**Luật:**
1. **R-1 (bất khả thi):** nếu **`PASS_both(15) = 0`** trên **toàn bộ** đối tượng ⇒ **TUYÊN BỐ: rào (a) tại 15 %
   KHÔNG THỂ ĐẠT** (0 đối tượng qua đồng thời (a)@15 và (b′)), kèm bảng chứng.
2. **R-2 (mức đề xuất):** duyệt `T` theo thứ tự tăng dần trong `{25, 50, 100}`; chọn **`T*` = mức NHỎ NHẤT**
   có `PASS_both(T) ≥ 1` **và** vẫn là bộ lọc thật (`PASS_a(T) ≤ 50 %` số đối tượng hợp lệ). Nếu mức nhỏ nhất
   đạt `PASS_both ≥ 1` mà `PASS_a > 50 %` ⇒ hạ xuống báo **kèm cảnh báo mất tính lọc**.
3. **R-3 (đánh đổi (a) ⇄ (b′)):** ở **mỗi** `T` đã báo, đếm `PASS_a(T)` và **trong đó** bao nhiêu `PASS_b′(25)`.
   Nếu nới (a) mà (b′) **tự động PASS gần hết** (`PASS_b′` tăng vọt) ⇒ **2 rào phải đi kèm nhau**;
   nếu (b′) vẫn chặn được phần lớn ⇒ có thể nới (a) **mà giữ (b′)**.
4. **R-4 (kết luận):** giữ 15 % **chỉ khi** `PASS_both(15) ≥ 1`. Ngược lại ⇒ **đổi sang `T*`** theo R-2,
   nêu rõ **mức đề xuất + số đối tượng PASS ở mức đó**.

**Đối tượng share THẤP NHẤT** (theo giá trị `share_top1 %` nhỏ nhất trong số **hợp lệ `Σ>0`**) sẽ được
mổ hồ sơ lệnh: `winrate · asym · freq · median/lệnh` ⇒ **mẫu hình nào mới đạt được**.

---

## 6. RÀNG BUỘC (CÙNG)

1. **Offline Python, 0 train / 0 sim**; **giữ box Oracle NHẸ** (shadow đang chạy). **KHÔNG** chạm
   production/242/ONNX/LIVE. 2. **KHÔNG push file dữ liệu** (chỉ `.md` + `.json` kết quả nhỏ).
3. **DEV ≤ 2025-12-31**; **không** chạm 2026. 4. `df -h /` 93 % ⇒ file NHỎ. 5. Output tool THẬT NHỎ.
6. Commit sớm + **push**.

**Output:** `docs/prereg/PREREG_BAR_A_CALIBRATION.md` (file này) + `docs/result/RESULT_BAR_A_CALIBRATION.md`
+ `docs/result/bar_a_calibration.json` (+ `.py` harness).
