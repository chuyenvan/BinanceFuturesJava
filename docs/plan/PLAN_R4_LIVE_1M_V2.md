# PLAN — R4 LIVE 1' V2: THIẾT KẾ ĐƯỜNG LIVE KHÔNG LÀM LỆCH S1 (KHÔNG deploy)

> **AMENDMENT 2026-09-29 (B5, commit `617a973`): MASTER chốt PHƯƠNG ÁN A (đồng bộ, giữ parity tuyệt đối)
> THAY B (async).** Lý do: B4 (`876250e`) OI cache + BatchRead + recent đưa 1 lượt live steady
> ~250ms (parity 60/60), nên async full-universe 15' + gate 1' KHÔNG còn cần — và B5 (`RESULT_PASS_SPEED_V2`)
> xác nhận funding predict ~52ms (232s cũ là OI IO, B4 đã bỏ). Phần §3 dưới đây (đề xuất B + variant B-trễ)
> GIỮ NGUYÊN làm lịch sử lập luận, KHÔNG còn là phương án chọn. Deploy theo A: xem `PLAN_DEPLOY_R4_1M_V3.md`.

Trạng thái: **THIẾT KẾ (chưa deploy)** · 2026-09-29 · branch `module` · KHÔNG push code live.
Bối cảnh: **B2 STOP đúng** — cascade (`ENTRY_CASCADE`) cắt tập rank xuống `SELECTOR_RANK_TOPK=16 < S1 min 20`
⇒ chỉ 10/16 top-16 thật còn lại (`0264816` FAIL + rollback). **MASTER chốt: KHÔNG dùng cascade cắt tập rank.**
Mọi phương án live **phải giữ S1 + net015 + quantile-map trên FULL universe** như sim.

