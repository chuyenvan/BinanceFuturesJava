# PREREG_COST_LIQUIDITY — (2) ngưỡng thanh khoản/biến động theo decile lệnh T170 + (1) audit mô hình chi phí & điểm hòa vốn

Ngày chốt: **2026-09-23**. Trạng thái: **chốt TRƯỚC khi đo** (commit file này rồi mới chạy script).
**Thuần Python** (numpy/pandas + `aerospike`/`cramjam` chỉ để ĐỌC). **KHÔNG** `claude-run`/Claude Code,
**KHÔNG** chạy Java trên Oracle (đang có job shadow), **KHÔNG push**, **KHÔNG dùng dữ liệu 2026**
(mốc dữ liệu ≤ 2025-12-31). DEV = 2022-01..2025-12 là **chính**; khi nào thêm 2021 thì dán nhãn rõ là phụ.

---

## 0. Hai việc này độc lập nhau

| Việc | Câu hỏi | Kết cục nếu xấu |
|---|---|---|
| **(2) Decile thanh khoản** | Lệnh T170 ở nhóm **kém thanh khoản nhất** có **lỗ net** không? Bao nhiêu % PnL tập trung ở nhóm thanh khoản cao? ⇒ **có nên cắt bớt universe theo thanh khoản** và cắt ở mức nào? | Nếu decile kém thanh khoản vẫn dương một cách nhất quán trên **mọi** ngưỡng thử ⇒ **KHÔNG** cắt (cắt = bỏ lãi). Nếu âm rõ ⇒ cắt là hợp lý, nhưng phải báo **nhiều** ngưỡng. |
| **(1) Audit chi phí + hòa vốn** | Mô hình chi phí trong sim có **khớp thực tế** không? Từng nhóm lệnh sống được tới **mức chi phí tối đa** bao nhiêu? | Nếu sim đắt hơn thực tế nhiều lần ⇒ kết luận "NO-GO" trước đây có thể do chi phí giả, cần **giảm slip tới đâu** mới có cửa. |

Hai việc **không** trộn kết luận: (2) dùng PnL/cost **nguyên trạng của run** (không đổi chi phí);
(1) mới là nơi quét chi phí.

---

## 1. Dữ liệu (chốt)

| Nguồn | Đường dẫn | Ghi chú |
|---|---|---|
| Lệnh T170 | `/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv` | md5 **`efb793e2468ca3a7318da0f0f0ad23d4fc`** (đã kiểm lại), 1089 dòng + header |
| Nến 1m + thanh khoản | `/home/ubuntu/claudedata/rvb_1m/raw/<SYM>USDT.f32` | 627 symbol, dtype `[ts<i4, o,h,l,c,v <f4]`, **ts = PHÚT EPOCH UTC**, v = `totalUsdt` (đã kiểm chứng, xem §2) |
| Funding | Aerospike `test.funding_data` (127.0.0.1:3222), bin `f_data` | Snappy(JSON `{ts_ms: rate}`) |
| Neo MOM15 | `/tmp/funding_factor/cache2.npz` + `/tmp/.trash_mine/range4h_topk_*/anchor_mom15.npz` | sinh bởi `range4h_topk.py` (commit `62e01bf`), giữ nguyên định nghĩa net |

### Bảng cột `printDone.csv` — ngữ nghĩa đã kiểm chứng

- `start` / `time_start_format` là **GMT+7** (đã chứng minh: PIPPIN `start=20251201 07:09` ⇒ nến UTC `2025-12-01 00:09` mới khớp **đúng** `entry`).
- `profit` = **gross** %: (`tp`/`entry` − 1)×100 (side BUY). Không phí.
- `pnl` = **net USDT** = `quantity*(tp-entry) − quantity*entry*RATE_FEE − quantity*entry*SLIPPAGE_RATE*2 − calFundingFee()`
  (nguồn: `research/OrderTargetInfoTest.java` → `calTp()`, gọi trong `TraceOrderDone.printOrderTestDone`).
- `margin` = `quantity*entry`. ⇒ **net% trên notional = `pnl/margin*100`**.
- `level` ∈ {`PREDICT_SYMBOL_TRADE` (selector), `BIG_DOWN`, `DCA_LEVEL1`}.
- `volume` = **`totalUsdt` của chính phút vào lệnh** (đã kiểm chứng 200/200 dòng khớp byte-for-byte với raw). ⇒ **KHÔNG dùng cột này làm biến causal**; chỉ dùng làm ô đối chiếu.

---

## 2. Chứng minh nguồn thanh khoản (làm TRƯỚC, ghi vào RESULT)

1. Đọc Aerospike `test.kline_1m_opt`, key `yyyyMMdd-HHmm` (GMT+7), bin `data` = **Snappy(protobuf `MinuteDataFinal`)**
   — map `sym -> KlineObjectOptimized{priceOpen(1), maxPrice(2), minPrice(3), priceClose(4), totalUsdt(5)}`,
   dùng `.proto` có sẵn ở `src/main/proto/MinuteDataFloat.proto`.
