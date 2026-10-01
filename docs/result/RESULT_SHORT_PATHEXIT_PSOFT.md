# RESULT_SHORT_PATHEXIT_PSOFT — SHORT: "APPLY CHUẨN" (P-SOFT, GIỮ DÒNG + TRỌNG SỐ) ĐO BẰNG THOÁT-THEO-ĐƯỜNG-GIÁ 1m

Ngày: **2026-10-01**. Pre-reg: `docs/prereg/PREREG_SHORT_PATHEXIT_PSOFT.md` (**`2f3d3935`**, commit TRƯỚC đo).
Code: kernel-maker **`939af5b5`** (`make_sm_pw_kernels.py`) · sim **`d095f508`** (TÁI DÙNG NGUYÊN
`short_pathexit_sim.py`) · driver mỏng `research/analysis/short_pathexit_sim_pw_drive.py`.
Số: `RESULT_SHORT_PATHEXIT_PSOFT.json`. Nền: `RESULT_SHORT_LABEL2` (**`f6a5cba2`**) · `RESULT_SHORT_PATHEXIT` (**`c4d56074`**).

**Tuân thủ:** 0 Java · không sửa `.java` · không chạm production/242/ONNX/LIVE · không push dữ liệu ·
DEV ≤ 2025-12-31 (không chạm 2026) · train CHỈ trên Kaggle (`sm-pw`) · Kaggle chạy xong (status
`complete`) · chỉ `git add` file của mình.

---

## 0. KẾT LUẬN NGẮN

**`NO-GO`** theo luật §4 pre-reg. **Ô CHƯA AI CHẠY đã được lấp: P-soft + path-exit.** Kết quả:
**net = −0,02 %** (CI95 `[−0,08 % ; +0,03 %]`, **chứa 0**), **2023 vẫn âm (−0,14 %)**, 1/4 năm dương.

⇒ Hai lỗi tách lớp của vòng trước **đã sửa ĐỦ** (không xoá dòng; đo đúng cơ chế), và cả hai đều
**chỉ đưa net về ≈ 0 — bằng đúng nhãn CŨ (`OLD`)**. Chênh giữa 3 nhãn ≤ 0,03 % (dưới nhiễu).
**Vấn đề KHÔNG nằm ở cách apply (nhãn/cơ chế đo) mà ở CHẤT LƯỢNG PICK/REGIME.**

---

## 1. ARM P-SOFT (PW) — ĐÚNG CHỮ OWNER (KHÔNG XOÁ DÒNG)

- Nhãn: `y = 1[retEnd_72h ≤ −1,5 %]` trên **MỌI dòng**; `w = 1` nếu `maxFav_72h ≤ +10 %`,
  `w = max(0, 1 − (maxFav−10 %)/10 %)` nếu `maxFav_72h > +10 %` (trọng số mẫu, KHÔNG loại dòng).
- Trainer `a0438b84` `--label-mode pw --label-h 72 --thr 0.015 --label-e 0.100 --label-kind bin`,
  45 feature selector, 16 fold, NEST=400, K=8/tick, seed {42, 7, 13} — **y hệt** control `PW_t15_E10_S42`
  của `sm-label2b`, chỉ thêm 2 seed.
- Kernel Kaggle **`chuyendinh/sm-pw`** (giữ `predict_wf_*.bin`, không push dữ liệu). Thời lượng ~**1h55**.
- **Kiểm chứng**: mỗi arm **1.111.944 pick** (KHỚP TUYỆT ĐỐI `PA_t15_E10_S42` / `OLD_ndown_S42` — cùng
  K=8/tick, cùng tick, cùng fold); union 615 sym; cross-check giá trên pick đã mô phỏng khớp `.pb`.

---

## 2. ĐO BẰNG **THOÁT-THEO-ĐƯỜNG-GIÁ** (LABEL-EXIT khớp nhãn: TP −1,5 % / SL +10 %, first-hit 1m)

Đơn vị %, net **sau phí base 0,112 %/vòng + funding pro-rata −0,585 %×(h/72)**, mean pick/tick.

