# RESULT_OFI_MONEY_REORIENT — OFI chạy lại với **ĐÚNG CHIỀU ĐIỂM** (`ORIENT = −1`)

**Ngày:** 2026-09-28 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG
**Pre-reg:** `docs/prereg/PREREG_OFI_MONEY_REORIENT.md` (commit `1a5cc92`) — chốt **TRƯỚC** khi tính số.
**Code:** `research/analysis/ofi_money_score_v2.py` (đường RE `P32`) · `ofi_money_ext_v2.py` (đường B2) ·
`ofi_ext_trades_build.py` (dựng file ứng viên B2) · `ofi_reorient_rulers.py` (mô tả) ·
`research/kaggle/ofi_money/make_ofi_ext_kernel_v2.py` (sinh kernel Kaggle).
**Số thô:** `docs/result/ofi_money_reorient.json` (487 KB) · `docs/result/ofi_money_ext_reorient.json` (480 KB) ·
`docs/result/ofi_reorient_rulers.json` (3 bảng mô tả) · `docs/result/ofi_reorient_summary.json` (tóm tắt).
**Kế thừa:** `PREREG_OFI_MONEY` (`4948795`) · `RESULT_OFI_MONEY` (`96a08e5`, **sai chiều**) · `RESULT_TAIL_ROBUST_RULERS` (lỗi chiều điểm)
· errata `RESULT_GROSS_ASYMMAP` (27/09). **KHÔNG** chạy Java/sim trên Oracle; **KHÔNG** chạm 2026/ONNX/LIVE/`NUM_FEATURES`.

---

## 0. TRẢ LỜI (4 câu bắt buộc)

### (1) Sau khi sửa chiều, `candidate` có `Δnet` **ngoài CI** vs **cả 2** đối chứng ở `f = 0,006`, dưới trần 70 %, **cả 2 đường**? → **KHÔNG — ở CẢ HAI đường**

| đường | `Δnet_gr1dv(cand−base)` [`k=5`] | `Δnet_gr1dv(cand−noise)` [`k=5`] | ngoài CI? |
|---|---|---|---|
| **RE (`P32`)** | **−3,20e−09** [−2,944e−05, +2,739e−05] | **+1,071e−05** [−1,753e−05, +3,778e−05] | **KHÔNG** (cả 2) |
| **B2 (pool đúng chiều)** | **−1,06e−06** [−2,710e−05, +2,390e−05] | **+1,010e−05** [−1,530e−05, +3,300e−05] | **KHÔNG** (cả 2) |

Không ô nào ngoài CI ở `k = 2 / 5 / 10`; **hai đường cùng kết luận**. Luật §4 (`outside CI DƯƠNG` **và** `≥2/3 seed`)
⇒ `CO_GIA_TRI_TIEN = **FALSE**` ở **cả 2** đường.

### (2) Lỗi chiều cũ làm **sai bao nhiêu** (số cụ thể)

Trên **cùng pool `P32`**, 2 chiều (`+1` = CŨ sai · `−1` = SỬA), ensemble 43/44/45, `K=8`:

| chỉ số | chiều CŨ (`+1`) | chiều SỬA (`−1`) | lệch |
|---|---|---|---|
| **entry** (`e_t` TB, vị thế mở) | 504,7 | 404,3 | **−20,0 %** (đỡ nghẽn) |
| **`net_coin`** (%/vòng, `f=0,006`) | +0,6416 | +0,6480 | +0,0006 |
| **`net_gr1dv`** (×10⁻³, `f=0,006`) | **+0,10171** | **+0,12820** | **+26,0 %** |
| **`TF50`** (tổng 50 % leg thấp nhất) | −2474,00 | −2514,89 | −1,7 % |
| **`asym`** (`mean|lo|/mean thắng`) | −2,509 | **−3,395** | **+35,3 %** (lệch đuôi lớn hơn) |
| **`%top-1`** (`share_top1_pct`) | 41,93 | 30,39 | −11,5 pp |
| **`B1`** (`K=8`, % top-8 **ngoài** `P32`) | **100,0 %** | **0,054 %** | **100 % → ~0** ✅ (khớp dự báo `<10 %`) |

