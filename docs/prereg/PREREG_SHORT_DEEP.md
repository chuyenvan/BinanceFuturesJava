# PREREG_SHORT_DEEP — ĐÀO SÂU model SHORT (label ngược): 2023 âm · cơ chế cắt · funding · ngưỡng label

Chốt: **2026-10-01**, TRƯỚC khi chạy bất kỳ phép đo mới nào của vòng này. File này commit
**TRƯỚC** mọi commit script/kết quả (đúng `docs/runbooks/AGENT_RUNBOOK.md` luật 2). Sau khi chạy
**KHÔNG sửa thiết kế** (định nghĩa nhãn, mức cắt, công thức phí, chỉ số, luật kết luận).

Trạng thái: **ĐANG CHỜ ĐO** (khi xong ⇒ `docs/result/RESULT_SHORT_DEEP.md`).

Owner 2026-10-01: *"do mới có bản chưa đào sâu từng phần nhỏ nên tiềm năng phải ko. Đi tiếp đi"*.

---

## 0. Quan hệ vòng trước (KHÁC gì)

- Vòng trước `docs/result/RESULT_SHORT_MODEL.md` (`a3b59757`) = **`NO-GO/NULL`**: **A PASS**
  (rank-IC `+0,0519`, 3/3 seed ngoài CI raw & ×1,21) **B FAIL** (cắt cứng +30/+50/+90 %: net
  dương ở điểm ước lượng nhưng **CI raw chứa 0** và **chỉ 2/4 năm dương**; 2023 **−0,59 %**,
  2024 **−0,11 %**; không cắt: 2023 −0,30 %, 2024 −0,37 %).
- Vòng này **KHÔNG train lại arm gốc**: **ĐÀO SÂU 4 nhánh** trên **NGUYÊN** model (cùng feature 45,
  cùng fold/purge, cùng hyperparam, cùng 3 seed `42,7,13`), chỉ **THÊM** (i) arm nhãn ngưỡng mới,
  (ii) cơ chế cắt mới, (iii) tầng **funding** cho short, (iv) phân rã 2023/2024. Định nghĩa nhãn
  gốc (`−0,015`) **giữ nguyên làm arm chính**; nhãn mới CHỈ dùng cho nhánh ④ (so ngưỡng).

---

## 1. Ràng buộc (CỨNG)

1. **Train CHỈ trên KAGGLE** (kernel GPU, dataset có sẵn); **KHÔNG** chạy Java/sim trên Oracle.
   Kaggle không chạy ⇒ **DỪNG + báo rõ**.
2. **0-sim**: mọi thứ trên repo = **đọc lại (re-scoring) offline** từ bins có sẵn + nhãn `.pb` +
   funding Aerospike. KHÔNG dựng Java sim mới. KHÔNG sửa `.java`.
3. KHÔNG chạm production/`242`/ONNX/LIVE. **KHÔNG push file dữ liệu** (bins/nhãn ở lại ngoài git).
4. **DEV ≤ 2025-12-31**; KHÔNG chạm 2026 (seal). Mọi nguồn funding/nhãn lọc `< 2026-01-01`.
5. Disk `/` ~95 % ⇒ dọn temp; **KHÔNG dùng CPU lớn trên Oracle** (có job deploy 242 đang chạy).
6. Output tool nhỏ; commit sớm + **push**.

---

## 2. DỮ LIỆU TÁI DÙNG (khoá)

| nguồn | đường dẫn | dùng cho |
|---|---|---|
| Bins dự đoán SHORT | output kernel `chuyendinh/sm-train-gpu` (`sm/SHORT{42,7,13}/predict_wf_*.bin`, slot 3 = head 72h) | ①②③④ (đọc lại) |
| Bins đối chứng LONG | `sm/LONG42/...` | đối chiếu |
| Nhãn 15m `.pb` | `/home/ubuntu/claudedata/wfo15m/label_ds_15m/funding_label_15m_*.pb` (horizon 4h/12h/24h/72h) | nhãn + time-stop |
| symbol_map | `/home/ubuntu/claudedata/kaggle_oi_stage/symbol_map.csv` | join symId |
| Funding rate | Aerospike `test.funding_data` (127.0.0.1:3222, **read-only**) | nhánh ③ |

Join bins ↔ nhãn theo key `ts*1024 + symId` (đúng quy ước `short_model_score.py`).
Lọc `nBars_72h ≥ 288` + `retEnd_72h` notna (đúng vòng trước).

---

## 3. (a) NGƯỠNG LABEL quét (nhánh ④) — KHOÁ TRƯỚC

- Ngưỡng khoá: **`t ∈ {0,010, 0,015, 0,030, 0,050}`**; nhãn `y_short = 1[retEnd_72h ≤ −t]`.
  `t*=0,015` = arm chính đã có (vòng trước), KHÔNG train lại.
