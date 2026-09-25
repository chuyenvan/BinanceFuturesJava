# PREREG_CAP70_FEE06 — **Trần gross = 70 % (CỨNG)** + **phí chuẩn = 0,6 %/vòng**: chọn `K` và `size`

**Ngày chốt:** 2026-09-26 · **Nhánh:** `module` · **Trạng thái:** CHỐT **TRƯỚC** khi đọc số.
**Quyết định owner (26/09 05:35, NGUỒN DUY NHẤT — không diễn giải lại):**
- **Trần gross exposure = 70 % equity (CỨNG / binding)** — thay cho "quan sát 54–58 %".
- **Phí chuẩn nghiên cứu = 0,6 %/vòng** — thay `0,8 %` mà các vòng trước dùng.

**Tiền đề (dùng tin, KHÔNG đo lại):**
- `RESULT_K_SWEEP.md` (`428b331`): nới `K` **trong CI** ở mọi `K`, mọi mức phí; `K=32` **âm** ở `f=0`;
  quan hệ gần phẳng, hơi gồ ở `K=12`. **Gross %equity POST-HOC** (neo `2,0 %/lệnh`, trên coin phân biệt):
  K=8 `48,8/70/84` · K=10 `58,5/80/92` · K=12 `67,4/92/106` · K=16 `83,3/110/134` · K=32 `144/182/206`
  (TB/p95/max). Size giữ gross như K=8: `1,00 / 0,79 / 0,65 / 0,48 / 0,22`.
- `RESULT_PNL_RULER.md` (`acb88bd`): gross/ro top-8 **1,3273 %/vòng**; cả pool **1,2677 %** ⇒ phí hoà vốn
  **1,27–1,56 %**. ⇒ Ở **0,6 %** và 0,8 % **đều dương**.
- `RESULT_MONEY_RANKER.md` (`4a94c36`): pool **P32** = `/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet`
  (309.024 dòng = 9.657 tick × 32; sha `1d42b7f6…`); `rank<8` tái lập `label_b_K8.parquet` **khớp 100 %**.
- Code tái dùng NGUYÊN: `research/analysis/model_ruler.ci_mean` → `stage2_score.block_boot_mean` + `c3_rates`
  (`BLOCK_H=72`, `NREP=2000`, `SEED=20260905`).

---

## 1. CÂU HỎI (ba câu, trả lời được)

1. **Dưới trần 70 % CỨNG**: `K` nào **khả thi**, `K` nào cho **net/tick cao nhất** — có **ngoài CI** không?
2. Ở phí **0,6 %**, **alpha xếp hạng trên 45 feature** có thành **dương ngoài CI** không?
3. **Khuyến nghị dứt khoát: `K` + `size`** (kèm cảnh báo còn lại).

---

## 2. NGUỒN (KHÔNG build lại)

| tệp | dòng | sha256 | dùng |
|---|---|---|---|
| `/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet` | 309.024 | `1d42b7f6…` | pool **P32** (đường RE) |
| `/tmp/mrpnp/cache/{arm}_{K}_{fold}.parquet` | per-fold | — | chỉ số **per-tick** của arm/đối chứng (chấm lại Δ, KHÔNG đọc bins nếu cache đủ) |
| `/home/ubuntu/ruler_bins/g015p2-arm44-gpu/stage2/A44` | 16 fold | — | **chỉ** để bổ sung `A44` vào cache (đối chứng thứ 4 của phép kiểm bất biến) |

**Chốt trước:** dùng cột **`gross`** (KHÔNG dùng cột `net` = `gross − 0,008`, một mức phí).
`top-K = rank < K`, không xếp lại, không chấm mô hình nào khi quét `K`.

---

## 3. CÁCH ÁP TRẦN 70 % — **KHAI BÁO ĐÚNG HAI CÁCH, BÁO CẢ HAI** (không chọn cái đẹp hơn)

Gọi `d_t` = **số coin PHÂN BIỆT đang mở** tại tick `t` (khớp sổ live có khoá symbol — POST-HOC, xem §7).
Neo size **`s₀ = 2,0 % equity / lệnh`** ⇒ **gross_t = s₀ · d_t** (đơn vị: `s₀ = 1` ⇔ 2,0 %/lệnh).

