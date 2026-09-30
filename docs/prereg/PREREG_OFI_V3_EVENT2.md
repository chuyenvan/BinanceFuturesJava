# PREREG_OFI_V3_EVENT2 — OFI V3 như **NGUỒN SỰ KIỆN THỨ 2**: có mở được TUẦN GATE ĐÓNG không?

**Ngày:** 2026-09-30 · **Nhánh:** `module` · **Trạng thái:** CHỐT **TRƯỚC** khi tính bất kỳ số quyết định nào.
**Kế thừa (bối cảnh, KHÔNG đọc lại số):** `docs/decisions/0013-giu-g2-chuyen-ofi.md` ·
`docs/plan/SUGGEST_DOUBLE_ENTRIES.md` (`8c0cd751`) · `docs/result/RESULT_K_DENSITY.md` ·
`docs/RESULT_S1_FREE_OFI_V3_MULTISEED.md` · `docs/result/RESULT_OFI_MONEY_REORIENT.md` ·
`docs/plan/RESULT_DOUBLE_ENTRIES.md` (`60384406`).
**Ràng buộc:** 0 sim / 0 train trên Oracle · DEV ≤ 2025-12-31 · không chạm 2026/ONLY/LIVE/`242` ·
không push file dữ liệu · `df -h /` ~93 % ⇒ output nhỏ.

---

## 0. CÂU HỎI (1 câu) + VÌ SAO CHỈ CÒN CỬA NÀY

Mọi lever **CONFIG** đã cạn cho mục tiêu ×2 `n` (`SUGGEST_DOUBLE_ENTRIES` §0–§1, trần 1,83× và vỡ T3;
`RESULT_K_DENSITY`: coverage tuần **33,8 %** và gap dài nhất **129,24 ngày BẤT BIẾN** ở K=8/12/16
⇒ *burstiness là thuộc tính của GATE, không của K*; `RESULT_CAPACITY_DIAG`: **0/1644 ngày chạm trần**
⇒ thiếu **SỰ KIỆN**, không thiếu chỗ). Cửa duy nhất còn lại: **nguồn sự kiện thứ 2 = OFI V3**.

> **Câu hỏi:** OFI V3 có **sinh được sự kiện/entry MỚI trong TUẦN GATE ĐÓNG** của `G2`, và các entry
> thêm đó có **NET > 0 ngoài CI** (so `random` + `noise`) không?

⚠️ **Nghịch lý phải giải:** OFI V3 **THẮNG edge5** (multi-seed pooled Δedge5 **+1,76 pp**, CI [+0,005009,+0,031524])
NHƯNG **OFI money = FALSE** ở **cả 2 đường** (`RESULT_OFI_MONEY_REORIENT`). Đó là mâu thuẫn
"kỹ năng XẾP HẠNG ≠ kỹ năng TIỀN". Vòng này hỏi **ô còn trống**: **mở được TUẦN GATE ĐÓNG**.

---

## 1. ĐỐI TƯỢNG + NGUỒN (chốt cứng, ghi sha)

| tên | nguồn | dùng để |
|---|---|---|
| **`G2`** | `/home/ubuntu/kaggle_sim/out/gdv2-g2-stress/storage/printDone.csv` (n **2509**, eq 129642, `20210701..20251230`, profile_hash `c14f79e28079ccb8`) | định nghĩa **TUẦN GATE ĐÓNG** (cột `start`) |
| **`G2_BASE`** (đối chứng định nghĩa tuần) | `/home/ubuntu/kaggle_sim/out/featv1-b0/storage/printDone.csv` (n 2517) | kiểm bền vững định nghĩa tuần |
| **lưới tick OFI V3** | index `ms_diffs_s42.parquet` (`/home/ubuntu/ofi_v3/ms/outALL/`) — **18 283 tick** (giờ, :27–:29) | phủ tick của mọi biến thể OFI V3 |
| **pool `P32` + nhãn tiền** | `/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet` (309 024 dòng = **9 657 tick × 32**, `sha256 1d42b7f6…`) | nhãn `gross` của MỌI (tick, coin) trong pool S1-top-32 |
| **entry OFI V3 THÊM THẬT** | `/home/ubuntu/ofi_v3/ofimoney/label_b_pnl_ext_reorient.parquet` (293 dòng, `ORIENT=−1`) | các cặp `(ts,sym)` **NGOÀI `P32`** (entry thật sự MỚI) |
| **định danh OFI ≈ S1** | `/home/ubuntu/claude_audit_0928/ofirx/step0_orient.json`; `ofi_money_reorient.json` (`B1_topk_outside_p32`) | đo ĐỘC LẬP |

**Nhãn tiền:** `gross` = PnL luật thoát (arm +7 %/ratchet/WEAK 0,03/TS 168 h, 1 leg, không funding).
**Phí quyết định:** `f = 0,006`/vòng. **K = 8** (K vận hành). **neo size** `s0 = 0,02` (chỉ dùng nếu cần).

---

## 2. ĐỊNH NGHĨA (chốt trước)

- **Tuần**: bin 7 ngày kể từ `2021-07-01` ⇒ **234 tuần** trên DEV.
- **TUẦN GATE ĐÓNG** = tuần có **0 lệnh `G2`** (cột `start`). Còn lại = **TUẦN GATE MỞ**.
- **Sự kiện OFI V3** = một **leg** `(tick, coin)` **trong `P32`**; chỉ ở hạt này OFI V3 có **đồng thời**
  dự đoán *và* nhãn tiền. Tick **ngoài `P32`** ⇒ thuộc nhóm **`NEW`** (entry thật sự mới, file 293 dòng).