2. So **cùng một phút cùng một symbol** giữa Aerospike và `raw/<SYM>.f32`: nếu `raw.v == totalUsdt` thì
   raw hợp lệ làm nguồn thanh khoản. Báo cả kết quả khớp và kết quả **không** khớp; nếu không khớp ⇒ **DỪNG**, ghi rõ bị chặn.
3. So `raw.v` tại phút vào lệnh với cột `volume` trong printDone cho **cả 1089** lệnh (không lấy mẫu).

---

## 3. VIỆC (2) — tham số CHỐT (không sửa sau khi chạy)

Biến **causal tại thời điểm vào lệnh** `t` (phút UTC của nến `entry`); mọi cửa sổ **kết thúc tại `t−1`** (nến
cuối đã đóng), tức KHÔNG bao giờ đọc nến `t`:

| Tên | Định nghĩa | Coverage tối thiểu |
|---|---|---|
| **`L60`** (CHÍNH) | mean `totalUsdt` trên `[t−60, t−1]` | ≥ 48/60 nến có mặt |
| `L240` (phụ) | mean `totalUsdt` trên `[t−240, t−1]` | ≥ 192/240 |
| `R1` (biến động, phụ) | `(high−low)/open` của nến `t−1` | nến `t−1` có mặt |
| `R15` (biến động, phụ) | `(max high − min low)/open` trên `[t−15, t−1]` | ≥ 13/15 |

Chuẩn hoá: `totalUsdt` đọc trực tiếp (USDT/1 phút). Lệnh không đủ coverage ⇒ **loại khỏi mọi bảng** và **báo số loại**.

### 3.1 Chia decile

- Chia **ĐÚNG 1089 lệnh T170** (không thêm universe, không lọc trước theo bất cứ thứ gì khác).
- Xếp hạng **rank-based**: sort theo `(giá trị chỉ số, −pnl, sym)` để **tất định tuyệt đối** khi trùng giá trị;
  decile `d=1..10` = 10 nhóm đều nhau `⌈n/10⌉` (nhóm đầu là **kém thanh khoản nhất / biến động nhỏ nhất**);
  decile 10 = thanh khoản cao nhất. Báo n thực từng decile.
- Chỉ số chính = `L60`. Làm lại y hệt cho `L240`, `R1`, `R15` (đều báo ở §5.3).

### 3.2 Mỗi decile báo

`n` · `Σpnl` (USDT) · `Σmargin` (USDT) · `meanP_net` = 100·Σpnl/Σmargin · `mean_gross` = mean(`profit`) ·
`win%` = tỉ lệ lệnh `pnl > 0` · `slip_proxy` = mean(0.5·(`high`−`low`)/`close`) **tại nến vào lệnh `t`**
(theo đúng convention repo, dùng làm *ước lượng* slip — KHÔNG phải số đo thực) ·
`%Σpnl` đóng góp và `%Σpnl` luỹ kế từ decile 10 xuống.

### 3.3 Khoảng tin cậy (bắt buộc cho decile thấp nhất và cao nhất)

Bootstrap **block theo ngày lịch** (block = 1 ngày GMT+7 của `start`), 2000 rep, seed `20260923`,
trên `meanP_net` từng decile. Báo CI 95%.

### 3.4 Quét ngưỡng cắt (BÁO HẾT, KHÔNG chọn ngưỡng tốt nhất)

Xét "cắt" = **chỉ giữ lệnh có `L60 ≥` phân vị p của `L60` trên chính 1089 lệnh**, với
`p ∈ {0, 5, 10, 20, 30, 40, 50, 60}` (p=0 là không cắt). Mỗi ngưỡng báo: `n giữ`, `%lệnh bị cắt`,
`Σpnl` giữ được, `%Σpnl` giữ được, `meanP_net` giữ, `win%` giữ.
**Quy tắc đọc (chốt trước, chống chọn-bừa):** chỉ coi là "nên cắt" nếu **mọi** ngưỡng trong `{5..40}` đều
cho `meanP_net` **tăng đơn điệu** so với không cắt **VÀ** decile thấp nhất có CI 95% **nằm ngoài 0 về phía âm**.
Ngược lại ⇒ **KHÔNG cắt**, kể cả khi một ngưỡng nào đó trông đẹp.

### 3.5 Giới hạn nhận thức (ghi trước để không overclaim)

Decile ở đây là **trên chính 1089 lệnh của MỘT run** (`X1_GS_T170_2021`) ⇒ lệnh tồn tại **chỉ vì selector
đã chọn coin đó** (selection bias). Vì vậy §3 kết luận được **"trong các coin selector đã chọn, nhóm thanh
khoản thấp có lỗ không"**, KHÔNG kết luận được "coin thanh khoản thấp nói chung lỗ".

---

## 4. VIỆC (1) — tham số CHỐT

### 4.1 Liệt kê hằng số chi phí