| arm (seed 42) | net% | CI95 (block-72h) | ngoài 0? | 2022 | 2023 | 2024 | 2025 | winrate | giữ (h) | max loss | SL-rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **P-soft `PW_t15_E10_S42`** | **−0,02** | [−0,08 ; +0,03] | **KHÔNG** | +0,09 | **−0,14** | −0,02 | −0,01 | 87,6 % | 5,8 | −10,7 % | 11,4 % |
| P-soft (mean 3 seed) | −0,02 | — | KHÔNG | +0,09 | −0,14 | −0,02 | −0,01 | 87,6 % | 5,8 | −10,7 % | 11,4 % |
| *(sanity)* P-hard `PA_t15_E10_S42` (c4d56074) | −0,03 | [−0,08 ; +0,02] | KHÔNG | +0,09 | −0,16 | −0,02 | −0,02 | 87,6 % | 5,4 | −10,7 % | 11,6 % |
| *(sanity)* `OLD_ndown_S42` (c4d56074) | −0,00 | [−0,07 ; +0,06] | KHÔNG | +0,08 | −0,15 | +0,03 | +0,03 | 87,3 % | 8,5 | −10,7 % | 10,5 % |

3 seed P-soft gần như trùng nhau (net `−0,0194 / −0,0184 / −0,0211 %`; CI chồng lấn hoàn toàn).

**Các kiểu thoát khác của P-soft (S42)**: CUT cắt cứng +20 % = **−0,20 %** (CI chứa 0, giữ 61,2 h);
TRAIL 5 % = −0,06 %; NOSTOP = −0,40 %.
**Cắt cứng đo bằng `.pb` cùng pick (có funding)**: CUT@+20 = −0,24 %, CUT@+30 = −0,29 % —
khớp `RESULT_SHORT_LABEL2` sau khi trừ funding (PW `+0,282 %` @+30 trước funding).

---

## 3. BẢNG ĐỐI CHIẾU **2×2** (cùng pick-nền K=8, cùng cơ chế path-exit)

*(a) cột "cắt cứng cũ" = `RESULT_SHORT_LABEL2` net @+30 **trước funding** (đúng số đã công bố);
(b) cột "path-exit" = LABEL-EXIT 1m **đã phí + funding**; (c) thêm cột CUT cùng-lượt-đo (đã funding).*

| arm nhãn | (a) cắt cứng @+30 (cũ, trước funding) | (b) **PATH-EXIT (đúng cơ chế)** | (c) CUT @+20 (cùng lượt, đã funding) |
|---|---|---|---|
| `OLD` ndown | +0,409 | **−0,00** | −0,14 |
| **P-hard** | +0,17 | **−0,03** | −0,32 |
| **P-soft (MỚI)** | +0,28 | **−0,02** | −0,20 |

⇒ **P-soft ≈ OLD ≈ P-hard** khi đo đúng cơ chế (chênh ≤ 0,03 %, CI chồng lấn). "Cú lật dấu"
`+0,28 → −0,02` là do **ĐO ĐÚNG CƠ CHẾ + TRỪ FUNDING**, không phải do nhãn.

---

## 4. SO VỚI VÒNG TRƯỚC — 2 LỖI TÁCH LỚP ĐÃ ĐƯỢC SỬA BAO NHIÊU?

| sửa gì | P-hard → P-soft | kết luận |
|---|---|---|
| **Không xoá dòng** (giữ "âm bản" coin đã pump) | LABEL: −0,026 % → **−0,019 %** (+0,007 %); CUT@+20: −0,32 % → **−0,20 %** (+0,12 %) | Có **giúp THẬT & đúng hướng** owner nghĩ, nhưng **chỉ +0,007…+0,12 %** — không đủ để >0 |
| **Đo đúng cơ chế** (path-exit thay cắt cứng) | +0,28 % (cắt cứng, trước funding) → −0,02 % (đã funding) | "Cú lật dấu" là do **funding 0,585 %** + phí, **không phải** mismatch nhãn |

⇒ **Nhãn path-aware (dù hard hay soft) không tạo edge.** Xoá dòng làm hại **một chút**; giữ dòng +
trọng số đưa về **đúng bằng nhãn CŨ**.

---

## 5. TRẢ LỜI (a)–(d)

