# PREREG_LS_TAKER — ba cột CHƯA TỪNG CHẠM: `ls_global` · `ls_toptrader` · `taker_buy`

Ngày chốt: **2026-09-24**. **Chốt TRƯỚC khi đo bất kỳ số nào.** Sau khi đo **không sửa thiết kế**;
mọi thứ không có trong file này là **post-hoc** và phải dán nhãn như vậy.

Ràng buộc thi hành: thuần **Python**; **không** Java/sim trên Oracle (shadow đang chạy); **không**
`claude-run`/Claude Code; **không push**; **không chạm HOLDOUT 2026** (mọi cửa sổ thống kê
`< 2026-01-01`). Trung gian ra file **ngoài repo** (`/tmp/ls_study/`).

Bối cảnh: `docs/RESULT_OI_STUDY.md` (commit `745d722`) đã đo **`oi_delta24h` + `oi_z`** ⇒ H1 NO-GO,
H2 NO-GO/NULL, H3 tách được thông tin nhưng **không** đề xuất lọc coin. **Ba cột `ls_global`,
`ls_toptrader`, `taker_buy` của cùng file CHƯA TỪNG được dùng** — vòng này đo đúng ba cột đó, dùng
**nguyên harness/neo đối chứng** của vòng OI để **so sánh được**.

---

## 0. BƯỚC 0 — ĐÃ xác minh schema bằng GIÁ TRỊ THẬT (không tin trí nhớ)

| mục | giá trị (in trực tiếp từ file) |
|---|---|
| đường dẫn | `/home/ubuntu/claudedata/oi/oi_percoin_full.bin` |
| sha256 | `e3887f63097299655213f8382ca7e473e126ee4d7ddf69a39658942651b305ec` ✔ khớp `OI_FIX_LOG` §3 |
| kích thước | 4 227 723 300 = **140 924 110** × **30 B**, dư **0** |
| dtype | `>i8 ts_ms`, `>i2 symId`, `>f4 ×5` — offset cột 0..4 = `ts`, `sym`, rồi 5 cột float |
| lưới | `ts % 300000 == 0` **100%**; 5 phút; `2021-01-01 00:00 → 2026-06-30 23:55 UTC` |
| thứ tự 5 cột | `oi_delta24h`, `oi_z`, `ls_global`, `ls_toptrader`, `taker_buy` |
| **scale** | **KHÔNG cần chia 1e**: `>f4` là float32 **thô** theo đơn vị tự nhiên (kiểm bằng giá trị) |
| chiều thời gian | cửa sổ ĐÃ ĐÓNG `[t−5m, t)` ⇒ **CAUSAL** (`OI_FIX_LOG` §2) |

### 0.1 Ba cột mới — thống kê thật (mẫu 8 000 000 bản ghi rải đều toàn file)

| cột | min | p01 | **p50** | p99 | max | mean | %NaN | miền giá trị |
|---|---|---|---|---|---|---|---|---|
| `ls_global` | 0,20712 | 0,45323 | **1,99335** | 5,83468 | 19,59666 | 2,15559 | **0,50%** | (0, ∞) — **ratio long/short** |
| `ls_toptrader` | 0,00000 | 0,46518 | **2,11891** | 5,65241 | 15,04860 | 2,23854 | **9,57%** | (0, ∞) — **ratio long/short** |
| `taker_buy` | 0,00000 | 0,08878 | **0,49306** | 0,90953 | 1,00000 | 0,49348 | **3,41%** | **[0, 1]** — **tỷ lệ khối lượng mua chủ động** |

- Không cột nào là **hằng số / toàn NaN** ⇒ **không bỏ cột nào**.
- Đơn vị: `ls_*` là **ratio** (p50 ≈ 2 ⇒ long nhiều hơn short), `taker_buy` là **fraction ∈ [0,1]**.
  Vì vậy factor gốc của `ls_*` đăng ký là **`log(ls_*)`** (ratio ⇒ log đối xứng); `taker_buy` dùng **mức**.

