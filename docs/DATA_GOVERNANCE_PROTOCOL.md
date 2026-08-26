# DATA GOVERNANCE PROTOCOL — luật chống leak, tách hẳn dữ liệu (2026-08-24)

> **Mục đích.** Chặn nguồn leak gốc: *thông tin chảy ngược từ dữ liệu-đánh-giá về tay người ra
> quyết định*. Mắt nhìn kết quả trên tập nào → tập đó cháy. Không chặn bằng kỷ luật cá nhân,
> chặn bằng **tách vai + tường vật lý**: mắt không bao giờ thấy thứ đáng để vặn.
>
> **Một câu luật.** DEV là nơi được làm người (nhìn, vặn thoải mái); VALIDATION và HOLDOUT là nơi
> **chỉ máy chạm**. Người chỉ nhận verdict cuối, không bao giờ thấy số per-config của hai tầng đó.
>
> Văn bản này là LUẬT dự án. Sửa nó = một quyết định pre-register mới, phải ghi ngày + lý do.

---

## 0. Nguyên tắc (đọc trước khi làm)

1. **Leak = decision phụ thuộc outcome trên tập đánh giá.** Gồm cả: chọn strategy family, chọn
   feature, vẽ range param, chọn objective, chọn ngưỡng pass, chọn lúc dừng. Mọi thứ tay-người
   đụng sau khi nhìn kết quả đều là leak.
2. **"Đi lại từ đầu" KHÔNG phải xoá code.** Simulator / CPCV harness / trial_ledger là *dụng cụ*,
   không leak. Cái vứt là **tầng quyết định đã nhiễm**: range gene bị sweep hẹp, objective chọn
   sau khi nhìn, ngưỡng pass. Giữ máy móc, reset quyết định trên data chưa đụng.
