# RESULT_CAP70_FEE06 — Trần gross **70 % CỨNG** + phí chuẩn **0,6 %/vòng**: `K` nào khả thi, `net/tick` nào cao nhất

**Ngày:** 2026-09-26 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG · **KHÔNG push**
**Pre-reg:** `docs/prereg/PREREG_CAP70_FEE06.md` (commit `6f37caa`) — chốt **TRƯỚC** khi đọc số.
**Code:** `research/analysis/cap70_fee06.py` (mới) · `research/analysis/fee_invariance_check.py` (mới)
· dùng **NGUYÊN** `model_ruler.ci_mean` → `stage2_score.block_boot_mean` + `c3_rates`
(`BLOCK_H=72`, `NREP=2000`, `SEED=20260905`); `inflate(k=5)=1,7941`.
**Số thô:** `docs/result/cap70_fee06.json` (67 KB) · `docs/result/fee_invariance.json`.
**Đường RE — KHÔNG build lại gì:** pool **P32** `/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet`
(309.024 dòng = 9.657 tick × 32, sha `1d42b7f6…`). **KHÔNG** chạy lại exit engine, **KHÔNG** train,
**KHÔNG** sim/Java. Chi phí: **~10 giây** (`free -g` trước khi chạy = 23 GB / 11 GB rảnh) ⇒ không Kaggle.

---

## 0. TRẢ LỜI NGẮN (3 câu bắt buộc)

### (1) Dưới trần 70 % CỨNG: `K` nào khả thi, `K` nào `net/tick` cao nhất — ngoài CI? → **MỌI `K` "khả thi" về số học; `K = 12` cao nhất ở tầng MỨC nhưng Δ vs `K = 8` TRONG CI**

| cách áp trần | `K=8` | `K=10` | **`K=12`** | `K=16` | `K=32` |
|---|---|---|---|---|---|
| **(A)** size `s_A = 70/gross_TB` | 1,4339 | 1,1969 | **1,0388** | 0,8400 | 0,4857 |
| gross sau A (TB / **max**) | 70,0 / 120,5 | 70,0 / 110,1 | **70,0 / 110,1** | 70,0 / 112,6 | 70,0 / 100,1 |
| **(B95)** size `s_B95 = 70/gross_p95` | 1,0000 | 0,8750 | **0,7609** | 0,6364 | 0,3846 |
| gross sau B95 (p95 / max) | 70,0 / 84,0 | 70,0 / 80,5 | **70,0 / 80,7** | 70,0 / 85,3 | 70,0 / 79,2 |
| **(Bmax)** size `s_Bmax = 70/gross_max` | 0,8333 | 0,7609 | **0,6604** | 0,5224 | 0,3398 |
| gross sau Bmax (TB / p95 / **max**) | 40,7 / 58,4 / **70,0** | 44,5 / 60,9 / **70,0** | 44,5 / 60,8 / **70,0** | 43,5 / 57,4 / **70,0** | 49,0 / 61,8 / **70,0** |
| **net/tick SAU size (A)** @f=0,006 (%equity/tick) | 0,1378 | 0,1472 | **0,1630** | 0,1791 | 0,2076 |
| Δ vs K=8 (A) @f=0,006 | — | +0,0094 | **+0,0252** | +0,0413 | +0,0698 |
| CI5 của Δ (A) | — | [−0,037,+0,053] | **[−0,057,+0,098]** | [−0,100,+0,166] | [−0,158,+0,274] |

**Đọc:** `K = 12` (và `16`) cho **MỨC** `net/tick` cao nhất trong dải 8–16 **ở mọi cách áp trần**, nhưng
**KHÔNG ô `Δ` nào NGOÀI CI** (CI rộng gấp ~2–4 lần điểm) ⇒ **không phân biệt được với `K = 8`**. `K = 32`
**cao nhất về `net/tick` (máy móc: 32 lệnh/tick)** — vẫn **trong CI**. ⇒ **không có `K*` đo được**.
**Dưới `K = 8`, trần 70 % CỨNG bind theo TỪNG TICK buộc size GIẢM còn `0,83×`** (vì `gross_max(K=8) = 84 % >
70 %`); theo **TB** thì còn **được phóng to `1,43×`** (vì `gross_TB = 48,8 % < 70 %`).

### (2) Ở phí 0,6 %, alpha xếp hạng trên 45 feature có dương ngoài CI? → **KHÔNG — và phí KHÔNG THỂ cứu `Δ = 0`**

- **Chấm lại `Δ` model-vs-model ở `f = 0,006` trên thước TIỀN `P32`** (12 cặp × 4 đối chứng, ghép cặp tick chung):
  **0/12 cặp ngoài CI**; `Δ` = **+0,0013 … +0,0032** (CI5 rộng ±0,002…0,009) — **giống hệt** `RESULT_PNL_RULER`
  (`acb88bd`) đã công bố ở mức `0,008`.
