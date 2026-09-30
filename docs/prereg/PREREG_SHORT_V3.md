# PREREG_SHORT_V3 — SHORT: NỀ FUNDING + TĂNG WINRATE

Chốt: **2026-10-01**, TRƯỚC khi chạy bất kỳ phép đo mới nào của vòng này. File này commit
**TRƯỚC** mọi commit script/kết quả (đúng `docs/runbooks/AGENT_RUNBOOK.md` luật 2; sai thứ tự
commit ⇒ kết quả **VOID**). Sau khi chạy **KHÔNG sửa thiết kế** (định nghĩa nề funding, cách tăng
winrate, lưới biến thể, chỉ số, CI, luật kết luận).

Trạng thái: **ĐANG CHỜ ĐO** (khi xong ⇒ `docs/result/RESULT_SHORT_V3.md`).

---

## 0. Quan hệ với các vòng trước (KHÁC gì)

- `RESULT_SHORT_MODEL.md` (`a3b59757`): nhãn NGƯỢC `ndown`; **A PASS** (rank-IC `+0,0519`,
  3/3 seed ngoài CI) nhưng **B FAIL** (net CI chứa 0, chỉ 2/4 năm dương; 2023 −0,59 %).
- `RESULT_SHORT_DEEP.md` (`90c9480e`): short **TRẢ** funding (mean **−0,585 %/72h** raw;
  −0,452 %/72h clip; 62,6 % kỳ NHẬN / 36,6 % kỳ TRẢ). Credit thẳng ⇒ lật net về ÂM. Lỗ tập trung
  ở **regime thị trường TĂNG** (2023 Q1 −1,81 %; 2024 Q1 −1,76 %; regime up −4,53 %/lệnh); cắt
  cứng +20/+30 % là tốt nhất nhưng CI chưa 0.
- `RESULT_SHORT_LABEL2.md` (`3c7b1422`): nhãn PATH-AWARE `pa` (loại dòng coin đã tăng > E) giảm
  cut-rate (78 %→46 %) nhưng **B vẫn FAIL**: 0/4 năm dương **sau funding**.
- **Vòng này KHÁC về bản chất:** KHÔNG đổi nhãn/feature/fold/hyperparam. Thay vào đó, trên **cùng
  đầu ra model** đã có, ta **NỀ (neutralise) FUNDING** bằng bộ LỌC/mô hình-hoá funding ở bước CHỌN
  lệnh và bước GIỮ, rồi đo lại **NET + WINRATE**. Đúng 2 câu owner: *"nề CA FUNDING"* và
  *"tìm phương pháp TĂNG WINRATE"*.

---

## 1. Ràng buộc (CỨNG)

1. **Train CHỈ trên KAGGLE**; **KHÔNG chạy Java/sim trên Oracle**; Kaggle không chạy ⇒ **DỪNG + báo rõ**.
   Vòng này **KHÔNG train mới** (bins có sẵn) ⇒ chỉ chấm điểm 0-sim, **không** đụng Java.
2. KHÔNG chạm production/242/ONNX/LIVE; **KHÔNG sửa `.java`**.
3. KHÔNG push file dữ liệu; chỉ push `.md`/`.py`/`.json` tổng hợp.
4. **DEV ≤ 2025-12-31**; KHÔNG chạm 2026 (seal).
5. Disk `/` ~96 % ⇒ dọn temp; output tool nhỏ.
6. Commit sớm + **push**.

---

## 2. (a) ĐỊNH NGHĨA **"NỀ FUNDING"** (khóa TRƯỚC)

**Nguồn funding (khóa):** `/tmp/fund_cache.npz` — scan Aerospike `test.funding_data` (read-only,
0-sim, ts < 2026-01-01), 831 coin. Quy ước **rate > 0 ⇒ long TRẢ / SHORT NHẬN** (`RESULT_FUNDING_SIGN`).
Với lệnh short mở tại `t`, giữ `h`: `f_h(t,sym) = Σ rate(sym, τ) với τ ∈ (t, t+h]`.
P&L short **có funding**: `pnl_funded = pnl_gross + f_h` (`f_h>0` = short ĐƯỢC nhận). Credit **CHÍNH XÁC
từng lệnh** (không dùng hằng số phẳng như vòng LABEL2).