Nguồn số: **Phần 1** (profile lượt 228s, `RESULT_R4_CADENCE.md`) + **Phần 2** (giá trị nhịp 1', sim Kaggle C0/C1).

---

## 0. RÀNG BUỘC CỨNG (không vi phạm)

1. **Giữ S1 + net015 + quantile-map trên FULL universe** (mọi tick chọn lệnh). KHÔNG cascade cắt rank.
2. **KHÔNG đụng shadow-c3** (jar/env/restart) trước 2026-09-30 03:00Z (MASTER đang so shadow vs 242).
3. **KHÔNG deploy** ở task này. KHÔNG sửa code live. KHÔNG chạm 242.
4. Sim → Kaggle (`sim-x1-2021-bundle`); KHÔNG sim trên Oracle.
5. DEV ≤ 2025-12-31; 2026 = HOLDOUT (không dùng để chọn/tune).

---

## 1. SỐ NỀN (Phần 1 — profile lượt selector)

Một lượt selector (nhịp 15') = **~234 s**: đọc dữ liệu ~1,8 s + **FUNDING predict ~232 s (94 %)** +
S1 (nap OI 12,5 s/lần/giờ) + net015/map ~25 ms + gate ~8 ms. Universe **664 coin**.

FUNDING predict = **BATCH 1 model 45-feature** (`Funding_Classifier_Final.onnx`, `predictBatch` cả universe);
nút thắt **KHÔNG phải ONNX** (~0,25 s/664 coin) mà là **feature extract (CPU) + OI lookup (IO từ 242, đọc lại mỗi tick)**.

Ước tốc độ (chi tiết `RESULT_R4_CADENCE.md` §1.5):
- **(i) song song N thread / 4 core:** ~3–4× ⇒ **~60–75 s** (không đủ <45 s; phá byte-determinism).
- **(ii) batch predict:** **đã làm** ⇒ ≈0 gain.
- **(iii) cache feature theo giờ:** funding (8h) đã cache; **OI (5/45) đổi 1h nhưng đang đọc lại mỗi tick** ⇒ cache OI theo giờ ~1,3–1,5×.
- **Kết hợp (i)+(iii): ~4–5× ⇒ ~45–55 s** — sát trần, không chắc <45 s. ADR-0005: đừng yak-shave single-node.

---

## 2. BA PHƯƠNG ÁN

### A) Tối ưu FUNDING predict để full universe < 45 s (giữ parity tuyệt đối)

- **Làm gì:** song song hoá feature-extract per-coin (pool N thread) + cache OI theo giờ (bỏ `clear()` mỗi tick).
- **Số:** ~4–5× ⇒ ~45–55 s — **sát trần 45 s**, kỳ vọng **~50/50 đạt**.
- **Rủi ro (cao):**
  1. **Phá byte-determinism**: song song + shared `HistoryManager`/`FundingCrossSectional` (mutate in-place,
     `selectorRankPool` TreeMap) ⇒ nguy cơ race/nondeterminism, **lệch parity** — đúng điều runbook §7 cảnh báo
     (GPU/nthread lech `dIC`). Chứng minh parity lại là **việc lớn** (mỗi chân 4,5 năm 1').
  2. `FundingCrossSectional.apply` + `EntrySignalFilter.selectCoins` là **PASS-2 toàn-universe** (không tách per-coin
     thuần) ⇒ song song không "sạch", phải giữ barrier ⇒ lợi ích co lại.
  3. ADR-0005 (đã chốt): tinh chỉnh single-node ≤1,1× — tuy nút thắt khác (extract/OI vs inference) nhưng tinh thần
     "đừng yak-shave" vẫn áp.
- **Verdict:** chỉ đáng nếu Phần 2 cho thấy 1' **bắt buộc** (C1 mất nhiều n/Calmar) VÀ chấp nhận rủi ro parity.

### B) Pipeline bất đồng bộ — full-universe S1+net015+map mỗi 15', gate/entry mỗi 1' dùng rank mới nhất (trễ ≤15')

- **Làm gì:** tách 2 nhịp rõ ràng (mở rộng CADENCE-SPLIT-V2 đã có):
  - **PREP nặng (15')**: FUNDING predict (664 coin) + S1 + net015 + quantile-map trên **FULL universe** → snapshot
    `LATEST_SEL_RANK/MAPPRED` (đã có `LATEST_SEL_MAPPRED` tách đường THAT).
  - **ENTRY nhẹ (1')**: selector chỉ đọc snapshot rank/map **mới nhất** (trễ ≤15') để gate + mở entry.
- **Số:** lượt PREP giữ ~234 s nhưng chạy **nền** (background thread), lượt ENTRY ~ms ⇒ **thông lượng 1' không bị
  block**. Không cần tối ưu FUNDING xuống <45 s.
- **Rủi ro (trung bình):** rank/map **trễ ≤15'** so với "fresh". Cần đo bằng **sim variant**:
  - **Sim variant cần:** đóng băng rank + `symbolPred` (gate value) tại **mốc 15'**, cho phép entry **mỗi phút**
    dùng giá trị đóng băng đó. Hiện **KHÔNG có key** nào làm được trực tiếp (sim sinh rank từ bins `predwf_map_s1a2_x1`
    ở granularity 1'); cần **bins con lấy mẫu 15'** (rank/symbolPred chỉ đổi mỗi 15') **hoặc** 1 flag Java gated
    (mặc định OFF = byte-identical) đóng băng rank trong 15'. Phải chạy parity trước khi tin.
  - **Giảm thiểu trễ:** S1 dùng **close 1h** (đổi mỗi giờ, §1.4) ⇒ rank S1 **gần như KHÔNG đổi** trong 15'; chỉ
    `symbolPred` (net015, per-minute) là đổi theo phút ⇒ trễ 15' chỉ ảnh hưởng **giá trị gate**, không ảnh hưởng thứ tự S1.

### C) R4 live nhịp C1 (selector 15', BD/DCA 1') — KHÔNG cần kỹ thuật mới

- **Làm gì:** giữ **đúng đường live hiện tại** (`LIVE_ENTRY_GRID_MIN=15`, `MARKET_SCAN_MIN=1` CADENCE-SPLIT-V2);
  chỉ cần **xác nhận knob R4** (F_BASE / SELECTOR_RANK_TOPK / SIM_GATE_DYN_SCALE / CONC_CAP) đã wire vào live sizing/gate
  (đã có từ `dd8d063`: `LIVE_ENTRY_GRID_MIN` + `CONC_CAP_PERCOIN` live).
- **Số:** bằng đúng **C1** ở Phần 2 — giữ **63,5 % n, 75,8 % Calmar** của R4 (C1 FAIL T4 Calmar 1,271 < 1,509).
- **Rủi ro (thấp nhất):** 0 kỹ thuật mới, 0 rủi ro parity (dùng nguyên engine), chỉ đổi config/env.
- **Nhược:** nếu Phần 2 cho thấy C1 mất **nhiều n/Calmar** ⇒ bỏ sót giá trị của nhịp 1'.

---

## 3. ĐỀ XUẤT — **PHƯƠNG ÁN B (pipeline bất đồng bộ)**

**Số quyết định (Phần 2):** nhịp 15' giữ **63,5 % n / 75,8 % Calmar** của R4 (C1 FAIL T4 Calmar 1,271 < 1,509;
loss tập trung selector, −15 % (2021) → −43 % (2024)); nhịp 1' **đáng làm**. Nhưng Phần 1: FUNDING predict 232 s,
cần ~4–5× để <45 s, và song song phá byte-determinism (rủi ro parity cao).

⇒ **Chọn B**: giữ full-universe S1+net015+quantile-map (ràng buộc CỨNG), đạt nhịp 1' **KHÔNG cần** hạ FUNDING <45 s.

**Vì sao B khả thi (lập luận từ Phần 1 §1.4):**
- Thành phần **đắt** (FUNDING predict 232 s) cho ra 2 thứ: (a) `symbolPred` = ngưỡng gate (net015/map, per-coin),
  (b) feature 45 cho net015/map. Cả hai **chậm đổi**: S1 rank dùng **close 1h** (đổi mỗi giờ); net015 P(win) gồm
  funding (8h) + OI (1h) + momentum/microstructure (phút) — phần phút là phần NHỎ.
- Thành phần **rẻ** = `p15` momentum thị trường (tính ở đầu lượt ~1,8 s, đổi MỖI PHÚT) — chính là thứ quyết định
  **THỜI ĐIỂM entry** (gate PASS ⟺ `p15 ≥ thr`). Giữ `p15` FRESH mỗi phút ⇒ bắt được tín hiệu fire-and-fade giữa 2 mốc 15'.
- ⇒ chạy PREP (FUNDING+S1+net015+map full universe) **nền mỗi 15'**, ENTRY **mỗi 1'** đọc snapshot mới nhất (trễ ≤15').

**Bắt buộc đo trước khi tin — sim variant đo tác động trễ:**
- **Variant B-trễ**: đóng băng `symbolPred` + rank S1 tại **mốc 15'** (giá trị từ bins `predwf_map_s1a2_x1` chỉ đổi mỗi 15'),
  cho phép entry **mỗi phút** dùng `p15` tươi + ngưỡng/rank đóng băng. Hiện **KHÔNG có key** nào làm trực tiếp ⇒ cần
  **bins con lấy mẫu 15'** (forward-fill) **hoặc** 1 flag Java gated (mặc định OFF = byte-identical, phải chạy parity trước).
- Tiêu chí: B-trễ phải giữ **≥ ~90 % n và ≥ 0,90×Calmar** của C0 (1'). Nếu **< ngưỡng** ⇒ trễ là đáng kể ⇒ chuyển **A**.

**Fallback = A**: chỉ khi B-trễ mất nhiều (trễ thực sự phá giá trị 1'). Khi đó chấp nhận rủi ro parity của
song song hoá + OI cache (đích ~45–55 s), và PHẢI chạy lại parity md5 `06fd6e9a` trước khi tin.

---

## 4. KẾ HOẠCH DEPLOY SHADOW (tiêu chí PASS 2h như B2, rollback) — áp cho phương án chọn

> Viết, KHÔNG thực hiện ở task này. Thứ tự **shadow → 242 (owner duyệt riêng)**, đúng bài học rollback `53c80a1`.
> **Phương án B cần CODE gated trước**: thêm cơ chế PREP nền + snapshot (mặc định OFF = byte-identical),
> chạy parity md5 `06fd6e9a` (R4) + `99e42b75` (KEEPLEG0) trước khi bật key — như đã nêu ở §3.

1. **Chốt jar chuẩn** (HEAD + patch B nếu cần) + ghi sha256; đối chiếu 3 jar đang tồn tại (242 / shadow / build HEAD).
2. **Backup** jar đang chạy + `conf/env.sh` (copy, KHÔNG sửa tại chỗ).
3. **Đặt key** theo phương án B: `LIVE_ENTRY_GRID_MIN=1` (selector 1') · `MARKET_SCAN_MIN=1` · `SELECTOR_RANK_TOPK=16` ·
   `SIM_GATE_DYN_SCALE=1.55` · `SIM_F_BASE=0.015` · `CONC_CAP 15%` · **KHÔNG dùng `ENTRY_CASCADE`** (đã chứng minh cắt rank).
4. **restart shadow-c3** theo quy trình.
5. **Xác minh 2h (tiêu chí PASS, giống B2):**
   - (i) median 1 lượt selector < 45 s **HOẶC** selector fire đúng 4 mốc/giờ (`[GATE]` chỉ :00/:15/:30/:45);
   - (ii) ≥ 1 dòng `[GATE]` mỗi phút ở nhánh MARKET (BD/DCA) nếu bật 1';
   - (iii) `[MAP]` universe **FULL** (~660+ coin), KHÔNG bị cắt (bằng chứng giữ S1 đầy đủ);
   - (iv) 0 ERROR/Exception mới; (v) RSS ổn định, free mem ≥ 4G.
6. **Rollback ngay** nếu FAIL: khôi phục jar + env backup, restart, verify active, báo.
7. Viết `docs/audit/DEPLOY_R4_LIVE_1M_V2_20260929.md` (sha256 jar, diff env không in secret, số đo).

---

## 5. KỶ LUẬT

KHÔNG sửa code live, KHÔNG deploy, KHÔNG chạm 242/shadow-c3 ở task này. KHÔNG quét thêm biến thể cadence ngoài C0/C1.
Kết quả là **ĐO LƯỜNG + THIẾT KẾ**, không đổi incumbent production.