- **Phí TRIỆT TIÊU trong `Δ`** (phí là hằng số mỗi vòng trên cùng rổ). **Kiểm bằng số (PREREG §6):**
  `|Δ(0,006) − Δ(0,008)| = 0,00e+00` trên **cả 24 cặp** (MRA4/MRB8/MRB32 × 45deploy/A45/V5/A44 × K=8/32)
  ⇒ **ĐẠT**; `Δ(f=0,004) = Δ(f=0,006) = Δ(f=0,008)` **trùng khít** ⇒ **mô hình phí ĐÚNG**.
  ⇒ **đổi phí (0,8 → 0,6) chỉ đổi MỨC, KHÔNG đổi `Δ`** ⇒ **kết luận "alpha xếp hạng = 0" bất biến theo phí**.
- **Kiểm hợp lệ (bắt buộc) ở `f = 0,006`:** `A45 − 45deploy` = **+0,00035** CI5 `[−0,00070, +0,00155]`
  (TRONG); `V5 − V1` = **−0,00018** CI5 `[−0,00171, +0,00136]` (TRONG) ⇒ thước/ghép cặp hợp lệ.

### (3) Khuyến nghị dứt khoát: **GIỮ `K = 8`**; nếu siết trần 70 % theo TỪNG TICK thì **size ≈ 0,83× hiện hành**

- **GIỮ `K = 8`**: mọi `Δ` (cả `net/tick` sau size lẫn `net/1đv-gross`) **trong CI** ở **cả 3 cách áp trần** và
  **cả 4 mức phí** ⇒ **không có bằng chứng ngoài CI để đổi `K`**. (Đúng LUẬT §8 pre-reg.)
- **Cảnh báo còn lại:** (a) mọi con số gross là **quy đổi POST-HOC neo `2,0 %/lệnh` TRÊN COIN PHÂN BIỆT**
  (§5) — **KHÔNG** mô hình hoá de-dup live / DCA nhiều chân / trần size·notional / funding; (b) `net/tick`
  tuyệt đối là **MÔ HÌNH**, không phải equity LIVE; (c) CI rộng ⇒ kết luận đúng là **"không phân biệt được"**,
  không phải "`K = 12` tệ".

---

## 1. PHÍ 0,6 % — MỨC TRỞ NÊN RÕ DƯƠNG (nhưng KHÔNG đổi `Δ`)

`net_coin_K(f)` = `mean_{t} mean_{i∈topK}(gross_i − f)`; `net_gr1dv_K(f)` = `Σ_i(gross_i − f)/Σ_t e_t`
(**CHỈ SỐ QUYẾT ĐỊNH** — net trên 1 đơn vị gross).

| `K` | `net_coin` @0,006 (%/vòng) | `net_coin` @0,008 | `net_gr1dv` @0,004 | **`net_gr1dv` @0,006** | `net_gr1dv` @0,008 | `BE_coin` (%/vòng) |
|---|---|---|---|---|---|---|
| **8** | +0,6006 | +0,4006 | +0,01561 | **+0,01171** | +0,00781 | **1,2006** |
| 10 | +0,6148 | +0,4148 | +0,01575 | +0,01188 | +0,00802 | 1,2148 |
| **12** | **+0,6537** | +0,4537 | +0,01633 | **+0,01250** | +0,00868 | **1,2537** |
| 16 | +0,6663 | +0,4663 | +0,01624 | +0,01249 | +0,00874 | 1,2663 |
| 32 | +0,6678 | +0,4678 | +0,01514 | +0,01165 | +0,00816 | 1,2678 |

- **`break-even fee` của rổ top-K = 1,2006 %/vòng (K=8) → 1,2678 %/vòng (K=32)** ⇒ ở **phí 0,6 %** biên an
  toàn **≈ 0,6 pp/vòng** (net_coin ≈ +0,60…+0,67 %/vòng); ở `0,8 %` còn ≈ +0,40…+0,47 %. ⇒ **0,6 % làm MỨC
  dương rõ hơn** (không đụng tới kết luận `Δ`).
- **Δ vs `K = 8` (tỉ số ghép cặp 72h, ×10⁻⁴):** mọi ô **TRONG CI** ở **cả 3 mức** `f = 0,004 / 0,006 / 0,008`
  (vd `K12 − K8` = `+0,72 / +0,79 / +0,87`; CI5 ≈ `[−0,28, +0,45]`) ⇒ **mức phí KHÔNG đổi kết luận `K`**.

---

## 2. BẢNG QUYẾT ĐỊNH — `K` × cách áp trần (A / B95 / Bmax) × `net/tick` sau size

