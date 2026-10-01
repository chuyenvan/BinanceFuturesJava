# PREREG_SHORT_PATHEXIT — SHORT: THOÁT THEO ĐƯỜNG GIÁ (khớp nhãn) vs CẮT CỨNG

Chốt: **2026-10-01**, TRƯỚC khi chạy bất kỳ phép đo mới nào của vòng này. File này commit
**TRƯỚC** mọi commit script/kết quả (đúng `docs/runbooks/AGENT_RUNBOOK.md` luật 2; sai thứ tự
commit ⇒ kết quả **VOID**). Sau khi chạy **KHÔNG sửa thiết kế** (cơ chế thoát, chi phí, chỉ số,
lưới quét, luật kết luận).

Trạng thái: **ĐANG CHỜ ĐO** (khi xong ⇒ `docs/result/RESULT_SHORT_PATHEXIT.md`).

---

## 0. Quan hệ với các vòng trước (KHÁC gì — câu hỏi owner)

Owner 2026-10-01 12:45: *"IC tăng nghĩa là nó tốt hơn — có thể **apply CHƯA KHỚP** thôi nhỉ,
hoặc có thể **logic cũ bị OVERFIT**"*.

- `RESULT_SHORT_LABEL2` (`f6a5cba2`) chốt **NO-GO** với một **MISMATCH đo lường khai báo rõ**:
  nhãn định nghĩa *"coin giảm ĐỀU (MAE ngược ≤ E)"* nhưng **đo tiền bằng CẮT CỨNG +20/+30 %**
  (cắt khi coin **spike**, không phải khi vượt E) ⇒ **thoát KHÔNG khớp nhãn**. Vòng đó tự ghi
  còn thiếu: *"THOÁT THEO ĐƯỜNG GIÁ"*.
- **Vòng này CHỈ để vá đúng lỗ đó:** giữ **NGUYÊN** feature/fold/hyperparam/label-mode/K — chỉ
  **ĐỔI CƠ CHẾ THOÁT** sang **mô phỏng trên ĐƯỜNG GIÁ 1 PHÚT** đúng như nhãn: thoát tại **MỤC
  TIÊU** hoặc **stop tại E**. Rồi so 3 kiểu thoát trên **cùng bộ pick**.

---

## 1. Ràng buộc (CỨNG)

1. **Train CHỈ trên KAGGLE**; phần đường giá = **Python offline** (stream Aerospike `kline_1m_opt`);
   **KHÔNG chạy Java/sim trên Oracle**; Kaggle không chạy ⇒ **DỪNG + báo rõ**.
2. KHÔNG chạm production/242/ONNX/LIVE; **KHÔNG sửa `.java`**.
3. KHÔNG push file dữ liệu (bins/model/1m); chỉ push `.md`/`.py`/`.json` tổng hợp.
4. **DEV ≤ 2025-12-31**; KHÔNG chạm 2026 (seal).
5. Disk `/` ~96 % ⇒ stream (KHÔNG dump 1m ra đĩa); output tool nhỏ; commit sớm + push.
6. CPU Oracle: **1 tiến trình, `nice`**, đọc tuần tự (không fan-out nhiều core) — có tiến trình khác.

---

## 2. (a) DỮ LIỆU + ĐỊNH NGHĨA **THOÁT THEO ĐƯỜNG GIÁ** (khóa TRƯỚC)

### 2.1 Pick (ứng viên SHORT) — giữ NGUYÊN mọi vòng trước
- Ma trận 45 feature selector (`g015_net_train_add.py`), 16 fold purge/OOS, NEST=400, K=**8/tick**.
- Chọn top-8 theo score mỗi tick (`r > n−8`), đúng `short_model_score.py`.
- Nhãn path-aware: `y = 1 ⇔ (retEnd_72h ≤ −thr) VÀ (maxFav_72h ≤ +E)` (`--label-mode pa`).
- **Arm khóa** (retrain trên Kaggle): `PA_t15_E10_S42`, `PA_t15_E10_S7`, và đối chứng nhãn CŨ
  `OLD_ndown_S42` (`--label-mode ndown`, thr=1.5 %). Mỗi arm LƯU `predict_wf_*.bin` (slot 3 =
  head 72h) để tải về đo (không push bins).

### 2.2 ĐƯỜNG GIÁ 1 PHÚT (nguồn + cách đọc)
- Aerospike `test.kline_1m_opt` (127.0.0.1:3222), key `YYYYMMDD-HHMM` (TZ+7), value protobuf+snappy
  `{symbol:[O,H,L,C,V]}` — **cùng nguồn** `RESULT_REVERSAL_BOUNCE` đã dùng (`raw/<sym>.f32` bản cũ
  đã bị dọn; đọc lại TRỰC TIẾP từ Aerospike, **stream, không ghi đĩa**).
- Giá vào = **close nến 1 phút tại `t`** (khớp `close(t)` của `.pb`). Path = nến `t+1 .. t+h`.
- **Không lookahead**: chỉ dùng nến đã đóng; không chạm 2026.

