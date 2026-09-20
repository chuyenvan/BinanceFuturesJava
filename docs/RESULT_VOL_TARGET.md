# RESULT_VOL_TARGET — TASK 5: VOL_TARGET sizing (2026-09-20)

Pre-reg: `docs/PREREG_VOL_TARGET.md` (commit `58c5d48`, trước khi chạy COIN/PORTFOLIO).
k=2 (COIN, PORTFOLIO), CI block-72h × sqrt(2 ln 2)=1.1774, 2000 rep, seed 20260905.

## 0. Kết luận một dòng

**Cả hai variant đều NULL** ở rate chất lượng (đúng như dự đoán ghi trước). Về rủi ro phụ:
**COIN cải thiện rủi ro thật** (maxDD/sd/Calmar/CV đều tốt hơn) — đúng như dự đoán, đây là
**cải thiện quản trị rủi ro, KHÔNG PHẢI bằng chứng alpha**. **PORTFOLIO làm XẤU ĐI rủi ro ở MỌI
năm** (maxDD, UW, sd, CV đều tệ hơn) — **ngược với dự đoán** — vì target-vol 25%/năm đã chọn
CAO HƠN vol tự nhiên của T170 (~14.5%/năm), nên cơ chế chủ động TĂNG đòn bẩy thay vì giảm.

## 1. Cổng OFF byte-identical — PASS

`X1_GS_T170_2021_VT_PARITY` (profile `x1_gs_t170.properties` không sửa, chạy với jar mới có
thêm nhánh `VolTargetSizing` nhưng mặc định OFF):

```
n=1089, b:111070, md5(printDone.csv) = efb793e2468ca3a7318da0f0ad23d4fc
```

Khớp CHÍNH XÁC với md5 tham chiếu `efb793e2468ca3a7318da0f0ad23d4fc` của T170
(`docs/AGENT_RUNBOOK.md` §3, `X1_GS_T170_2021`). **Byte-identical — cổng bắt buộc PASS**, tin
được số của COIN/PORTFOLIO dưới đây.

## 2. Bảng chính + CI (toàn cửa sổ)

| tag | n | win% | TSloss% | mP&#124;SM | mP&#124;SL | meanP | mMargin | maxDD% | UW | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PARITY (T170) | 1089 | 88.25 | 9.73 | 7.642 | −16.992 | 5.244 | 1851 | −11.84 | 92 | 111070 | 29.27 |
| COIN | 1095 | 88.22 | 9.68 | 7.266 | −16.992 | 4.918 | 1068 | −8.13 | 88 | 80307 | 20.28 |
| PORTFOLIO | 1085 | 88.20 | 10.14 | 7.917 | −17.138 | 5.377 | 2548 | −13.42 | 164 | 123665 | 32.39 |

### CI (variant − PARITY), toàn cửa sổ, 4 rate chất lượng theo luật thắng (win%, TSloss%, meanP, mP|SL)

| variant | rate | hiệu | lo | hi | ngoài CI |
|---|---|---|---|---|---|
| COIN | win% | −0.027 | −0.131 | 0.073 | − |
| COIN | TSloss% | −0.053 | −0.112 | 0.009 | − |
| COIN | meanP | −0.326 | −0.775 | 0.045 | − |
| COIN | mP&#124;SL | 0.000 | 0.000 | 0.000 | − |
| PORTFOLIO | win% | −0.043 | −0.112 | 0.009 | − |
| PORTFOLIO | TSloss% | 0.405 | −0.059 | 0.867 | − |
| PORTFOLIO | meanP | 0.133 | −0.194 | 0.478 | − |
| PORTFOLIO | mP&#124;SL | −0.146 | −1.557 | 1.003 | − |

