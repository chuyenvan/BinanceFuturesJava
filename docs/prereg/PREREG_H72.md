# PREREG_H72 — ĐO Ở **HORIZON 72h** (live ranker S1): **2 THƯỚC × 3 NHÃN**

**Ngày:** 2026-09-25 · **Trạng thái:** CHỐT **TRƯỚC** khi đọc số của vòng này · **KHÔNG push** · **DEV only**.
Kế tiếp `PREREG_YCONT_4H.md` (§14 `RESULT_MODEL_RULER.md`) — **KHÔNG** thay luật cũ.

## 1. CÂU HỎI
`RESULT_MODEL_RULER` §14.7 / §12.7 G-2: **`h = 72h` N/A** vì `z[:,2]` (slot 72h) của mọi bins = **NaN 100 %**
(`docs/diag/DIAG_SCORE72H.md`). ⇒ chưa trả lời được: *model có kỹ năng ở ĐÚNG horizon 72h không*, và
*`A44` vs `A45` ở 72h thua Ở TẦNG NÀO* (4h: thua ở tầng NHÃN, `≈` ở tầng TIỀN — §14.4).

## 2. VIỆC 0 — KIỂM "RẺ TRƯỚC" (ghi kết quả TRƯỚC khi đo)
Điểm của **ranker sống (S1)** có sẵn theo `(ts, symId)` hay không?
- **CÓ** ⇒ chấm NGAY ở 72h, **KHÔNG train**. Nguồn: `/home/ubuntu/ledger/pred_s1a2x1.parquet`
  (`ts, sym, score`; `score` **thấp = tốt**), sinh bởi `research/pipeline/x1/x1_s1_save_all_folds.py`
  (16 fold `20220101..20251001`, `PURGE = 72h`, `xgb.XGBRanker(objective=rank:ndcg)` trên `rel5` của
  `g1lite`). Nhãn train của S1 **chính là `g1lite`** (`g1lite = maxFav_72h − min(0,5·maxFav_72h; 0,08)`
  nếu `maxFav_72h ≥ 0,05`, ngược lại `retEnd_72h` — `x1_ledger.py:7,44`) ⇒ S1 **là model 72h**.
  Mỗi fold OOS được dự báo bởi model **chỉ** train trên dữ liệu `< cutoff − 72h` ⇒ **đo OOS hợp lệ**.
- **KHÔNG** ⇒ phải train đầu 72h cho arm (VIỆC 1, Kaggle GPU).

## 3. BA NHÃN Ở `h = 72h` (chốt trước)
| # | `y` | thước | nguồn |
|---|---|---|---|
| (i) | **`g1lite`** | **ĐÚNG nhãn live ranker** | `maxFav_72h` pha `retEnd_72h` (công thức §2) |
| (ii) | **`retEnd_72h` net** (gross − `FEE_RT` = 0,008) | **THƯỚC TIỀN** | cột `retEnd_72h` của label `.pb` |
| (iii) | **`maxFav_72h`** | thước **CHẠM** (nhãn liên tục) | cột `maxFav_72h` |

**Lọc:** `nBars_72h >= 288` (đủ cửa sổ = 72h/15m). `ts` ∈ `[2022-01-01, 2026-01-01)` — **KHÔNG chạm 2026 /
`HoldoutSeal`**.

## 4. CHỈ SỐ (chốt trước; KHÔNG nới ngưỡng)
Bộ chính: **`rank-IC`** · **`pacc`** (pairwise `P(s_A<s_B | y_A>y_B)`, `score` thấp = tốt) ·
**`dec_mono`** · **`dec_rho`** · **`glift8`** (lift liên tục top-8 theo `y`) · **`netm8`** (mức net top-8).
Bổ sung nếu tính được: **`AUC@top8` (`auc8`)** · **`lift@8/12/16`** · **decile monotonicity**.
Công thức **dùng lại nguyên** `research/analysis/model_ruler.py::tick_metrics` (`FEE_RT = 0,008`,
`K_SEL = 8`, decile 10) — **không viết lại**, không đổi `K`, không đổi `THR`.

## 5. CI + NHIỀU PHÉP SO (chốt trước)
- **Block-72h bootstrap** (`stage2_score.block_boot_mean`, `BLOCK_H = 72`, `NREP = 2000`,
  `SEED = 20260905`), "ngoài CI" = ngoài **CẢ HAI** độ rộng (raw + đã nới).
- **Nới rộng** `inflate(k)` của `c3_rates` với **`k = 2`** (2 ứng viên cùng họ: `A44`, `V0` — như §14).
  Đo S1 (không phải so arm) vẫn in ở `k = 2` để **bảo thủ**, ghi rõ.
- **Ghép cặp trên tập tick CHUNG** giữa các nhãn/arm (không so số của 2 tập khác nhau) · in `n_tick`.

## 6. LUẬT QUYẾT ĐỊNH (chốt trước)
1. **"CÓ kỹ năng ở 72h trên thước X"** ⇔ `ic` **và** `pacc` (cùng `dec_mono`/`dec_rho` nếu cùng chiều)
   ngoài CI **cùng hướng TỐT**.
2. **"KHÔNG có tín hiệu"** ⇔ `ic ≈ 0` / `pacc ≈ 0,5` / decile phẳng, **mọi** Δ trong CI ⇒ nói **RÕ**
   "không có tín hiệu ở 72h" (KHÔNG tô hồng, **KHÔNG** đọc thành "arm tốt").
3. **"PASS RỖNG"** = `Δ ≈ 0` **vì** base 72h cao (0,39–0,46) ⇒ phải in kèm **`base` kỳ vọng** và **`Δ` thô**
   để người đọc thấy độ lớn ≈ 0 **không** phải bằng chứng GO.