| cách | ràng buộc | hệ số size | hệ quả |
|---|---|---|---|
| **(A) chuẩn hoá theo TB** | `gross_TB(K) ≤ 70 %` | **`s_A(K) = 70 / gross_TB(K)`** | TB = 70 %; **p95/max CÓ THỂ vượt** |
| **(B) chặn TỪNG TICK** (nghiêm ngặt hơn) | `max_t gross_t ≤ 70 %` | **`s_Bmax(K) = 70 / gross_max(K)`** | **mọi tick ≤ 70 %**; TB tụt mạnh |
| **(B′) chặn theo p95** (mốc phụ của B) | `p95_t gross_t ≤ 70 %` | **`s_B95(K) = 70 / gross_p95(K)`** | p95 = 70 %; max còn vượt |

`size sau khi áp = s₀ · s(K)`; `s(K) = 1` ⇔ giữ nguyên neo 2,0 %/lệnh.
**Chốt trước:** **BÁO CẢ BA** `s_A`, `s_B95`, `s_Bmax` + **gross TB/p95/max sau size** — **KHÔNG** chỉ báo cách
có lợi. Nhận xét nào dùng cách nào phải ghi rõ.

**net/tick sau khi co size** (đại lượng quyết định): PnL/tick/equity `= s₀ · s(K) · Σ_{i∈S_K(t)}(gross_i − f)`.
Báo:
- **`net_gr1dv(K,f)`** = `Σ_i (gross_i − f) / Σ_t e_t` (**bất biến size** — net trên 1 đơn vị gross exposure);
- **`net/tick sau size`** = `100 · s₀ · s(K) · net_tick_K(f)` (**%/equity/tick**) cho **từng cách A / B95 / Bmax**,
  kèm CI và **Δ ghép cặp vs `K = 8` trong CÙNG cách**.
⚠️ Khai trước: `net_tick_K` **TĂNG theo `K` là MÁY MÓC** (nhiều lệnh hơn) — **KHÔNG** đếm làm bằng chứng.

---

## 4. MỨC PHÍ (chốt trước)

- **CHÍNH:** **`f = 0,006`** (quyết định owner).
- **ĐỐI CHIẾU:** `f ∈ {0,000 (gross) · 0,004 · 0,008}` (mốc cũ để so các vòng trước).
- **Cấu trúc chốt trước:** phí là **hằng số trên cùng một rổ** ⇒ trong mọi so sánh **model-vs-model trên
  CÙNG tập (tick, coin)**, phí **TRIỆT TIÊU trong `Δ`** ⇒ **kết luận "alpha xếp hạng = 0" BẤT BIẾN theo phí**
  (đổi phí chỉ đổi **MỨC**, không đổi **Δ**). Nhưng khi **quét `K`**, **số lệnh đổi theo `K`** ⇒ phí **KHÔNG**
  triệt tiêu ⇒ phải **tính lại thật**.

---

## 5. BỘ `K` + ĐỘ RỘNG CI (chốt trước)

- `K ∈ {8, 10, 12, 16, 32}` (8 = hiện hành; 10/12 = câu hỏi; 16/32 = bối cảnh).
- **`k = 5`** ⇒ `inflate(k) = sqrt(2 ln 5) = 1,7941`. In **cả** `raw95` **và** `inflate(5)`; kết luận phải
  giống nhau ở cả 2 (khác ⇒ khai rõ). Khối **72h**, `NREP=2000`, `SEED=20260905`.
- **KHÔNG nới ngưỡng.** "Ngoài CI" = **ngoài cả `raw95` lẫn `inflate(5)`**.

---

## 6. PHÉP KIỂM BẮT BUỘC — **tính bất biến của `Δ` theo phí** (bằng SỐ, không chỉ nói)

