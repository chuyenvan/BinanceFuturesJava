# PREREG_SHORT_PATHEXIT_PSOFT — SHORT: ÁP NHÃN "CHUẨN OWNER" (P-SOFT, TRỌNG SỐ) + ĐO BẰNG THOÁT-THEO-ĐƯỜNG-GIÁ 1m

Chốt: **2026-10-01**, TRƯỚC khi chạy bất kỳ phép đo mới nào của vòng này. File này commit
**TRƯỚC** mọi commit script/kết quả (đúng `docs/runbooks/AGENT_RUNBOOK.md` luật 2; sai thứ tự
commit ⇒ kết quả **VOID**). Sau khi chạy **KHÔNG sửa thiết kế** (arm, cơ chế thoát, chi phí,
chỉ số, luật kết luận).

Trạng thái: **ĐANG CHỜ ĐO** (khi xong ⇒ `docs/result/RESULT_SHORT_PATHEXIT_PSOFT.md`).

---

## 0. Vì sao vòng này (2 lỗi tách lớp của vòng trước)

Owner chỉ ra 2 lỗi tách lớp trong chuỗi `RESULT_SHORT_LABEL2` → `RESULT_SHORT_PATHEXIT`:

1. **Áp nhãn SAI chuẩn.** `PREREG_SHORT_LABEL2 §2` chốt **P-hard** = **XOÁ dòng** `maxFav_72h > E`
   cho **arm CHÍNH**; còn **P-soft** (`w = 1` nếu `maxFav≤E`; `w = max(0, 1−(maxFav−E)/E)` nếu
   `maxFav>E`) chỉ là **đối chứng** (1 seed). Nhưng pre-reg ghi rõ P-soft là **"đúng chữ owner"**.
   ⇒ Arm chính đã **xoá đúng các "âm bản" coin đã pump** — chính là mẫu model cần để **học NÉ**.
   Kết luận "nhãn path-aware làm TỆ HƠN" của `RESULT_SHORT_LABEL2` **có thể chỉ là do XOÁ DÒNG**,
   không phải do ý tưởng path-aware.
2. **Đo SAI cơ chế.** `RESULT_SHORT_LABEL2` chấm net bằng **CẮT CỨNG** (mismatched với nhãn).
   Bản vá `RESULT_SHORT_PATHEXIT` (`c4d56074`) đo bằng **thoát-theo-đường-giá 1m** NHƯNG **chỉ chạy
   cho P-HARD** (+ `OLD_ndown`) ⇒ `LABEL −0,03 %`.

⇒ **Ô CHƯA AI CHẠY: `P-soft + path-exit`.** Đây đúng là "apply chuẩn hơn" cần đo: giữ nhãn theo
**trọng số** (KHÔNG xoá dòng) **VÀ** đo bằng **thoát khớp nhãn trên đường 1m**.

---

## 1. Ràng buộc (CỨNG)

1. **Train CHỈ trên KAGGLE**; phần đường giá = **Python offline** (stream Aerospike `kline_1m_opt`);
   **KHÔNG chạy Java/sim trên Oracle**; Kaggle không chạy ⇒ **DỪNG + báo rõ** (kiểm bằng
   `kaggle kernels status <ref>`, **KHÔNG tin "0/5 slot" CLI 1.6.17**).
2. KHÔNG chạm production/242/ONNX/LIVE; **KHÔNG sửa `.java`**.
3. KHÔNG push file dữ liệu (bins/model/1m); chỉ push `.md`/`.py`/`.json` tổng hợp.
4. **DEV ≤ 2025-12-31**; KHÔNG chạm 2026 (seal).
5. Disk `/` ~82 % ⇒ dọn temp; output tool nhỏ; commit sớm + push.
6. CPU Oracle: **1 tiến trình, `nice`**, đọc tuần tự (không fan-out nhiều core).
7. **CHỈ `git add <file của mình>`** (working tree có file dở của job khác) — KHÔNG `git add .`/`-A`.

---

## 2. (a) ARM — **P-SOFT (PW), GIỮ MỌI DÒNG + TRỌNG SỐ** (khóa)

- **Nhãn (đúng `PREREG_SHORT_LABEL2 §2` + chữ owner):**
  ```
  y = 1[retEnd_72h ≤ −thr]                        trên MỌI dòng (không xoá)
  w = 1                                nếu maxFav_72h ≤ E
  w = max(0, 1 − (maxFav_72h − E)/E)   nếu maxFav_72h > E
  ```
- Trainer **`a0438b84`** `--label-mode pw --label-h 72 --thr 0.015 --label-e 0.100 --label-kind bin`
  (`sample_weight` đã có sẵn). **GIỮ NGUYÊN** feature (45 selector) / fold (16) / hyperparam
  (NEST=400) / K=8 / purge — y hệt `PW_t15_E10_S42` (control cũ của `sm-label2b`).
