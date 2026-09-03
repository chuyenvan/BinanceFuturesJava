# PRE-REG RND — HẰNG SỐ HPO NHIỀU CHỮ SỐ CÓ LOAD-BEARING KHÔNG?

*Viết TRƯỚC khi chạy, 2026-09-03. Xuất phát từ nhận xét của Uni: "vẫn dùng mấy cấu hình 4 chữ số thập phân là overfit rồi".*

## Vì sao phải thử
Các hằng số 5 chữ số trong `Configs.java` là **di sản HPO chạy trên range đã nhiễm** — chưa ai kiểm chúng có thật sự quyết định kết quả hay chỉ là số lẻ vô hại. Nếu kết quả phụ thuộc chữ số thập phân thứ 3 thì C2b là overfit và **không được chốt**.

### Trước hết: phần lớn đã chết rồi (rà code, không đoán)

| hằng số | trạng thái trong engine |
|---|---|
| `BUDGET_MARGIN_RATIO_1=0.4820`, `BUDGET_DIVIDER_1=1.5578`, `BUDGET_MARGIN_RATIO_2=0.7475`, `BUDGET_DIVIDER_2=1.5984` | **CHẾT** — `managerBudget` FROZEN v1 (2026-08-24) thay "vách rời rạc = overfit" bằng throttle liên tục 2 gene tròn: `F_BASE=0.03`, `U_MAX=0.6`. Bốn hằng số này chỉ còn trong tool HPO. |
| `TS_DYNAMIC_K=0.29774` | **CHẾT** — `calRateMinWithPredReturn15MForTradingStop` đã FROZEN bỏ, chỉ còn trong tool HPO. |
| `TS_PROFIT_MULTIPLIER=5.21847` | **TRƠ** với C2b — `TS_GIVEBACK_MODE=1` ⇒ ratchet liên tục, bỏ qua hệ số này. |
| `MS_*`, `PREDICT_SYMBOL_RATE_UP/DOWN_*` | **TRƠ** với C2b — `SELECTOR_ONLY_ENTRY=1` + `OFF_FLAT_HARD=true`. |
| `DENSITY_ALPHA=0.6`, `CIRCUIT_DANGER_RATIO=0.7` | **TRƠ** — `BREAKER_MODE=OFF` (và đều là số tròn). |

### Còn sống — đúng 3 hằng số, và chúng quyết định AI ĐƯỢC VÀO LỆNH

| hằng số | giá trị | vai trò trong C2b |
|---|---|---|
| `AI_DYNAMIC_MULTIPLIER` | **1.28760** | độ dốc đường ngưỡng: `thr = 0.008 × max(MIN, score/0.15 × MULT)` |
| `AI_DYNAMIC_MIN` | **0.26787** | sàn ngưỡng, bind khi `score < 0.0312` |
| `AI_DYNAMIC_MAX` | **2.14135** | **trần ứng viên**: `0.15 × 2.14135 = 0.32120`; coin score cao hơn không bao giờ là ứng viên |

Đã mở env override (`SIM_AI_DYNAMIC_MULTIPLIER`, `SIM_AI_DYNAMIC_MAX`; `SIM_AI_DYNAMIC_MIN` có sẵn), default = giá trị cũ ⇒ byte-identical. Parity gate đã chạy cùng vòng tối giản profile.

## Thiết kế — 2 biến thể, không hơn

Nền = **C2b tối giản** (profile đã verify byte-identical với C2b gốc).

| run | MULTIPLIER | MIN | MAX | trần ứng viên |
|---|---|---|---|---|
| **C2b_MIN** (nền) | 1.28760 | 0.26787 | 2.14135 | 0.32120 |
| **RND1** — làm tròn 2 chữ số | **1.29** | **0.27** | **2.14** | 0.32100 |
| **RND2** — số tròn | **1.3** | **0.25** | **2.0** | 0.30000 |

Không dò thêm giá trị nào sau khi thấy kết quả. Không đổi tham số khác.

## Tiêu chí (chốt TRƯỚC)

Nền C2b: equity **60,390** · CAGR **24.48%** · maxDD **−13.12%** · quý dương 8/10 · quý ≥+5% 6/10 · không năm nào âm.

**Kết luận "hằng số KHÔNG load-bearing"** ⟺ **CẢ HAI** RND1 và RND2 đạt hết:
1. |ΔCAGR| ≤ **2.0pp** (tức CAGR trong [22.48, 26.48])
2. |ΔmaxDD| ≤ **2.0pp** (tức maxDD ≥ −15.12%)
3. quý dương ≥ **8/10**
4. không năm nào âm

## Ba kịch bản, cách đọc đã chốt trước

- **Cả hai PASS** ⇒ số lẻ chỉ là vết HPO vô hại. **Thay bằng số tròn** trong cấu hình đóng băng: đơn giản hơn, trung thực hơn, không mất gì. Đây là kết quả tốt.
- **RND1 pass, RND2 fail** ⇒ cơ chế có optimum thật gần đó nhưng **C2b mong manh ở chữ số thập phân thứ nhất**. Phải đo cả cao nguyên (plateau) quanh giá trị đó trước khi chốt — như đã làm với `arm` (4/5/6/7/8% → plateau 6–8%, chọn tâm 7%).
- **RND1 FAIL** ⇒ kết quả phụ thuộc chữ số thập phân thứ 3 ⇒ **overfit đã xác nhận, C2b KHÔNG được chốt.** Phải đo plateau và chọn tâm, hoặc bỏ hẳn cơ chế ngưỡng-động.

## Ràng buộc
- DEV only (`SIM_END_DATE=20240630`). Không chạm VALIDATION.
- Mỗi run in `PROFILE_HASH` để về sau không phải đoán config.
- Oracle chạy một job java tại một thời điểm.
