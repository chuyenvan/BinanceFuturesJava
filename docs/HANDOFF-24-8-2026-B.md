# HANDOFF — phiên 2026-08-24 (tiếp `HANDOFF-24-8-2026.md`). Đọc file này TRƯỚC.

> Phiên trước mất bridge → mất `cpcv_validation.py` + prereg doc. Phiên này **đã commit chúng vào repo** nên
> không mất lần 2. Bridge lại rớt lúc cuối (đang thu kết quả LEG B) — kết quả **an toàn trên đĩa Oracle**.

## 0. VIỆC ĐẦU TIÊN KHI VÀO (1 lệnh, ~10s)

```bash
ssh -i /root/.ssh/ora_key -o StrictHostKeyChecking=no ubuntu@161.118.212.3 \
  'grep -a "EXPLORE12\|DONE_B\|^w" ~/khungv1/RESULT_B.txt; grep -a "VERDICT\|O (khung v1)" ~/khungv1/REPORT_B.md'
```

LEG B (12 window EXPLORE ≤2024, `WFO_OBJ_SOFT=true` + `SIM_MAX_HOLD_H=48`) chạy tới **w10 lúc 13:04 local**,
còn w11 (~3 phút) → gần như chắc chắn đã DONE. Nếu `REPORT_B.md` thiếu dòng `O (khung v1)` thì regenerate:

```bash
cd /home/ubuntu/claudedata/.run/oracle_worker_cwd && \
env WFO_STATE_HOST=127.0.0.1 WFO_STATE_PORT=3222 WFO_STATE_NS=test WFO_HARNESS_FIX=true WFO_OBJ_SOFT=true \
  java -cp /home/ubuntu/java/simulator/binance-khungv1-20260824.jar \
  com.binance.chuyennd.ai_ml.wfo.framework.WfoCoordinator report strategy_window
cp docs/reports/wfo_strategy_window.md ~/khungv1/REPORT_B.md
```

⚠️ `gatecount.jar` (GJAR) là **jar CŨ** — dùng nó chạy `report` sẽ ra markdown KHÔNG có dòng O. Luôn report bằng
`binance-khungv1-20260824.jar`.

## 1. ĐÃ LÀM XONG (đã commit, đã verify bằng số)

Branch **`feat/khung-v1-objective-o`** (từ `module`), 2 commit:

| commit | nội dung |
|---|---|
| `c13574a` | checkpoint WIP 85 file tracked của user (user yêu cầu dọn git). Không đưa untracked (`.bak_*`, `_to_delete/`, `_wfotmp/`) vào. |
| `b11fe56` | khung v1: objective O soft + knob MAX_HOLD_H + khôi phục CPCV harness |

### 1a. Objective O soft — `WFO_OBJ_SOFT=true`
- `HPOFitnessCalculatorV4`: thoát TRƯỚC chuỗi constraint cứng. Bỏ `TOO_FEW_TRADES`,
  `TOO_MUCH_CAPITAL_LOCK`, `UNSTABLE_ACROSS_YEARS`, bỏ thưởng-tần-suất V4.2.
  Còn 1 luật sống-còn: maxDD-cap **70%** (`WFO_SURVIVAL_MAXDD`). `ZERO_TRADES` → **0** (không phải −100000,
  nếu không 1 fold rỗng kéo sập median/std). Lỗ → Calmar âm, note `NEG_PNL` (giữ gradient).
- `StrategyWfoTask.aggregate`: `O = median_fold(Calmar_net) − 0.5·std_fold(Calmar_net)` trên **TOÀN BỘ** fold
  (không lọc theo note — lọc = tái tạo bẫy survivorship). Report-only khi `OBJ_SOFT=false`.
  Khi bật: PASS dùng ngưỡng v1 (%fold dương ≥80%, maxDD ≤70%) và đánh dấu **PARTIAL** vì PBO/DSR do harness quyết.
- Default OFF ⇒ byte-identical (đã CHỨNG MINH bằng số, xem §2).