Quét `src/main/java/**/*.java`, `profiles/*.properties`, `configs/*.properties` (grep `RATE_FEE|SLIPPAGE|SPREAD|
FEE|funding|FUNDING|commission`). Với mỗi hằng: giá trị, `file:dòng`, nơi **áp** (mỗi chân? mỗi lệnh? phân biệt
maker/taker?), có bị profile/env override không, và **giá trị đang chạy** của `x1_gs_t170.properties`.
Bắt buộc nêu rõ hằng **KHÔNG phải chi phí** dù tên gợi chi phí (kiểm `RATE_PROFIT_STOP_MARKET`).
Nêu **mâu thuẫn nội bộ** nếu phát hiện (chỗ in cost khác chỗ áp cost).

### 4.2 Số đo từ dữ liệu

- `cost_implied` mỗi lệnh = `profit` − `pnl/margin×100` (pp). Báo mean/median theo `level`.
  Kỳ vọng = `RATE_FEE + 2·SLIPPAGE_RATE` = 0,800% **± funding**.
- `slip_proxy` = 0,5·(h−l)/c tại nến vào lệnh, theo `level` và theo decile thanh khoản (bắc cầu với §3).
- **So thực tế**: Binance USDⓈ-M — taker **0,05%**/leg (đã có trong repo: `PREREG_HARNESS_CONTROL.md:38`,
  `PREREG_HEDGE_OVERLAY_A.md:117`), maker **0,02%**/leg ⇒ round-trip taker/taker **0,10%**, maker/maker **0,04%**.
  Nếu repo có **bằng chứng slip đo được** (log fill thật / ledger) thì dùng; **không có thì ghi rõ là không có**,
  KHÔNG bịa số. `ledger.csv` ở gốc repo là dữ liệu test tổng hợp (AAA/CCC) — **không** dùng làm bằng chứng thực.

### 4.3 Điểm hòa vốn theo nhóm lệnh

Với `c` = chi phí **round-trip** mỗi lệnh ∈ **{0,02% (maker), 0,05%, 0,10% (taker), 0,15%}**:

- **T170 theo `level`** (3 nhóm: `PREDICT_SYMBOL_TRADE`, `BIG_DOWN`, `DCA_LEVEL1`) **và toàn bộ 1089 lệnh**:
  `net(c) = mean_gross − c`. Báo thêm **`c*` = `mean_gross`** (mức chi phí tối đa còn dương, đơn vị %, round-trip)
  và `%lệnh` có `profit > c`. Cân bằng **theo từng lệnh rồi lấy mean** (equal-weight mỗi lệnh), KHÔNG theo vốn.
- **Neo MOM15**: dùng lại `anchor_mom15.npz`, HOLD 24h, `base = mean(m_raw[1440] − m_slip − m_fund[1440])`
  **không phí** (đúng định nghĩa vòng trước) ⇒ `net(c) = base − c`. Đối chiếu `net(0,10%)` DEV phải ra **+1,6690%**
  (±0,05pp); **lệch ⇒ VOID** (bộ đo hỏng, không kết luận gì từ (1)).
- **2–3 ứng viên gần nhất** (đọc số đã công bố, KHÔNG chạy lại tốn kém): `FUNDING_TOPK_ROTATE` §4
  (0,05/0,10/0,15% đã có sẵn) + `RANGE4H_TOPK` (idem) + một ứng viên nữa có bảng phí. Ghi `net(c)` và `c*`
  (mức phí tối đa còn dương). Nếu file không có bảng phí ⇒ bỏ ứng viên đó và nói rõ, không tự suy.

### 4.4 Kết luận bắt buộc của (1)

(a) mô hình chi phí sim **khớp / không khớp** thực tế, **lệch bao nhiêu lần**, theo **từng thành phần**
(fee, slip); (b) **cần giảm slip tới đâu** để từng nhóm có cửa — trả lời bằng `c*` và **hai** ước lượng độc lập:
`slip_proxy` đo từ dữ liệu, và phần dư `cost_implied − RATE_FEE`.

---

## 5. Cổng tự-kiểm (fail ⇒ báo bị chặn, KHÔNG bịa)

| Cổng | Điều kiện |
|---|---|
| G1 | md5 printDone = `efb793e2468ca3a7318da0f0f0ad23d4fc`, n = 1089 |
| G2 | `raw.v == totalUsdt` Aerospike tại ≥ 1 phút/symbol kiểm chứng, và `raw.v == volume` cho ≥ 95% trong 1089 lệnh |
| G3 | Mọi lệnh dùng được có `t` suy từ `start` GMT+7 và có nến tại `t` (khớp `entry` ±0,5%) |
| G4 | MOM15 DEV 24h `net(0,10%)` = +1,6690% ±0,05pp |
| G5 | Không có bản ghi nào ngày ≥ 2026-01-01 lọt vào bảng |

## 6. Trung gian + dọn dẹp

Trung gian: `/tmp/liq_decide/` (resume được từng phần; ghi ra file NGOÀI repo ngay sau mỗi bước).
Sản phẩm: `docs/RESULT_COST_LIQUIDITY.md` + `research/analysis/liq_decile_t170.py` +
`research/analysis/cost_breakeven.py`. Commit (**KHÔNG push**), dọn file tạm sau khi commit.