**Biến thể nề (khóa, đo CẢ 3):**

| # | tên | định nghĩa (khóa) |
|---|---|---|
| **N1a** | **Lọc theo DẤU funding cả cửa sổ** | chỉ giữ lệnh short có `f_72h ≥ 0` (short KHÔNG trả ròng trong 72h); báo **tần suất bị lọc** + net/số lệnh trước–sau |
| **N1b** | **Lọc theo DẤU kỳ kế tiếp** | chỉ giữ lệnh có `rate` của **settle kế tiếp sau `t`** `≥ 0` (biết trước tại `t`); báo tần suất + net |
| **N2a** | **Time-stop ngắn** | giữ `T ∈ {4h, 12h, 24h, 72h}`, `pnl = −retEnd_Th` (nhãn `retEnd_Th` có sẵn: 4/12/24/72h) + `f_Th` |
| **N2b** | **Settle-aware entry** | chỉ vào lệnh nếu **settle kế tiếp cách `t` > H** (H = horizon giữ) ⇒ **KHÔNG cắt ngang mốc funding**; báo tần suất tránh được |
| **N3** | **Funding vào FEATURE** | **BỎ mới — lý do:** 45 feature selector ĐÃ chứa `f17 coinFundingRate, f18 basketFundingAvg, f19 fundingRateAvg24H, f20 fundingRateTrend, f21 fundingPercentileCoin, f22 fundingZCoin, f23 fundingPersistence, f24 fundingSum24h, f25 fundingAbs` (thứ tự `ExportFeaturesForPythonTool.convertFeaturesToArray`). Không có biến thể feature MỚI hợp lệ ⇒ chỉ **kiểm tra lại model ĐÃ dùng funding** (báo hệ số/IC phụ) |

- **Chi phí:** base **0,112 %/vòng** (`RESULT_COST_TRUTH`), stress 0,150 %.
- **Không** đổi feature/fold/hyperparam/nhãn. Nhãn gốc = `ndown thr 1,5 %` (bins vòng
  `RESULT_SHORT_MODEL`), 3 seed {42, 7, 13}.

---

## 3. (b) ĐỊNH NGHĨA **"TĂNG WINRATE"** (khóa TRƯỚC)