`net/tick sau size` (pct equity/tick) `= 100 · 0,02 · s(K) · net_tick_K(f)` (@`f = 0,006`).
`*` = Δ **ngoài CI k=5** vs `K = 8` cùng cách (ở đây **KHÔNG ô nào có `*`**).

| `K` | `s_A` | net/tick (A) | Δ(A) vs 8 | `s_B95` | net/tick (B95) | Δ(B95) | `s_Bmax` | net/tick (Bmax) | Δ(Bmax) |
|---|---|---|---|---|---|---|---|---|---|
| **8** | 1,4339 | **0,1378** | — | 1,0000 | **0,0961** | — | 0,8333 | **0,0801** | — |
| 10 | 1,1969 | 0,1472 | +0,0094 (CI) | 0,8750 | 0,1076 | +0,0115 (CI) | 0,7609 | 0,0936 | +0,0135 (CI) |
| **12** | 1,0388 | **0,1630** | +0,0252 (CI) | 0,7609 | **0,1194** | +0,0233 (CI) | 0,6604 | **0,1036** | +0,0235 (CI) |
| 16 | 0,8400 | 0,1791 | +0,0413 (CI) | 0,6364 | 0,1357 | +0,0396 (CI) | 0,5224 | 0,1114 | +0,0313 (CI) |
| 32 | 0,4857 | 0,2076 | +0,0698 (CI) | 0,3846 | 0,1644 | +0,0683 (CI) | 0,3398 | 0,1452 | +0,0651 (CI) |

**Đọc đúng:** (i) cả 3 cách cho **cùng một kết luận** (mọi Δ trong CI); (ii) **cách áp trần đổi MỨC rất mạnh**
(`K = 8`: A `0,1378` vs Bmax `0,0801` — **siết theo max TỐN ~42 % net/tick**); (iii) `K = 12` là **đỉnh MỨC**
trong dải 8–16; `K = 32` cao nhất nhưng **máy móc** (32 lệnh/tick) và **vẫn trong CI**.

---

## 3. GROSS EXPOSURE THEO `K` SAU KHI CO SIZE (xác nhận trần)

| `K` | `d_mean` | `d_p95` | `d_max` | gross TB (neo) | gross p95 | gross max |
|---|---|---|---|---|---|---|
| 8 | 24,41 | 35 | 42 | 48,82 | 70,00 | 84,00 |
| 10 | 29,24 | 40 | 46 | 58,49 | 80,00 | 92,00 |
| **12** | 33,69 | 46 | 53 | 67,38 | 92,00 | 106,00 |
| 16 | 41,67 | 55 | 67 | 83,34 | 110,00 | 134,00 |
| 32 | 72,06 | 91 | 103 | 144,11 | 182,00 | 206,00 |

- **(A)** ⇒ TB = **70,00** mọi `K` ⇒ **KHẲNG ĐỊNH ĐƯỢC: TB ≤ 70 %**; **p95/max VƯỢT** (K=8 max **120,5 %**).
- **(B95)** ⇒ p95 = **70,00**; max còn **79–85 %** ⇒ **CHƯA** bảo đảm mọi tick.
- **(Bmax)** ⇒ **max = 70,0 % mọi `K`** (làm tròn 69,997–70,003) ⇒ **xác nhận ≤ 70 % MỌI tick** (mốc đo = 9.657
  mốc `ts` của pool; không có mốc nào vượt).
- ⚠️ **`K = 8` dưới trần TỪNG TICK đã bind ngay** (`84 % > 70 %`) ⇒ nếu siết cứng, **size phải GIẢM còn 0,83×**
  — nghĩa là **trần 70 % không phải ràng buộc "cho phép nới", mà là ràng buộc "buộc CO"** ở `K` hiện hành.

---

## 4. KIỂM TÍNH BẤT BIẾN CỦA `Δ` THEO PHÍ (bắt buộc, bằng SỐ)

`Δ(f) = mean_{t chung}[(gross8_arm − f) − (gross8_ctl − f)]`, ghép cặp tick chung.

| cặp (thước `P32`) | n | Δ(0,004) | Δ(0,006) | Δ(0,008) | max\|Δ(0,006)−Δ(0,008)\| | **bất biến** |
|---|---|---|---|---|---|---|
| MRA4 − 45deploy | 9.657 | +0,001699 | +0,001699 | +0,001699 | **0,00e+00** | ✔ |
| MRA4 − A45 / V5 / **A44** | 9.657 | … | +0,00135 / +0,00178 / +0,00204 | (y hệt) | **0,00e+00** | ✔ |
| MRB8 − 45deploy | 8.717 | +0,001938 | +0,001938 | +0,001938 | **0,00e+00** | ✔ |
| MRB8 − A45 / V5 / A44 | 8.717 | … | +0,00159 / +0,00204 / +0,00220 | (y hệt) | **0,00e+00** | ✔ |
| MRB32 − 45deploy | 8.717 | +0,002907 | +0,002907 | +0,002907 | **0,00e+00** | ✔ |
| MRB32 − A45 / V5 / A44 | 8.717 | … | +0,00256 / +0,00301 / +0,00317 | (y hệt) | **0,00e+00** | ✔ |

