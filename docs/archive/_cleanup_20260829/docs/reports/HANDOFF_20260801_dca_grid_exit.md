# HANDOFF 2026-08-01 — DCA grid + trần margin theo bậc — ĐỌC TRƯỚC KHI LÀM TIẾP

> Nối mạch từ `HANDOFF_20260730_exit_min_ratchet.md`. Số liệu chi tiết ở
> `EXIT_SWEEP_20260731_rate_ratchet.md` (PHẦN 6-8), `DCA_GRID_20260801.md`,
> `STRATEGY_SPEC_20260801_mean_reversion.md`, `EXIT_MACHINE_20260730_stop_schedule.md` (PHẦN 5).

---

## 🔴 VIỆC ĐẦU TIÊN — ORACLE ĐANG TREO, PHẢI GIẢI CỨU TRƯỚC KHI LÀM BẤT CỨ GÌ

**Nguyên nhân là lỗi của phiên này, không phải sự cố hạ tầng.** Tôi bung 3 batch chồng nhau mà
không đo RAM và không đi qua CE:

| batch | song song | heap mỗi JVM | tổng |
|---|---:|---:|---:|
| `run_tier2.sh` | `xargs -P 4` | `-Xmx3g` | 12 GB |
| `run_tier2b.sh` | `-P 2` | `-Xmx3g` | 6 GB |
| `run_tier2c.sh` | `-P 6` | `-Xmx3g` | 18 GB |
| **cộng dồn (chạy đè lên nhau)** | **12 JVM** | | **≈ 36 GB** |

Vượt RAM box → thrash → SSH `Connection timed out during banner exchange`.

Cách xử lý:

1. Chạy `outputs/rescue.sh` (đã viết sẵn, retry SSH 8 lần rồi
   `pkill -9 -f TrailingStopSweepProbe`). Nếu SSH vào được thì xong.
2. Nếu 8 lần vẫn fail → box không cứu được qua SSH, **cần Uni reboot từ Oracle Cloud console**.
3. Sau khi sống lại: `rm -rf /home/ubuntu/claudedata/.run/tier2c` (kết quả dở dang, bỏ).

**Luật rút ra — ghi vào `docs/rules/run-226.md` + `INFRA_FACTS.md`:**

- ⛔ Cấm bash driver ad-hoc khi đã có nút CE (luật R1 — Uni đã nhắc **2 lần** trong phiên này,
  tôi vi phạm cả 2 lần). Dùng `ce wfo_fanout` / `ce wfo_status`.
- ⛔ Trước bất kỳ fanout nào: `free -g` và đếm JVM đang chạy. Ngân sách an toàn
  ≈ `(RAM_free_GB - 4) / heap_GB` process, và **không bao giờ launch batch mới khi batch cũ chưa
  `ALL_DONE`**.
- Batch trước phải kết thúc rồi mới launch batch sau. Phiên này tôi launch tier2b khi tier2 mới
  chạy 7/11 fold, rồi launch tier2c khi tier2 mới 8/11.

---

## Bối cảnh 1 câu

Hệ là **DCA hold-to-die** (chủ ý của Uni: coin không delist thì trước sau gì cũng pump, chấp nhận
chôn vốn — **không có exit lỗ là thiết kế, không phải bug**). Selector chọn coin biến động mạnh
(pump 500% nhưng cũng dump 3-4 lần) → nhánh DCA phải chịu được xoáy sâu. Phiên này hoàn thiện DCA
để chốt exit, rồi quay lại entry.

## ✅ Đã chốt được (có số, đã kiểm chứng)

### 1. Lỗi cấu trúc DCA cũ — đã tìm ra và sửa

DCA cũ dùng `calRateLoss()` trên `avgEntry` **đang trôi** → khoảng cách giữa các lần nhồi co lại:
15% → 8.1% → 5.5% → 4.4%. Nghĩa là nhồi càng lúc càng dày ở vùng nông, hết vốn trước khi tới đáy
thật. Sửa: đo mức trên `firstEntryPrice` (bất biến qua DCA) — `DcaUtils.shouldDcaGrid()`.