- **arm `S1-8` (PROXY cho OFI V3)**: mỗi tick lấy **top-8 theo `rank`** của pool (`rank < 8`).
  *Lý do hợp lệ hoá (đo được, không suy đoán):* `meanrank_top8` của OFI V3 = **4,09–4,32**/32 (baseline 3,95–4,25);
  `spearman(score_OFI, rank)` = **0,88–0,93**; `B1` = **99,95 %** top-8 OFI **nằm TRONG `P32`**;
  và `RESULT_OFI_MONEY_REORIENT` đã đo trực tiếp `candidate` ≈ `baseline_fresh` (`Δnet` trong CI).
- **đối chứng `random-8`**: mỗi tick bốc **8 coin ngẫu nhiên** trong 32 (RNG seed **20260930**).
- **đối chứng `noise`**: *yêu cầu đề bài*; **KHÔNG có offline** (cần `pred_ofi_noise_v2.parquet` per-`(ts,sym)`
  đã xoá) ⇒ **ghi rõ THIẾU**, đề xuất bước Kaggle (§5).
- **Chỉ số quyết định**: `net_coin = mean_leg(gross − f)`; `Δ` = **ghép cặp theo tick**; CI block-**72 h**,
  NREP **2000**, seed **20260919**, nhân `inflate(k=2) = 1,177410` (`c3_rates`/`stage2_score`, KHÔNG viết lại).

---

## 3. LUẬT KẾT LUẬN (chốt TRƯỚC, không đổi sau khi thấy số)

| mã | tiêu chí | ngưỡng |
|---|---|---|
| **A1** (phủ) | số **TUẦN GATE ĐÓNG** có ≥1 **tick OFI V3** / tổng tuần đóng | báo cáo số; **ĐẠT** nếu ≥ 25 % |
| **A2** (phủ, mạnh) | số tuần đóng có ≥1 tick **`P32`** (⇒ có leg tiền để đo) | báo cáo số; **ĐẠT** nếu ≥ 20 tuần |
| **B1** (chất lượng) | `net_coin` arm `S1-8` **trong tuần đóng** (f=0,006) | phải **> 0** |
| **B2** (ngoài CI vs random) | `Δnet_coin`(đóng: `S1-8` − `random-8`) | CI95×`k2` **không chứa 0** và **DƯƠNG** |
| **B3** (ngoài CI vs random nền MỞ) | `Δnet_coin`(`S1-8` nền ĐÓNG − `S1-8` nền MỞ) | báo cáo (đo "tuần đóng có bị bào mòn không") |
| **C1** (entry THÊM thật) | `NEW` 293 cặp: `gross` trung bình + CI block-72h | phải **> 0 ngoài CI** |
| **C2** (độc lập cấu trúc) | `spearman(OFI,S1)`; `%` top-8 OFI **ngoài `P32`** | ≥ 10 % coi là "nguồn độc lập" |

**VERDICT**: **GO** ⟺ **B2 ĐẠT** **VÀ** **C1 ĐẠT** (tức *thêm entry trong tuần đóng có net dương ngoài CI* **và**
*entry ngoài pool S1 có net dương ngoài CI*) **VÀ** **C2 ≥ 10 %**.
Ngược lại ⇒ **NO-GO/NULL** (nói thẳng). **A1/A2/A3/B1/B3** là số mô tả, không tự đủ để GO.

**Khai báo trước về giới hạn (KHÔNG over-claim):**
1. OFI V3 artifact **chỉ có điểm trên lưới tick S1** (`P32 ⊆ lưới OFI 100 %`) ⇒ **về mặt cấu trúc không thể**
   sinh sự kiện ở thời điểm S1 không có ứng viên. Đây là **phép thử công bằng nhất hiện có**, không phải chứng minh mọi hệ OFI.
2. `noise` offline **THIẾU** ⇒ mọi tiêu chí "ngoài CI" ở đây so **random**; phần `noise` ghi **THIẾU** (§5).
3. `S1-8` là **PROXY** cho OFI V3 (đã hợp lệ hoá §2); số **thật** của OFI V3 trong tuần đóng cần lại 4 file `pred_*`.

---

## 4. KHÔNG làm (chốt trước)

KHÔNG sim/Java · KHÔNG train/lại kernel · KHÔNG chạm 2026/`242`/ONNX/LIVE · KHÔNG đổi luật sau khi thấy số ·
KHÔNG tune K/fee/window · KHÔNG push `.parquet`.

## 5. BƯỚC KAGGLE TỐI THIỂU (chỉ ĐỀ XUẤT — chưa chạy)

Nếu cần số **THẬT** của OFI V3 trong tuần đóng: 1 kernel **CPU ~5 phút, 0 quota train** đọc lại 4 output
`chuyendinh/ofi-v3-ms-s{42..45}` (đã COMPLETE) và xuất **`topk_sel.parquet`** = `(ts, symId, object∈{cand,base,noise}, seed, rank_in_top8)`
(~4×77k dòng ≈ **vài MB**), rồi chấm offline trên cùng `label_b_pnl.parquet`. Đây là bước **duy nhất** bù được
`noise` + số thật.
