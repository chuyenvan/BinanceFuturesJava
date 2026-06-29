# CONTEXT HANDOFF — TASK-111 (sensitivity gene + hàm mục tiêu) — 2026-06-26 23:40

> File này tổng hợp toàn bộ trạng thái cho session mới tiếp tục. Đọc cùng:
> `docs/insights/GENE_AUDIT_TASK111.md` (bản đồ gene) + `docs/insights/SENSITIVITY_TASK111.md` (kết quả sensitivity).

## ĐANG CHẠY NỀN (KHÔNG được tự dừng — Uni yêu cầu chạy tới khi ra bộ gene)

Sensitivity OAT 26 gene, chia 2 máy (Kaggle ĐÃ BỎ — kernel rơi vào nhánh HPO đọc file `kaggle_data_hpo/*.bin`, không hợp):
- **Oracle** (`ubuntu@161.118.212.3`, key id_rsa_chuyennd port 22): gene 0-8 → tự nối 17-21.
  - Log: `~/claudedata/sens_oracle.log` (batch1 0-8), `~/claudedata/sens_oracle2.log` (batch2 17-21).
  - Script tự-nối: `~/claudedata/sens_oracle_next.sh` (chờ batch1 xong → chạy 17-21).
  - jar: `~/java/simulator/binance-futures-verify.jar`. Chạy `-Xmx18g`.
- **226** (`root@103.157.218.226` port 2222, key id_rsa_chuyennd): gene 9-16 → tự nối 22-25.
  - Log: `/tmp/sens_226.log` (batch1 9-16), `/tmp/sens_226_2.log` (batch2 22-25).
  - Script tự-nối: `/tmp/sens_226_next.sh`. jar: `binance-futures-bench.jar`. Chạy `-Xmx11g` (KHÔNG OOM, đã verify). Aerospike local.
- Tốc độ: ~42-45 phút/gene (4 backtest FAST 2.5y × ~10.5 phút). Còn ~9h → xong khoảng trưa 27.
- **Lệnh lấy kết quả:**
  - Oracle: `grep "range=" ~/claudedata/sens_oracle.log ~/claudedata/sens_oracle2.log`
  - 226: `grep "range=" /tmp/sens_226.log /tmp/sens_226_2.log`
- **Kiểm còn chạy:** `pgrep -f SensitivityTool`.

## KẾT QUẢ SENSITIVITY (6/26 gene, baseline finalFitness=1.51966)

| Gene | Tầng | range | Kết luận |
|---|---|---|---|
| MIN_MOMENTUM_15M | entry | 115895 (REJECT) | **GIỮ — cực quan trọng** |
| PREDICT_SYMBOL_RATE_MAX_THRESHOLD | entry | 100035 (REJECT) | **GIỮ — cực quan trọng** |
| HARD_RISK_LIMIT_4H | entry | 0.2577 | giữ (nhạy vừa) |
| MS_DOWN_SMALL_AVG_OR_15M | market | 0.0044 | ứng viên cắt (gần phẳng) |
| PREDICT_SYMBOL_RATE_DOWN_15M | market | 0.0000 | **CẮT (phẳng)** |
| PREDICT_SYMBOL_RATE_UP_AVG | market | 0.0000 | **CẮT (phẳng)** |
| PREDICT_SYMBOL_RATE_DOWN_AVG | market | 0.0000 | **CẮT (phẳng)** |

**Phát hiện chắc chắn:** cụm `PREDICT_SYMBOL_RATE_*` (3 gene) phẳng tuyệt đối → cắt cả 3. MS_* mới là cụm thật điều khiển market-state, PREDICT_RATE_* là cụm thừa (khớp nghi ngờ chồng chéo trong GENE_AUDIT).

## VIỆC TIẾP (khi sensitivity xong)
1. Gom kết quả 26 gene (4 log), xếp range giảm dần, xác định "vách" cắt.
2. Đối chiếu GENE_AUDIT: giữ tầng trailing (4-5 gene, bot no-stoploss → exit sống còn) + DCA (4) + entry cốt lõi (3).
3. Chốt ~12 gene giữ + lý do từng gene bỏ. Cập nhật `SENSITIVITY_TASK111.md` mục "ĐỀ XUẤT CẮT" + "CÂU HỎI UNI".
4. Uni duyệt danh sách 12 gene sáng 27 → mới HPO/WFO.