### 2. Lưới DCA lấy từ dữ liệu, không phải đoán

Đo phân phối MAE (`MaeDistributionProbe`, tập 171k lệnh, selector gate 0.008): p50 −56.1%,
p75 −70.4%. Từ đó chốt lưới:

```
DCA_GRID_ENABLED=true
DCA_GRID_LEVELS=-0.50,-0.75,-0.90     # đo trên firstEntryPrice
DCA_GRID_WEIGHTS=1,1,3,8              # tổng 13 phần
DCA_GRID_SCALE=8
RATE_PROFIT_STOP_MARKET=0.05          # min-rate; sàn Uni yêu cầu ≥0.03
```

### 3. Lưới thắng DCA cũ về rủi ro điều chỉnh

| | PnL OOS | maxDD (abs) | PnL/DD | WFE | %OOS dương |
|---|---:|---:|---:|---:|---:|
| exit003 (DCA cũ) | 17,906 | 12,021 | 1.49 | 0.442 | 37.5% |
| dcascale8 (lưới) | 12,863 | **4,729** | **2.72** | 0.380 | 37.5% |

PnL/DD **+83%**. ⚠️ Nhưng xem mục "chưa giải quyết" bên dưới — con số này **không sạch**.

### 4. Trần margin theo bậc — cơ chế "chặn trần khi sập mạnh"

Bản đầu tôi thiết kế sai: leg 1 = 25% → bóp nghẹt động cơ chính (86% cụm không bao giờ nhồi, chúng
tạo phần lớn lợi nhuận) → PnL −20% mà rủi ro chỉ giảm 7%. **Bác bỏ.**

Bản sửa (`DCA_TIER_MARGIN_CAPS=0.50,0.60,0.70,0.80`): leg 1 giữ 50% y hệt production
(`BREAKER_MARGIN_HALT`), các leg sâu được nới rộng hơn. Khi sập mạnh: lệnh **mới** bị chặn, còn leg
sâu (nhóm có tỷ lệ hồi 76.4%) vẫn nhồi được.

**Kết quả đo (8/11 fold trước khi box treo):**

| nhánh | fold | pnlTotal | pnlClosed | ddMtmTB | ddMtmMax |
|---|---:|---:|---:|---:|---:|
| s8_flat50 | 8 | 12,184 | 13,168 | 2.91% | 6.41% |
| s8_tierWide | 8 | 12,184 | 13,168 | 2.91% | 6.41% |
| s20_flat50 | 8 | 27,000 | 29,462 | 6.89% | 16.13% |
| s20_tierWide | 8 | 27,000 | 29,462 | 6.89% | 16.13% |

**Y hệt nhau tới từng chữ số.** Đã sanity-check để phân biệt "cơ chế chết" vs "trần không bao giờ
chạm" — đặt trần phi lý `0.02,0.03,0.04,0.05`:

```
canary02  fold=1  pnlTotal=131      <- cơ chế SỐNG
off       fold=1  pnlTotal=3215
```

→ **Kết luận: cơ chế hoạt động, nhưng trần 50/60/70/80 chưa từng chạm trên dữ liệu 2021-2026 ở
scale 8 và scale 20.** Nó là **bảo hiểm miễn phí**: không tốn gì, không cải thiện gì, chỉ giới hạn
đuôi trong kịch bản sập tệ hơn mọi thứ lịch sử đã có.

Câu hỏi còn dở: **phải phóng vốn lên scale bao nhiêu thì trần mới bắt đầu cắn?** Đó chính là
`run_tier2c.sh` (scale 40/80/160) — job làm treo box. Cần chạy lại **tuần tự, `-P 2` tối đa**.

---

## 🔒 BẢN CHỐT TẠM (theo yêu cầu "tạm chốt 1 bản tốt nhất có chặn trần khi sập mạnh")