- **Train mới trên Kaggle** cho `t ∈ {0,010, 0,030, 0,050}`, **3 seed {42,7,13}** (9 arm), cùng
  trainer/feature 45/fold 16/purge 72h/hyperparam. KHÔNG tune gì khác.
- Chấm mỗi arm: **rank-IC**, **top-K8 net** (không cắt, và cắt +30 %), **by-year 2022–2025**, **CI
  block-72h**, base rate, số lệnh.
- Mục đích: ngưỡng nào cho **IC mạnh + net bền** nhất (đặc biệt **2023/2024**).

---

## 4. (b) CƠ CHẾ CẮT — KHOÁ TRƯỚC

Vào short ở close nến 15m tại `t`, thoát ở `t+T`. PnL short (gross, %/notional) = `−retEnd`.
**Bất lợi của short = coin TĂNG.** Mọi mức dưới đây tính **offline từ aggregate** (KHÔNG sim Java);
đều dùng `maxFav_h` (đỉnh tăng trong cửa sổ, = bất lợi cho short) làm chỉ báo "đã chạm ngưỡng".

1. **Cắt CỨNG** `C ∈ {0,20, 0,30, 0,40, 0,50, 0,70, 0,90}`:
   `pnl(C) = −C nếu maxFav_72h ≥ C, ngược lại pnl = −retEnd_72h`.
   (Mở rộng dải vòng trước +30/+50/+90 thêm 20/40/70 — chốt TRƯỚC.)
2. **TIME-STOP** `T ∈ {12h, 24h, 48h}` (không cắt): `pnl = −retEnd_Th` (yêu cầu `nBars_Th ≥ T/15m`).
   Và **TIME-STOP + cắt cứng**: `pnl = −C nếu maxFav_Th ≥ C, ngược lại −retEnd_Th`.
3. **Cắt MỀM 2 tầng** (partial de-risk), bộ khoá `(S, C)`:
   `S ∈ {0,15, 0,20, 0,30}`, `C ∈ {0,30, 0,40, 0,50, 0,60}` với `S < C`; quy tắc:
   `pnl = −C nếu maxFav ≥ C` · `pnl = −(S+C)/2 nếu S ≤ maxFav < C` · `pnl = −retEnd` nếu `maxFav < S`.
   (Cắt mềm = giảm một nửa vị thế khi đã bất lợi `S` ⇒ thoát trung bình `−(S+C)/2`.)
4. **TRAILING (theo đường giá) — KHÔNG nhận dạng được từ aggregate** `.pb` (chỉ có `maxFav/maxAdv/
   retEnd/tHitFav/tHitAdv`, KHÔNG có đường giá giữa các mốc). ⇒ **KHÔNG đo trailing thật** ở vòng
   aggregate này; khai báo là hạn chế (muốn có phải replay đường giá = sim Java ⇒ ngoài phạm vi §1.2).
   Báo kèm **CẬN TRÊN LOOKAHEAD** (không phải cơ chế thật, chỉ để định vị tiềm năng):
   `pnl_ub(P) = +P nếu maxAdv_72h ≥ P, ngược lại −retEnd_72h` (`P ∈ {0,05, 0,10, 0,20}`), gắn nhãn rõ `UB/lookahead`.

Báo cáo mỗi mức: **net mean-seed**, **CI raw (và ×1,21)**, **theo từng năm**, **cut-rate**, **p99 &
max lỗ sau cắt**, và **so có cắt vs không cắt**.

---

## 5. (c) PHÍ SHORT — FUNDING + BORROW (KHOÁ TRƯỚC)

- **Fee + spread/impact**: giữ nguyên `RESULT_COST_TRUTH` — **base `0,112 %/vòng`**, **stress `0,150 %/vòng`**.
- **Funding (short)**: quy ước khoá `RESULT_FUNDING_SIGN`: `rate > 0` ⇒ long TRẢ ⇒ **short NHẬN**.
  Với mỗi lệnh short chọn `(sym, t_entry, T)`:
  `f_pp = 100 × Σ_{τ ∈ (t_entry, t_entry+T]} rate(sym, τ)` (%/notional);
  **PnL funding của short = `+f_pp`** (rate>0 ⇒ f_pp>0 ⇒ short nhận).
  - Báo: **% lệnh nhận** / **% lệnh trả**, **mean `f_pp` theo năm**, **phân bố** (p01/med/p99),
    và **net CÓ funding vs KHÔNG funding** (trên cùng tập chọn, cùng mức cắt tốt nhất).
  - Nguồn = Aerospike `test.funding_data`; **read-only**; settle chuẩn 8h; clip trần `|rate| ≤ 0,0075`
    báo song song (độ nhạy).
- **Borrow**: hợp đồng PERP ⇒ **borrow = 0** (không mượn spot). Khai báo rõ; không mô hình borrow spot.
- **Liquidation**: KHÔNG mô hình (ngoài dữ liệu). Mọi số short là **cận trên lạc quan** đã ghi.