## TRẠNG THÁI ROADMAP (Bước 4 WFO)
- **Bước 0,1,2** ✅. **Bước 3** (margin-call) ⏸ hoãn — Uni xác nhận chạy 1x KHÔNG cần margin-call.
- **WFO gate (TASK-107)** ✅ DONE: 14/14 quý dương, gate WFO ổn định ≈ gate cũ. Report `docs/reports/107.md`.
- **Bước 4 (WFO chiến lược)** 🔄 ĐANG Ở ĐÂY. Thứ tự: sensitivity giảm gene (đang chạy) → vá hàm mục tiêu → HPO genome selector → A/B công bằng.

## HÀM MỤC TIÊU (đã làm nền, GÁC chờ Uni)
- `HPOFitnessCalculatorV4` thiết kế TỐT: tách constraint cứng (maxDD-cap 65%, %lệnh>7d ≤2%, %năm-dương ≥80%, min-trade) khỏi mục tiêu (Calmar); Sortino chỉ làm cờ đỏ.
- `FitnessBaselineTool` (committed): chạy A/B/C qua V4 + per-quý. KQ FAST (2025-10..2026-04):
  - A (AI thật) fitness=0.335, PnL +6571, maxDD **56%**, 3/3 quý dương (Q4 +11.4%, Q1 +3.9%, Q2 +2.7%).
  - B (no-filter) BURN -116962, C (placebo) BURN -111139. → **V4 xếp hạng ĐÚNG (A>B,A>C).**
- **Lỗ hổng V4 cần vá (vừa đủ):** Calmar toàn-kỳ KHÔNG phạt gập ghềnh giữa quý. Vá = đưa ổn-định-theo-thời-gian vào mục tiêu (Sortino vào fitness hoặc Calmar-theo-quý). KHÔNG đụng margin-call.
- **Đã chốt nguyên tắc:** target "5%/quý + phạt" là SAI/nguy hiểm (ngưỡng tùy tiện, phá thích nghi regime, là penalty mềm). Đúng = "% quý dương cao + không quý lỗ quá X% + phạt gập ghềnh". Số thật: chỉ 1/3 quý >5% → 5% quá tham vọng.
- **maxDD 56% là điểm yếu lớn nhất** — tối ưu đáng giá nhất = giảm maxDD qua DCA ladder + breaker, KHÔNG nặn thêm PnL.

## CÔNG CỤ ĐÃ COMMIT (TASK-111)
- `FitnessBaselineTool.java` — baseline + validate hàm mục tiêu.
- `SensitivityTool.java` — OAT sensitivity, arg `MODE LEVELS FROM:TO`, env `SENS_KAGGLE=1` ép đọc 226.
- `GENE_AUDIT_TASK111.md` — bản đồ 26 gene thật (6 tầng) + đề xuất thêm/bớt/ghép.
- Commits: 707a4c9 (SensitivityTool Kaggle fix), + các commit trước (FitnessBaselineTool, gene audit).

## GENE THIẾU (đang hardcode — cân nhắc THÊM khi chốt genome, Uni quyết)
- **DCA margin ladder** (DcaUtils 4 bậc 1.5/2.0/2.5/3.0→-0.6/-0.7/-0.9/-0.99) — điều khiển rủi ro đuôi mạnh nhất, đang hardcode. Quan trọng nhất.
- Trailing "nhả nửa lãi 0.5f", budget hardcode (≥0.9→/4, switch→/3).

## NGUYÊN TẮC (giữ nguyên)
- Rà gene theo BACKTEST THẬT, KHÔNG theo HPO code (HPO code rác/phân mảnh: RunOptimizationCombined 12 gene, WFOTier1/2/3 chết).
- Đo không đoán. Pre-register tiêu chí. Java là nguồn chân lý. Build local JDK17 `--release 11` → scp. SLF4J. Output /d/claudedata hoặc ~/claudedata.
- Planning ở lại với Uni: Claude đề xuất + chứng minh số, KHÔNG tự chốt thay đổi lớn (hàm mục tiêu, genome).