- **24/24 cặp ĐẠT** (max lệch = `0,00e+00`) ⇒ **mô hình phí ĐÚNG**; **KHÔNG** phải báo RỚT.
- **Tái lập đúng số đã công bố**: `MRA4−45deploy = 0,001699` ↔ `RESULT_PNL_RULER` `+0,00170` (khớp tới 1e-5)
  cho **cả 9 cặp** ⇒ thước vòng này **khớp vòng trước**, không phải số mới.
- **0/12 cặp ngoài CI ở `f = 0,006`** (CI5: `MRA4−45deploy` `[−0,00247,+0,00569]`; `MRB32−A44` `[−0,00228,+0,00870]`)
  ⇒ **alpha xếp hạng = 0 ngoài CI, bất biến theo phí**.

---

## 5. ⚠️ GIẢ ĐỊNH PHẢI KHAI (chống over-claim — bắt buộc)

1. **Neo `2,0 %/lệnh` TRÊN COIN PHÂN BIỆT là POST-HOC** (đã ghi từ `RESULT_K_SWEEP` §5): **KHÔNG** đo trên
   sổ LIVE. Bản neo trên **số VỊ THẾ `e_t`** cho `K=8` = **410,3 × 2 % = 821 %** — **vô lý** ⇒ **chỉ tỉ lệ
   giữa các `K`** đọc được. Con số `d_mean` khớp **bậc** với mốc quan sát **54–58 %** ⇒ dùng được làm
   **quy đổi**, **KHÔNG** phải đo.
2. **KHÔNG mô hình hoá**: de-dup live theo symbol · DCA nhiều chân · trần size/notional · trần gross ·
   funding. Nếu hệ thống thật **có** các thứ đó thì **bảng §2 KHÔNG mô tả hết** ⇒ **không** over-claim.
3. **`net/tick` tuyệt đối = MÔ HÌNH**, không phải equity kỳ vọng của LIVE (sim không de-dup ⇒ số VỊ THẾ
   ≠ số lệnh live; `net_tick` TĂNG theo `K` là **MÁY MÓC**).
4. **CI rộng** (±40–60 % tương đối): kết luận đúng là **"không phân biệt được"**, KHÔNG phải "`K` khác tệ".
5. Nhãn (b) là **bản bảo thủ** (WEAK `cap=0,03`, 1 leg, không funding, bỏ 6,9 % cặp) ⇒ **KHÔNG** phải PnL LIVE.

---

## 6. VIỆC BỎ + LÝ DO

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Quét `K ∈ {8,10,12,16,32}` × 3 cách áp trần 70 % × 4 mức phí | ✅ XONG (~10 s) | đúng câu hỏi vòng này |
| 2 | Kiểm bất biến `Δ` theo phí (24 cặp) | ✅ XONG, **ĐẠT** | bắt buộc PREREG §6 |
| 3 | Δ vs 2 đối chứng bắt buộc ở `f=0,006` | ✅ XONG, TRONG CI | bắt buộc §6b |
| 4 | Thêm `A44` làm đối chứng thứ 4 | ✅ XONG (chấm 16 fold từ bins có sẵn) | PREREG §6 yêu cầu 4 đối chứng |
| 5 | Build lại nhãn (b) / chạy exit engine | ⛔ BỎ | pool + sha khớp; **không cần** |
| 6 | `K > 32` (64/128) | ⛔ BỎ | pool chỉ có top-32 ⇒ phải build lại nhãn mới; ngoài ngân sách |
| 7 | Chạy Java/sim, Kaggle, train, claude-run | ⛔ BỎ | ràng buộc đề bài; 10 s tại chỗ |
| 8 | Mô hình hoá de-dup live / DCA / trần gross thật | ⛔ BỎ | ngoài phạm vi; **đã khai** ở §5 |

## 7. KẾT LUẬN (1 dòng)

**GIỮ `K = 8`**: dưới trần 70 % CỨNG, `K = 12` cho **MỨC** `net/tick` cao nhất trong dải 8–16 nhưng **KHÔNG
ngoài CI**; ở **phí 0,6 %** rổ dương rõ (BE ≈ 1,20–1,27 %/vòng) nhưng **`Δ` model-vs-model ≡ 0 bất biến
theo phí** (kiểm bằng số: lệch `0,00e+00`) ⇒ **phí không cứu được `Δ = 0`**; nếu siết trần theo **từng tick**,
`K = 8` đã bind ⇒ **size ≈ 0,83× hiện hành**.