1. **(a) P-soft + path-exit có > 0 & ngoài CI không?** **KHÔNG.** net **−0,019 %** (S42) / **−0,020 %**
   (mean 3 seed); CI95 raw `[−0,076 % ; +0,030 %]`, inflated `[−0,087 % ; +0,041 %]` ⇒ **chứa 0 cả hai**.
2. **(b) 2023 còn âm không?** **CÒN — và vẫn âm nhất**: 2023 **−0,14 %**; 2024 −0,02 % (gần hết âm);
   2025 −0,01 %; 2022 +0,09 %. ⇒ **1/4 năm dương** ⇒ điều kiện B FAIL.
3. **(c) So với OLD / P-hard?** **Nằm giữa, chênh ≤ 0,03 %** (OLD −0,00 / P-soft −0,02 / P-hard −0,03);
   CI ba arm chồng lấn hoàn toàn ⇒ **khác biệt dưới nhiễu**. Ở cột CUT cùng-lượt: P-soft (−0,20) tốt hơn
   P-hard (−0,32) và xấu hơn OLD (−0,14).
4. **(d) GO/NO-GO?** **`NO-GO`.** ⇒ **Kết luận cuối: vấn đề là CHẤT LƯỢNG PICK/REGIME, KHÔNG phải cách
   apply.** Cụ thể cơ chế chết: (i) **top-8/tick không có edge ròng** sau phí+funding (TP +1,5 % chạm
   nhanh, winrate 87,6 %, nhưng **11,4 % lệnh ăn SL −10 %** ⇒ `0,876×1,5 % − 0,114×10 % ≈ +0,17 %` gross
   bị phí 0,112 % + funding ăn gần hết); (ii) **funding short là chi phí cấu trúc**; (iii) **2023 regime
   tăng ⇒ short thua**. Không dựng đường SELL.

---

## 6. PHƯƠNG PHÁP / LỆCH KỸ THUẬT (khai báo)

- **Train**: Kaggle `sm-pw` (3 arm, ~1h55). **Đường giá 1m**: Aerospike `test.kline_1m_opt`, stream
  1 lượt, entry = **nến mở 15m + 14 phút**, buffer trượt 72h, không ghi đĩa. DEV ≤ 2025-12-31.
- **Lệch duy nhất so pre-reg (chỉ về BỘ NHỚ, KHÔNG đổi logic/số)**: lượt chạy đầu (gộp 5 arm
  PW+PA+OLD trong 1 tiến trình) bị **OOM-kill** ở năm 2024 (box 23 GB, nền Java trading ~4 GB +
  Aerospike ~2,9 GB). Chuyển sang **driver mỏng** `short_pathexit_sim_pw_drive.py` **import nguyên hàm**
  của `short_pathexit_sim.py`, chỉ (i) nạp `.pb` **72h** thay vì 12/24/72h và (ii) **bỏ `sweep_pb`**;
  mọi công thức (pick top-8, entry, LABEL/CUT/TRAIL/NOSTOP, cost, funding, CI block-72h, theo năm)
  giữ NGUYÊN. Ô `OLD`/`P-hard` của bảng 2×2 lấy từ `RESULT_SHORT_PATHEXIT` (cùng code/entry) **đúng
  như pre-reg §3 đã chốt**.
- **Kiểm chứng chéo**: pick/arm = 1.111.944 (khớp PA/OLD); `pb_cut20_same_mean` +0,0040;
  `pb` CUT@+30 = −0,29 % khớp `LABEL2` sau khi trừ funding (−0,303 %).

---

## 7. VIỆC BỎ + LÝ DO

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Lưới `(h,thr,E)` mở rộng cho P-soft | ⛔ BỎ | `PATHEXIT` đã chứng minh 0/27 GO; vòng này chỉ vá 2 lỗi tách lớp |
| 2 | Gộp 5 arm 1 tiến trình sim | ⛔ BỎ | OOM (đã thay bằng 3 arm + driver mỏng) |
| 3 | Gate-33/S1-9, feature mới, tune sau khi thấy số | ⛔ BỎ | dataset / luật vòng này |
| 4 | Java/sim, ONNX, sửa `.java`, push dữ liệu | ⛔ BỎ | §1 pre-reg |
| 5 | Dựng đường SELL / production | ⛔ BỎ | verdict NO-GO |
