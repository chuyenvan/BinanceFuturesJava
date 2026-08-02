# 2026-08-01 (tối) — DCA grid + min-rate ratchet đưa thành cấu hình HPO-able

> Nối mạch từ `HANDOFF_20260801_dca_grid_exit.md`. Phiên này KHÔNG tune gì, chỉ **đấu dây** để
> vòng HPO sau chạy được. Có 1 kết quả đo bất ngờ ở cuối — đọc mục 4 trước khi chạy HPO.

## 1. Lỗi cấu trúc đã sửa: HPO không thể chạm tới DCA

`StrategyWfoTask` áp gene bằng reflection lên **field scalar** (`Field.setFloat/setInt`).
Ba tham số grid lại là mảng `float[]` (`DCA_GRID_LEVELS`, `DCA_GRID_WEIGHTS`,
`DCA_TIER_MARGIN_CAPS`) → **không có đường nào để HPO tune DCA**. Nếu cứ thế fanout, HPO sẽ
quay hàng nghìn sample mà lưới không đổi, cho ra kết quả *trông hợp lý* nhưng vô nghĩa.

Sửa: mô tả cùng một lưới bằng số vô hướng, mảng vẫn giữ làm đường tương thích.

| scalar | ý nghĩa | default |
|---|---|---|
| `DCA_GRID_L1` | mốc nhồi đầu, đo trên `firstEntryPrice` | −0.50 |
| `DCA_GRID_STEP` | độ giãn giữa 2 bậc | 0.20 |
| `DCA_GRID_LEGS` | số bậc nhồi | 3 |
| `DCA_GRID_W_RATIO` | tỉ lệ nhân tỉ trọng giữa 2 leg | 2.0 |
| `DCA_TIER_CAP_BASE` / `_STEP` | trần margin bậc = BASE + STEP·i | 0.50 / 0.10 |

`levels[i] = clamp(L1 − STEP·i, −0.99..−0.01)`, `weights[i] = W_RATIO^i` (w₀=1).
Với default → `−0.50/−0.70/−0.90`, `1/2/4/8` — xấp xỉ `−0.50/−0.75/−0.90`, `1:1:3:8` đã đo.

**Công tắc `DCA_GRID_SCALAR` (mặc định false)**: false = đọc thẳng mảng như cũ, **byte-identical**
với bản chốt tạm. true = bỏ qua mảng hoàn toàn, dùng scalar. Một nguồn sự thật duy nhất tại mỗi
thời điểm — cố ý, để không rơi vào cảnh "set env mảng nhưng HPO tune scalar, không biết cái nào thắng".

## 2. Genome: HOÁN ĐỔI, không cộng dồn

Gene chết được bỏ đi thay vì để lại tốn chiều search:

| bật cờ | bỏ (đã chết) | thêm | net |
|---|---|---|---|
| `DCA_GRID_ENABLED` + `SCALAR` | `DCA_LOSS_BIG_DOWN`, `DCA_TIME_BIG_DOWN` — chỉ đọc trong `DcaUtils.getDcaConfig(BIG_DOWN)`, mà grid rẽ sang `shouldDcaGrid()` nên **không bao giờ gọi tới** | `DCA_GRID_L1/STEP/LEGS/W_RATIO/SCALE` | +3 |
| `DCA_TIER_MARGIN_ENABLED` + `SCALAR` | — | `DCA_TIER_CAP_BASE/STEP` | +2 |
| `TS_GIVEBACK_FLOOR` | `TS_MAX_GAP`, `TS_MAX_GAP_WEAK`, `TS_WEAK_MOMENTUM_THRES` — nhánh `Math.max(peak·ratio, TS_MIN_GAP)` **không đụng maxGap**, 3 gene này là nhiễu thuần | `TS_MIN_GAP`, `TS_GIVEBACK_RATIO` | −1 |

**17 → 21 gene.** Cả 3 cờ tắt = đúng 17 gene cũ, `WFO_FROZEN_GENOME` cũ vẫn chạy.
Bật lên thì vector 17 số cũ sẽ fail-fast — đúng ý đồ, nó không còn mô tả đúng không gian nữa.

