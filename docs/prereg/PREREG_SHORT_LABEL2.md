# PREREG_SHORT_LABEL2 — SHORT: ĐỔI ĐỊNH NGHĨA NHÃN PATH-AWARE (tránh coin "pump rồi dump")

Chốt: **2026-10-01**, TRƯỚC khi chạy bất kỳ phép đo mới nào của vòng này. File này commit
**TRƯỚC** mọi commit script/kết quả (đúng `docs/runbooks/AGENT_RUNBOOK.md` luật 2; sai thứ tự
commit ⇒ kết quả **VOID**). Sau khi chạy **KHÔNG sửa thiết kế** (định nghĩa nhãn, bộ feature,
mức cắt, chi phí, chỉ số, luật kết luận).

Trạng thái: **ĐANG CHỜ ĐO** (khi xong ⇒ `docs/result/RESULT_SHORT_LABEL2.md`).

---

## 0. Quan hệ với các vòng trước (KHÁC gì)

- `RESULT_SHORT_MODEL.md` (`a3b59757`) — nhãn NGƯỢC `y=1[retEnd_72h≤−0,015]`: **A PASS**
  (rank-IC `+0,0519`) nhưng **B FAIL** (net CI chứa 0, chỉ 2/4 năm dương).
- `RESULT_SHORT_DEEP.md` (`90c9480e`) — đào sâu: chốt chết là **2023/2024 âm** + **funding short
  là CHI PHÍ** (`−0,585 %/72h`); cắt cứng không cứu được; lỗ tập trung ở **bucket `maxFav≥10 %`**
  (`−23,6 %/−32,2 %/lệnh`).
- **Vòng này KHÁC về bản chất:** không đổi feature/fold/hyperparam/threshold-hay-cơ-chế-thoát,
  mà **ĐỔI ĐỊNH NGHĨA NHÃN** để **nhìn ĐƯỜNG ĐI**: chỉ coi là tín hiệu GIẢM khi coin **giảm đủ
  sâu VÀ KHÔNG đã tăng quá mạnh** trước đó (loại "coin pump rồi dump" — loại lệnh mà SL cắt và
  funding ăn). Đây đúng câu owner: *"cần TƯ DUY CHỌN LABEL TRÁNH các coin này để model chọn ra
  coin GIẢM ĐỀU"*.

---

## 1. Ràng buộc (CỨNG)

1. **Train CHỈ trên KAGGLE**; **KHÔNG chạy Java/sim trên Oracle**; Kaggle không chạy ⇒ **DỪNG + báo rõ**.
2. KHÔNG chạm production/242/ONNX/LIVE; **KHÔNG sửa `.java`**.
3. KHÔNG push file dữ liệu; chỉ push `.md`/`.py`/`.json` tổng hợp.
4. **DEV ≤ 2025-12-31**; KHÔNG chạm 2026 (seal).
5. Disk `/` ~96 % ⇒ dọn temp; **KHÔNG dùng CPU lớn trên Oracle** (có kernel `sm-thr-sweep` đang chạy).
6. Output tool nhỏ; commit sớm + push.

---

## 2. (a) ĐỊNH NGHĨA **NHÃN PATH-AWARE** (khóa TRƯỚC)

Trên **cùng ma trận feature** (`g015_net_train_add.py`, 45 feature selector), **cùng fold / purge /
seed / hyperparam** (NEST=400), chỉ đổi **NHÃN**.

**Hai đại lượng nguồn** (từ `funding_label_*.pb`, cùng file trainer dùng; filter `nBars_72h ≥ 288`
và `ts < hi_all`; DEV `< 2026-07-01`):
- `retEnd_72h` = `close(t+72h)/close(t) − 1`. Giá vào = **close nến 15m tại `t`**.
- **`MAE_nguoc_72h` ≡ `maxFav_72h`** = `max` trên **mọi nến 15m trong `(t, t+72h]`** của
  `(high / close(t) − 1)`. Đây là **mức ĐI NGƯỢC tệ nhất của một lệnh SHORT** (coin TĂNG mạnh
  nhất trong cửa sổ), tính trên **đường giá** (đỉnh nến 1m gộp 15m — xem
  `ExportFundingLabel.updateAnchor`: `favR = hi/closeT − 1`). Đây là **thông tin path** duy nhất
  `.pb` có (cùng `maxAdv`, `tHitFav`); KHÔNG có chuỗi nến đầy đủ.

**Nhãn khóa cho arm chính (P-hard, "tránh coin pump-rồi-dump"):**