**`mean-rank` top-8 trong `P32`** (Bước 0, KHÔNG làm lại): CŨ **25,1–26,4** → SỬA **3,89–4,32** trên thang 32.
**Diễn giải:** lỗi không làm "âm" mà làm **chọn nhầm đáy**; hậu quả **lớn nhất** là **vô hiệu hoá thiết kế đo**:
chiều CŨ chọn 8 coin **tệ nhất vũ trụ** ⇒ **100 %** nằm **ngoài `P32`**, nên vòng `RESULT_OFI_MONEY` thực chất đo
**rổ coin đáy**, không đo ứng viên; sau khi sửa, `B1` về **0,054 %** và phép đo nằm đúng trong rổ.

### (3) Kết luận dứt khoát — OFI có **giá trị TIỀN** không?

**KHÔNG.** Ở `f = 0,6 %/vòng`, `K = 8`, `Δnet` (chỉ số quyết định `net/1đv-gross`) so **cả** `baseline_fresh`
**và** `noise_ofi_check` **nằm TRONG CI** ở **mọi `K`**, **mọi mức phí**, **cả 3 cách áp trần**, trên **cả 2 pool** —
*đã sửa đúng chiều điểm và dựng lại pool B2 theo đúng chiều*.
**Đây là lần thứ 5 trên TRỤC TIỀN của chuỗi "xếp hạng model"** (kể rõ, theo thứ tự thời gian):
**①** `RESULT_PNL_RULER` (`acb88bd`) — 0 chỉ số kinh tế dương ngoài CI ·
**②** `RESULT_MONEY_RANKER` (`4a94c36`) — mạnh hơn ở tầng thống kê, kinh tế = 0 ·
**③** `RESULT_TAIL_ROBUST_RULERS` (§5, trần 70 %) — mọi Δ giữa các đối tượng **trong CI** ·
**④** `RESULT_OFI_MONEY` (`96a08e5`) — **ứng viên OFI, nhưng SAI CHIỀU** (vòng này sửa) ·
**⑤** `RESULT_OFI_MONEY_REORIENT` (**vòng này**) — ứng viên OFI, **ĐÚNG CHIỀU** ⇒ vẫn **0**.
⇒ Riêng ứng viên OFI: **lần thứ 2** (sau vòng sai chiều `④`); và **lần đầu tiên đo được đúng chiều**.

### (4) Nếu **CÓ** thì mạnh bao nhiêu + cần gì để deploy?

**Không áp dụng** (kết luận là **KHÔNG**). Ghi lại đúng chi phí tích hợp nếu sau này có bằng chứng mới:
thêm **2 feature** ⇒ **47 cột** ⇒ **đụng ONNX/LIVE** ⇒ **cần owner duyệt riêng**; và phải qua
**ONNX/LIVE** chứ không được deploy bằng đường offline.

---

## 1. LỖI ĐƯỢC SỬA (điểm sửa `file:line`)

| # | tệp:dòng | nội dung |
|---|---|---|
| A | `research/pipeline/x1/kaggle_ofi_v3/ofi_train_eval_v3.py:153,177` | **nguồn**: `score = −pred` ⇒ **THẤP = TỐT** |
| B | `research/analysis/ofi_money_score.py:149,165` | **lỗi**: chọn top-K bằng `argsort(−score)` ⇒ lấy điểm **CAO** = coin **TỆ NHẤT** |
| C | `research/analysis/ofi_money_ext.py:106` | **lỗi**: y hệt ở đường B2 |
| D | `research/analysis/ofi_money_score_v2.py` | **bản sửa**: `--orient` (mặc định `−1`); điểm xếp hạng `= ORIENT·score` |
| E | `research/analysis/ofi_money_ext_v2.py` | **bản sửa** đường B2, cùng `--orient` |
| F | `research/analysis/ofi_ext_trades_build.py` | **dựng lại** file ứng viên B2 theo `ORIENT` |
| G | `research/analysis/ofi_reorient_rulers.py` | bảng mô tả §5 |
| H | `research/kaggle/ofi_money/make_ofi_ext_kernel_v2.py` | kernel `ofi-ext-labelb-cpu-reorient` |

Bản cũ **KHÔNG** bị sửa (giữ tái lập). Thay đổi **DUY NHẤT** so với `PREREG_OFI_MONEY`: `ORIENT = −1`.