3. **Ledger không rửa được leak quá khứ.** trial_ledger chỉ đếm từ lúc bật. Range gene hiện tại
   trong StrategyWfoTask đã bake hàng trăm trial ẩn (xem comment "sweep cho thấy...", "TASK-139
   phát hiện lớn..."). Nên VALIDATION 2024-2025 coi như ĐÃ BỊ NHÌN → DSR ở đó lạc quan. Chỉ
   **HOLDOUT 2026 mới là test thật** vì lúc vặn nút nó chưa tồn tại (chưa có pred).

---

## 1. Ba tầng dữ liệu (time-ordered, một chiều, KHÔNG shuffle)

Data gốc: ticker + OI + funding từ 2021-01-01. Nguồn: 242 (Aerospike) tới nay; Oracle tới ~2026-08-13.
Selector pred (feature của sim) hiện chỉ phủ tới **2025-12** → đây là ràng buộc chia tầng.

| Tầng | Khoảng (**CHỐT 2026-08-24**) | Ai được nhìn | Vai trò |
|---|---|---|---|
| **DEV** | 2021-01-01 → 2024-06-30 (3.5y) | Người, tự do | Nghĩ giả thuyết, vẽ search space rộng, chọn objective. Leak được PHÉP ở đây. |
| _gap_ | 2024-07-01 → 2024-07-14 (14 ngày) | — | Purge+embargo giữa tầng (≥ max(label_horizon 4h, MAX_HOLD 10 ngày)). Vứt, không ai dùng. |
| **VALIDATION** | 2024-07-15 → 2025-12-31 (~17.5 th) | **Chỉ máy** | Auto-search + CPCV + ledger + DSR/PBO. Người chỉ thấy PASS/FAIL cuối. |
| **HOLDOUT / VAULT** | 2026-01-01 → 2026-08-13 (~7.5 th) | **Không ai, tới Pha 3** | Trinh trắng thật (chưa có pred lúc tuning). Chạm ĐÚNG 1 LẦN cả đời. |

**Vì sao HOLDOUT = 2026:** suốt quá trình tinh chỉnh, selector chưa từng sinh pred cho 2026 →
strategy không thể đã nhìn nó → đây là lát duy nhất chưa nhiễm. Kích hoạt bằng cách chạy
**pipeline ĐÃ ĐÓNG BĂNG** forward lên 2026 (train selector với cutoff ≤2025-12, sinh pred 2026,
rồi chạy đúng 1 config thắng). Không vặn gì trong lúc đó.

---

## 2. Tường phải dựng ở TẦNG SỚM NHẤT (selector), không chỉ ở strategy

Selector (model funding) tự train bằng WFO riêng; **pred của nó là feature đưa vào sim**. Nếu chỉ
tách data ở tầng strategy, selector vẫn có thể được train trên đúng kỳ HOLDOUT rồi xuất pred cho
kỳ đó → strategy "OOS" ăn pred leak. Luật:

- Selector train cutoff **KHÔNG được vượt biên trái của tầng đang đánh giá**. Đánh giá VALIDATION
  → selector chỉ train tới ≤ đầu VALIDATION (trừ purge). Đánh giá HOLDOUT → selector chỉ train
  tới ≤2025-12, sinh pred 2026 hoàn toàn OOS.
- Pred đưa vào sim của một tầng phải là pred **walk-forward OOS** với purge (PURGE_STEPS đã có),
  không phải pred in-sample.
- Manifest dataset phải ghi: train-cutoff selector + tầng nó phục vụ. Loader reject nếu lệch.

---

## 3. Bốn pha — mỗi pha CHỈ thấy tầng của nó

### Pha 0 — Dựng tường (chưa mô hình gì)
- [ ] Chốt 3 mốc thời gian (bảng §1) — quyết định của Uni, ghi vào đây.
- [ ] Niêm phong HOLDOUT 2026: tính hash manifest+bin, cất metadata ra chỗ script không đọc tuỳ tiện.
- [ ] Ghi hash + ngày vào §6. Từ đây HOLDOUT coi như KHÔNG TỒN TẠI.

### Pha 1 — Khám phá trên DEV (được phép leak)
- [ ] Nhìn/thử/bỏ tự do CHỈ trên DEV. Đây là chỗ trực giác người được tự do.
- [ ] Ra **công thức đóng băng, pre-register + hash**, gồm:
      strategy family · feature set · **search space RỘNG theo lý thuyết** (KHÔNG dùng range đã
      sweep hẹp trong StrategyWfoTask) · objective O · ngưỡng pass (PBO<0.2, DSR>0.95, %fold+ ≥…) ·
      **budget n_trials** · stopping rule.
- [ ] Xác nhận công thức KHÔNG tham chiếu 1 byte nào từ VALIDATION/HOLDOUT.

### Pha 2 — Validate tự động (chỉ máy)
- [ ] Chạy công thức đóng băng: auto-search + CPCV (28 path, purge+embargo) + trial_ledger + DSR/PBO
      trên VALIDATION.
- [ ] Người CHỈ nhận: PASS/FAIL + DSR + PBO. KHÔNG xem số per-config, KHÔNG xem equity từng fold.
- [ ] **FAIL → KHÔNG vặn rồi chạy lại trên VALIDATION.** Quay về DEV nghĩ giả thuyết mới. Mỗi lần
      chạm VALIDATION bị ledger cộng dồn n_trials vĩnh viễn → cửa DSR tự cao lên.

### Pha 3 — Holdout, một lần
- [ ] CHỈ khi Pha 2 pass: chạy pipeline đóng băng forward lên HOLDOUT 2026, đúng 1 config thắng, 1 lần.
- [ ] Số ra sao báo vậy. KHÔNG vặn sau đó. Nếu muốn thử lại → holdout đã cháy, cần data mới (2026H2+).

---

## 4. Giữ gì / Vứt gì khi restart

**GIỮ (dụng cụ, không leak):** SimulatorMarketLevelTicker1MStopLoss · WfoDataset/framework ·
cpcv_validation.py · trial_ledger.py · cpcv_harness.py · pipeline export/train/predict.

**VỨT / DỰNG LẠI (quyết định đã nhiễm):** range 17 gene trong StrategyWfoTask (vẽ lại RỘNG, theo
lý thuyết, trên DEV) · objective đã chọn sau khi nhìn · mọi ngưỡng pass chưa pre-register · mọi
"finding" dạng "vùng tốt là X" rút ra từ nhìn OOS.

---

## 5. Cơ chế đóng băng (chống sửa lén)
- Công thức Pha 1 + mốc data Pha 0 → 1 file, sha256, ghi ngày. Đổi = pre-register mới.
- HOLDOUT: hash bin+manifest, lưu tách. Trước Pha 3 verify hash khớp → đảm bảo chưa ai đụng.
- trial_ledger append-only hash-chain: verify() trước mọi lần tính DSR.

## 6. Sổ niêm phong (Pha 0 — CHỐT 2026-08-24)
- [x] DEV:        2021-01-01 → 2024-06-30
- [x] gap:        2024-07-01 → 2024-07-14  (14 ngày, vứt)
- [x] VALIDATION: 2024-07-15 → 2025-12-31
- [x] HOLDOUT:    2026-01-01 → 2026-08-13   (đóng băng tuyệt đối tới khi PASS Pha 2)
      sha256 = _CHƯA TÍNH_ (dataset 2026 chưa build — hash lúc kích hoạt sau Pha 2, xem §7)
      trạng thái = SEALED-BY-DECLARATION (chưa có bytes để hash; cấm chạm theo tuyên bố)
- [x] CÔNG THỨC PHA 1 v1: FROZEN 2026-08-24 author=chuyennd
      sha256(docs/PHASE1_RECIPE_FROZEN_v1.md) = 738772ff3b494e6066dd9784acc923b74028af25f69c6de6d9fae158c920ebf3

## 7. Quyết định đã chốt + ràng buộc (2026-08-24)

- **HOLDOUT 2026 ĐÓNG BĂNG TUYỆT ĐỐI tới khi PASS Pha 2** (Uni chốt). KHÔNG build pred 2026,
  KHÔNG chạy pipeline forward, KHÔNG hash-poke gì trên lát 2026 cho tới lúc đó. Bước sinh pred 2026
  (Stage A/C train cutoff ≤2025-12) chỉ khởi động NGAY SAU khi Pha 2 pass — và pipeline đó cũng
  phải đóng băng trước khi chạy.
- **VALIDATION 2024-2025 đã bị nhìn → DSR ở đó là CẬN TRÊN lạc quan** (Uni chấp nhận). Van bù:
  (1) 2026 là trọng tài thật; (2) Pha 1 vẽ space RỘNG hơn mọi range đã sweep; (3) rolling holdout
  — mỗi quý data mới chưa đụng (2026H2, 2027...) thành holdout trinh trắng kế tiếp. Report VALIDATION
  phải ghi rõ chữ "CẬN TRÊN — đã bị nhìn quá khứ", không được trình như test sạch.
- CpcvBatchRunner (1 JVM nạp dataset 1 lần, chạy hết ma trận) — mắt xích Java còn thiếu, chỉ viết
  SAU khi công thức Pha 1 đóng băng (không viết trước, tránh code dẫn dắt quyết định).

---

## Phụ lục A — MẪU công thức Pha 1 (Uni điền trên DEV, rồi hash để đóng băng)

> Đây là thứ Pha 1 phải sinh ra. Điền XONG trên DEV → tính sha256 → từ đó CẤM sửa cho tới khi có
> verdict Pha 2. Pha 1 là việc của NGƯỜI (trực giác được tự do); Claude KHÔNG tự điền các ô này —
> tự điền = Claude lại thành người-ra-quyết-định, tái sinh leak.

```
CÔNG THỨC v___  | ngày đóng băng: ______ | tác giả: ______
data dùng ở Pha 1: CHỈ DEV (2021-01-01 → 2024-06-30) — xác nhận: [ ]

1. STRATEGY FAMILY: ______________________________________________
2. FEATURE SET (liệt kê nguồn, KHÔNG thêm/bớt sau freeze): ________
3. SEARCH SPACE (mỗi knob: [lo, hi], RỘNG theo lý thuyết — KHÔNG dùng
   range đã sweep hẹp trong StrategyWfoTask):
     - <knob>: [lo, hi]  lý do vật lý (không phải "sweep thấy tốt"): ____
     - ...
4. OBJECTIVE O (công thức chính xác): ____________________________
5. NGƯỠNG PASS (pre-registered): PBO < ___ ; DSR > ___ ;
   %fold dương ≥ ___ ; maxDD-cap ≤ ___ ; (khác) ___
6. BUDGET n_trials tối đa cho toàn chiến dịch VALIDATION: ______
7. STOPPING RULE (khi nào dừng search): __________________________
8. CPCV setup: N blocks = ___ , k_test = ___ , gap = ___ ngày
     (gap ≥ max(label_horizon, MAX_HOLD) = ___ )
9. selector train-cutoff cho VALIDATION: ≤ ______ (§2)

sha256(file này) = ____________________  ← dán sau khi điền xong, đây là dấu niêm phong
```

**Sau khi có công thức đóng băng này, Claude mới viết CpcvBatchRunner khớp đúng nó (§7).**