### 1b. Knob `MAX_HOLD_H` — env `SIM_MAX_HOLD_H`, range tune v1 [4,240] giờ
- `Configs.MAX_HOLD_H` (default 0 = OFF) + `SimulatorMarketLevelTicker1MStopLoss.maybeTimeStop()`.
- Đóng MARKET tại `ticker.priceClose`, status **`STOP_LOSS_OVERTIME`** (enum có sẵn, trước đó chưa dùng ở đâu
  → đếm riêng được trong report).
- Mốc đếm giờ = `clusterFirstLegTime` (fallback `timeStart`) ⇒ **DCA nhồi thêm KHÔNG reset đồng hồ**.
- Chạy **SAU** TP/SL/trailing trong cùng nến — cố ý: TP/SL là lệnh chờ sẵn (resting) nên fill trước;
  time-stop là lệnh market chủ động. Áp cả long lẫn short.
- **KHÔNG** đưa vào GENOME 17 gene (sẽ vỡ `loadFrozenGenome` + baseline). Harness CPCV set knob **qua env**.
- `TP`/`TS_MULT` đã có sẵn env `SIM_RATE_PROFIT_STOP_MARKET` / `SIM_TS_PROFIT_MULTIPLIER`.
  `L_TP`/`L_SL` ở branch `feat/leakfree-2sided-rebuild`.

### 1c. Khôi phục 2 file đã mất
- `docs/project-memory/code/cpcv_validation.py` — self-test PASS, **khớp đúng số cũ**:
  28 path 0-leak · DSR deflate theo n_trials (0.805 → 0.000) · PBO noise **0.67** vs edge **0.00**.
- `docs/project-memory/preregistration_frame_v1_2026-08-23.md` — khung đóng băng v1.

### 1d. Verify
`mvn -DskipTests package` BUILD SUCCESS (449 file, jar 99,624,771 B, md5 `73673a50294e3bee0dab8025babea75b`).
`StrategyWfoTaskMetricTest` 6/6 PASS.

## 2. KẾT QUẢ ORACLE — LEG A (parity) ĐÃ XONG

`~/khungv1/RESULT_A.txt` · `REPORT_A.md` · script `~/_khungv1_explore.sh`

**`EXPLORE12 = 14357.9` — trùng khít baseline 12 window đầu, cả 12/12 window giống hệt từng số.**
Data khớp seal: ticker `b329fa06`, funding `779e2f8e`. Chạy 33 phút (04:54→05:27 UTC).
⇒ **Jar mới byte-identical khi tắt cờ.** Không tái diễn vụ jar-root-cause 17k-vs-20k.

Baseline 18w = 22687.6 = 20240.8 (16w) + 1888.7 + 558.0 (2 window 2026) — đã đối chiếu khớp.

## 3. PHÁT HIỆN MỚI — 2 cái, cái thứ 2 QUAN TRỌNG

### 3a. Fitness cũ reject GẦN NHƯ TOÀN BỘ window thắng (mạnh hơn bằng chứng cũ)
`BASELINE.txt`: **14/16 window đang LÃI đều mang note `TOO_MUCH_CAPITAL_LOCK`**; 2 window còn lại `BURN_ACCOUNT`.
Tức **0/16 window đạt `SUCCESS`** dù tổng +20240.8. Trước đây chỉ có bằng chứng 1 config (+1031 PnL bị fit=−100003).
LEG A xác nhận lại: 12/12 window `reject=1/1`, IS/OOS fitness ≈ −100015.
⇒ Mọi kết luận "no-edge" từ rolling WFO cũ đều **vô nghĩa về mặt thống kê** — HPO chưa từng được phép chọn.

### 3b. ⚠️ PHẢN BIỆN: `O = median − 0.5·std` PHẠT CẢ ĐUÔI TỐT — đo được, không phải lý thuyết

LEG A (report-only, `OBJ_SOFT=false`): **O = −0.2263** với `median = 0.6637`, `std = 1.7798`, n=12.