### 2.3 BA KIỂU THOÁT (khóa) — mọi kiểu đóng ở `t+h` nếu chưa chạm ngưỡng
| mã | cơ chế |
|---|---|
| **(i) CUT** `C` | cắt cứng khi giá TĂNG ≥ `C`: `pnl = −C` nếu `high ≥ entry·(1+C)` (nến đầu tiên), ngược lại `= −(close_h/entry − 1)`. `C ∈ {+20 %, +30 %}` (chính) + báo `+50 %,+90 %`, không cắt. |
| **(ii) LABEL-EXIT** `(thr,E)` | **khớp nhãn**: TP tại `−thr` ⇒ `pnl = +thr − cost` khi `low ≤ entry·(1−thr)`; **stop tại `+E`** ⇒ `pnl = −E − cost` khi `high ≥ entry·(1+E)`; ai chạm trước thì thoát (nến đầu tiên thỏa bất kỳ ⇒ nếu cùng nến, **ưu tiên STOP** — bảo thủ). Chưa chạm ⇒ `= −(close_h/entry−1) − cost`. `thr,E` **bằng đúng tham số nhãn của arm** (PA_t15_E10 ⇒ thr=1,5 %, E=+10 %). |
| **(iii) NOSTOP** | không stop: `= −(close_h/entry−1) − cost`. |
| **(iv) TRAIL** (biến thể khác) | trailing stop `T`: theo dõi đỉnh-lợi thấp nhất; thoát khi giá hồi từ đáy lợi `≥ T`. `T ∈ {+5 %}`. |

### 2.4 ĐỐI CHIẾU 3 KIỂU (khóa)
Câu hỏi trung tâm: **thoát theo đường giá (ii), so với cắt cứng cũ (i), có làm net DƯƠNG & BỀN
không?** Báo cả (iii) làm mốc "không can thiệp". So trên **cùng bộ pick** mỗi arm.

---

## 3. (c) CHI PHÍ (khóa — như vòng trước)

- Base **0,112 %/vòng** (`RESULT_COST_TRUTH`); stress **0,150 %**.
- **Funding**: short **TRẢ** — `δ_f = −0,585 %/72h` (`RESULT_SHORT_DEEP`). **Chính = pro-rata theo
  thời gian giữ** `δ_f·(hours/72)` (vì thoát sớm trả ít hơn); **phụ = phẳng** `−0,585 %` mọi lệnh.

---

## 4. (d) CHỈ SỐ + CI (khóa)

Trên **OOS hợp nhất 16 fold** (`2022-01 .. 2025-12-31`), join bins ↔ nhãn `.pb (ts,sym)`:
1. **Net%** mean per-tick (K=8) sau base+funding; kèm **stress**.
2. **Winrate** (tỷ lệ lệnh pnl>0) mỗi kiểu thoát.
3. **Theo năm** 2022–2025 (**đặc biệt 2023/2024**).
4. **Đuôi trái**: `p01`, `max_loss` mỗi kiểu.
5. **CI**: block-**72h** bootstrap, `NREP=2000`, `SEED=20260905`; "ngoài CI" = ngoài **raw VÀ** `×1,21`.
   Đọc trên **mean-seed** (báo per-seed).
6. **Khớp `.pb` cross-check**: so net(ii) tính bằng đường 1m vs tính bằng cực trị `.pb`
   (`maxFav/maxAdv`) trên cùng pick — lệch nhỏ ⇒ đường 1m đọc đúng.

---

## 5. (V2) LƯỚI QUÉT "OVERFIT" (khóa TRƯỚC)

Quét exit-params trên **CÙNG pick** (không retrain): `h ∈ {24, 72}`h (48h **không có** trong
`.pb`; bổ sung `12`h), `thr ∈ {1,5 %, 3 %, 7 %}`, `E ∈ {+3 %, +5 %, +10 %}` ⇒ **18 tổ hợp**.
Đếm **số tổ hợp đạt GO**; cảnh báo overfit nếu **chỉ 1** tổ hợp đẹp (không có "vùng").
(48h thiếu ⇒ ghi rõ, không nội suy.)

---

## 6. (e) LUẬT KẾT LUẬN (khóa TRƯỚC)

**GO** (đáng build đường SELL) **chỉ khi** tồn tại cấu hình thoát trong lưới §5 đạt **cả**:

| # | Điều kiện (khóa) |
|---|---|
| **A** | net(K=8) **> 0** **đã credit funding** (pro-rata), **ngoài CI** (raw **và** ×1,21), mean-seed |
| **B** | net > 0 ở **≥ 3/4 năm** (2022–2025) |

**NO-GO** nếu A hoặc B FAIL (không vùng xám). Bắt buộc báo phụ trợ: (i) net(ii) vs net(i);
(ii) 2023/2024 còn âm không; (iii) số tổ hợp đạt GO (§5); (iv) **nguyên nhân THẬT** nếu NO-GO
(không được viết "apply chưa khớp" nếu đã đo khớp).

---

## 7. VIỆC **BỎ** + lý do (ghi TRƯỚC)

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Retrain 12 arm của `sm-label2` | ⛔ BỎ | chỉ cần pick để đo thoát; ngân sách GPU (2 arm PA + 1 arm cũ) |
| 2 | Horizon 48h | ⛔ BỎ | `.pb` chỉ có 4/12/24/72h (không nội suy) |
| 3 | Gate-33 / S1-9 train riêng | ⛔ BỎ | dataset không có sẵn trên Kaggle |
| 4 | Java/sim, ONNX, production/242 | ⛔ BỎ | §1.2 |
| 5 | Push bins/model/1m | ⛔ BỎ | §1.3 |
| 6 | Sửa `.java` | ⛔ BỎ | §1.2 |
| 7 | Liquidation/intrabar tick | ⛔ BỎ | chỉ có nến 1m (O/H/L/C) |

---

## 8. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_PATHEXIT.md` | file này (commit TRƯỚC đo) |
| `research/kaggle/short_model/make_sm_pathexit_kernels.py` | sinh kernel Kaggle `sm-pathexit` (3 arm, GIỮ bins) |
| `research/analysis/short_pathexit_sim.py` | mô phỏng thoát trên đường 1m (stream Aerospike) + chấm điểm |
| `docs/result/RESULT_SHORT_PATHEXIT.md` (+`.json`) | kết quả + trả lời 4 câu |