### 0.2 ⚠ PHÁT HIỆN QUAN TRỌNG NHẤT CỦA BƯỚC 0 — LỖ HỔNG DỮ LIỆU 2022

Coverage **% giá trị hữu hạn theo tháng** (đếm trên TOÀN file), 3 cột mới:

| tháng | `ls_global` | `ls_toptrader` | `taker_buy` |
|---|---|---|---|
| 2022-01 | 40,5% | **4,1%** | 4,1% |
| 2022-02 | 100,0% | **1,0%** | 1,0% |
| 2022-03 | 100,0% | **0,9%** | 0,9% |
| 2022-04 | 100,0% | **1,6%** | 1,4% |
| 2022-05 | 100,0% | 27,5% | 84,2% |
| 2022-06 | 100,0% | 64,1% | 99,8% |
| 2022-07..2022-11 | 100,0% | **~0,0-0,7%** | 100,0% |
| 2022-12 | 100,0% | 72,3% | 100,0% |
| **2023-01 → 2025-12** | **100,0%** | **100,0%** | **100,0%** |
| 2021-12 | 94,2% | 94,2% | 94,2% |

⇒ `ls_global` phủ **toàn bộ** 2021-12→2025-12. `ls_toptrader` và `taker_buy` **KHÔNG có dữ liệu
trong ~2022** (lst gần như trắng 2022-02..2022-11).
**Hệ quả thiết kế (chốt trước, KHÔNG phải phát hiện sau):** cửa sổ chính **W1 = 2023-01-01 →
2026-01-01** (3 năm, cả 3 cột phủ 100%); **KHÔNG** tái dùng IS/OOS 2022-2023/2024-2025 như vòng OI.
**IS/OOS nội bộ mới: IS = 2023-01-01..2024-12-31, OOS = 2025-01-01..2025-12-31** (phán quyết trên OOS).
`ls_global` được chạy **thêm** cửa sổ **W0 = 2022-01-01..2026-01-01** như **biến thể đã đăng ký** để
nối được với vòng OI; kết quả W0 **không** dùng để cứu kết quả W1.

### 0.3 Giá / funding (như vòng OI)
`/home/ubuntu/claudedata/rvb_1m/raw/<SYM>.f32` (`ts <i4` phút, `o,h,l,c,v <f4`), 627 symbol có mặt
trong OI. Funding: Aerospike `test/funding_data` (**chỉ ĐỌC**), tích lũy.

---

## 1. Ba giả thuyết (k = 3, KHÔNG thêm)

**Lưới cross-section: 1 GIỜ (UTC `:00`)** — y hệt vòng OI (để so sánh được). **Universe** tại mốc =
symbol có `close` **và** factor **hữu hạn** tại mốc đó; **≥ 50 symbol** (MIN_SYM). Decile/tercile =
**rank tất định**: `bin = min(rank*K // N, K-1)`. **LONG-ONLY** cho mọi phép cross-section.

### H1 — `ls_global` (tỷ lệ long/short TOÀN thị trường) như FACTOR cross-section
- Factor chính `f = log(ls_global(t))`; **Q9 = ls_global CAO NHẤT** (đám đông long nhất), Q0 = thấp nhất.
- H = **24h** (CHÍNH) từ `close(t)`; phụ 4h, 1h.
- Đo `net` từng decile + **chênh `Q_d − EW`** (universe EW cùng mốc) + câu hỏi quyết định
  **long-only: có decile nào `net > 0` sau phí, CI ngoài 0?**
- **H1-regime (đo cả chiều REGIME):** tại mỗi mốc, lấy **median cross-section** của `log(ls_global)`
  (mức "đám đông long" của cả thị trường); chia **tercile theo THỜI GIAN** (rank tất định toàn kỳ);
  đo `net` 24h của **universe EW** ở mỗi regime + tương phản `cao − thấp`.
  Đây là câu hỏi "ls_global cực trị ⇒ lọc/đứng ngoài thị trường", **cấp THỊ TRƯỜNG** (khác cấp coin).

