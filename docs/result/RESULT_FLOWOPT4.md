# RESULT_FLOWOPT4 — Path `BIG_DOWN`/`DCA_LEVEL1` có **MỞ ĐƯỢC TUẦN GATE ĐÓNG** không? ⇒ **NO-GO / NULL**

**Ngày:** 2026-09-30 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG (offline, **0 sim / 0 train / 0 build**)
**Pre-reg:** `docs/prereg/PREREG_FLOWOPT4.md` (commit `87dfe715`) — chốt **TRƯỚC** khi chạy script quyết định; luật §4 không đổi sau khi thấy số.
**Code:** `research/analysis/flowopt4_bd_week.py` · **Số thô:** `docs/result/flowopt4.json` (8 KB)
**Nguồn:** `G2` = `/home/ubuntu/kaggle_sim/out/de-p1/storage/printDone.csv` (n **2517**, eq **131 908**, `profile_hash c47b73f3…`, `jar_sha256 7368be46…`) · robustness `gdv2-g2-stress` (n 2509) · `featv1-b0` (n 2517).
**Kế thừa:** `REVIEW_FLOW_OPT` `f3573a2e` (mục ④/H4, §1 bảng luồng) · `RESULT_K_DENSITY` (burstiness là của GATE) · `RESULT_OFI_V3_EVENT2` (cùng phương pháp, NO-GO) · `RESULT_BD_THRESHOLD_FRAGILITY` · `RESULT_SEL_BIGDOWN`.
**KHÔNG** chạm `242`/ONNX/LIVE/2026/`HoldoutSeal` · **KHÔNG** sửa `.java` · **KHÔNG** push file dữ liệu.

---

## 0. TRẢ LỜI (4 câu bắt buộc)

### (1) `BIG_DOWN`/`DCA_LEVEL1` có mở được **TUẦN GATE ĐÓNG** không? — **CÓ nhưng chỉ 8 tuần / 141 (5,7 %)**

Tuần bin 7 ngày từ `2021-07-01`, **235 tuần** trên DEV. `D1` = tuần có **0 leg `PREDICT_SYMBOL_TRADE`** (cổng chặn hết selector):
**141 tuần `D1`** (94 tuần có PREDICT; `D2` = tuần 0 leg bất kỳ = **133**).

| đo | số | đọc |
|---|---|---|
| `PATH` = `BIG_DOWN` ∪ `DCA_LEVEL1` toàn kỳ | **294 leg** (248 BD + 46 DCA) | 11,7 % của n 2517 |
| **leg `PATH` rơi vào tuần `D1`** | **17 leg / 8 tuần** (16 BD + 1 DCA) | **phủ 8/141 = 5,67 %** tuần đóng |
| `PATH` trong tuần `D2` (0 leg) | **0** | tầm thường (tuần không có leg nào) |

⇒ Cơ chế **có thật** (bypass gate ⇒ nổ được ở tuần đóng: 8 tuần), nhưng **sức mở quá nhỏ**: 5,7 % tuần đóng
so yêu cầu lấp phần lớn 141 tuần. **Δn = +17/2517 = +0,675 %** (và 17 leg này **ĐÃ NẰM TRONG `G2`** — xem §0(3)).

### (2) Các lệnh đó có **NET > 0 NGOÀI CI** không? — **KHÔNG** (`net` âm; CI chứa 0)

`net_leg = pnl/margin` (`calTp()` đã net fee + slippage×2 + funding). CI block-**72 h**, NREP 2000, seed `20260919`, ×`k2=1,177410`.

| tập | `m` | `net_leg` TB | CI95 `k2` | ngoài CI? |
|---|---|---|---|---|
| **`PATH` trong tuần `D1`** | 17 | **−0,327 %** | **[−10,53 %, +6,91 %]** | **KHÔNG** (chứa 0) |
| placebo `perm` (17 leg ngẫu nhiên từ 2517) | 2000 rep | +4,364 % (null) | null 2,5–97,5 %: [−1,77 %, +11,87 %] | **p 2 phía = 0,116** (không ý nghĩa) |
| `PATH` trong tuần **MỞ** (`B3`) | 277 | **+10,979 %** | **[+4,52 %, +14,80 %]** | **CÓ (DƯƠNG)** |

