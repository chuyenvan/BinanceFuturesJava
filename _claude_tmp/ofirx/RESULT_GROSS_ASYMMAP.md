# RESULT_GROSS_ASYMMAP — Đối chiếu định nghĩa `gross` + bản đồ `asym` trên 462 artifact (0 sim)

**Ngày:** 2026-09-27 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG · **KHÔNG push**
**Pre-reg:** `docs/prereg/PREREG_GROSS_ASYMMAP.md` (commit `3f6993b`) — chốt TRƯỚC khi đo.
**Code:** `research/analysis/gross_asymmap.py` (`2d63b53`) · `gross_asymmap_report.py` · `gross_asymmap_summary.py`.
**Số thô:** `docs/result/gross_asymmap.json` (417 KB, 462 dòng) · `docs/result/gross_asymmap_summary.json`.
**Chi phí:** **0** Kaggle, **0** sim/Java, ~6 phút 1 lõi local. DEV only ≤ 2025-12-31 (0 run chạm 2026). KHÔNG chạm production/242/ONNX/LIVE.

---

## 0. TRẢ LỜI NGẮN (4 câu bắt buộc)

1. **Hai công thức `gross` CÙNG DẠNG** `100 × (%equity/lệnh) × (số vị thế đồng thời)`; lệch vì **INPUT khác**,
   không phải vì công thức. Trên **cùng artifact `cd-sel15`**, công thức CŨ (với `d` của ledger) = **1,06 % / 48,0 %**,
   công thức MỚI = **1,74 % / 49,5 %** ⇒ **khớp**. Số CŨ đã công bố (48,82 % / 84,0 %) lấy `d` từ **pool ứng viên**
   (24,409 coin đồng thời) chứ không từ ledger thật (0,531) ⇒ **lệch 28× (TB)**. **Định nghĩa dùng để hỏi "trần 70 % có bind không" là cụm LEDGER.**
2. **Kết luận cũ "`K=12` phá trần ⇒ size phải 0,83×" KHÔNG CÒN ĐÚNG**: nó dựa trên `gross_max[pool](K=8)=84 %>70 %`;
   `gross_max` THẬT của `cd-sel15` = **48–49,5 %** (và < `U_MAX=0,60`) ⇒ **trần 70 % KHÔNG bind** ở họ `cd-sel15`.
   *(Ngoại lệ có thật: **14/461** run devrun cũ vượt 70 % theo **cả hai** định nghĩa — trần bind ở **họ đó**, không phải họ này.)*
3. **PASS (a) = 3/461** (`cd-sel15-q999` 14,37 % · `gr-kg0-q998-15m` 12,91 % · `selcut-cut` 6,55 %) ·
   **PASS (b′) = 0/461** (TF50 tốt nhất = **−174 USDT**, `T2_full_c2b`) · **PASS CẢ HAI = 0/461**. *(12 run có `top1≤15` nhưng 9 cái là run LỖ ⇒ `top1_share` âm, không tính.)*
4. **`asym` thấp nhất = 0,261** (`R2_trail`, devrun) — **có 32 run `asym<1`** (30 run có ΣPnL>0), NHƯNG **tất cả** ở chế độ
   **win-rate 29–42 % + top-1 chiếm 35–96 % + TF50 < 0** ⇒ vi phạm (a) và (b′). Trong **pipeline hiện tại** (`x1_gs_t170`) `asym` min = **0,705** (`sl3-v2-sl3`, SL trước −3 %, **run LỖ**), median **3,03**. ⇒ **`asym<1` CHƯA từng tồn tại cùng lúc với PnL dương bền** (không phải "chưa thử": 32 run đã thử, đều fail 2 rào).

---

## 1. VIỆC 1 — HAI CÔNG THỨC `gross` (file:line) + BẢNG ĐỐI CHIẾU

**MỚI — `research/analysis/size_count_score.py::gross()` (def dòng 93, vòng lặp 118–131, trả về 145–146):**
```
run_m  = Σ margin của MỌI leg đang mở tại t          (margin USDT của từng vị thế, cộng dồn leg)
g(t)   = run_m / E(t)                                (E = equity NGÀY)
G_new  = 100 × Σ_t g(t)·Δt / Σ_t Δt                  (TB theo thời gian) ; G_new_max = 100 × max g(t)
```
⇒ đo **margin thực tế đang triển khai / equity**, có cộng dồn **mọi leg** (kể cả nhiều leg cùng coin).

**CŨ — `research/analysis/cap70_fee06.py` (công thức dòng 12–16; `S0 = 0.02` dòng 40; neo `gross_pct_anchor` 129–132; dùng 156–157):**
```
S0     = 0,02                                        # "2,0 %equity/lệnh" — GIẢ ĐỊNH POST-HOC
d(t)   = số COIN PHÂN BIỆT đang mở tại t             (từ pool label, drop_duplicates theo (tick,sym))
G_old  = 100 × S0 × mean_t d(t)  ;  G_old_max = 100 × S0 × max_t d(t)
```
⇒ đo **số coin đồng thời × giả định 2 %/lệnh**, KHÔNG dùng `margin` thật.