Calmar_net từng fold (LEG A):

| fold | calmar | ddPct | | fold | calmar | ddPct |
|---|---|---|---|---|---|---|
| w00 | 0.4529 | 5.5% | | w06 | 0.6185 | 2.8% |
| w01 | 0.5776 | 12.9% | | **w07** | **5.9431** | **1.2%** |
| **w02** | **3.5887** | **0.6%** | | w08 | 2.6349 | 3.4% |
| w03 | 0.0678 | 7.2% | | w09 | 0.2355 | 14.4% |
| w04 | 0.9393 | 1.6% | | w10 | 1.0914 | 6.2% |
| w05 | 0.0612 | 10.2% | | w11 | 0.7088 | 5.5% |

12/12 fold PnL **dương**, median Calmar 0.66 — nhưng `std` bị thổi lên 1.78 bởi **w07 (5.94) và w02 (3.59)**,
tức đúng 2 fold **TỐT NHẤT** (lãi tốt, maxDD cực nhỏ 0.6–1.2% vốn). Trừ `0.5·std` kéo O từ +0.66 xuống **−0.23**.

**Vấn đề:** `std` là 2 chiều, Calmar không có trần trên (maxDD→0 thì Calmar→∞), nên O đang **phạt kết quả xuất sắc**.
Một chiến lược ăn đều 12/12 quý bị chấm điểm ÂM. Nếu để nguyên, HPO sẽ được thưởng khi làm cho các fold tốt **tệ đi**.

Thêm 1 lỗi biên: `HPOFitnessCalculatorV4` dùng `absDD = max(1f, maxDrawdown)` — window nào maxDD < 1 USD sẽ
cho Calmar = netPnl (hàng trăm). Chưa nổ ở EXPLORE nhưng là mìn.

**Đề xuất cho v2 (KHÔNG tự sửa — khung đang FROZEN, sửa = pre-register mới):**
1. Downside-only: `O = median − 0.5·std_downside` (chỉ tính fold dưới median). Giữ đúng tinh thần "chống
   đứng-đỉnh-nhọn" mà không phạt đuôi tốt.
2. Hoặc dùng MAD/IQR thay std (robust với outlier).
3. Hoặc cap Calmar (vd min(Calmar, 3)) + sàn maxDD theo % vốn thay vì `max(1f, ...)` USD.

→ **Cần bạn quyết** trước khi chạm TEST 2025. Đây là thay đổi hàm mục tiêu = việc có tầm ảnh hưởng.

## 4. LEG B — đang/đã chạy, CHƯA thu số cuối

`WFO_OBJ_SOFT=true` + `SIM_MAX_HOLD_H=48`, cùng 12 window. Quan sát tới w10:

- `reject=0/1` (LEG A: `1/1`) ⇒ **hết reject cứng, code mới chạy đúng**.
- Fitness giờ là Calmar thật (0.048 / 0.492 / 4.58 / 1.26) thay vì −100015 ⇒ **objective mới hoạt động**.
- PnL đổi mạnh: w00 854.6 → **46.4**; w01 2681.7 → **1782.9**; w09 1223.3 → **717.3**; w10 2248.2 → **1645.4**
  ⇒ **time-stop 48h đang cắt lệnh thật** (chiến lược này là "nuôi", ép thoát 48h thì gãy).

⚠️ Đây là **DEBUG pipeline, KHÔNG kết luận** (đúng pre-registration). Cụ thể **không** được đọc "MAX_HOLD_H=48 làm
giảm PnL" thành "nuôi tốt hơn lướt" — 48h là giá trị chọn bừa để ép chạy code, không phải điểm tune.

⚠️ Artifact metric cần biết: WFE = PnL_OOS/PnL_IS, khi IS PnL ≈ 0 thì WFE nổ (w01 LEG B: **WFE=38.4**).
Với objective soft, WFE mất ý nghĩa ở fold IS gần 0 → tiêu chí `median WFE ≥ 0.5` của khung v1 **cần xem lại**
(gợi ý: chỉ tính WFE trên fold có |PnL_IS| ≥ ngưỡng, hoặc thay bằng tỉ số Calmar OOS/IS).