`TS_RATCHET_DECOUPLED` **bị nuốt**: `TS_PROFIT_MULTIPLIER=1.0` chính là decoupled
(`updateTPSL: rateMin2MoveSl = DECOUPLED ? base : MULT*base`). Sàn range mở xuống 1.0 khi
`TS_GIVEBACK_FLOOR=true`; ép tay bằng `WFO_TSMULT_LO`/`_HI`. Đừng set cả hai — đếm 2 lần một ý định.

## 3. Hạ tầng

- **`orchestrator/tools/verify_stage.py` được viết LẠI** — handoff trước ghi "đã viết sẵn" nhưng
  file **không có trong repo** (chưa commit, mất). Đây đúng là loại thất thoát mà nó sinh ra để chặn.
  Gắn thành nút CE: `bash ce.sh verify_stage <jar> dca_grid exit` → soi jar **đã stage trên Oracle**,
  đếm token trong bytecode. Đã chạy: **PASS 21/21**.
- `[TIER-MARGIN] blockCount=... caps=[...]` log SLF4J vào cuối `simulatorWithInitEntry`
  (mục E handoff — trước đây counter tăng mà không in ra nên phải suy bằng canary).
- Unit test `DcaGridScalarTest` — 7/7 pass. Quan trọng nhất là case
  `hpoTouchesShouldDcaGrid`: đổi field scalar mà kết quả không đổi = gene chết, test sẽ gãy.
- Config: `configs/exit_dca_20260801_frozen.env` (tái lập chính xác bản chốt tạm) và
  `configs/exit_dca_20260801_hpo.env`. Pipeline: `orchestrator/pipelines/wfo_dca_grid_hpo.json`.

## 4. ⚠️ Smoke test ra số cần chú ý TRƯỚC KHI chạy HPO

`wfo_verify` trên `wfo_ds_oiz75`, N=2 (chỉ 2 sample — **không phải kết luận**):

| w15 (Oct 2025–Jan 2026) | oosPnl | trades | oosNote | held>7d |
|---|---:|---:|---|---:|
| control (DCA cũ, không cờ nào) | 8,137 | 716 | SUCCESS | 0.0% |
| grid scalar + tier + giveback-floor | 6,987 | 594 | **TOO_MUCH_CAPITAL_LOCK** | **3.87%** |

Đọc được hai điều:

1. **Cơ chế sống** — hai nhánh khác nhau rõ rệt (594 vs 716 lệnh), gene không chết. Đây là điều
   smoke test cần chứng minh, và nó chứng minh được.
2. **Giá trị khởi điểm trong `exit_dca_20260801_hpo.env` làm sample-0 rơi vào sentinel ở đúng
   window nặng nhất.** Sample-0 = baseline của random search → fitness bị phạt ngay từ mẫu đầu.
   `held>7d=3.87%` cũng vượt ràng buộc production 2% (đúng như mục D handoff cảnh báo, và giờ có số).

Chưa tách được phần nào do grid, phần nào do `TS_GIVEBACK_FLOOR` — control đang là DCA cũ + exit cũ,
không phải bản chốt tạm. Muốn tách thì chạy thêm w15 với `SCALAR=false` + mảng `−0.50/−0.75/−0.90`
(và riêng `TS_GIVEBACK_FLOOR` on/off). Rẻ: 2 lần `wfo_verify`, ~15 phút.

## 5. Việc chưa làm

- Chưa commit (`git status` vẫn bẩn từ phiên trước — chờ Uni quyết dọn `notebooklm_ready/` v.v.).
- Chưa chạy HPO. Chưa tách nguồn gốc chênh lệch ở mục 4.
- Bốn vấn đề mục A–D của handoff trước **vẫn nguyên**: %OOS-dương kẹt 37.5% (nút thắt ở ENTRY),
  PnL dồn vào w15, Spearman train↔holdout 0.14, `%hold>7d` vượt ràng buộc.
  Đấu dây xong không có nghĩa là nên chạy HPO ngay — mục A vẫn là bằng chứng nên quay về entry.
- `run_tier2c.sh` (scale 40/80/160, tìm ngưỡng trần bắt đầu cắn) vẫn treo. RAM box hiện 15G rảnh,
  0 JVM — chạy được, nhưng `-P 2` tối đa.
