# PREREG_SHORT_V4 — SHORT: CHỌN COIN ĐANG **MẤT THANH KHOẢN** ⇒ GIẢM ĐỀU ⇒ **GIỮ ĐỦ LÂU**

Chốt: **2026-10-01**, TRƯỚC mọi phép đo mới của vòng này. File này commit **TRƯỚC** script/kết quả
(luật 2 `docs/runbooks/AGENT_RUNBOOK.md`; sai thứ tự commit ⇒ kết quả **VOID**). Sau khi chạy
**KHÔNG sửa thiết kế** (định nghĩa feature, cơ chế giữ, thước đo path, lưới, chỉ số, CI, luật).

Trạng thái: **ĐANG CHỜ ĐO** (xong ⇒ `docs/result/RESULT_SHORT_V4.md`).

---

## 0. Quan hệ vòng trước + STEER owner (nguyên văn)

**STEER owner 2026-10-01 06:32:** *"Chú ý cái rút ngắn giữ lệnh vì lý thuyết là chọn coin đã vào
chu kì mất thanh khoản nó sẽ giảm đều"*. ⇒ **Luận điểm V4:** chọn coin **ĐÃ VÀO CHU KÌ MẤT THANH
KHOẢN**, nó **GIẢM ĐỀU** ⇒ **GIỮ ĐỦ LÂU**. **KHÔNG** lấy "rút ngắn giữ lệnh" làm cách nề funding.

**Vòng trước (dùng làm điểm xuất phát):**
- `RESULT_SHORT_V3.md` (`06b8046d`/`e4d73e93`): nề funding **causal** (N1b) lật net −0,171 % →
  **+0,374 %/lệnh** (+0,545 pp) NHƯNG CI chứa 0 & 2/4 năm dương; **LOOKAHEAD** +0,725 %/4 năm ⇒
  funding là chi phí LỚN nhưng **không dự báo được**; winrate **bất biến 0,542–0,570**; alpha short
  **ngược chiều** "được nhận funding" (coin K1 `fund −1,268 %/72h`, gap 2,2×); rút ngắn giữ lệnh
  (N2a/N2b) **âm hơn** baseline; lọc regime **không** cứu 2023.
- `RESULT_SHORT_DEEP.md` (`90c9480e`): lỗ dồn vào pha coin TĂNG; funding là CHI PHÍ (short TRẢ).
- ⚠️ `PREREG_SHORT_LABEL2.md` (`8edf7c7b`) + code `sm-label2` **CÓ trong repo**, nhưng
  **`docs/result/RESULT_SHORT_LABEL2.md` KHÔNG tồn tại** (đã kiểm bằng `find` — xem §7). Vòng V3
  báo đúng việc này. ⇒ Nhãn path-aware per-lệnh **không đo được** (như V3 §deviation).

**Vòng này KHÁC về bản chất:** vẫn **0-sim trên cùng bins SHORT** (không đổi nhãn/feature/fold/
hyperparam — không train lại), nhưng đo **3 trụ mới** trên cùng đầu ra model:
(a) **CHỌN COIN theo LIQ = "đang mất thanh khoản"** (OI giảm) ở bước chọn;
(b) **GIỮ ĐỦ LÂU** (72 h — horizon dài nhất `.pb` có) so với giữ ngắn;
(c) **ĐỘ ĐỀU của nhịp giảm** (path: ít nhúng lên + kết gần đáy) + **dự báo funding CẢ CỬA SỔ** tại `t`.

---

## 1. Ràng buộc (CỨNG)

1. **Train CHỈ trên KAGGLE**; KHÔNG chạy Java/sim trên Oracle; Kaggle không chạy ⇒ DỪNG + báo rõ.
   Vòng này **KHÔNG train** (dùng bins có sẵn) ⇒ chỉ chấm numpy 0-sim; KHÔNG chạm `.java`.