### H2 — `ls_toptrader` (dòng tiền lớn) và **PHÂN KỲ smart-vs-retail** ← giả thuyết được kỳ vọng nhất
- Factor chính: **`div = log(ls_toptrader) − log(ls_global)`** (top trader long hơn đám đông bao nhiêu).
  Q9 = phân kỳ dương cao nhất (smart long mạnh hơn retail) ⇒ kỳ vọng forward return TỐT HƠN EW.
- Factor phụ: **`log(ls_toptrader)`** mức (dòng tiền lớn long).
- H = 24h (CHÍNH), phụ 4h cho `div`. Đo decile + `Q9 − EW` (+ `Q0 − EW` mô tả).

### H3 — `taker_buy` (áp lực mua chủ động) như OVERLAY lên MOM15 (M-LEVEL k=1)
- Event = **đúng bộ MOM15 đang chạy live**: "M-LEVEL MOM15 k=1" (`/tmp/funding_factor/pools.npz`,
  `m_min`/`m_sym`; n ALL = 11 367), HOLD 24h. Net lấy **nguyên** `m_raw[24h] − m_slip − m_fund[24h] − 0,0010`.
- Tại entry `m` tra `taker_buy` causal (bản ghi 5m gần nhất ≤ `m`, tolerance 15 phút). Giữ event **chỉ
  khi** tra được (báo %coverage).
- Tách theo **(a) mức `tak`**, **(b) rank percentile cross-section của `tak`** tại mốc giờ tương ứng.
- Đo `net` 24h theo tercile + tương phản `ter2 − ter0` + CI + null + AUC(tách thắng/thua).

### 1.4 Đăng ký TRƯỚC số ô đo (chống multiplicity)
| # | ô đo | giả thuyết |
|---|---|---|
| 1 | W1, `log(lsg)` decile `Q9−EW`, 24h | **H1 PRIMARY** |
| 2 | W1, `log(lsg)` decile `Q9−EW`, 4h | H1 |
| 3 | W1, `log(lsg)` decile `Q9−EW`, 1h | H1 |
| 4 | W1, `Δ24h log(lsg)` decile `Q9−EW`, 24h | H1 |
| 5 | W0 (2022-2025), `log(lsg)` decile `Q9−EW`, 24h | H1 |
| 6 | H1-regime: EW 24h `ter_cao − ter_thấp` | H1 |
| 7 | W1, `div` decile `Q9−EW`, 24h | **H2 PRIMARY** |
| 8 | W1, `div` decile `Q9−EW`, 4h | H2 |
| 9 | W1, `log(lst)` mức decile `Q9−EW`, 24h | H2 |
| 10 | MOM15 overlay `tak` **mức** `ter2−ter0`, 24h | **H3 PRIMARY** |
| 11 | MOM15 overlay `tak` **rank(cs)** `ter2−ter0`, 24h | H3 |
| 12 | W1, `tak` mức decile `Q9−EW` (lưới 1h), 24h | H3 |

**k_H1 = 6, k_H2 = 3, k_H3 = 3, k_tổng = 12.** Mọi ô ở trên đã chốt; **thêm bất kỳ ô nào = post-hoc**.

---

## 2. Đo lường — harness chuẩn (dùng NGUYÊN hàm của `research/analysis/oi_study.py`)

- **Chi phí CHÍNH (harness):** `net = raw − FEE_RT − SLIP − FUNDING`, `FEE_RT = 0,0010`,
  `SLIP = 0,5 × (high−low)/close` của nến 1m tại phút vào, `FUNDING` = chênh tích lũy `(t, t+H]`.