```
y = 1  ⇔  (retEnd_72h ≤ −thr)  VÀ  (maxFav_72h ≤ +E)
```

- Dòng `maxFav_72h > E` (coin **ĐÃ TĂNG quá E** trong cửa sổ) **bị LOẠI khỏi tập train** (nhãn NaN)
  — dù cuối cùng nó có giảm `≤ −thr` hay không.
- **Đối chứng (a) nhãn CŨ = `E = +∞`** ⇒ `y = 1[retEnd_72h ≤ −thr]` (đúng `--label-mode ndown`).

**Biến thể đối chiếu (b) NHÃN TRỌNG SỐ (P-soft):** giữ `y = 1[retEnd_72h ≤ −thr]` trên **mọi dòng**,
gán **trọng số mẫu**:
```
w = 1                                  nếu maxFav_72h ≤ E
w = max(0, 1 − (maxFav_72h − E)/E)     nếu maxFav_72h > E     (giảm tuyến tính → 0 tại maxFav = 2E)
```
⇒ coin "pump rồi dump" **không bị xoá hẳn** mà bị **TRỪ ĐIỂM NẶNG** (đúng chữ owner).

**Biến thể đối chiếu (c) NOISE control (P-noise):** **CÙNG mask** như arm chính (giữ đúng các dòng
`maxFav_72h ≤ E`), nhưng `y` = **Bernoulli(tỉ lệ gốc)** (seed `NOISE_SEED=20260924`) ⇒ phá tương
quan feature↔nhãn. Nếu "hiệu ứng path-aware" là THẬT thì arm thật phải **hơn hẳn** noise (Ở ĐÂY
noise cũng dùng NaN-mask y hệt ⇒ kiểm tra mask không tự tạo edge).

- Horizon khóa: **h = 72h** (giữ nguyên mọi vòng trước).
- **Không binarize kiểu `1−y_long`**; nhãn là **sự kiện giảm CÓ ĐIỀU KIỆN đường đi**.

---

## 3. (b) BỘ FEATURE (khóa — "dùng lại NGUYÊN", KHÔNG thêm feature mới)

**45 feature selector** (`extractFeatures45` = 40 cột Tool1-15m + 5 cột OI `oi_delta24h, oi_z,
ls_global, ls_toptrader, taker_buy`) — y hệt `RESULT_SHORT_MODEL`. KHÔNG sửa
`extractFeatures45`/`build_matrix`. Gate-33/S1-9 **BỎ** (như §8 vòng trước: extractor/schema
không có sẵn trên Kaggle ⇒ cần push dataset mới ⇒ vi phạm §1.3).

---

## 4. (c) LƯỚI ARM (khóa TRƯỚC) — **thr ∈ {1,5 %, 7 %} × E ∈ {+3 %, +10 %}**

| nhóm | mode | `thr` | `E` | seeds | #arm |
|---|---|---|---|---|---|
| **chính (P-hard)** | `pa` | 1,5 % , 7 % | +3 % , +10 % | 42, 7, 13 | 4×3 = **12** |
| đối chiếu (a) | `ndown` (`E=∞`) | 1,5 % | ∞ | 42, 7, 13 | **đã có** (`sm-train-gpu`) |
| đối chiếu (b) | `pw` | 1,5 % | +10 % | 42, 7, 13 | **3** |
| đối chiếu (c) | `pn` | 1,5 % | +10 % | 42, 7, 13 | **3** |

- **GIẢM so với đề bài (8 arm):** lock **2 mức E {+3 %, +10 %}** thay vì 4 mức {+3,+5,+10,+20 %},
  **lý do CPU/GPU**: kernel anh em `sm-thr-sweep` (9 arm) đang chiếm GPU; mỗi arm ~40 phút
  ⇒ 12+6 = 18 arm ≈ 12 g giờ GPU chia 2 kernel (giới hạn 12 g/kernel + quota ~30 g/tuần).
  E=+5 %/+20 % **để vòng sau** nếu lưới này có tín hiệu (ghi rõ, KHÔNG tune sau khi thấy số).
- Không tune feature/hyperparam/K/cơ-chế-thoát. K=8/tick như mọi vòng.

---

## 5. (d) MỨC **CẮT CỨNG** + CHI PHÍ (khóa — như vòng trước)

- Cắt cứng khi coin TĂNG `≥ C` (bất lợi của short): `C ∈ {+20 %, +30 %}` (chính, task yêu cầu),
  báo thêm **+50 %, +90 %** và **không cắt**.
  `pnl_cut(C) = −C` nếu `maxFav_72h ≥ C`, ngược lại `= −retEnd_72h` (XẤP XỈ cận, khai báo như cũ).