2. KHÔNG chạm production/242/ONNX/LIVE; KHÔNG sửa `.java`.
3. KHÔNG push file dữ liệu; chỉ push `.md`/`.py`/`.json` tổng hợp.
4. **DEV ≤ 2025-12-31**; KHÔNG chạm 2026 (seal). Mọi join cắt `ts < 1767225600000`.
5. Disk `/` ~96 % ⇒ dọn temp; output tool nhỏ.
6. Commit sớm + **push**.

---

## 2. (a) FEATURE **"MẤT THANH KHOẢN"** (định nghĩa KHOÁ TRƯỚC)

**Nguồn (khoá):** `/home/ubuntu/claudedata/oi/oi_percoin_full.bin` — memmap `dtype=[("ts",">i8"),
("sym",">i2"),("oi",">f4",5)]`, grid **5 phút**, `symId` cùng không gian `symbol_map.csv`
(1..863), phủ **2021-01-01 .. 2026-06-30**, 140.924.110 dòng, 779 coin. Cột `oi`:
`[oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy]` (`OI_NAMES` trong
`research/pipeline/g015_net_train_add.py`). Join theo `key = ts*1024 + symId` (khớp cột `t` của
nhãn, bước 15 phút ⊂ 5 phút ⇒ khớp CHÍNH XÁC; thiếu ⇒ NaN).

**Hai đại lượng nguồn tại `t` (chỉ dùng thông tin ≤ t — CAUSAL):**
- `d_oi(t,sym) = oi_delta24h(t,sym)` = thay đổi OI tương đối trong `(t−24h, t]`. **Âm = OI co lại.**
- `z_oi(t,sym) = oi_z(t,sym)` = z-score OI so 20 nến trước. **Thấp = OI cạn.**

**ĐIỂM LIQ (mất thanh khoản) — KHOÁ:**
```
LIQ(t,sym) = 0,5 * z_CS(−d_oi)  +  0,5 * z_CS(−z_oi)
```
trong đó `z_CS(·)` = z-score **cross-section trong cùng tick** `t` (trên mọi coin có mặt tại `t`).
`LIQ` cao ⇒ OI vừa co nhanh vừa dưới chuẩn ⇒ **đang mất thanh khoản**. (Biến thể phụ, báo thêm:
`LIQa = z_CS(−d_oi)` chỉ OI-co; `LIQb = z_CS(−z_oi)` chỉ OI-cạn. `LIQ` là bản CHÍNH.)

**Cách dùng ở bước CHỌN (khoá):**
- **X1** (gate): chỉ giữ lệnh có `LIQ ≥ Q`, `Q ∈ {0,0 (không gate), +0,5, +1,0}` (đơn vị z).
- **X2** (ranker): trong tick, xếp hạng tổ hợp `rank(score) + rank(LIQ)` rồi lấy top-K (K ∈ {1,2,3,8}).
- Báo **IC(LIQ, −retEnd_72h)** per-tick (Spearman) + **decile net theo LIQ** để trả lời Q1.

**Khai báo giới hạn (khoá):** LIQ là **proxy OI** cho "thanh khoản"; KHÔNG có cột volume THÔ
(Tool1-15m chỉ có `f26 volumeZCoin / f27 volumeTrend` **đã nằm trong 45 feature của model**;
đọc lại T1 4 năm bị loại vì nặng I/O + trùng feature — xem §7).

---

## 3. (b) CƠ CHẾ **"GIỮ ĐỦ LÂU"** (định nghĩa KHOÁ TRƯỚC)

- Nhãn `.pb` chỉ có horizon **4/12/24/72 h** ⇒ **không có horizon > 72 h** ⇒ "giữ đủ lâu" KHOÁ =
  **T = 72 h** (mốc dài nhất đo được). Giữ ngắn = T ∈ {4, 12, 24 h}.
- **ĐO RIÊNG cả hai** (đúng steer mục 3): net(T=72) so net(T=4/12/24) trên CÙNG cấu hình chọn.
- **Không rút ngắn để nề funding** (V3 N2a/N2b đã thất bại; V4 coi đó là đối chứng âm).
- Entry: giữ **per-tick** như mọi vòng (chồng lấn), K coin/tick.