---

## 2. TÁI LẬP (kiểm chứng "chỉ khác chiều")

| việc | kết quả | kết luận |
|---|---|---|
| RE `ofi_money_score_v2.py --orient +1` vs `docs/result/ofi_money.json` | khớp (candidate `K8`: coin `+0,6416` · gr1dv `+0,01017` · `B1`=100,0 %) | ✅ |
| **B2** `ofi_ext_trades_build.py --orient +1 --compare <file cũ>` | **`cu=166080 · moi=166080 · chi_cu=0 · chi_moi=0 · bang_giong_het=True`** | ✅ **KHỚP TUYỆT ĐỐI** |
| B2 `ofi_money_ext_v2.py --orient +1` trên pool cũ | `cand−base K8`: `dnet_coin=−0,000565 [−0,002152,+0,000961]`, `dnet_gr1dv=−7,29e−06` | ✅ **khớp `RESULT_OFI_MONEY` §4.3** |

⇒ Chứng minh **chỉ** khác chiều điểm (mọi thứ khác giữ nguyên).

---

## 3. BẢNG CHÍNH — `candidate` vs `baseline_fresh` vs `noise` × 2 đường (đúng chiều, `K=8`, `f=0,006`)

| đường · đối tượng | `entry` | `net_coin` (%/vòng) | **`net_gr1dv`** (×10⁻³) | `%top-1` (rao a `≤15 %`) | `TF50` (rao b′ `>0`) | `asym` |
|---|---|---|---|---|---|---|
| **RE** `candidate` | 404,3 | +0,6480 | **+0,12820** | 30,39 (**FAIL**) | −2514,89 (**FAIL**) | −3,395 |
| **RE** `baseline_fresh` | 407,6 | +0,6533 | +0,12820 | 30,17 (FAIL) | −2506,45 (FAIL) | −3,355 |
| **RE** `noise_ofi_check` | 408,1 | +0,5995 | +0,11750 | 32,86 (FAIL) | −2541,11 (FAIL) | −3,383 |
| **B2** `candidate` | 404,4 | +0,6485 | **+0,11270** | 30,37 (FAIL) | −2514,68 (FAIL) | −3,393 |
| **B2** `baseline_fresh` | 407,6 | +0,6551 | +0,11330 | 30,09 (FAIL) | −2505,20 (FAIL) | −3,355 |
| **B2** `noise_ofi_check` | 408,1 | +0,5987 | +0,10290 | 32,91 (FAIL) | −2541,63 (FAIL) | −3,382 |

`q*` (ngưỡng bỏ-đuôi hoà vốn): **RE/B2 = 4,0–4,5 %** (candidate 4,5 RE · 4,5 B2). `median`/leg = **+0,04895** mọi đối tượng
(giá trị rời rạc — không phân biệt). `sign%` (net>0) = **79,6 / 79,4 / 79,3** (RE) · **79,6 / 79,4 / 79,3** (B2).

**Δ ghép cặp theo tick (`f=0,006`, `K=8`) — QUYẾT ĐỊNH:**

| đường · Δ | `Δnet_coin` | **`Δnet_gr1dv`** [`k=5`] | ngoài CI |
|---|---|---|---|
| RE `cand−base` | −0,000053 | **−3,20e−09** [−2,944e−05, +2,739e−05] | KHÔNG |
| RE `cand−noise` | +0,000485 | **+1,071e−05** [−1,753e−05, +3,778e−05] | KHÔNG |
| B2 `cand−base` | −0,000066 | **−1,06e−06** [−2,710e−05, +2,390e−05] | KHÔNG |
| B2 `cand−noise` | +0,000499 | **+1,010e−05** [−1,530e−05, +3,300e−05] | KHÔNG |

**Theo seed** (`dnet_gr1dv`, `K=8`): RE `cand−base` = `+7,1e−6 / −5,9e−6 / +1,70e−5` (2/3 dương) ·
RE `cand−noise` = `+1,99e−5 / +1,9e−6 / +1,44e−5` (**3/3** dương) ·
B2 `cand−base` = `+4,7e−6 / −2,2e−6 / +1,20e−5` (2/3) · B2 `cand−noise` = `+1,67e−5 / +1,6e−6 / +1,17e−5` (**3/3**).
⇒ Có **dấu dương yếu vs `noise`** (3/3 seed, cả 2 đường) nhưng **CI vẫn chứa 0**; vs `baseline` thì ≈ 0.

