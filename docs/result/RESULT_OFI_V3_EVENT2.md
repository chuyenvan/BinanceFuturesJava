# RESULT_OFI_V3_EVENT2 — OFI V3 có mở được **TUẦN GATE ĐÓNG** của `G2` không? ⇒ **NO-GO**

**Ngày:** 2026-09-30 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG (offline, **0 sim / 0 train**)
**Pre-reg:** `docs/prereg/PREREG_OFI_V3_EVENT2.md` (commit `e0e73bf7`) — chốt **TRƯỚC** khi tính số; luật §3 không đổi sau khi thấy số.
**Code:** `research/analysis/ofi_v3_event2.py` · **Số thô:** `docs/result/ofi_v3_event2.json`
**Kế thừa:** `0013-giu-g2-chuyen-ofi` · `SUGGEST_DOUBLE_ENTRIES` (§1: 10/11 lever đã chặn; §3.3 hướng cấu trúc) ·
`RESULT_K_DENSITY` (burstiness là thuộc tính GATE, không của K) · `RESULT_S1_FREE_OFI_V3_MULTISEED` (PASS ứng viên) ·
`RESULT_OFI_MONEY_REORIENT` (**OFI money = FALSE**).
**KHÔNG** chạy Java/sim · **KHÔNG** chạm 2026/ONNX/LIVE/`242` · **KHÔNG** push file dữ liệu.

---

## 0. TRẢ LỜI (4 câu bắt buộc)

### (1) OFI V3 có mở được TUẦN GATE ĐÓNG không? — **KHÔNG mở được SỰ KIỆN MỚI**

`G2` @stress (`printDone` n **2509**, eq 129 642, `20210701..20251230`): **102 tuần MỞ / 132 tuần ĐÓNG** trên 234 tuần
(coverage **43,6 %**; lệnh chỉ rơi vào **152 ngày**; khe dài nhất **70,48 ngày**; 9 tuần đóng liên tiếp).
Định nghĩa tuần **bền vững** (giống hệt khi dùng `G2_BASE` n=2517).

| đo | số | đọc |
|---|---|---|
| tuần đóng có **tick OFI V3** (lưới 18 283 tick) | **125 / 132 (94,7 %)** | OFI V3 *có mặt* ở tuần đóng |
| tuần đóng có **tick `P32`** (có nhãn tiền) | **104 / 132** | đo được tiền ở tuần đóng |
| **`P32` ⊆ lưới OFI V3** | **100,0 %** | ⚠️ lưới tick OFI **nằm trong** lưới ứng viên S1 |
| **top-8 OFI nằm NGOÀI `P32`** | **0,054 %** | ⚠️ 99,95 % pick OFI là coin S1 đã có |

⇒ OFI V3 **không sinh tick ngoài lưới S1**, và **hầu như chỉ chọn lại coin S1**. Sự kiện THÊM THẬT
(ngoài pool S1) = **293 cặp / 4 năm** (206 trong tuần đóng) ⇒ ~**73 cặp/năm** — không phải nguồn sự kiện.

### (2) Các lệnh THÊM có NET > 0 **ngoài CI** (vs `random` + `noise`)? — **KHÔNG**

`net_coin = mean_leg(gross − 0,006)`; CI block-72 h, NREP 2000, seed 20260919, ×`inflate(k2)=1,1774`; Δ ghép cặp theo tick.