```bash
RATE_PROFIT_STOP_MARKET=0.05
TS_PROFIT_MULTIPLIER=5.21847         # đã xác nhận là đỉnh thật, không phải nhiễu
DCA_GRID_ENABLED=true
DCA_GRID_LEVELS=-0.50,-0.75,-0.90
DCA_GRID_WEIGHTS=1,1,3,8
DCA_GRID_SCALE=8
DCA_TIER_MARGIN_ENABLED=true
DCA_TIER_MARGIN_CAPS=0.50,0.60,0.70,0.80
SIM_BREAKER_MODE=OFF                 # trần theo bậc thay thế breaker phẳng
SIM_APPLY_FUNDING=true
```

Trạng thái: **chốt tạm, chưa production-ready.** Lý do ở mục kế.

---

## ❌ Chưa giải quyết — đây mới là phần quan trọng

### A. %OOS-dương kẹt cứng 37.5% ở MỌI cấu hình exit → nút thắt là ENTRY, không phải exit

10/16 window rơi vào `TOO_FEW` / `ZERO_TRADES` / `CAPITAL_LOCK`. Đổi exit kiểu gì con số này cũng
không nhúc nhích. **Không có lý do gì tiếp tục tune exit.** Việc kế tiếp đúng đắn là quay lại
nhánh entry (tăng tần suất tín hiệu), đúng như Uni đã định hướng từ đầu.

### B. Kết quả bị dồn vào 1 window

w15 (Oct 2025 – Jan 2026, sự kiện thanh lý 19 tỷ USD ngày 2025-10-11) chiếm **63.6%** tổng PnL của
bản lưới (bản cũ 64.8% — gần như không cải thiện). **Bỏ w15 ra thì lưới còn TỆ HƠN DCA cũ:
4,686 vs 6,295.** Nghĩa là "+83% PnL/DD" ở trên chủ yếu là chuyện của 1 sự kiện. Đừng trích con số
đó ra khỏi ngữ cảnh này.

### C. Overfit đã đo, kết quả không đẹp

Uni nghi overfit 2 lần, cả 2 lần đều đúng. Spearman train↔holdout = **0.14**, hiệu ứng **0.68
sigma**. → **Giá trị tham số không học được từ dữ liệu này.** Tôi đã rút lại tuyên bố "+26%" trước
đó xuống "+13-15%", và ngay cả con số đó cũng nên coi là chưa chắc chắn.

### D. `%hold>7d` ≈ 5-6%, vượt ràng buộc production 2% (`MAX_PCT_HELD_OVER_7D=0.02`)

Chưa quyết: nới ràng buộc (hợp với hold-to-die) hay ép exit sớm. Cần Uni chốt — nó mâu thuẫn trực
tiếp với luận điểm chôn vốn tới cùng.

### E. Việc còn treo

- `run_tier2c.sh` (scale 40/80/160) — tìm ngưỡng trần bắt đầu cắn. Chạy lại `-P 2`.
- `CapacityProbe` chạy lại với lưới −50/−75/−90 + scale 8 (số slot và cap mỗi coin đang sai).
- `tierMarginBlockCount` có tăng nhưng **không log ra** → không đếm được số lần chặn. Thêm log
  SLF4J vào `SimulatorMarketLevelTicker1MStopLoss`.
- `isDcaAlt()` (bộ dò dump toàn thị trường) đang nối để **kích thêm DCA** chứ không phải để phanh —
  ngược với ý đồ "hạn chế margin khi thị trường sập".
- Audit rò rỉ nhãn theo timestamp trong pipeline Python sinh `pred.bin` — chưa từng làm.

---

## Bẫy hạ tầng đã dính trong phiên (đừng lặp lại)

1. **Jar stale 2 lần liên tiếp.** Lần 1: build + bump Kaggle nhưng quên `scp` sang Oracle → sweep
   chạy jar cũ → kết quả byte-identical baseline (27,412 vs 27,413), mất cả vòng đo. Lần 2: bump
   Kaggle **trước khi** thêm `DCA_GRID_SCALE` → `dcagrid8` y hệt `dcagrid1`.
   → Đã viết `outputs/verify_stage.py`: mở jar đã stage, đếm 6 field trong `Configs.class`, **PASS
   mới được fanout**. **Bắt buộc chạy trước mọi fanout.**