- **Chi phí BIẾN THỂ (sim):** `net = raw − 0,0080 − FUNDING`. Báo kèm, **không** dùng phán quyết.
- **CI:** block-72h bootstrap, **2000 rep, seed 20260905**, pct 2.5/97.5, nửa-độ-rộng **×1,21**,
  centered trên `obs` ⇒ `CI72h_x1.21`.
- **CI hiệu chỉnh multiplicity (DÙNG ĐỂ PHÁN QUYẾT):** `half_adj = 1,21 × √k_giả_thuyết × half`.
  (H1: ×√6 = 2,449; H2: ×√3 = 1,732; H3: ×√3 = 1,732. Báo thêm mức **toàn cục** ×√12 = 3,464.)
  Lý do: cùng một luật "√k" như tinh thần chống multiplicity của repo; **làm GO KHÓ hơn**, không dễ hơn.
- **Null:** block sign-flip 72h (`block_perm`), 2000 rep, cùng seed ⇒ `p(>=obs)`.
- **MDE:** p80 phân bố nửa-độ-rộng (×1,21) trên **500** chuỗi null sign-flip 72h; đối chiếu `2,8×sd(null)`.
  Ngưỡng phán quyết = MDE(p80). MDE cũng báo bản **×√k**.
- **N và N_eff:** `N_eff = N/(1+(n̄_b−1)·ICC72h)`.
- **Độ bền:** `%quý dương` ALL + OOS; `%năm dương`; AUC cho tercile.

## 3. Đối chứng (bắt buộc, chạy TRƯỚC khi kết luận)
- **(a) Universe equal-weight cùng kỳ** — hàng `EW` trong **mọi** bảng.
- **(b) NEO MOM15** — tái lập `net@0,10% = +1,6690%` (±0,05pp), n = **7 128** trên DEV 2022-2025
  (HOLD 24h, `m_raw[24h] − m_slip − m_fund[24h]`). **Đã tái lập trong lúc soạn pre-reg: +1,6690% ✔.**
  Lệch ⇒ báo RỎ và **KHÔNG kết luận**.

## 4. Luật kết luận (chốt trước)
Một giả thuyết **GO** chỉ khi **đồng thời**:
1. hiệu ứng **OOS (2025)** > 0 sau phí CHÍNH;
2. **`CI72h_x1.21` HIỆU CHỈNH (√k)** ngoài 0 (hai đầu cùng dấu);
3. **nhất quán ≥ 60%** số **quý OOS** có hiệu ứng > 0;
4. **bền vững qua các biến thể đã đăng ký** — H1: ≥3/5 biến thể phụ cùng dấu; H2: ≥2/2; H3: ≥2/2;
5. cỡ hiệu ứng **> MDE(p80)** đã tính.
- Với H1/H3 (long-only): nếu **không decile/tercile nào `net > 0`** ⇒ **long-only BẤT KHẢ**, nói thẳng.
- Biến thể dương mà biến thể khác không ⇒ **UNCONFIRMED (post-hoc)**. Không có hiệu ứng ⇒ **NULL**.
- **Nhắc lại bài học đã đo (ghi TRƯỚC để không tự lừa):** mọi **filter cấp-coin** trong repo này đã
  **VÔ HIỆU** (hệ lấy coin kế tiếp). ⇒ Kể cả H3/H1 dương, kết luận **"thông tin, KHÔNG đề xuất lọc coin"**,
  và bất kỳ đề xuất filter cấp-coin nào bị coi là **đã biết vô hiệu**.
- **Không tự tích hợp** bất cứ thứ gì vào hệ giao dịch. Không đề xuất short.
- Nếu **cả 5 cột** (2 cột OI + 3 cột này) đều không dùng được ⇒ **đóng trục dữ liệu OI hoàn toàn**.

## 5. Output
`docs/PREREG_LS_TAKER.md` (file này) + `docs/RESULT_LS_TAKER.md` + script
`research/analysis/ls_taker_build.py`, `research/analysis/ls_taker.py`. Commit (**KHÔNG push**), dọn `/tmp/ls_study` sau khi commit.
