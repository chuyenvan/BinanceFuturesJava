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

---

## ĐÍNH CHÍNH 2026-09-03 (viết SAU khi có kết quả — đọc kỹ phần nào là kết quả, phần nào là đính chính)

### 1. Bảng "Còn sống — đúng 3 hằng số" mô tả SAI vai trò của `AI_DYNAMIC_MAX`

Dòng "**trần ứng viên**: `0.15 × 2.14135 = 0.32120`; coin score cao hơn không bao giờ là ứng viên" là **SAI**.
Nguồn: `docs/C2B_SPEC.md` mục 0 + `docs/FEAT40_LOOKAHEAD.md`.

- Tầng 1 (trần ứng viên `maxThres`) **bị bỏ qua hoàn toàn** khi `SELECTOR_RANK_TOPK=8` — nhánh rank
  top-K không đi qua nó (`SimulatorMarketLevelTicker1MStopLoss` ~dòng 307-322 chỉ còn ghi log debug).
  Đường live y hệt (`DetectEntrySignal2TradeNormal:322-327`).
- Tầng 2 **không có cận trên**: code chỉ có `Math.max(AI_DYNAMIC_MIN, scaleFactor)`, nhánh
  `Math.min(..., AI_DYNAMIC_MAX)` đã bị xoá. Ngưỡng **tăng đơn điệu** theo score: 0.214% → 2.206%.
  Không có chuyện "score ≥ 0.30 chạm trần rồi hằng 1.713%".
- Đo được: **0.017%** số hàng có score > 0.32120 **vẫn vượt** tầng 2 (2,551 dòng, `g1lite` chỉ +0.0521).

**Hệ quả cho chính thí nghiệm này:** RND2 đổi `AI_DYNAMIC_MAX` 2.14135 → 2.0, nhưng với
`SELECTOR_RANK_TOPK=8` thì hằng số đó **gần như trơ**. Vậy RND2 kiểm được **ÍT HƠN** ý định ban đầu:
nó chủ yếu kiểm `MULTIPLIER` và `MIN`, không kiểm `MAX`. Kết luận PASS của RND2 vẫn đứng, nhưng
phạm vi của nó hẹp hơn phần "Vì sao phải thử" tuyên bố.

### 2. Lời phê "'không mất gì' là SAI" — chính lời phê đó mới sai

`docs/AUDIT_APPLIED.md` Bảng 2 mục 3 từng viết: *"RND1 −387 / RND2 −544 USDT ⇒ mất thật 0.4-0.5pp
CAGR; pre-reg viết 'không mất gì' là sai"*. Đo lại bằng block-bootstrap ghép cặp
(`docs/PREREG_CI.md` → `docs/CI_REAUDIT.md`):

| cặp | hiệu CAGR | CI95 của hiệu | phán quyết |
|---|---|---|---|
| C2b vs RND1 (2 chữ số) | +0.32pp | **[−0.08, +0.81]** | không phân biệt được |
| C2b vs RND2 (số tròn) | +0.45pp | **[−0.63, +1.46]** | không phân biệt được |
| RND1 vs RND2 | +0.13pp | trong nhiễu | không phân biệt được |

387 và 544 USDT nằm **hoàn toàn trong nhiễu**. sd(hiệu CAGR) cho thay đổi kiểu này là 2.57pp —
lớn hơn "mất mát" quan sát được 5-8 lần. Vậy:

- Kết luận gốc của PRE-REG RND (**hằng số nhiều chữ số KHÔNG load-bearing**) **đứng vững**.
- **Không có 0.4-0.5pp nào phải đánh đổi.** Việc thay 3 hằng số bằng số tròn là **miễn phí** theo
  mọi phép đo hiện có, và nên làm — đúng như Uni yêu cầu.

### 3. Cách thi hành đã chọn: qua PROFILE, không sửa default trong `Configs.java`

Tạo `profiles/c2c_round.properties` = `c2b_min` + 3 hằng số tròn. Lý do **không** sửa
`Configs.java:307-309`:

1. Cổng nghiệm thu của mọi refactor là **byte-identity của `printDone.csv`** so với baseline C2b.
   Đổi default trong code sẽ phá mốc đó và phải dựng lại baseline — mất công cụ kiểm tốt nhất đang có.
2. Thiết kế cổng `Cfg` + `TRADING_PROFILE` vừa dựng nói rõ: tham số giao dịch thuộc **profile**,
   không thuộc default hardcode. Sửa default là đi ngược chính thiết kế đó.
3. GS wave-1 đang quét cả 3 chiều này với range rộng (`research/kaggle/gsearch/gen_params.py`) ⇒
   tâm vùng phẳng nó tìm ra sẽ **thay thế** việc làm tròn bằng tay. Chốt default bây giờ là chốt sớm.

Quyết định chuyển baseline mặc định sang `c2c_round` (hay sang một điểm plateau của wave-1) để
**sau khi wave-1 kết thúc**. Ghi trong `docs/RUNS_DEV.md`.