### Bảng đối chiếu trên CÙNG artifact `cd-sel15` (n=744, equity 35.000→74.362)

| định nghĩa | nguồn `d` | `S0`/`m/E` | gross TB | gross MAX |
|---|---|---|---|---|
| **`G_new`** (MỚI) | ledger `cd-sel15` (margin thật, mọi leg) | `m/E` thật (~2,0–4,3 %) | **1,74 %** | **49,53 %** |
| **`G_old[ledger]`** (CŨ, nhưng `d` từ ledger) | ledger: `d_mean=0,531`, `d_max=24` | 2,0 % | **1,06 %** | **48,00 %** |
| **`G_old[pool]`** (CŨ, ĐÃ CÔNG BỐ) | pool P32 top-8: `d_mean=24,409`, `d_max=42` | 2,0 % | **48,82 %** | **84,00 %** |
| `G_old[pool]` @ `K=12` | pool top-12: `d_mean=33,692`, `d_max=53` | 2,0 % | 67,38 % | 106,00 % |

- **Hai dòng đầu KHỚP** (TB 1,06 vs 1,74 %; MAX 48,0 vs 49,5 %) ⇒ **cùng một công thức**; chênh TB nhỏ vì `m/E` thật
  (~2,0–4,3 %, TB ~3,3 % khi mở) > neo `S0=2,0 %` (tỷ số 1,64× — đúng bằng `G_new/G_old[ledger]`).
- **Vì sao lệch ~25–50×:** `d_mean[pool] / d_mean[ledger] = 24,409 / 0,531 = ` **46,0×** (TB); `48,82/1,06 = 46,0×`
  (đúng bằng tỷ số `d`); còn `48,82/1,74 = ` **28,0×** (46,0 ÷ 1,64). `MAX` chỉ lệch `84/49,5 = 1,70×` vì **đỉnh** đồng thời
  của ledger (`d_max=24`) ≈ đỉnh pool (`42`), khác biệt nằm ở **TB**: pool giả định **luôn có ~24 coin mở**,
  ledger thật **phần lớn thời gian KHÔNG có vị thế nào** (`coin_mean=0,531`).
- **Kết luận dứt khoát:** cụm ledgers đúng cho câu hỏi "trần 70 % có bind không" ⇒ **KHÔNG bind** ở `cd-sel15`
  (`max 49,5 % < 60 % = U_MAX < 70 %`); con số 84 % là của **kịch bản lấp đầy toàn bộ ứng viên top-K** (không phải vị thế thật).
  ⇒ **"size 0,83×" là hệ quả của neo pool ⇒ BỎ.** (Sim còn tự chặn ở `U_MAX=0,60` — `RESULT_SIZE_COUNT`.)

---

## 2. VIỆC 2 — RE-SCORE 462 ARTIFACT (0 sim)

**Phủ:** 462 run dir có `printDone.csv`+`sim.out` = **361 `java/devrun`** (cửa sổ 2022-01→2024-06) + **101 `kaggle_sim/out`** (2021-07→2025-12).
**Chấm được 461**; **THIẾU 1**: `cc-g92` (không có cột `profit` ⇒ `no_legs`).

### 2.1 RÀO (a)/(b′) + bộ thước (toàn bộ)

| chỉ tiêu | số run |
|---|---|
| PASS **(a)** `%top-1 ≤ 15` **và** ΣPnL>0 | **3** |
| PASS **(b′)** bỏ top-50 % ⇒ ΣPnL>0 (`TF50>0`) | **0** (TF50 max = −174 USDT) |
| PASS **CẢ HAI** | **0** |
| `asym < 1` | 32 (30 có ΣPnL>0) |
| `asym` median | 3,06 |

### 2.2 BẢNG XẾP HẠNG `asym` (thấp → cao; (a)/(b′) FAIL gần như toàn bộ)

| # | tag | root | n | asym | sign% | %top-1 | TF50 | (a) | (b′) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | R2_trail | devrun | 1907 | **0,261** | 29,2 | 73,9 | −309 | FAIL | FAIL |
| 2 | R2f_trail | devrun | 1907 | 0,329 | 29,0 | 96,3 | −351 | FAIL | FAIL |
| 3 | A6_ts96 | devrun | 1837 | 0,424 | 36,1 | 51,0 | −38.337 | FAIL | FAIL |
| … | S3_ts168 / A2_nobigdown / D1_full_ts / A5_tierflat | devrun | ~1800 | 0,43–0,45 | 37 | 42–52 | ≪0 | FAIL | FAIL |
| — | **sl3-v2-sl3** | kaggle | 3021 | **0,705** | 38,2 | <0 (LỖ) | −70.724 | FAIL | FAIL |
| — | sl3-v4-sl7 | kaggle | 2013 | 1,269 | 58,3 | 151 (LỖ) | −84.271 | FAIL | FAIL |
| — | gb-r1 | kaggle | 1071 | 1,366 | 75,6 | 26,1 | −42.413 | FAIL | FAIL |
| — | **cd-sel15** (base) | kaggle | 744 | **3,38** | 88,4 | 19,1 | −17.551 | FAIL | FAIL |
| — | v2_d1 | devrun | 2240 | 0,510 | 33,8 | âm (LỖ) | −59.836 | FAIL | FAIL |