- Chi phí: **base `0,112 %/vòng`** (`RESULT_COST_TRUTH`), stress `0,150 %`.
- **Funding (credit bắt buộc theo `RESULT_SHORT_DEEP`)**: short **TRẢ** funding;
  **δ_f = −0,585 %/72h** (raw) và **−0,452 %/72h** (clip) — **trừ phẳng** mọi tick/năm (xấp xỉ;
  bản CLIP song song; caveat per-year ở `RESULT_SHORT_DEEP §2/§4`). Net sau funding = net − |δ_f|.

---

## 6. (e) CHỈ SỐ + CI (khóa — như vòng trước)

Trên **OOS hợp nhất 16 fold** (`2022-01 .. 2025-12-31`), join bins ↔ nhãn `.pb` theo `(ts, sym)`:

1. **rank-IC** = `Spearman(score, −retEnd_72h)` per-tick rồi mean (giữ NGUYÊN định nghĩa để so vòng trước).
2. **Decile** d0..d9 theo score (báo cả 10).
3. **Net K=8** per-tick: gross = `−mean(retEnd)`, net = gross − cost; + bản cắt cứng +20/+30/+50/+90.
4. **CUT-RATE** mỗi mức C = `% lệnh có maxFav_72h ≥ C` (chỉ số chính để trả lời "có tránh được coin pump không").
5. **Bền vững theo năm** 2022–2025 (đặc biệt **2023/2024** — mục tiêu là hết âm).
6. **CI**: block-72h bootstrap, `NREP=2000`, `SEED=20260905`; "ngoài CI" = ngoài **raw VÀ** `×1,21`.
   Đọc trên **mean-seed** (báo per-seed). 3 seed {42, 7, 13}.

---

## 7. LUẬT KẾT LUẬN (khóa TRƯỚC)

**GO** (đáng build đường SELL) **chỉ khi tồn tại** cấu hình path-aware `(thr, E) ∈ lưới §4`:

| # | Điều kiện (khóa) |
|---|---|
| **A** | rank-IC > 0 **ngoài CI** (raw **và** ×1,21), mean-seed, ở h=72h |
| **B** | net(K=8, `C* ∈ {+20 %, +30 %}`) **> 0**, **đã credit funding δ_f**, **ngoài CI** (raw **và** ×1,21), mean-seed, **VÀ** net > 0 ở **≥3/4 năm** (2022–2025) |

**NO-GO/NULL** nếu A hoặc B FAIL (không vùng xám). Phụ trợ **bắt buộc báo**: (i) **cut-rate** có
**GIẢM** so nhãn cũ không, (ii) **2023/2024** có hết âm không, (iii) arm P-hard vs P-noise vs P-soft.
Arm `pn` (noise) **không** được dùng để tuyên bố GO; nó chỉ là mốc "0".

---

## 8. VIỆC **BỎ** + lý do (ghi TRƯỚC)

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | `E ∈ {+5 %, +20 %}` | ⛔ BỎ (vòng này) | ngân sách GPU (§4); để vòng sau |
| 2 | Gate-33 / S1-9 train riêng | ⛔ BỎ | như vòng trước (dataset) |
| 3 | Horizon 4h/12h/24h làm arm quyết định | ⛔ BỎ | h=72h khóa |
| 4 | Time-stop / trailing đường giá / liquidation | ⛔ BỎ | `.pb` aggregate không có chuỗi path đầy đủ |
| 5 | Tune threshold/feature/hyperparam sau khi thấy số | ⛔ BỎ | cấm theo luật vòng này |
| 6 | Push model/bins/dữ liệu | ⛔ BỎ | §1.3 |

---

## 9. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_LABEL2.md` | file này (commit TRƯỚC đo) |
| `research/pipeline/g015_net_train_add.py` | thêm `--label-mode pa/pw/pn` + `--label-e` + `sample_weight` (nhánh mới, giữ nguyên hành vi cũ) |
| `research/kaggle/short_model/make_sm_label2_kernels.py` | sinh 2 kernel Kaggle `sm-label2` (12 arm chính) · `sm-label2b` (6 arm đối chiếu) |
| `research/analysis/short_model_score.py` | TÁI DÙNG NGUYÊN (rank-IC/decile/cắt cứng/cut-rate/CI/năm) |
| `docs/result/RESULT_SHORT_LABEL2.md` (+`.json`) | kết quả + trả lời 4 câu |
