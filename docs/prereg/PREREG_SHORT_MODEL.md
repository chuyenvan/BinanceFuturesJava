# PREREG_SHORT_MODEL — model RIÊNG cho SHORT: LABEL NGƯỢC + CẮT CỨNG (train trên Kaggle, 0-sim)

Chốt: **2026-09-30**, TRƯỚC khi chạy bất kỳ phép đo mới nào của vòng này. File này commit
**TRƯỚC** mọi commit script/kết quả (đúng `docs/runbooks/AGENT_RUNBOOK.md` luật 2; sai thứ tự
commit ⇒ kết quả **VOID**). Sau khi chạy **KHÔNG sửa thiết kế** (định nghĩa label, bộ feature,
mức cắt, chi phí, chỉ số, luật kết luận).

Trạng thái: **ĐANG CHỜ ĐO** (khi xong ⇒ `docs/result/RESULT_SHORT_MODEL.md`).

Owner 2026-09-30: *"nghiên cứu sâu hơn về short ⇒ thay vì ngược model, giờ dựa trên features của
cả gate, selector, s1 nhưng TRAIN với LABEL NGƯỢC rồi thử đọ như với long nhưng cần ngược lại;
và short thì cần có thêm điều kiện là coin tăng 90 % thì phải CẮT CỨNG không nó sẽ chạy, không
giống long"*.

---

## 0. Quan hệ với vòng trước (KHÁC gì)

- Vòng trước `RESULT_SHORT_FEASIBILITY.md` (`5241ba56`) = **NO-GO cho cách ĐẢO DẤU**: mirror
  lệnh long `net_short = −102 173 USDT`; đảo gate S1 (decile âm nhất −0,0898 %/24h ≫ ngưỡng
  −0,2098 %); carry `RESULT_SHORT_CARRY` (`edd1e70`), hedge `RESULT_HEDGE_OVERLAY_A` (`03c037e`),
  down-signal `RESULT_BIGUP_MEDIUPDOWN` (`5102899`) đều NO-GO/NULL.
- **Vòng này KHÁC về bản chất:** **train một MODEL RIÊNG** với **label NGƯỢC** (không đảo dấu một
  model long có sẵn), rồi **đo hướng ngược** + **mô hình CẮT CỨNG** ở các mức +30/+50/+90 %
  (chặn đuôi squeeze — rủi ro chính của short, `RESULT_ALT_REGIME_WAVES` excess kurt
  **+370/+1964/+878**; squeeze MAE p99 **+20,38 %**, max **+602 %**, ALPACA 2025-04-30).
- Bất đối xứng nhớ sẵn: long lỗ bị chặn (−100 %), **short lỗ VÔ HẠN** ⇒ cổng cắt cứng là **điều
  kiện bắt buộc** của mọi kết luận GO của vòng này.

---

## 1. Ràng buộc (CỨNG)

1. **Train CHỈ trên KAGGLE** (kernel GPU, dùng lại dataset có sẵn); **KHÔNG chạy Java/sim trên
   Oracle**; nếu Kaggle không chạy ⇒ **DỪNG và báo rõ** (không thay bằng train trên Oracle).
2. KHÔNG chạm production/242/ONNX/LIVE; **KHÔNG sửa `.java`** trong vòng này.
3. KHÔNG push file dữ liệu; chỉ push `.md`/`.py`/`.json` tổng hợp (bins/model vẫn nằm trên Kaggle).
4. **DEV ≤ 2025-12-31**; KHÔNG chạm 2026 (seal).
5. Disk `/` ~95 % ⇒ dọn temp; **KHÔNG dùng CPU lớn trên Oracle** (có tiến trình khác đang chạy).
6. Output tool nhỏ; commit sớm + push.

---

## 2. (a) ĐỊNH NGHĨA **LABEL NGƯỢC** (khóa TRƯỚC)

Trên **cùng ma trận feature** (`g015_net_train_add.py`), **cùng fold / purge / seed / hyperparam**,
chỉ đổi **NHÃN** (đối xứng gương — không đổi feature, không đổi trainer core):

| arm | nhãn | định nghĩa | ý nghĩa |
|---|---|---|---|
| **LONG** (đối chứng gương) | `y_long` | `1[ retEnd_72h ≥ +0,015 ]` | "coin TĂNG ≥ 1,5 % trong 72h" (gương của recipe x26 `NET_THR=0,015`) |
| **SHORT** (label ngược — arm chính) | `y_short` | `1[ retEnd_72h ≤ −0,015 ]` | "coin GIẢM ≥ 1,5 % trong 72h" (gương ngược chiều) |
| **SHORT-CONT** (bền vững) | `y_cont` | `−retEnd_72h` (liên tục, XGBRegressor) | kiểm tra giả thuyết "hồi quy đối xứng = flip vô nghĩa" |