- **Seeds: {42, 7, 13}** (3 arm). S42 là arm **khớp trực tiếp** bảng 2×2 (cùng seed với
  `PA_t15_E10_S42` / `OLD_ndown_S42` đã có); 3 seed cho **mean-seed**.
- Mỗi arm **LƯU `predict_wf_*.bin`** (slot 3 = head 72h) để tải về đo (không push bins).

---

## 3. (b) ĐO — **THOÁT-THEO-ĐƯỜNG-GIÁ 1m** (khóa — y hệt `RESULT_SHORT_PATHEXIT`)

- Sim **`research/analysis/short_pathexit_sim.py`** (TÁI DÙNG NGUYÊN), đường giá 1m Aerospike
  `test.kline_1m_opt` (key `YYYYMMDD-HHMM` TZ+7, stream 1 lượt, buffer trượt 72h, không ghi đĩa).
- Entry = **nến mở 15m + 14 phút** (= `close(t)` của `.pb`; đã kiểm chứng `mae=0`).
- Pick = top-8/tick theo score (`r > n−8`), đúng `short_model_score.py`.
- **Cơ chế thoát (khớp nhãn):** **LABEL-EXIT** TP tại `−thr=1,5 %`, **stop tại `+E=+10 %`**,
  first-hit trên nến 1m (cùng nến ưu tiên STOP — bảo thủ); chưa chạm ⇒ đóng tại `t+72h`.
- **Đối chiếu trong cùng bộ pick:** **CUT cắt cứng** `C ∈ {+20 %,+30 %,+50 %,+90 %}`, **TRAIL 5 %**,
  **NOSTOP** (mốc "không can thiệp").
- **Chi phí:** base **0,112 %/vòng** (`RESULT_COST_TRUTH`); **funding pro-rata** `−0,585 %×(h/72)`
  (chính), phẳng `−0,585 %` (phụ).
- **Chỉ số:** net% (mean pick/tick), **CI95 block-72h bootstrap** (`NREP=2000`, `SEED=20260905`,
  "ngoài 0" = ngoài **raw VÀ** ×1,21), **winrate**, **giữ (h)**, **max loss**, và **theo năm 2022–2025**.
- **Bảng 2×2** (cùng picks-nền, cùng cơ chế path-exit LABEL): ghép kết quả MỚI (P-soft) với kết quả
  ĐÃ CÓ (`RESULT_SHORT_PATHEXIT c4d56074`) cho OLD/P-hard.

---

## 4. LUẬT KẾT LUẬN (khóa TRƯỚC)

**GO** (đáng build đường SELL) **chỉ khi** arm P-soft, ở cơ chế **LABEL-EXIT** (khớp nhãn):

| # | Điều kiện (khóa) |
|---|---|
| **A** | net **> 0** **ngoài CI** (raw **và** ×1,21), mean-seed, đã credit funding pro-rata |
| **B** | **> 0 ở ≥3/4 năm** (2022–2025) |

**NO-GO/NULL** nếu A hoặc B FAIL (không vùng xám). Bắt buộc báo kèm:
(i) **2023** còn âm không; (ii) so với **OLD** (LABEL ≈ −0,00 %) và **P-hard** (LABEL ≈ −0,03 %);
(iii) nếu vẫn ≤0 ⇒ kết luận cuối: vấn đề ở **CHẤT LƯỢNG PICK/REGIME**, không phải cách apply.
Báo thêm **cut-hard** (CUT @+20/+30) cùng bộ pick để đối chiếu cột "cu" của bảng 2×2.

---

## 5. VIỆC BỎ + LÝ DO (ghi TRƯỚC)

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Lưới `(h,thr,E)` mở rộng cho P-soft | ⛔ BỎ | vòng `PATHEXIT` đã chứng minh 0/27 GO; vòng này CHỈ vá 2 lỗi tách lớp |
| 2 | Gate-33/S1-9, feature mới | ⛔ BỎ | dataset không có sẵn trên Kaggle (§1.3) |
| 3 | Tune threshold/feature/hyperparam sau khi thấy số | ⛔ BỎ | cấm theo luật vòng này |
| 4 | Java/sim, ONNX, sửa `.java`, push dữ liệu | ⛔ BỎ | §1 |
| 5 | Dựng đường SELL / production | ⛔ BỎ | chỉ khi verdict GO (dự kiến NO-GO) |

---

## 6. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_PATHEXIT_PSOFT.md` | file này (commit TRƯỚC đo) |
| `research/kaggle/short_model/make_sm_pw_kernels.py` | sinh kernel Kaggle `sm-pw` (3 arm P-soft, giữ bins) |
| `research/analysis/short_pathexit_sim.py` | TÁI DÙNG NGUYÊN |
| `docs/result/RESULT_SHORT_PATHEXIT_PSOFT.md` (+`.json`) | kết quả + bảng 2×2 + trả lời (a)-(d) |