**Mệnh đề:** phí là hằng số mỗi vòng ⇒ `Δnet(f) ≡ Δgross` với mọi `f` trên cùng tập ghép cặp.
**Cách kiểm (chốt trước):** với các arm `MRA4 / MRB8 / MRB32` và đối chứng `45deploy / A45 / V5 / A44`,
ghép cặp theo tick chung ở `K=8` và `K=32`; tính `Δ(f) = mean_{{t chung}}[(gross8_arm − f) − (gross8_ctl − f)]`
ở **`f = 0,006` và `f = 0,008`** và CI `inflate(5)` cho từng mức.
- **ĐẠT** ⟺ `|Δ(0,006) − Δ(0,008)| < 1e-12` **và** CI hai mức **trùng khít**.
- **RỚT** ⟺ khác nhau đáng kể ⇒ **có LỖI trong mô hình phí** ⇒ **BÁO RỚT**, không che.
**Δ vs 2 đối chứng bắt buộc** (`A45 − 45deploy` bước *retrain*; `V5 − V1` bước *nhiễu*) ở `f = 0,006`:
phải **≈ 0 và TRONG CI** ⇒ thước hợp lệ. Nếu **dương ngoài CI** ⇒ phải báo (không mong đợi).

## 6b. VIỆC 3 — kinh tế ở `f = 0,006`

- **`break-even fee`** của rổ top-K (mức phí làm `net_coin = 0`) = `mean(gross | rank < K)`; so với `0,006`.
- **Δ vs 2 đối chứng bắt buộc** (như §6) ở `f = 0,006`: **có mức KINH TẾ DƯƠNG ngoài CI nào không?**
  (**Dự kiến: KHÔNG** — nhưng phải **khẳng định bằng số**.)

---

## 7. GIẢ ĐỊNH PHẢI KHAI (⚠️ chống over-claim)

Con số **gross neo `2,0 %/lệnh` TRÊN COIN PHÂN BIỆT** là **POST-HOC** (đã ghi rõ từ `RESULT_K_SWEEP` §5):
- **KHÔNG** đo trên sổ LIVE; **KHÔNG** mô hình hoá **de-dup live / DCA nhiều chân / trần size·notional /
  trần gross / funding**. Bản neo trên **số VỊ THẾ `e_t`** cho gross **821 %** (`K=8`) — **vô lý** ⇒
  chỉ **tỉ lệ giữa các `K`** là đọc được; **MỨC tuyệt đối** là quy đổi, không phải đo.
- **Hệ quả:** bảng `net/tick sau size` là con số **MÔ HÌNH**, không phải equity kỳ vọng của LIVE. Phải ghi rõ
  trong RESULT/DECISION.

---

## 8. LUẬT TRẢ LỜI (chốt TRƯỚC — KHÔNG đổi sau khi đọc số)

1. **"`K` khả thi dưới trần 70 %"**: theo **(A)** `s(K) ≤ 1` (không phải phóng to) và theo **(B)** tồn tại
   `s_B(K) > 0` ⇒ **mọi `K` đều "khả thi" về mặt số học**; câu hỏi thật là **có ĐÁNG** không:
   **"đáng" ⟺ `Δnet/tick` (cùng cách áp trần) `> 0` NGOÀI CI vs `K = 8` ở `f = 0,006` VÀ `f = 0`.**
2. **Khuyến nghị `K`**: nếu **mọi Δ trong CI** ⇒ **GIỮ `K = 8`** (không có bằng chứng ngoài CI để đổi);
   nếu tồn tại `K*` ngoài CI ở **cả** `f=0,006` và `f=0` ⇒ nêu `K*` **kèm `s(K*)`** và cách áp trần.
   **KHÔNG** chọn `K` theo mức phí "đẹp" — nếu kết luận đổi theo mức phí ⇒ **khai rõ**, không chọn.
3. **Câu (2) alpha xếp hạng**: `Δ` model-vs-model ở `f = 0,006` **ngoài CI**? Nếu **KHÔNG** ⇒ nói dứt khoát
   **"phí không thể cứu `Δ = 0`"** và giải thích bằng **đại số bất biến** (§4) + số của §6.
4. **Post-hoc:** mọi phân tích ngoài §1–§8 ⇒ ghi rõ **"POST-HOC"**.

---

## 9. RÀNG BUỘC THI HÀNH

Thuần Python offline · **KHÔNG** train · **KHÔNG** chạy Java/sim trên Oracle (shadow LIVE) · **KHÔNG** claude-run ·
**KHÔNG** push git (commit local, commit sớm) · **DEV only**, không chạm 2026/`HoldoutSeal` · kiểm `free -g`
trước mỗi bước · output tool **rất nhỏ**.