**0/4 rate ngoài CI cho CẢ HAI variant, toàn cửa sổ VÀ mọi năm riêng lẻ (2021–2025)** — xem log
đầy đủ `research/analysis` output (`x1_rates.py --k 2`) đã chạy 2026-09-20. `mP|SL` bằng 0 tuyệt
đối ở phần lớn năm vì sizing không đổi coin/thời điểm nào bị STOP_LOSS — đúng cơ chế (sizing
không đổi lệnh nào được chọn). `mMargin` ngoài CI ở cả hai variant (dự kiến — đó chính là kênh
sizing đổi) nhưng **không tính vào luật thắng** (loại trừ tường minh trong pre-reg §2.5 và trong
`x1_rates.py`).

⇒ **Luật thắng (≥2/4 rate ngoài CI cùng hướng): 0/4 cho cả hai variant ⇒ NULL cho cả COIN và
PORTFOLIO** trên tiêu chí rate chất lượng. Đúng như dự đoán ghi trước.

## 3. Rào cứng theo năm (khẩu vị MỚI: maxDD≤30%, UW≤200, năm không âm, quý≥−15%)

| tag | năm | maxDD% | UW | ret_năm% | quý_min% | PASS (mới) |
|---|---|---|---|---|---|---|
| PARITY | 2021 | −2.46 | 37 | 12.21 | 4.44 | PASS |
| PARITY | 2022 | −11.84 | 72 | 19.58 | 2.90 | PASS |
| PARITY | 2023 | −2.73 | 63 | 34.96 | −0.37 | PASS |
| PARITY | 2024 | −6.60 | 92 | 32.14 | −0.92 | PASS |
| PARITY | 2025 | −4.23 | 52 | 32.71 | 1.27 | PASS |
| COIN | 2021 | −2.04 | 37 | 8.25 | 2.76 | PASS |
| COIN | 2022 | −8.13 | 73 | 15.51 | 2.34 | PASS |
| COIN | 2023 | −2.61 | 88 | 20.69 | −0.03 | PASS |
| COIN | 2024 | −4.06 | 88 | 23.07 | −0.09 | PASS |
| COIN | 2025 | −2.21 | 52 | 23.60 | 1.17 | PASS |
| PORTFOLIO | 2021 | −3.93 | 37 | 13.19 | 4.51 | PASS |
| PORTFOLIO | 2022 | −13.42 | 72 | 21.74 | 3.26 | PASS |
| PORTFOLIO | 2023 | −4.71 | 63 | 43.24 | −0.24 | PASS |
| PORTFOLIO | 2024 | −10.53 | 119 | 41.49 | −2.68 | PASS |
| PORTFOLIO | 2025 | −6.12 | **164** | 26.67 | 1.27 | PASS (mới; FAIL ở ngưỡng CŨ 120) |