4. `A44` **THUA** `A45` trên thước X ⇔ **MỌI** chỉ số quyết định của X có `Δ = A44 − A45 < 0` **và** `out_both`.
   `A44` **≈** `A45` ⇔ **KHÔNG** chỉ số nào `Δ < 0` `out_both`. Trộn ⇒ báo **TRỘN**.
5. **CẤM** lấy điểm 4h (`p4h`) *thay cho* điểm 72h rồi gọi là "cổng 72h" (DIAG_SCORE72H §7-1).
   Nếu buộc phải đo **cross-horizon** (điểm 4h × nhãn 72h — công cụ có sẵn `--label-horizon`), **phải ghi
   rõ là cross-horizon**, KHÔNG được gọi là "đầu 72h của arm".
6. **CẤM** sửa `K`/`THR`/`h`/nhãn **sau khi thấy số**. Base 72h cao hơn ⇒ Δ nhỏ hơn là **BÌNH THƯỜNG**.

## 7. DỰ ĐOÁN KHOÁ TRƯỚC (ghi TRƯỚC khi đo; đối chiếu ở RESULT)
| # | dự đoán |
|---|---|
| **Q22** | S1 (train trên `g1lite`) ở 72h trên **nhãn (i) `g1lite`**: `ic > 0` **ngoài CI** (có kỹ năng — kỳ vọng mạnh nhất). |
| **Q23** | S1 ở 72h trên **thước TIỀN (ii) `retEnd_72h` net**: `ic ≈ 0` (hoặc < 0), `pacc < 0,5` ⇒ **KHÔNG** kỹ năng tiền (tiếp nối §14.2: mọi arm 4h đều `pacc < 0,5`). |
| **Q24** | S1 ở 72h trên **(iii) `maxFav_72h`**: trung gian, `pacc > 0,5` (nền 9x: Y1 `pacc` = 0,59–0,61 ở 4h). |
| **Q25** | `base` (`g1lite`-style) ở 72h ≈ **0,39–0,46**, **cao hơn** 4h ⇒ mọi `lift@8`/`Δ` **NHỎ hơn**. |
| **Q26** | `n_tick(72h) < n_tick(4h)` (mất ~3 ngày cuối mỗi kỳ + cuối cửa sổ). |
| **Q27** | `A44` vs `A45` ở 72h (nếu train được): **vẫn** `A44 < A45` ở **tầng NHÃN**, **`≈`** ở **tầng TIỀN** (bản sao §14.4 ở horizon xa hơn). Nếu **không** train được ⇒ ghi **RÕ** là **KHÔNG ĐO ĐƯỢC**, không bịa. |

## 8. ĐỐI CHỨNG (nếu train arm ở 72h)
`retrain = A45 − 45deploy` · `nhiễu = V5 − V1`. Nếu 2 đối chứng **không** ≈ 0 ⇒ **mất chức năng**, phải báo.
`45deploy` ở 72h **đã có một phần** (`/home/ubuntu/ledger/pred_g5_net015_72h.parquet`) nhưng **chỉ POOL**
(`cand_dev_x1`, phủ theo fold lệch 3,2 %–77 % — DIAG_SCORE72H §3.1) ⇒ **KHÔNG dùng** thay full-universe;
nếu dùng phải khai là **pool-subset**.

## 9. NGOÀI PHẠM VI (ghi rõ, không suy diễn)
- **KHÔNG** chạy Java/sim trên Oracle (shadow LIVE) · **KHÔNG** train/predict trên Oracle · **KHÔNG** push.
- **KHÔNG** chạm 2026 / `HoldoutSeal` · **KHÔNG** chạm ONNX / `NUM_FEATURES` / LIVE.
- Không chạy được ⇒ **báo là KHÔNG ĐO ĐƯỢC**, ghi rõ lý do; **không** lấy số horizon khác thay thế.

## 10. LỆNH DỰ KIẾN
```
python3 -u research/analysis/h72_s1_measure.py                 # VIỆC 0 + VIỆC 2 (nhãn 72h × 3)
python3 -u research/analysis/model_ruler.py ruler --name <arm> --bins <dir> --horizon 72h --out ...
```

---

## 11. AMEND (2026-09-25, TRƯỚC khi đo 4h) — đo S1 ở `h = 4h` bằng **ĐÚNG** code/ngưỡng

VIỆC 3-(4) hỏi *"4h vs 72h: horizon nào model mạnh hơn"*. Để trả lời **không** phải đem số của 2
bảng khác nhau ra so (S1 vs arm, universe khác), tôi **thêm** một lượt đo **cùng một model S1,
cùng code (`tick_metrics`), cùng cách lọc, cùng CI**, chỉ khác `h`:

- `h = 4h`: `retEnd_4h`, `maxFav_4h`, lọc `nBars_4h >= 16` (`NB_NEED["4h"]`).
- `h = 72h`: như §3.
- **KHÔNG** đổi `K`/`THR`/`TOUCH`/nhãn/CI. **KHÔNG** nới ngưỡng.
- Nhãn (i) `g1lite` **luôn** dùng định nghĩa 72h (§2) ở **cả hai** lượt (đó là công thức nhãn của S1,
  không phải tham số của lượt đo) — ghi rõ để không so nhầm.
- Đây là **so sánh THÊM**, khai báo TRƯỚC khi có số; không dùng để đổi luật §6.

**Dự đoán Q28 (trước khi đo):** kỹ năng **nhãn** (i)/(iii) **giảm** khi `h` tăng (72h khó hơn);
kỹ năng **tiền** (ii) `≈ 0`/âm ở **cả hai** `h`.