---

## 4. MÔ TẢ §5 (KHÔNG dùng quyết định) — 4 thước chuẩn + rao + martingale

**4 thước chuẩn hiện hành** (Δ ghép cặp, block-72h/NREP 2000/seed 20260905; `*` = **ngoài raw95**, `k=5`=×1,7941):

| Δ | `wl_ratio` | `tf_5` | `loss_mean` | `conc_5` |
|---|---|---|---|---|
| RE `cand−base` | **−0,00348** raw[−0,00651,−0,00042] `*raw` (k5 ⊇ 0) | +0,00007 | **+0,00264** raw[+0,00042,+0,00485] `*raw` (k5 ⊇ 0) | −0,04388 |
| RE `cand−noise` | −0,00103 | +0,00047 | +0,00123 | +0,25930 |
| B2 `cand−base` | **−0,00340** raw[−0,00646,−0,00029] `*raw` (k5 ⊇ 0) | +0,00006 | **+0,00260** raw[+0,00034,+0,00481] `*raw` (k5 ⊇ 0) | −0,04968 |
| B2 `cand−noise` | −0,00096 | +0,00048 | +0,00121 | +0,26690 |

**Mức (level)** `wl_ratio` = 0,295/0,298/0,296 · `loss_mean` = 0,2161/0,2135/0,2149 · `conc_5` = 1,147/1,134/1,237
(RE ≈ B2). Đọc: candidate so baseline **lỗ trung bình hơn ~0,0026** và **tỷ số thắng/thua thấp hơn ~0,0034**
(ngoài **raw95** nhưng **trong `k=5`**) — tức **hơi xấu hơn ở trục RỦI RO**, không phải tốt hơn.

**3 chỉ số martingale** (`K=8`, `f=0,006`, RE ≈ B2): ① lỗ lớn nhất 1 leg = **−0,974** (cand) / −0,974 (base) / −0,974 (noise)
· ② `conc 1 coin` = **8,4 % / 8,4 % / 9,4 %** (dưới ngưỡng 15 %) · ③ số coin "chết" (Σnet < 0) = **207/536 · 209/531 · 217/530**.

---

## 5. Δ vs **2 đối chứng** (retrain `A45−45deploy`; nhiễu `V5−V1`) khi **so model**

Chuẩn đối chứng (khung thước model, `RESULT_TAIL_ROBUST_RULERS` §4, `f=0,006`, 72h/2000/20260905):