Cả ba PASS toàn bộ rào cứng theo khẩu vị MỚI. **Lưu ý**: `x1_rates.py` tự in PASS/**FAIL** bằng
ngưỡng CŨ (15/120/−5, chưa cập nhật) — cột `PASS (mới)` ở trên do agent tự chấm lại bằng số thô
theo ngưỡng MỚI của `docs/RISK_APPETITE.md`. PORTFOLIO 2025 UW=164 ngày là dòng DUY NHẤT phân
biệt CŨ/MỚI (FAIL cũ → PASS mới).

**Rào cứng "tập trung 1 coin ≤15% equity": KHÔNG đo trong round này** — `x1_rates.py` không
xuất số này, và đo riêng cần công cụ khác (giống task `CONC_CAP_PERCOIN`, không nằm trong ước
tính 1 ngày của TASK 5 này). Ghi nhận đây là khoảng trống, không ảnh hưởng verdict NULL vì tiêu
chí rate quyết định đã chốt ở mức 0/4.

## 4. Metric phụ: sd(return ngày), Calmar, CV quý

Tính từ chuỗi equity thật (resample ngày, log-return, `ddof=1`; Calmar=CAGR/|maxDD| toàn cửa
sổ; CV=sd(quý)/mean(quý) trên 16 quý 2022Q1–2025Q4):

| tag | sd(ret ngày) | sd annualize (×√365) | CAGR | maxDD | Calmar | CV quý |
|---|---|---|---|---|---|---|
| PARITY (T170) | 0.757% | 14.46% | 29.25% | −11.84% | 2.469 | 0.749 |
| COIN | **0.520%** | **9.93%** | 20.26% | **−8.13%** | **2.494** | **0.675** |
| PORTFOLIO | **0.904%** | **17.26%** | 32.37% | **−13.42%** | **2.412** | **0.898** |

- **COIN**: sd ngày giảm 31% (0.757%→0.520%), maxDD giảm từ −11.84% xuống −8.13% (tốt hơn ở CẢ
  5 năm — xem bảng §3), Calmar nhích lên nhẹ (2.469→2.494), CV quý giảm (đều hơn). Đổi lại CAGR
  giảm (29.27%→20.28%) — đánh đổi lợi nhuận lấy sự ổn định, đúng bản chất risk-parity (giảm size
  các coin altcoin biến động cao mà chiến lược này hay chọn).
- **PORTFOLIO**: sd ngày TĂNG 19% (0.757%→0.904%), maxDD XẤU ĐI ở **CẢ 5 NĂM KHÔNG TRỪ NĂM NÀO**
  (xem bảng §3), UW xấu đi rõ ở 2024 (92→119) và 2025 (52→164), Calmar giảm nhẹ (2.469→2.412),
  CV quý TĂNG (0.749→0.898, biến động ROI quý sang quý lớn hơn). CAGR tăng (29.27%→32.39%) —
  nhưng đây là tăng ĐÒN BẨY đi kèm tăng rủi ro tương ứng, không phải Calmar tốt hơn.

## 5. Vì sao PORTFOLIO đi ngược dự đoán — phân tích nguyên nhân (không phải bug)

`TARGET_ANNUAL_VOL = 0.25` (25%/năm) được chốt TRƯỚC khi chạy (pre-reg §2.3), chọn như một con
số "hợp lý" độc lập, KHÔNG đối chiếu với vol tự nhiên của chính T170. Nhưng vol thật đo được của
T170 (PARITY) chỉ **14.46%/năm** — THẤP HƠN target 25%. Cơ chế vol-target hoạt động ĐÚNG như
thiết kế: `multiplier = targetDailyVol / sigma_equity_20d`; khi vol đo được (nội suy từ 20 ngày
gần nhất) thấp hơn target, multiplier > 1 → chiến lược được lệnh **TĂNG size** để cố kéo vol lên
gần 25%. Kết quả: đòn bẩy hiệu dụng tăng → CAGR tăng NHƯNG maxDD/sd/UW cũng tăng theo — đúng
quan hệ risk-return, KHÔNG phải lỗi tính toán hay look-ahead. Đây là **rủi ro đã cảnh báo trước
khi chạy** trong ngành thực tế của vol-targeting: chọn target sai phía (cao hơn vol tự nhiên) sẽ
làm chiến lược pro-cyclical/leverage-up thay vì giảm rủi ro. Bài học: một target-vol hợp lý cho
mục đích GIẢM rủi ro phải được chọn THẤP HƠN (hoặc bằng) vol tự nhiên đo được của baseline — ở
đây nên là một số ≤14% chứ không phải 25%. **KHÔNG được sửa hằng số này và chạy lại trong round
này** (pre-reg §2.4 cấm mở biến thể thứ 3 sau khi thấy số) — đây là input cho một pre-reg MỚI,
round MỚI nếu muốn thử lại PORTFOLIO với target thấp hơn.

## 6. Đối chiếu dự đoán ghi trước

> "NULL ở các rate chất lượng chuẩn (win%, TSloss%, meanP, mP|SL) — đúng vì sizing không làm đổi
> lệnh nào được chọn vào/ra, chỉ đổi kích thước. Kỳ vọng cải thiện ở maxDD/UW/CV — đây là CẢI
> THIỆN RỦI RO, KHÔNG PHẢI bằng chứng alpha, phải ghi rõ như vậy trong RESULT."

- **Phần rate chất lượng NULL: ĐÚNG cho cả hai variant** (0/4 ngoài CI, mọi năm và toàn cửa sổ).
- **Phần "cải thiện maxDD/UW/CV": ĐÚNG cho COIN, SAI cho PORTFOLIO** (PORTFOLIO làm XẤU ĐI cả
  ba ở mọi năm — xem §5 để biết nguyên nhân cơ học, không phải bug).
- Câu "đây là cải thiện quản trị rủi ro, không phải bằng chứng alpha" **chỉ đúng cho COIN**.
  Với PORTFOLIO, kết luận đúng là: "đây là một phép thử quản trị rủi ro bị đặt sai tham số
  (target-vol cao hơn vol tự nhiên), không phải bằng chứng alpha lẫn bằng chứng cải thiện rủi
  ro — cần pre-reg mới với target-vol thấp hơn nếu muốn thử lại."

## 7. Kết luận cuối cùng theo luật thắng/thua

- **COIN: NULL** (0/4 rate chất lượng ngoài CI). PASS mọi rào cứng cứng theo khẩu vị mới. Ghi
  nhận cải thiện rủi ro phụ có thật (maxDD/sd/Calmar/CV đều tốt hơn) — đây là **cải thiện quản
  trị rủi ro, KHÔNG PHẢI bằng chứng alpha**, đổi lấy CAGR thấp hơn. Không đủ bằng chứng để đưa
  vào baseline, nhưng là một lựa chọn risk-preference hợp lệ nếu user muốn ưu tiên ổn định hơn
  CAGR.
- **PORTFOLIO: NULL** (0/4 rate chất lượng ngoài CI). PASS mọi rào cứng cứng theo khẩu vị mới
  (kể cả UW=164 của 2025, chỉ PASS nhờ ngưỡng MỚI 200 — sẽ FAIL ở ngưỡng CŨ 120). Rủi ro phụ XẤU
  ĐI ở mọi năm — KHÔNG khuyến nghị dùng target-vol=25% cho PORTFOLIO mode; cần round mới với
  target thấp hơn (≤14%) nếu muốn thử lại đúng mục đích giảm rủi ro.
- **Không mở biến thể thứ 3** trong round này (đúng kỷ luật pre-reg §2.4), kể cả khi PORTFOLIO
  cho kết quả không như kỳ vọng.

## 8. File & run tham chiếu

- Code: `src/main/java/com/binance/chuyennd/tradecore/VolTargetSizing.java` (mới),
  `Configs.java`, `research/BudgetManagerSimple.java`,
  `research/SimulatorMarketLevelTicker1MStopLoss.java` (commit `58c5d48`).
- Profile: `profiles/x1_gs_t170_vt_coin.properties`, `profiles/x1_gs_t170_vt_portfolio.properties`
  (bản sao `x1_gs_t170.properties` + 1 dòng `SIZE_VOL_TARGET_MODE=...`, KHÔNG commit — file phát
  sinh cục bộ trên Oracle theo đúng pattern các task trước, vd `dca_round_cap`).
- Devrun: `/home/ubuntu/java/devrun/X1_GS_T170_2021_VT_PARITY` (md5 `efb793e2468ca3a7318da0f0ad23d4fc`),
  `.../X1_GS_T170_2021_VT_COIN` (md5 `89334f676faa767d07db09037854a580`),
  `.../X1_GS_T170_2021_VT_PORTFOLIO` (md5 `9fd4c45aaf0b6fabfe72b287597e388e`).
- Chấm điểm: `python3 research/analysis/x1_rates.py --k 2 X1_GS_T170_2021_VT_PARITY
  X1_GS_T170_2021_VT_COIN` và tương tự `..._VT_PORTFOLIO`, chạy 2026-09-20.