- Horizon khóa: **h = 72h** cho CẢ HAI arm (§2 lý do: cửa sổ đủ dài để cú giảm/squeeze bộc lộ,
  và `.pb` có sẵn `retEnd_72h/maxFav_72h/maxAdv_72h/nBars_72h`). 24h chỉ **báo phụ**, không quyết định.
- **Không binarize ngược kiểu `1 − y_long`**: `1 − 1[ret ≥ +t]` = "KHÔNG tăng ≥ t" (gồm cả đi
  ngang) ≠ "giảm ≥ t". Nhãn khóa là **sự kiện giảm**, không phải phủ định của tăng.
- Threshold ngược khóa: `−0,015` (mirror của `+0,015`); **không tune**.

---

## 3. (b) BỘ FEATURE (khóa — "dùng lại NGUYÊN", KHÔNG thêm feature mới)

**Arm chính = 45 feature selector** (`extractFeatures45` = 40 cột Tool1-15m + 5 cột OI
`oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy`), **y hệt** ma trận mà model long production
dùng (`g015_net_train_add.py::build_matrix`, `NUM_FEATURES=45`). Đây là cùng feature **selector**.

- **Gate (33)** và **S1 (9)** KHÔNG train riêng ở vòng này — lý do ở §8 (`bỏ việc`), ghi trước.
  Gate-33 là extractor riêng (`extractFeaturesV3Full`), S1-9 là schema `feat_v2` **không có** trên
  Kaggle (đòi push dataset mới ⇒ vi phạm §1.3); vòng này chỉ dùng ma trận 45 đã có sẵn dataset.
- **KHÔNG thêm feature mới**, KHÔNG sửa `extractFeatures45`/`build_matrix`. Chỉ đổi **NHÃN**.

---

## 4. (c) MỨC **CẮT CỨNG** (khóa TRƯỚC — không chọn lại sau khi thấy số)

Với lệnh short vào ở `t` (giá entry = close nến 15m tại `t`):

- **Bất lợi của short = coin TĂNG** ⇒ cắt cứng khi coin **tăng ≥ C** so với entry.
- Mức khóa: **C ∈ {+30 %, +50 %, +90 %}** (owner đề xuất +90 %; +30/+50 là mức chặt hơn để so) —
  **và mức "KHÔNG cắt"** làm mốc đối chứng.
- Mô phỏng (offline, từ aggregate `.pb`, **KHÔNG phải sim Java**):
  `pnl_cut(C) = −C nếu maxFav_72h ≥ C, ngược lại pnl_cut = −retEnd_72h`.
  ⚠️ **XẤP XỈ có khai báo:** dùng `maxFav_72h` (đỉnh tăng trong cửa sổ) ⇒ giả định "đã cắt" khi
  đỉnh chạm C; **không** mô hình thứ tự trong nến (path) ⇒ đây là **cận** (bảo thủ về phía cắt:
  cắt sớm hơn thực tế ⇒ lỗ đúng C). Không mô hình liquidation/borrow (ngoài dữ liệu).
- Báo cáo bắt buộc mỗi mức: **số lần bị cắt / tổng lệnh (%)**, **net sau cắt**, so **có cắt vs không cắt**.

---

## 5. (d) CHI PHÍ (khóa)

- Dùng **`RESULT_COST_TRUTH`** (`docs/result/RESULT_COST_TRUTH.md`): **base `0,112 %/vòng`**
  (fee `2×0,0491 %` + spread/impact `0,0134 %/vòng`), **stress `0,150 %/vòng`**. **BỎ `legacy 0,8 %`**
  (double-count — sim đã vào ở close nến).
- **Funding: KHÔNG credit** (conservative, tránh mọi tranh cãi dấu episode — `RESULT_FUNDING_SIGN`
  2024 đổi dấu). Nếu kết luận sát 0 sẽ báo funding như **độ nhạy**, không đưa vào số chính.
- Net của lệnh short (theo notional, 1 leg, không đòn bẩy): `net = pnl − 0,112 %` (base);
  báo thêm stress.

---

## 6. (e) CHỈ SỐ + CI (khóa)

Trên **OOS hợp nhất 16 fold** (2022-01 .. 2025-12-31), join bins ↔ nhãn `.pb` theo `(ts, sym)`:

1. **rank-IC** = `Spearman(score_short, −retEnd_72h)` (score cao = kỳ vọng giảm mạnh ⇒ IC > 0 là tốt),
   tính **per-tick** rồi lấy mean; báo IC gương cho arm LONG.
2. **Decile spread**: chia **decile theo score trong mỗi tick** (d0..d9); báo **mean `retEnd_72h`**
   và **net short pnl** mỗi decile; decile "short-mạnh" (d9) phải có `retEnd` **ÂM**. Báo **cả 10 decile**
   (không chọn sau khi thấy số).