## 5. GIỚI HẠN CHƯA VƯỢT (đọc kỹ trước khi kết luận bất cứ gì)

- **`WFO_N_SAMPLES=1`** trong recipe baseline ⇒ chỉ 1 genome, **HPO KHÔNG search**. Nên cả LEG A và B chỉ chứng
  minh *plumbing*. Objective mới **chưa từng được thử với vai trò chọn genome**. Cần `WFO_N_SAMPLES=30` (đắt ~30×,
  ~10-15h cho 12 window) — đây là việc lớn tiếp theo.
- Chưa reproduce baseline **18 window** (22687.6) với jar mới; mới chứng minh 12 window ≤2024 = 14357.9.
- Chưa ghép `cpcv_validation.py` vào pipeline (§8.5 handoff cũ) → chưa có PBO/DSR → **chưa được phép chạm TEST 2025**.
- Chưa làm §8.2 vá leak nền (purge/embargo ở `buildWindows` + `train_gate_fold.py` đọc `GATE_PURGE_MS`).
- Shadow (§8.6) vẫn chờ **tay user** trên 242.

## 6. HẠ TẦNG — cập nhật so với handoff cũ

- **Bridge desktop-commander RỚT 2 lần trong phiên này.** Nhưng phát hiện đường ổn hơn: WSL truy cập repo qua
  **`/mnt/e/educa/source/github/20260415/BinanceFuturesJava`** — `git` chạy bình thường, **KHÔNG** để lại
  `.git/*.lock` như `device_bash`. Ưu tiên đường này.
- `device_bash` (Linux VM trên máy user) **không boot được** cả phiên → bỏ qua.
- **Maven CÓ trên Windows**: `C:\Users\pc\bin\mvn.cmd`. Claude tự build được qua desktop-commander
  (`cmd /c "cd /d E:\... && C:\Users\pc\bin\mvn.cmd -DskipTests package"`, 55s). Không cần nhờ user bấm `.bat`.
- **Oracle KHÔNG có maven** (chỉ java 11) → build phải trên Windows.
- Oracle disk `/` **91% (còn 19G)** — sát. Dọn trước khi chạy job đẻ nhiều output.
- `edit_block` của desktop-commander có thể ghi file thành **CRLF** → `git diff` phình cả nghìn dòng nhiễu.
  Đã dính với `Configs.java` (694/694 dòng CRLF). **Sau mỗi lần sửa file Java, kiểm `grep -c $'\r$'` và
  `sed -i 's/\r$//'` nếu cần.**

## 7. NỢ KỸ THUẬT NHÌN THẤY (không sửa trong phiên này, tránh churn ngoài scope)

- `Configs.java` static block dùng `System.err.println` cho lỗi parse env — vi phạm luật SLF4J của `CORE.md`.
- `CORE.md` ghi genome chuẩn **18-gene** (ADR-0012) nhưng `StrategyWfoTask.GENOME` đang **17 gene**
  (bỏ `DCA_TIME_BIG_Up` 2026-07-13). Doc lệch code — nên sửa doc.

## 8. VIỆC TIẾP THEO (thứ tự đề xuất)

1. Thu số LEG B (§0) → ghi vào project-memory.
2. **Chốt với user về §3b** (O phạt đuôi tốt) — pre-register v2 hay giữ nguyên. Chặn mọi việc phía sau.
3. Ghép `cpcv_validation.py` vào pipeline → PBO/DSR (§8.5 cũ).
4. Chạy EXPLORE ≤2024 với `WFO_N_SAMPLES=30` để objective mới thực sự **chọn** genome.
5. Vá leak nền (§8.2 cũ).
6. Chỉ khi 3+4+5 xong và khung freeze lần cuối → chạm TEST 2025 **một lần**.