**Bền vững**: `G2S` (n 2509) và `G2B` (n 2517) cho **cùng 17 leg / 8 tuần** (`net` −0,339 % / −0,327 %) ⇒ không phải artifact của 1 lần chạy.
**Dịch gốc tuần ±1…3 ngày**: `m` = 13 / 8 / 10, `net` = +1,38 % / +4,81 % / −0,16 %, tuần phủ 6 / 4 / 5 ⇒ **dấu đổi theo gốc bin**
⇒ kết quả **KHÔNG ổn định** (đúng bằng 17 mẫu).
**Phân phối đáng chú ý:** trung vị `+5,42 %`, winrate **70,6 %** — nhưng **trung bình âm** ⇒ **1 vài leg lỗ lớn kéo âm**
(tổng `pnl` của 17 leg = **−671 USDT**). Đây là "đuôi trái", không phải "edge đều".

### (3) `n` tăng bao nhiêu %; có vượt T3/T1 không? — **+0,675 % (và là +0 THẬT vs `G2`); T3/T1 KHÔNG đo được, không tuyên bố**

- **Nghịch lý trung tâm:** 17 leg này **đã ở trong `n = 2517` của `G2`** (baseline PASS 4 tầng). Đo 0-sim **không thể**
  "thêm" sự kiện so với `G2` — cửa duy nhất để thêm là **nới ngưỡng `BIG_DOWN`**, mà `RESULT_BD_THRESHOLD_FRAGILITY`
  cho thấy PnL dao **2×** giữa 4 điểm quét và cấu hình hiện tại **đã là local max**. ⇒ **Δn hiệu dụng = 0 %**.
- **Tác động tài khoản (cận trên thô, KHÔNG phải T3):** tập `PATH`-trong-`D1` đóng góp **−671 USDT** trong khi
  **toàn bộ `PATH` đóng góp +19 944 USDT** (tổng lãi `G2` = 96 908 = 131 908 − 35 000). ⇒ các leg ở tuần đóng là **PHA LOÃNG PnL**.
- **T3/T1:** `UW`/`dd` **không đo lại được** bằng 0-sim; các leg **đã nằm trong** baseline PASS ⇒ luật pre-reg §4
  **không cho phép** tuyên bố gì về T1/T3. Không over-claim.

### (4) KẾT LUẬN DỨT KHOÁT — **NO-GO / NULL**

| mã (luật §4 pre-reg, kế thừa `REVIEW_FLOW_OPT` H4) | ngưỡng | kết quả |
|---|---|---|
| **A1** đủ sự kiện | `m ≥ 100` | **FAIL** — `m = 17` |
| **B1** `net_ev > 0` | > 0 | **FAIL** — −0,327 % |
| **B2** ngoài CI **dương** | CI95×k2 không chứa 0 & > 0 | **FAIL** — [−10,53 %, +6,91 %] chứa 0 |
| **VERDICT** | A1∧B1∧B2 | **NO-GO / NULL** |

**Bước tiếp tối thiểu (nếu owner vẫn muốn "mở tuần đóng" bằng path này) — CHƯA CHẠY:** chỉ còn 1 đường là
**nới `BIG_DOWN`** (`RESULT_BD_THRESHOLD_FRAGILITY` đã cho khung quét); nhưng **tiền đề A1 đã chặn** (path chỉ chạm
8/141 tuần) và ngưỡng brittle ⇒ **khuyến nghị KHÔNG chạy**; nếu buộc phải có số thì **1 arm sim** trên
`SIM_MIN_MOMENTUM_15M`/BD-threshold là bước rẻ nhất, dự báo trước: **vỡ T3** (đồng nhất mọi lần mở gate trước đây).