---

## 6. (d) CHỈ SỐ + CI + k/seed/block (KHOÁ TRƯỚC)

Giống `PREREG_SHORT_MODEL §6`: trên **OOS hợp nhất 16 fold** (2022-01..2025-12-31), join theo `(ts,symId)`.

1. `rank-IC = Spearman(score, −retEnd_72h)` per-tick rồi mean.
2. Decile theo score trong tick: mean `retEnd_72h` + net short.
3. **Top-K = 8/tick** (giữ nguyên K của vòng trước để so được).
4. **Đuôi trái**: p99/max lỗ **trước và sau** cắt.
5. **Theo năm** 2022–2025 (dấu net) — điều kiện "bền" = **≥3/4 năm dương**; báo thêm **năm xấu nhất**.
6. **CI**: block-72h bootstrap, `NREP=2000`, `SEED=20260905`; "ngoài CI" = ngoài **cả** raw **và**
   ×1,21. **k = 3 seed** (`42,7,13`) cho mọi arm SHORT; đọc trên **mean-seed**, báo per-seed.
7. **Phân rã 2023/2024** (nhánh ①): theo **tháng & quý & năm**; theo **coin** (top coin đóng góp âm);
   theo **regime** (proxy: `retEnd_72h` của BTC cùng tick ≥ 0 = regime tăng / < 0 = regime giảm);
   theo **entry type** (bucket của `maxFav_72h` = mức bất lợi đã xảy ra; bucket của score decile).
   Mục tiêu: tách **âm do TÍN HIỆU** (chọn coin vẫn giảm) vs **âm do CẮT/PHÍ**.

---

## 7. (e) LUẬT KẾT LUẬN — "BỀN" = ? (KHOÁ TRƯỚC)

**GO** (đáng build đường SELL) **chỉ khi thoả CẢ HAI**:

| # | Điều kiện (khoá) |
|---|---|
| **A** | `rank-IC` arm chính (`t*=0,015`) > 0 **VÀ ngoài CI** (raw & ×1,21), mean-seed |
| **B2** | tồn tại cấu hình `(t, M)` — `t` ∈ ngưỡng §3, `M` ∈ cơ chế cắt §4 — sao cho **net(K=8) > 0**, **ngoài CI** (raw & ×1,21), **net > 0 ở ≥3/4 năm**, **VÀ đã credit funding** (§5) |

**NO-GO / NULL** nếu A hoặc B2 FAIL. Không vùng xám.

**Định nghĩa phụ (bắt buộc báo, không thay verdict):**
- **"2023 sửa được"** = tồn tại cấu hình `(t,M)` làm net 2023 **≥ 0** (đồng thời 2024 **≥ 0**), trong
  khi vẫn A PASS. Nếu không tồn tại ⇒ ghi rõ **2023 là điểm chết của hướng short** ở DEV.
- **Đối chiếu LONG**: giữ số vòng trước (không train lại) chỉ để so bất đối xứng.

**Nếu GO** ⇒ bước 2 tối thiểu: (i) dựng đường SELL trong sim (647–890 dòng Java, `RESULT_HEDGE_OVERLAY_A §7.1`);
(ii) kế toán margin/liquidation/borrow + chốt dấu funding cho SELL; (iii) port cơ chế cắt `M*`; (iv) parity + 1 vòng DEV.

---

## 8. VIỆC **BỎ** + lý do (ghi TRƯỚC)

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Trailing theo đường giá (path) | ⛔ BỎ | aggregate `.pb` không có path ⇒ không nhận dạng được; cần sim Java đường giá (ngoài §1.2) |
| 2 | Liquidation / margin call mô hình hoá | ⛔ BỎ | dữ liệu hiện có không mô hình được |
| 3 | Borrow spot cho short | ⛔ BỎ | arm là PERP ⇒ borrow = 0 |
| 4 | Đổi feature/hyperparam/fold/K | ⛔ BỎ | giữ nguyên để so được với vòng trước |
| 5 | Gate-33 / S1-9 train riêng | ⛔ BỎ | như vòng trước (dataset/§1.3) |
| 6 | Horizon 4h/12h/24h làm arm quyết định | ⛔ BỎ | h=72h khoá; 12/24/48h CHỈ dùng cho time-stop (§4) |

---

## 9. SẢN PHẨM

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_DEEP.md` | file này (commit TRƯỚC đo) |
| `research/analysis/short_model_deep.py` | chấm sâu offline (①②③④-eval) trên bins + nhãn + funding |
| `research/kaggle/short_model/make_sm_deep_kernels.py` | sinh kernel Kaggle train quét ngưỡng nhãn |
| `docs/result/RESULT_SHORT_DEEP.md` | kết quả + trả lời 4 câu |
| `docs/result/RESULT_SHORT_DEEP.json` | số tổng hợp (nhỏ) |