3. **Net lệnh short**: tập chọn **top-K = 8** theo score mỗi tick (gương `K_SEL=8`), net = mean
   `(−retEnd_72h − cost)`; và bản **cắt cứng** ở §4.
4. **Đuôi trái (rủi ro)**: phân bố `−retEnd_72h` của tập chọn — p99/max **trước cắt**, và **sau cắt**
   (max lỗ bị chặn đúng = C); **tỉ lệ bị cắt** mỗi mức C.
5. **Bền vững theo năm**: dấu của net/K8 ở mỗi năm 2022–2025 (yêu cầu ≥3/4 nếu tuyên bố dương).
6. **CI**: **block-72h bootstrap**, `NREP=2000`, `SEED=20260905` (đúng quy ước `c3_rates`), trên chuỗi
   **per-tick** (mean theo tick). "Ngoài CI" = ngoài **cả** CI raw **và** CI nhân hệ số legacy
   (`×1,21`, như `model_ruler.decide`). **k = 3 seed** cho arm SHORT (`42, 7, 13`); arm LONG +
   SHORT-CONT **1 seed (`42`)** — khai báo rõ; quyết định đọc trên **mean-seed** (báo per-seed).

---

## 7. LUẬT KẾT LUẬN (khóa TRƯỚC)

**GO** (có tín hiệu ⇒ đáng build đường SELL) **chỉ khi thoả CẢ HAI**:

| # | Điều kiện (khóa) |
|---|---|
| **A** | `rank-IC` của arm SHORT > 0 **VÀ ngoài CI** (raw **và** ×1,21), ở **h=72h**, trên **mean-seed** |
| **B** | tồn tại mức cắt `C* ∈ {+30, +50, +90}%` sao cho **net(K=8, C*) > 0** **VÀ ngoài CI** (raw và ×1,21) **VÀ** net > 0 ở **≥3/4 năm** (2022–2025) |

**NO-GO / NULL** nếu **A hoặc B FAIL**. **Không vùng xám** (y như `RESULT_BIGUP_MEDIUPDOWN`/
`RESULT_SHORT_FEASIBILITY`): không đề xuất build nếu chỉ "gần dương"/"dương 1 năm".

- **Đối chiếu đối xứng** (không quyết định, bắt buộc báo): so arm LONG gương cùng fold/seed —
  nếu LONG ra số dương và SHORT ra số âm **đối xứng** ⇒ xác nhận bất đối xứng (không có cửa short
  từ cùng thông tin); nếu SHORT ≈ 0/lật dấu ⇒ nêu cơ chế.
- **Nếu GO** ⇒ bước 2 tối thiểu: (i) dựng đường SELL trong sim (ước 647–890 dòng Java theo
  `RESULT_HEDGE_OVERLAY_A §7.1`); (ii) kế toán margin/liquidation/borrow + chốt dấu funding cho SELL
  (`OrderTargetInfoTest.computeFundingOnClose` còn DRAFT); (iii) cắt cứng C* port vào sim; (iv) chạy
  parity + 1 vòng DEV.

---

## 8. VIỆC **BỎ** + lý do (ghi TRƯỚC)

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | Train riêng **gate-33** (`extractFeaturesV3Full`) | ⛔ BỎ | extractor khác (không nằm trong ma trận 45 của dataset có sẵn); cần dataset mới ⇒ vi phạm §1.3; để vòng sau nếu arm 45 có tín hiệu |
| 2 | Train riêng **S1-9** (`feat_v2`) | ⛔ BỎ | schema `feat_v2` **không có** trên Kaggle; push dataset mới ⇒ vi phạm §1.3 |
| 3 | Horizon 4h/12h/24h làm arm quyết định | ⛔ BỎ | khóa h=72h (§2); 24h chỉ báo phụ |
| 4 | Mô hình liquidation/borrow/funding dấu | ⛔ BỎ | dữ liệu hiện có không mô hình được (đã ghi ở `RESULT_SHORT_FEASIBILITY §6`); funding không credit (§5) |
| 5 | Tune threshold/feature/hyperparam | ⛔ BỎ | cấm theo luật vòng này (không tune sau khi thấy số) |

---

## 9. Sản phẩm

| File | Nội dung |
|---|---|
| `docs/prereg/PREREG_SHORT_MODEL.md` | file này (commit TRƯỚC đo) |
| `research/kaggle/short_model/make_sm_kernels.py` | sinh kernel Kaggle (nhúng base64 code repo) |
| `research/analysis/short_model_score.py` | chấm điểm in-kernel (rank-IC/decile/cắt cứng/CI) |
| `docs/result/RESULT_SHORT_MODEL.md` | kết quả + trả lời 4 câu |
| `docs/result/RESULT_SHORT_MODEL.json` | số tổng hợp (nhỏ) |