---

## 1. ĐỌC KÈM (điều 17 leg nói lên)

1. **Path KHÔNG hỏng** — nó rất tốt ở tuần MỞ: `net` **+10,98 %/leg**, CI k2 **[+4,52 %, +14,80 %]** (ngoài 0, dương).
   ⇒ **KHÔNG** được tắt path; nó là nguồn sự kiện hợp lệ.
2. **Edge của path đảo ở tuần đóng** bất kể artifact (âm/dương-0, không ngoài CI, dấu đổi theo gốc bin) ⇒
   "bypass gate" không tự mang edge; đúng như `RESULT_OFI_V3_EVENT2` (tín hiệu/nguồn hoạt động *đúng lúc gate mở*,
   *hết edge khi gate đóng*). Hai vòng độc lập **khớp nhau**.
3. **Đuôi trái:** mean âm + median dương + winrate 70,6 % ⇒ path có "vài cú lỗ lớn" ở tuần đóng ⇒ thêm loại sự kiện này
   sẽ **tăng đuôi**, đúng rủi ro mà `REVIEW_FLOW_OPT` §3-H4 đánh dấu **CAO** ("edge brittle ×2").

---

## 2. MỤC BỎ + LÝ DO

| # | việc | lý do |
|---|---|---|
| 1 | Sim/train/build/`claude-run`; chạm `242`/ONNX/LIVE/2026/`HoldoutSeal` | ràng buộc cứng đề bài |
| 2 | Dùng `java/devrun/*` | **THIẾU** — thư mục không tồn tại trong repo/box này; đã thay bằng `de-p1` + 2 artifact robustness (`gdv2-g2-stress`, `featv1-b0`), ghi rõ |
| 3 | Đo `noise` control offline kiểu OFI | **THIẾU** — không có pool nhãn tiền per-`(tick,coin)` cho tick `BIG_DOWN`; thay bằng **placebo hoán vị** (null đúng trong cùng quần thể leg) |
| 4 | Đo lại `UW`/`dd` (T3) bằng 0-sim | bất khả thi không chạy sim; pre-reg §4 chặn tuyên bố |
| 5 | Cộng thêm leg giả định để "ước" `n` mới | 17 leg đã ở trong `n`; mọi con số "nếu nới ngưỡng" là **suy đoán** ⇒ không viết |

## 3. GHI CHÚ TRUNG THỰC

1. Pre-reg viết **sau khi tác giả liếc đếm thô ban đầu**, nhưng **luật A1/B1/B2 kế thừa nguyên văn** cổng DỪNG đã chốt
   trong `REVIEW_FLOW_OPT` §3-H4 ⇒ **không tune ngưỡng sau khi thấy số** (đã nêu rõ ở đầu pre-reg).
2. `m = 17` ⇒ **mọi CI rất rộng**; đọc đúng là **NULL/không dương**, không phải "đã chứng minh âm" (trừ `pnl_sum = −671`).
3. `timeStart` = **leg-cuối của cụm** ⇒ bin tuần của cụm DCA có thể lệch biên tuần; đã kiểm bằng dịch gốc ±1…3 ngày (vẫn NO-GO).
4. Không có tuyên bố nào về 2026 (HOLDOUT nguyên vẹn).

## 4. KẾT LUẬN (1 dòng)

**Path `BIG_DOWN`/`DCA_LEVEL1` có bypass gate thật nhưng chỉ chạm 8/141 tuần gate đóng (5,67 %) với 17 leg có
`net` −0,327 % (CI k2 [−10,53 %, +6,91 %] chứa 0; placebo p=0,116; −671 USDT; dấu đổi theo gốc bin) ⇒ A1/B1/B2 đều FAIL
⇒ NO-GO/NULL** — mục tiêu "mở tuần gate đóng bằng path market-signal" **vẫn bế tắc**; nguồn sự kiện thứ 2 **vẫn cần DỮ LIỆU MỚI**.