| cặp | `tf_5` | `loss_mean` | `wl_ratio` | `max_loss` | ngoài CI? |
|---|---|---|---|---|---|
| `A45 − 45deploy` **(ĐC#1, retrain)** | +0,00039 w3,52 | +0,00043 w7,50 | +0,00079 w5,72 | +0,00079 w6,59 | **KHÔNG** |
| `V5 − V1` **(ĐC#2, nhiễu)** | −0,00007 w23,2 | +0,00082 w4,49 | +0,00002 w237,7 | +0,00143 w3,71 | **KHÔNG** |
| OFI `cand − base` (cùng khung) | +0,00101 w2,29 | +0,00015 w38,8 | +0,00011 w73,5 | +0,00083 w8,23 | KHÔNG |

⇒ **Độ rộng nhiễu của 2 đối chứng ~ 4e−4 … 8e−4** ở `loss_mean`; Δ của OFI (`+0,00015 … +0,00264`) **cùng bậc** với
nhiễu retrain ⇒ **không phân giải được** khỏi nền nhiễu. Khớp dự báo MASTER ghi trước ("Δ nhiều khả năng TRONG CI").

---

## 6. ĐƯỜNG B2 — dựng lại pool đúng chiều

- Ứng viên tập coin MỚI (hợp top-8 của **3 đối tượng × 3 seed** đúng chiều, trừ `P32`): **293 cặp / 290 tick / 43 sym**
  (chiều SAI cho **166.080 cặp / 456 sym** — hai tập **gần như rời nhau**).
- nhãn luật thoát dựng trên **Kaggle CPU** (`chuyendinh/ofi-ext-labelb-cpu-reorient`, dataset
  `chuyendinh/ofi-money-ext-trades-reorient`): `n_rows=293`, `noentry=0`, `OPEN_AT_END=0`, `total=9,2 phút`, `peak=0,93 GB`
  (⇒ **dưới cổng 120 phút**, KHÔNG cần báo trước); gross TB của 293 cặp mới = **−0,0134**.
- Pool B2 cuối: `P32 309.024 + NEW 293 = 309.317` dòng · 9.657 tick · **32,0 coin/tick** (max 34).
  Nhãn: `/home/ubuntu/ofi_v3/ofimoney/label_b_pnl_ext_reorient.parquet` (**ngoài repo**, 23 KB, sha `cb2fa5e4…`).

---

## 7. KIỂM HỢP LỆ (bắt buộc) — PASS ở cả 2 đường

1. `noise − candidate` **KHÔNG** dương ngoài CI (`k=5`): RE −1,071e−05 · B2 −9,82e−06 ⇒ **không HARNESS_NGHI_NGỜ** ✅
2. `dnet_coin` **bất biến theo `f`**: RE `−0,000053059914` · B2 `−0,000065526046` (lệch **0,00e+00** trên 4 mức phí) ✅
3. `K=32`: `dnet_coin(cand−base) = 0,0000000000` tuyệt đối (cả 2 đường) ✅
4. **`B1`** (dự báo `<10 %`): SỬA **0,054 %** (cand) / 0,003 % / 0,027 % · `K=32` ≤ 8,4 % ⇒ **khớp dự báo** ✅
   (chiều CŨ: **100 %** ở mọi `K`) · `B1` hợp 3 seed: cand **56/93.485 (0,06 %)**.

---

## 8. VIỆC BỎ + LÝ DO

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Bước 0 (Spearman chiều điểm) | ✅ **KHÔNG làm lại** | đã chạy + xác nhận (`step0_orient.py`; pre-reg §0) |
| 2 | Rate `{TSloss% · mP\|SM · mP\|SL · mMargin}` + CI | ⛔ **N/A** | cần khung **sim Java** (`printDone.csv` có `status`/`margin`); ràng buộc 1 cấm chạy sim, khung here là **leg-based offline** (không margin/portfolio) |
| 3 | Rao cũ `--appetite latest` (dd 40/uw 250/q −20 + 0 năm âm + conc 15 %) | ⛔ **N/A** | cần **đường equity + theo năm** từ sim — cùng lý do #2 |
| 4 | `K ∈ {10,12,16}` trên B2 với **nhãn MỚI** | ⛔ BỎ | ứng viên đúng chiều cần thêm 293 cặp; `K>8` trên pool hiện có đã cho mọi Δ **trong CI** ⇒ không đổi kết luận |
| 5 | Sweep/retrain/đổi luật thoát/funding/DCA/de-dup live | ⛔ BỎ | ngoài phạm vi pre-reg; **4 vòng tiền trước đã đóng trục** |
| 6 | Chạy Java/sim, `claude-run`, chạm 2026/ONNX/LIVE/`HoldoutSeal` | ⛔ BỎ | ràng buộc đề bài (shadow đang LIVE) |
| 7 | Giữ `pred_*.parquet` lâu dài trên Oracle | ⛔ BỎ | đĩa `/` 94 %; đã xoá sau khi chấm |

---

## 9. KẾT LUẬN (1 dòng)

**Sửa đúng chiều điểm KHÔNG cứu được OFI**: sau khi `ORIENT = −1` (và dựng lại pool B2 đúng chiều),
`Δnet_gr1dv` của `candidate` so **cả** `baseline_fresh` **và** `noise_ofi_check` vẫn **TRONG CI** ở **cả 2 đường**
(RE `P32` và B2) — **OFI candidate không có giá trị TIỀN** (lần thứ **5** trên trục tiền; lần thứ **2** của riêng OFI);
giá trị **thật** của vòng này là **bịt lỗ hổng đo**: chiều cũ chọn **100 % coin ngoài `P32`** (rổ đáy) ⇒ phép đo cũ
vô hiệu, và `B1` nay về **0,054 %** (khớp dự báo `<10 %`).