*(32 run `asym<1` **đều** nằm ở nhóm sign% 29–42 %.)*

### 2.3 BẢN ĐỒ `asym` THEO CẤU TRÚC

| trục (số liệu) | nhóm | n | `asym` min | `asym` median | (a) |
|---|---|---|---|---|---|
| **win-rate `sign%`** | ≤ 45 % | 32 | **0,261** | **0,453** | 0 |
| | 45–65 % | 3 | 1,269 | 1,491 | 0 |
| | 65–80 % | 20 | 1,366 | 2,830 | 0 |
| | > 80 % | 406 | 1,793 | 3,077 | 3 |
| **cắt lỗ trước (`SIM_PRE_ARM_SL`, pipeline `x1_gs_t170`)** | OFF (`sl3-base`) | — | 3,077 | 3,077 | 0 |
| | **−3 %** (`sl3-v2-sl3`) | — | **0,705** | 0,705 | 0 (LỖ) |
| | −3 % + TP 3 % (`sl3-v3-both`) | — | 1,563 | 1,563 | 0 (LỖ) |
| | −7 % (`sl3-v4-sl7`) | — | 1,269 | 1,269 | 0 (LỖ) |
| **time-stop** | `LOSER_TIME_STOP=0` (`xs-a1/a2/a3`) | 3 | 1,793 | 2,046 | 0 |
| **`K` (kaggle)** | 3 / 8 / 16 / 32 | | 3,42 / **0,705** / 3,09 / 2,78 | | |
| **loss_mean** (nhịp phân vị) | ít âm nhất | 92 | **0,261** | 2,654 | 9 |

**Cấu trúc kéo `asym` xuống (theo số):** (1) **win-rate thấp 29–42 %** (chế độ "ít thắng, thắng to") → `asym` 0,26–0,53;
(2) **cắt lỗ trước/ngắn** (`SIM_PRE_ARM_SL=−0,03`, hold ~14′) → `asym` 0,71; (3) **`loss_mean` nhỏ** — tương quan
`asym ~ loss_mean` **−0,47**, `asym ~ sign%` **+0,25**. Nhưng **cả 3 kênh đều đẩy (a)/(b′) FAIL**.
**Limits:** (i) devrun & kaggle khác cửa sổ và khác thế hệ code ⇒ bản đồ, không nhân–quả; (ii) `asym` là tỷ số nội run
nên so được dù đơn vị `pnl` khác nhau; (iii) **grid vs reactive DCA: THIẾU** metadata (mọi run `multi_leg_frac≈0`), không suy diễn.

---

## 3. ĐỀ XUẤT 3 GIÁ TRỊ CHƯA TỪNG THỬ (để không đốt sim vô ích)

Knob đã thử: `SIM_PRE_ARM_SL ∈ {−0,03; −0,07}` · `SIM_LOSER_TIME_STOP_HOURS ∈ {0; 96; 120}` · `TS_GIVEBACK_RATIO ∈ {1;2;5}` · `K ∈ {3;8;16;32}`.

1. **`SIM_PRE_ARM_SL = −0,05`** trên base `x1_gs_t170` K=8 — điểm giữa của thang cắt-lỗ (đã thử −0,03 **chết PnL**, OFF `asym` 3,08) ⇒ tìm sweet spot `asym` vs PnL. **CHƯA THỬ.**
2. **`SIM_PRE_ARM_SL = −0,03` + `SELECTOR_RANK_TOPK = 16`** — kết hợp CHƯA TỪNG có: cắt `asym` (kênh SL) **+** sửa tập trung (a) (kênh K). Mọi `sl3-*` hiện chạy K=8.
3. **`SIM_LOSER_TIME_STOP_HOURS = 8`** (giữ SL mặc định) — time-box lỗ thay vì cắt cứng; đã thử 0/96/120, **chưa thử dải ngắn 2–48 h**.

## 4. MỤC BỎ + LÝ DO

- **Tách "grid vs reactive DCA":** không có metadata tách được (mọi `multi_leg_frac≈0`, devrun thiếu profile) ⇒ ghi **THIẾU**, không suy diễn.
- **CI block-72h / inflate(k)** cho (a)/(b′) và 4 thước: đây là **đại lượng tổng toàn chuỗi** (không phải ước lượng mẫu) ⇒ bỏ để giữ output nhỏ; chỉ báo điểm.
- **`G_old[pool]` cho mọi run:** chỉ có **1** file pool label ⇒ chỉ đối chiếu được trên `cd-sel15`; các run khác dùng `G_old[ledger]` (cùng dữ liệu, đã chứng minh tương đương).