| nền | arm | `net_coin` (f=0,006) | Δ vs `random-8` | ngoài CI (k2)? |
|---|---|---|---|---|
| **TUẦN ĐÓNG** (3 941 tick) | `S1-8` (proxy OFI V3) | **−0,241 %** [−1,583 %, +0,825 %] | **−0,674 %** raw[−1,376,−0,028] · k2[−1,501,+0,087] | **KHÔNG** |
| tuần đóng | `random-8` | +0,433 % | — | — |
| **TUẦN MỞ** (5 716 tick) | `S1-8` | **+1,181 %** [+0,042, +2,173] | +0,346 % (trong CI) | **CÓ (DƯƠNG)** |
| tuần mở | `random-8` | +0,836 % | — | — |
| **293 entry MỚI thật** | toàn bộ | **−1,940 %** | — | KHÔNG (k2 ⊇ 0) |
| 293 entry MỚI thật | **206 cặp trong tuần đóng** | **−4,634 %** [−17,36 %, +5,69 %] | **−4,958 %** vs coin pool ngẫu nhiên cùng tick | **KHÔNG** |

**Bền vững**: dịch gốc bin 0…6 ngày ⇒ `net_coin(S1-8\|đóng) < net_coin(random-8)` ở **7/7** pha
(Δ ∈ [−0,0052, −0,0065]) ⇒ tuần đóng **nhất quán âm**, không phải nhiễu gốc-tuần.
**`noise` control: THIẾU OFFLINE** — cần `pred_ofi_noise_v2.parquet` per-`(ts,sym)`, đã xoá sau vòng tiền (bẫy cũ: noise **cùng NaN-mask**).

### (3) OFI V3 có thể là "nguồn sự kiện thứ 2" ⇒ `n` tăng bao nhiêu %? — **≈ 0 %; KHÔNG tới ×2**

Bằng chứng ĐỘC LẬP (đo được, không suy đoán): `spearman(score OFI, rank S1)` = **0,869–0,908** (candidate),
0,898–0,931 (baseline), 0,911–0,924 (noise); `meanrank_top8` = **4,09–4,32/32**; top-8 ngoài pool **0,054 %**.
⇒ OFI V3 **là S1 + 2 cột OFI**, không phải tín hiệu độc lập.
**Trần lạc quan nhất** cho "sự kiện thêm" = 293 leg/4 năm ⇒ **+293/2 509 ≈ +12 %** và **chất lượng ÂM**
(⇒ `n` hiệu dụng **0 %**). **KHÔNG có đường nào gần ×2**; mục tiêu ×2 sự kiện **vẫn bế tắc**.

### (4) KẾT LUẬN DỨT KHOÁT — **NO-GO** (cho hướng "OFI V3 = nguồn sự kiện thứ 2 mở tuần gate đóng")

| mã (luật §3 pre-reg) | kết quả |
|---|---|
| B1 `net_coin` tuần đóng > 0 | **FAIL** (−0,241 %; 7/7 pha Δ<0) |
| B2 Δ vs `random` ngoài CI **dương** | **FAIL** (âm; k2 ⊇ 0) |
| C1 293 entry MỚI ngoài CI **dương** | **FAIL** (−1,94 % toàn bộ; −4,63 % trong tuần đóng) |
| C2 độc lập ≥ 10 % | **FAIL** (0,054 %) |
| **VERDICT** | **NO-GO / NULL** |

**Giải nghịch lý "thắng edge5 nhưng money = FALSE":** OFI V3 cải thiện **thứ tự trong pool S1**
(+1,76 pp edge5) nhưng **không tạo SỰ KIỆN mới** — 99,95 % pick vẫn là coin/thời điểm S1 đã có.
Và **đúng lúc gate đóng thì xếp hạng kiểu-S1 *TỆ HƠN ngẫu nhiên*** (Δ −0,67 %/leg) ⇒ tín hiệu ≈S1
được "mở tuần" sẽ **mang net âm**, không phải net dương. Hai vòng tiền trước (FALSE) và vòng này **khớp nhau**.