---

## 4. (c) ĐỘ ĐỀU của nhịp giảm (định nghĩa KHOÁ TRƯỚC)

Path info `.pb` tại h=72 h: `maxFav_72h ≥ 0` = **mức nhúng LÊN tệ nhất** (bất lợi SHORT);
`maxAdv_72h ≤ 0` = **mức XUỐNG sâu nhất** (có lợi SHORT); `retEnd_72h` = kết cuối.

Hai thước đo (KHOÁ):
```
bounce(t) = maxFav_72h                         # thấp = giảm đều (ít nhúng lên)
retain(t) = retEnd_72h / maxAdv_72h            # cả âm; ≈1 = kết sát đáy = giảm đều
```
- **Q3a (mô tả / EX-POST — KHÔNG tradeable vì dùng path TƯƠNG LAI):** chia lệnh theo
  `bounce ≤ median_tick(bounce)` ("đều") vs phần còn lại ("giật"); báo net/winrate mỗi nhóm ⇒
  **cận trên** của một "path predictor".
- **Q3b (CAUSAL — tradeable nếu thắng):** `S_hist(t)` = độ đều của đường giá QUÁ KHỨ, dựng từ
  chính panel nhãn tại `t−72h` (causal: `bounce_hist = maxFav_72h(t−72h)`,
  `retain_hist = retEnd_72h(t−72h)/maxAdv_72h(t−72h)`). Gate `S_hist ≤ median` (đều) → đo IC + net.

---

## 5. (d) NỀ FUNDING BẰNG **CHỌN** (không rút ngắn) + DỰ BÁO CẢ CỬA SỔ (KHOÁ)

Funding: `fund_cache.npz` (Aerospike `test.funding_data`, read-only, `ts < 2026-01-01`, 831 coin);
quy ước **rate > 0 ⇒ long TRẢ / SHORT NHẬN** (`RESULT_FUNDING_SIGN`); `f_h(t,sym)=Σ rate trong
(t, t+h]`; `pnl_funded = pnl_gross + f_h`. Credit **CHÍNH XÁC từng lệnh** (như V3).

**F1 — Lọc coin short KHÔNG phải trả (causal, tại `t`):** dùng **dự báo funding CẢ CỬA SỔ GIỮ**
(dựng từ rate QUÁ KHỨ, KHÔNG chạm tương lai):
```
F̂_72h(t,sym) = Σ_{τ ∈ diễn ra trong (t, t+72h]}  r̂(τ) ,  r̂(τ) = rate settle gần nhất TRƯỚC t
            (= trung bình 8 settle gần nhất trước t nhân số settle trong 72h — KHOÁ)
```
Cụ thể KHOÁ: `r̂ = mean(rate của 8 settle gần nhất trước t)`; số settle 72 h = 3/ngày × 3 = **9**;
`F̂_72h = 9 * r̂`. Gate **F1**: chỉ giữ lệnh `F̂_72h ≥ 0` (short KHÔNG phải trả ròng kỳ vọng).
(Đây là sửa **thiếu sót (a) của V3** — V3 chỉ dùng DẤU 1 settle kế tiếp `N1b`.)
- **Đối chứng (khoá, bắt buộc):** `N1b` (dấu 1 settle kế tiếp — như V3) và `N1a` (`f_72h ≥ 0`
  LOOKAHEAD = cận trên).

**F2 — dự báo funding vào RANKER:** trộn `F̂_72h` như hệ số phụ khi chọn K (báo thêm).

---

## 6. (e) CHỈ SỐ + CI (KHOÁ — như vòng trước)

Trên OOS 16 fold (`2022-01 .. 2025-12-31`), join bins ↔ `.pb` theo `(ts, symId)`:
1. **rank-IC** = `Spearman(score, −retEnd_72h)` per-tick rồi mean; + **IC(LIQ, −retEnd_72h)**,
   **IC(S_hist, …)**, **IC(F̂_72h, f_72h)** (kiểm dự báo funding).
