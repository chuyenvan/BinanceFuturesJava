# DECISION — Đổi BASELINE nghiên cứu sang R4 (2026-09-29)

## Quyết định
Ngày **2026-09-29**, owner **CHỌN** baseline nghiên cứu mới = **R4** (vì **ưu tiên số lệnh**; `R3` bị loại vì kém rõ).
Baseline (mốc so sánh + cổng parity) chuyển từ **`B*`** (`R0` = KEEPLEG0 + nhịp 1' + CONC_CAP 15%) sang **`R4`**.

| | `B*` = R0 (baseline CŨ) | **R4 (baseline MỚI)** |
|---|---|---|
| profile | `profiles/t170_flat_keepleg0.properties` | **`profiles/r4_kg0_k16_f015_g155.properties`** |
| `DCA_GRID_WEIGHTS` | 1,1,1,1 | 1,1,1,1 (giữ) |
| `DCA_GRID_SCALE` | 6.0 | 6.0 (giữ) |
| `CONC_CAP_PERCOIN` | 15% (bật) | 15% (giữ) |
| `SIM_F_BASE` | 0.03 (×1) | **0.015 (×0,5)** |
| `SELECTOR_RANK_TOPK` | 8 | **16** |
| `SIM_GATE_DYN_SCALE` | 1.70 | **1.55** |
| nhịp | 1' | 1' (giữ) |
| phí | base | base (`SIM_RATE_FEE=0.000982` + `SIM_SLIPPAGE_RATE=0.000067`) |
| run tham chiếu | `p2-r0-base` | **`p2-r4-base`** |
| `printDone.csv` md5 | `d297ce6b` (base) / `99e42b75` (legacy) | **`06fd6e9aa9c916945b2cf12310b337ff`** |

`diff` tường minh (profile mới sinh từ `t170_flat_keepleg0.properties`, đúng key kernel `p2-r4-base`):
**5 key đổi/thêm** — `SELECTOR_RANK_TOPK` 8→16 · `SIM_GATE_DYN_SCALE` 1.70→1.55 · thêm `SIM_F_BASE=0.015` ·
thêm `SIM_ENTRY_SAMPLE_MIN=1` (nhịp 1', no-op) · thêm `SIM_RATE_FEE`/`SIM_SLIPPAGE_RATE` (phí base). Không đoán key nào khác.

## BẢNG SO `R0`/`R4` @base (số thật từ `RESULT_RESET_RULE_P2.md`, `47a9d90`)

| thước | `R0` (`B*`) | `R4` | Δ (R4 − R0) |
|---|---|---|---|
| `n` (số lệnh) | 1 086 | **2 027** | **×1,87** |
| CAGR % | **32,97** | 27,53 | −5,44 pp |
| ddMTM (phút) % | −19,85 | **−16,42** | +3,43 pp (tốt) |
| UW (ngày) | 147,2 | 164,7 | +17,5 |
| Calmar_MTM | 1,661 | 1,676 | +0,95 % |
| conc/coin % | 7,11 | **5,30** | −1,81 pp (tốt) |
| top-1% lệnh | 20,72 | 19,38 | −1,34 pp |
| q* % | 24,2 | 21,7 | −2,5 pp |

## ĐÂY LÀ QUYẾT ĐỊNH KHẨU VỊ — **KHÔNG PHẢI "WIN"** — phải ghi rõ bằng chứng

`R4` là arm DUY NHẤT qua **cả 4 tầng** ở P2, nhưng **bằng chứng độ bền (P3, `911ad42`) nói `R4` ≤ `B*`**:

- **KHÔNG hơn `B*` về Calmar:** CI chênh `Calmar` `R4−B*` = **−9,52**, CI **[−30,45; +3,95] CHỨA 0** ⇒ biên
  `Calmar +0,7…0,95 %` của P2 là **NHIỄU**. (Bootstrap cụm episode, 5000 rep, seed `20260928`.)
- **THUA về CAGR:** chênh `CAGR` = **−5,62 pp**, CI **[−9,41; −2,34]** (âm, **NGOÀI 0**); chênh `ΣPnL` =
  **−21 510**, CI **[−35 252; −8 499]** (âm ngoài CI) ⇒ bootstrap nói **`B*` ≥ `R4`** về CAGR/ΣPnL.
- **T1 episode jackknife FAIL:** bỏ top-3 episode, `Calmar_còn(3)` của `R4` = **2,70** < `B*` **4,15**.

**Vì sao vẫn chọn `R4` (lý do KHẨU VỊ, owner 09-29 — "ưu tiên số lệnh"):**
- `n` **×1,87** (2027 vs 1086) — đúng ưu tiên "nhiều lệnh để ổn định";
- ddMTM **−16,4 vs −19,9** (rủi ro đuôi MỎNG hơn);
- conc **5,3 vs 7,1** (phân tán tốt hơn);
- đổi lại chấp nhận **CAGR thấp hơn** (27,5 vs 33,0) và **Calmar không hơn** — đây là **đánh đổi**, không phải cải thiện.

## THAY ĐỔI LUẬT KÈM THEO (owner 09-29) — **T4: ƯU TIÊN SỐ LỆNH**

Chính thức hoá luật 4 tầng vào `docs/runbooks/RISK_APPETITE.md` §9, và **sửa tầng 4**:
- `n` **là mục tiêu chính** (thay vì `n ≥ 1,3×B*`);
- ràng buộc: **`Calmar_MTM ≥ 0,90 × baseline`** (thay vì `≥ baseline`) và **`conc ≤ baseline`** (giữ).

**Chỉ áp cho vòng MỚI — KHÔNG hồi tố P2/P3.** (P2/P3 vẫn giữ luật tầng 4 gốc `Calmar_MTM ≥ B*` đã chốt trước.)

## HỆ QUẢ — BẮT BUỘC

1. **Cổng parity MỚI:** mọi run mới không override DCA/knob R4 phải tái hiện
   **`06fd6e9aa9c916945b2cf12310b337ff`** / n **2 027** / equity **104 489** (`p2-r4-base`).
   `99e42b75` (KEEPLEG0 legacy) và `d297ce6b` (`R0` @base) **không còn là mốc baseline** — chỉ là mốc đối chiếu.
2. **Kết luận cũ KHÔNG tự chuyển:** mọi kết luận trên trục exit/gap/sizing/gate được đo trên `B*` (KEEPLEG0, K=8, gate 1.70)
   ⇒ **phạm vi hiệu lực là nền cũ**. Muốn kết luận trên `R4` thì **chạy lại** với **pre-reg mới**.
3. **Khẩu vị rủi ro KHÔNG đổi:** `maxDD ≤ 40%/năm` (MTM phút) · `UW ≤ 250` · quý xấu nhất `≥ −20%` · 0 năm âm (CỨNG) ·
   conc 1 coin `≤ 15%` (CỨNG) vẫn giữ nguyên (`docs/runbooks/RISK_APPETITE.md` §6–§7). Luật tầng 1–3 của §9 giữ nguyên.
4. **Nền chạy:** `R4` sinh từ Kaggle (`p2-r4-base`, bundle `chuyendinh/sim-x1-2021-bundle`, `TICKER_SOURCE=file`) — so sánh
   phải **cùng nguồn hạ tầng** (Kaggle ↔ Kaggle), không trộn với Oracle.

## Ghi chú 1x (bối cảnh khẩu vị)
`margin == notional` = **1,0000** trên toàn bộ leg (`docs/result/RESULT_FRAGILITY_N.md`) ⇒ đánh **1x**, không đòn bẩy;
max concurrent margin ~47–58% equity ⇒ **không thể cháy tài khoản** ⇒ `maxDD`/`UW` là **lỗ TẠM THỜI**. **Kênh mất thật
duy nhất = tập trung 1 coin** (delist/về 0 khi đang giữ) ⇒ trần `conc ≤ 15%` giữ **CỨNG**. `R4` conc 5,30% ⇒ càng an toàn.