2. **Kaggle không inject env động** — flag phải hardcode vào `run_worker.py` trước khi push (5 kernel).
3. **`bg_run` báo SUCCESS giả với log 0 byte** — chưa tìm ra root cause. Workaround:
   `nohup ... & disown`.
4. **PowerShell nuốt quoting SSH.** Mẫu chạy được: ghi script ra file → `scp` → chạy. Tránh
   `|`, `"`, `\`, nháy đơn, ngoặc trong lệnh remote.
5. **`ddPct` KHÔNG phải drawdown** (= `|unProfitMin| / balanceBasic`, gần như mù với tham số exit).
   Phải dùng `ddPctMtm`. PnL phải tách `pnlClosed` (status ≠ REQUEST) vs `pnlMtm` (== REQUEST).

## Lỗi đo lường tự bắt được (giữ để không tái phạm)

- `GridEvalProbe` look-ahead: dùng `high` của **cả ngày vào lệnh** kể cả phút trước khi vào → 99%
  "TP" ngay ngày 1. Sửa bằng `t2t.tailMap(ets[i], true)`.
- `SurvivalProbe` dùng `high` thay `close` khi định giá cuối kỳ → nhóm kẹt trông đỡ tệ hơn thực tế.
- **"97.4% hồi vốn" là ảo** — đo trúng các nhịp trũng nông hồi lại trước cú sập thật. Đã rút lại.
- `cmp_wfo.sh` map nhầm cột: lấy `$8` (`OOS_maxDD`) tưởng là PnL. Bản đúng ở `cmp_wfo2.sh`:
  `$7=OOS_pnl, $8=OOS_maxDD, $9=OOS_calmar, $11=oosNote`.
- `%noArm` đo sai (`closeOrder` không copy `priceSL` sang leg) → thực chất đang đo tỷ lệ leg DCA.
  Đã bỏ metric này.

## Code đã đổi (chưa commit hết — kiểm `git status` đầu phiên mới)

- `Configs.java`: `DCA_GRID_*`, `DCA_TIER_MARGIN_*`, `tierMarginCap()`, `dcaGridTotalWeight()`,
  `TS_CARRY_SL_ON_DCA`, `SIM_TREAT_ZERO_VOL_AS_DELIST`, `SIM_FAIL_FAST_ON_DATA_ERROR`,
  `TS_GIVEBACK_FLOOR`/`TS_MIN_GAP`; un-final `TS_RATCHET_DECOUPLED` + `TS_GIVEBACK_FLOOR` để sweep.
- `DcaUtils.java`: `shouldDcaGrid()`, `gridLegWeightRatio()`.
- `DcaProcessor.java`: nhánh `DCA_GRID_ENABLED`.
- `OrderTargetInfoTest.java`: `legCount`.
- `SimulatorMarketLevelTicker1MStopLoss.java`: F7/F8/F9/F10 + `putOrderDone()` chống va khoá +
  audit counter + sizing lưới trong `createOrderBUY` + khối trần theo bậc.
- Probe mới: `RatchetSweepV2Probe`, `ExitParamSweepProbe`, `MaeDistributionProbe`,
  `EntryPathTrackProbe`, `GridEvalProbe`, `CapacityProbe`, `SurvivalProbe`.
- 4 lỗi audit F7-F10 đã sửa nhưng **đo ra vô hại trên dataset này** (không đổi kết quả).

---

## Đề xuất thứ tự cho phiên mới

1. Giải cứu Oracle (mục 🔴 đầu file).
2. Ghi luật RAM + CE-FIRST vào `docs/rules/run-226.md` và `INFRA_FACTS.md`.
3. **Dừng tune exit** — chốt tạm cấu hình ở trên và chuyển sang entry (mục A là bằng chứng).
4. Nếu Uni vẫn muốn khép exit: chạy nốt `tier2c` (`-P 2`) để biết biên an toàn của trần, và chốt
   câu D (`%hold>7d` 2% hay nới).
