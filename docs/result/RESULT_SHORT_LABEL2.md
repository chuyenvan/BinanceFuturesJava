# RESULT_SHORT_LABEL2 — SHORT với NHÃN PATH-AWARE: kết quả (đang cập nhật)

Ngày: **2026-10-01**. Pre-reg: `docs/prereg/PREREG_SHORT_LABEL2.md` (`8edf7c7b`, amend `ad2ee6b3`).
Trainer: `a0438b84` (`--label-mode pa/pw/pn`, `--label-e`). Kernel maker: `b8403282`.
Script chấm: `research/analysis/short_model_score.py` (tái dùng) + `short_model_label2_analyze.py` (`d988aa2d`).

**Tuân thủ:** 0-sim · KHÔNG Java/sim trên Oracle · không sửa `.java` · không chạm production/242/ONNX/LIVE ·
không push dữ liệu · DEV ≤ 2025-12-31 · train CHỈ trên Kaggle. Kernel `sm-label2c` (3 arm) **đã xong**;
`sm-label2` (12 arm) + `sm-label2b` (2 control) **đang chạy** — file này cập nhật khi xong.

---

## 0. Trạng thái & phạm vi

| kernel | arm | trạng thái |
|---|---|---|
| `sm-label2c` | pa thr=1,5 % × E=+10 % × seed{42,7,13} | ✅ **COMPLETE** (có số) |
| `sm-label2` | pa thr{1,5 %,7 %} × E{+3 %,+10 %} × 3 seed | ⏳ running |
| `sm-label2b` | pw(E=+10 %) + pn noise, seed42 | ⏳ running |

Thời lượng thật: **~28–33 phút/arm** (khớp ước lượng ⇒ cắt từ 12+6 arm xuống còn 6+2, xem amend §4
ở pre-reg). Nhãn path-aware dùng **`maxFav_72h`** (đỉnh TĂNG trong cửa sổ = MAE ngược của SHORT).

---

## 1. NHÃN PATH-AWARE (đã khóa)

```
MAE_nguoc_72h  ≡  maxFav_72h  = max(high/close(t) − 1) trên mọi nến 15m trong (t, t+72h]
nhãn P-hard:  y = 1  ⇔  (retEnd_72h ≤ −thr)  VÀ  (maxFav_72h ≤ +E)
              (dòng maxFav_72h > E bị LOẠI khỏi tập train)
đối chứng:    E = +∞  ⇒ nhãn cũ `ndown` y = 1[retEnd_72h ≤ −thr]
```
Nguồn: `funding_label_*.pb` (cột `retEnd_72h`, `maxFav_72h`, `nBars_72h ≥ 288`), như trainer vòng trước.

---

## 2. KẾT QUẢ — cấu hình `PA thr=1,5 % × E=+10 %` (mean 3 seed)

| chỉ số | **path-aware (E=+10 %)** | **nhãn cũ (E=∞)** | Δ |
|---|---|---|---|
| rank-IC (Spearman với −retEnd) | **+0,07780** (raw [0,0683 ; 0,0864], out_both ✓) | +0,05187 | **+50 %** (tốt hơn) |
| CUT-RATE @ +20 % | **0,2490** | 0,1772 | **+41 %** (XẤU hơn) |
| CUT-RATE @ +30 % | **0,1487** | 0,0995 | **+49 %** (XẤU hơn) |
| net K8 không cắt | +0,00003 | +0,00338 | −99 % |
| net K8 @ +20 % (base 0,112 %) | **+0,00213** (raw [−0,00340 ; 0,00749], CI chứa 0) | +0,00419 | **−49 %** |
| net K8 @ +30 % | **+0,00173** (raw [−0,00454 ; 0,00763], CI chứa 0) | +0,00409 | **−58 %** |
| net @ +20 % **đã credit funding** (−0,585 %) | **−0,00372** (âm) | −0,00166 | — |
| by-year @ +30 % (2022/23/24/25) | +0,0133 / **−0,0089** / **−0,0032** / +0,0059 | +0,0117 / −0,0059 / −0,0011 / +0,0118 | 2023/2024 **vẫn âm, âm hơn** |
| số năm dương (sau funding) | **2/4** | 2/4 | — |

Per-seed IC: 0,07741 / 0,07862 / 0,07738 (3/3 ngoài CI raw & ×1,21) ⇒ **A PASS**.
Economy: không mức cắt nào net ngoài CI; 2023/2024 vẫn âm ⇒ **B FAIL ⇒ `NO-GO/NULL`**.

---

## 3. TRẢ LỜI 4 CÂU

1. **Có tránh được coin pump-rồi-dump không?** **KHÔNG — ngược lại.** Cut-rate **TĂNG**: +20 % từ
   0,177 → **0,249**, +30 % từ 0,100 → **0,149**. Nhãn path-aware làm model chọn ra coin **DỄ pump
   hơn**. Cơ chế: mask `maxFav>E` **xoá khỏi tập train chính các âm bản "coin đã pump"** ⇒ model
   **không còn mẫu để học né** ⇒ ở OOS nó kém phân biệt đuôi pump.
2. **Net sau cắt cứng + funding có ngoài CI & ≥3/4 năm dương?** **KHÔNG.** Mọi mức cắt: CI chứa 0
   (raw & ×1,21); credit funding (−0,585 %/72h) ⇒ net **ÂM** (−0,37 % @+20 %, −0,41 % @+30 %);
   chỉ 2/4 năm dương.
3. **2023/2024 hết âm chưa?** **CHƯA — còn ÂM và âm HƠN nhãn cũ** (2023 −0,89 % vs −0,59 %;
   2024 −0,32 % vs −0,11 %, @+30 %). Vì cùng cơ chế regime (Q1 âm) + đuôi `maxFav≥10 %` như
   `RESULT_SHORT_DEEP §2`; nhãn path-aware **không sửa được regime**.
4. **Kết luận:** **`NO-GO/NULL`** cho `thr=1,5 %, E=+10 %`. rank-IC tăng đẹp (0,052 → 0,078) nhưng
   **IC ≠ net**: kinh tế tệ hơn (net −50 %), cut-rate tệ hơn, 2023/2024 không hết âm.

---

## 4. VIỆC BỎ + LÝ DO

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | `thr=7 %`, `E=+3 %`, control `pw`/`pn` | ⏳ đang chạy (`sm-label2`, `sm-label2b`) | file này cập nhật khi xong |
| 2 | `E ∈ {+5 %, +20 %}` | ⛔ BỎ (vòng này) | ngân sách thời gian (~28 ph/arm; amend §4) |
| 3 | Gate-33 / S1-9 | ⛔ BỎ | dataset (như vòng trước) |
| 4 | Time-stop / trailing đường giá / liquidation | ⛔ BỎ | `.pb` chỉ có aggregate |
| 5 | Dựng đường SELL / production | ⛔ BỎ | verdict NO-GO |