**Bước tiếp tối thiểu (nếu owner vẫn muốn số THẬT, không proxy) — CHƯA CHẠY:**
1 kernel Kaggle **CPU ~5 phút, 0 quota train** đọc lại 4 output `chuyendinh/ofi-v3-ms-s{42..45}` (đã COMPLETE) và xuất
`topk_sel.parquet` = `(ts, symId, object∈{cand,base,noise}, seed, rank_in_top8)` (~**vài MB**), rồi chấm **offline**
trên cùng `label_b_pnl.parquet` (tách tuần đóng/mở + `random`). Chi phí ≈ 0; **dự báo trước: củng cố NO-GO**
(vì C2 đã chặn tiền đề). **Khuyến nghị: KHÔNG cần chạy** — trừ khi owner muốn bịt hẳn khe `noise`.

---

## 1. VIỆC BỎ + LÝ DO

| # | việc | lý do |
|---|---|---|
| 1 | Chạy Java/sim, `claude-run`, chạm `242`/2026/ONNX/LIVE/`HoldoutSeal` | ràng buộc cứng đề bài (shadow LIVE) |
| 2 | Tải lại 4 `pred_*.parquet` (~145 MB×4) để lấy điểm per-tick | `/` **95 %** (10 G free); và kết luận tiền đã chốt FALSE; thay bằng kernel nhỏ ở §0(4) |
| 3 | Đo `noise` control offline | file `pred_ofi_noise_v2.parquet` **đã xoá** ⇒ **THIẾU**, ghi rõ (không bịa) |
| 4 | Đổi `K`/phí/window, sweep/thử gate khác | ngoài pre-reg; `K_DENSITY`/`GATESCALE`/`GD92` đã đóng |
| 5 | Dùng Java gate đọc state per-tick | sim 1' cần chạy (ràng buộc 1); định nghĩa **tuần** từ `printDone` là đủ và đã kiểm bền vững |

## 2. GHI CHÚ TRUNG THỰC

1. `S1-8` là **PROXY** cho OFI V3 (hợp lệ hoá ở pre-reg §2: `meanrank_top8` 4,09–4,32; spearman 0,87–0,94; B1 0,054 %;
   và vòng tiền đã đo trực tiếp `candidate` ≈ `baseline_fresh`). Số **thật** của OFI V3 cần §0(4).
2. Phần lớn CI **chứa 0** ⇒ đọc đúng là **NULL/không dương**, không phải "đã chứng minh âm" (trừ B1 điểm ước lượng âm
   và C2 cấu trúc — hai cái này **dứt khoát**).
3. OFI V3 **chỉ có điểm trên lưới tick S1** ⇒ phép thử này là **công bằng nhất hiện có**, không phải chứng minh cho mọi hệ OFI tương lai.
4. Không có tuyên bố nào về 2026 (HOLDOUT nguyên vẹn).

## 3. FILE / ARTIFACT

- Pre-reg `docs/prereg/PREREG_OFI_V3_EVENT2.md` (`e0e73bf7`) · code `research/analysis/ofi_v3_event2.py` · số `docs/result/ofi_v3_event2.json` (5 KB).
- Nguồn đo: `gdv2-g2-stress/printDone.csv` · `featv1-b0/printDone.csv` · `ofi_v3/ms/outALL/ms_diffs_s42.parquet` ·
  `mr_kaggle/ds_mr_labels/label_b_pnl.parquet` (`sha256 1d42b7f6…`) · `ofi_v3/ofimoney/label_b_pnl_ext_reorient.parquet` · `claude_audit_0928/ofirx/step0_orient.json`.

## 4. KẾT LUẬN (1 dòng)

**OFI V3 KHÔNG phải nguồn sự kiện thứ 2**: nó *có mặt* ở 125/132 tuần gate đóng nhưng **99,95 % pick nằm trong pool S1**
(⇒ không thêm sự kiện; 293 entry thật/4 năm), các entry thêm **net âm** (−4,63 % trong tuần đóng; proxy S1-8 −0,24 %,
Δ vs random −0,67 %), và `n` tăng **≈ 0 %** (không tới ×2) ⇒ **NO-GO**, mục tiêu ×2 sự kiện **vẫn bế tắc**.