**WINRATE** (khóa): `% số LỆNH có pnl ròng > 0`, pnl ròng = `−retEnd_h` (cắt cứng nếu áp) **− cost
+ f_h`. Báo ở mean-seed + per-seed.

Ba đòn (khóa, đo từng đòn + tổ hợp):

| # | tên | định nghĩa (khóa) |
|---|---|---|
| **P1** | **Chọn TINH (precision)** | mỗi tick chỉ lấy **K ∈ {1, 2, 3, 8}** coin có score cao nhất (K=8 = baseline) |
| **P2** | **Lọc REGIME** | chỉ giao dịch khi thị trường **KHÔNG tăng**, dùng **2 thước đo backward (không lookahead)**: (i) `btc_back72_t` = `retEnd_72h` của BTC tại `t−72h` (tức lợi suất BTC trong `(t−72h, t]`); (ii) `breadth_t` = tỉ lệ coin có `retEnd_72h(t−72h) > 0`. **Gate:** `btc_back72_t ≤ 0` **VÀ** `breadth_t ≤ 0,5` |
| **P3** | **Exit** | cắt cứng `C ∈ {+20 %, +30 %, +50 %}` (từ `maxFav_72h`) × time-stop `T ∈ {4, 12, 24, 72h}` |

`pnl_cut(C,T) = −C nếu maxFav_Th ≥ C, ngược lại −retEnd_Th`.

---

## 4. Nguồn bins (khóa TRƯỚC) + giới hạn

- **Bins SHORT (ndown, 3 seed {42,7,13})** của kernel Kaggle `chuyendinh/sm-train-gpu`
  (`PREREG_SHORT_MODEL`), tải về `/tmp/smv3/sm/SHORT{42,7,13}/predict_wf_*.bin` (16 fold OOS
  2022-01..2025-12). Đây là **cùng model** đã cho `RESULT_SHORT_MODEL/DEEP`.
- **Bins PATH-AWARE (pa)**: kernel `sm-label2` **tự xoá bins sau khi chấm** ⇒ KHÔNG còn để chấm lại
  per-lệnh. Vì vậy **"path-aware + nề funding"** chỉ đo được ở **mức aggregate** từ
  `sm_label2_score.json` (credit funding): dùng làm **phụ trợ**, KHÔNG dùng để tuyên bố GO.
- KHÔNG train lại trong vòng này (tiết kiệm GPU; 2 kernel `sm-thr-sweep`/`sm-label2` đang chạy).

---

## 5. (d) CHỈ SỐ + CI (khóa — như các vòng trước)

Trên **OOS hợp nhất 16 fold** (`2022-01 .. 2025-12-31`), join bins ↔ nhãn `.pb` theo `(ts, symId)`:

1. **rank-IC** = `Spearman(score, −retEnd_72h)` per-tick rồi mean (giữ nguyên để so vòng trước).
2. **Net K ∈ {1,2,3,8}** per-tick: gross = `−mean(retEnd_h)`, net = gross − cost **+ funding**
   (bản CHƯA và ĐÃ credit funding, tách rõ).
3. **WINRATE** (§3) cho mọi cấu hình.
4. **CUT-RATE** mỗi mức C.
5. **Bền vững theo năm** 2022–2025 (đặc biệt **2023/2024** — mục tiêu hết âm).
6. **CI**: block-72h bootstrap, `NREP=2000`, `SEED=20260905`; "ngoài CI" = ngoài **raw VÀ** `×1,21`.
   Đọc trên **mean-seed** (báo per-seed).
7. **0-sim**, `k = 3` seed, `K = 8/tick` trừ khi đổi theo P1.

---

## 6. LUẬT KẾT LUẬN (khóa TRƯỚC)

**GO** (đáng build đường SELL) **chỉ khi tồn tại** cấu hình trong §2×§3 (bất kỳ tổ hợp
`{N1a,N1b,N2a,N2b} × {K} × {regime}` × `C`) thoả **đồng thời**:

| # | Điều kiện (khóa) |
|---|---|
| **A** | net(K, `C*`, **đã credit funding CHÍNH XÁC từng lệnh**) **> 0**, **ngoài CI** (raw **và** ×1,21), mean-seed |
| **B** | net > 0 ở **≥3/4 năm** (2022–2025) |
| **C** | **WINRATE ≥ 55 %** (mean-seed) **VÀ** ≥ baseline(K=8, không lọc) **+5 điểm %** |

**NO-GO/NULL** nếu A hoặc B hoặc C FAIL (không vùng xám). **Bắt buộc báo phụ trợ:**
(i) **nề funding giúp bao nhiêu** — net trước/sau (số cụ thể, cả N1a/N1b/N2a/N2b);
(ii) **winrate tăng bao nhiêu** và bằng đòn nào (P1/P2/P3);
(iii) **2023/2024 có hết âm không** (nhờ lọc regime);
(iv) kết luận GO/NO-GO + **còn thiếu gì CỤ THỂ**.

---

## 7. VIỆC **BỎ** + lý do (ghi TRƯỚC)

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Train lại nhãn/feature mới | ⛔ BỎ | bins còn; GPU đang bận; vòng này chủ đích là "nề funding + winrate" trên model hiện có |
| 2 | Funding-as-feature (N3) | ⛔ BỎ | funding ĐÃ nằm trong 45 feature (§2) |
| 3 | Path-aware + nề funding **per-lệnh** | ⛔ BỎ (chỉ aggregate) | bins `pa` đã bị xoá trên Kaggle (§4) |
| 4 | Time-stop < 4h | ⛔ BỎ | nhãn ngắn nhất là 4h |
| 5 | Liquidation / borrow cost | ⛔ BỎ | PERP, borrow = 0; không mô hình liquidation |
| 6 | Tune ngưỡng sau khi thấy số | ⛔ BỎ | cấm theo luật vòng này |
| 7 | Push model/bins/dữ liệu | ⛔ BỎ | §1.3 |

---

## 8. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_V3.md` | file này (commit TRƯỚC đo) |
| `research/analysis/short_v3_score.py` | chấm 0-sim: N1a/N1b/N2a/N2b + P1/P2/P3 + WINRATE + CI + year |
| `docs/result/RESULT_SHORT_V3.md` (+`.json`) | kết quả + trả lời 4 câu |