2. **Decile** theo score (d0..d9): mean `retEnd_72h` + net short.
3. **net K ∈ {1,2,3,8}** per-tick: `gross = −mean(retEnd_h)`; `net = gross − cost + f_h` (tách rõ).
4. **WINRATE** = `% lệnh có pnl ròng > 0`.
5. **CUT-RATE** mỗi mức `C ∈ {+20 %, +30 %, +50 %}` + không cắt; `pnl_cut(C)=−C nếu maxFav_h ≥ C,
   ngược lại −retEnd_h`.
6. **Bền vững theo năm** 2022–2025 (đặc biệt 2023/2024).
7. **CI**: block-72h bootstrap, `NREP=2000`, `SEED=20260905`; "ngoài CI" = ngoài **raw VÀ cận
   `×1,21`**. Đọc trên **mean-seed**, báo per-seed. `k = 3` seed **{42, 7, 13}**.
8. Chi phí base **0,112 %/vòng** (`RESULT_COST_TRUTH`); stress 0,150 %.

---

## 7. LUẬT KẾT LUẬN (KHOÁ TRƯỚC)

**GO** (đáng build đường SELL) **chỉ khi tồn tại** cấu hình trong §2×§3×§4×§5 thoả **đồng thời**:

| # | Điều kiện (khoá) |
|---|---|
| **A** | net(K, `C*`, `T*`, **đã credit funding CHÍNH XÁC từng lệnh**) **> 0**, **ngoài CI** (raw **và** ×1,21), mean-seed |
| **B** | net > 0 ở **≥3/4 năm** (2022–2025) |
| **C** | **WINRATE ≥ 55 %** (mean-seed) **VÀ** ≥ baseline(K=8, không lọc) **+5 điểm %** |

**NO-GO/NULL** nếu A|B|C FAIL (không vùng xám). **Bắt buộc báo phụ trợ:**
(i) **LIQ giúp gì** — IC(LIQ) + decile + net có/không gate; (ii) **giữ đủ lâu vs giữ ngắn** (cả hai
con số T=72 vs 4/12/24); (iii) **coin đều vs giật** (Q3a cận trên + Q3b causal);
(iv) **dự báo funding cả cửa sổ** — IC + net F1 vs N1b/N1a; (v) **kết luận GO/NO-GO + còn thiếu gì CỤ THỂ**.

### 7.b VIỆC **BỎ** + lý do (ghi TRƯỚC)

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Train lại nhãn/feature/fold | ⛔ BỎ | bins còn; giữ "cùng đầu ra model" như V3; 0-sim |
| 2 | `RESULT_SHORT_LABEL2.md` (nhãn path-aware per-lệnh) | ⛔ KHÔNG có | **file KHÔNG tồn tại** trong repo (đã `find`) ⇒ không dùng làm nền |
| 3 | Rerun path-aware label PER-LEG (~4 h GPU) | ⛔ BỎ (vòng này) | ngân sách GPU + phải push dataset mới; giữ 0-sim như V3/V4 |
| 4 | Horizon giữ > 72 h | ⛔ BỎ | `.pb` chỉ có 4/12/24/72 h |
| 5 | Volume THÔ làm LIQ | ⛔ BỎ | đọc T1 4 năm nặng I/O + `volumeZCoin/volumeTrend` ĐÃ trong 45 feature |
| 6 | Liquidation / borrow cost | ⛔ BỎ | PERP, borrow = 0 |
| 7 | Tune ngưỡng sau khi thấy số | ⛔ BỎ | cấm theo luật vòng này |
| 8 | Push model/bins/dữ liệu | ⛔ BỎ | §1.3 |

---

## 8. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_V4.md` | file này (commit TRƯỚC đo) |
| `research/analysis/short_v4_score.py` | chấm 0-sim: LIQ × T × path × funding-forecast + CI + year |
| `docs/result/RESULT_SHORT_V4.md` (+`.json`) | kết quả + trả lời 5 câu |
