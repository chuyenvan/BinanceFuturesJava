# PLAN — R4 LÊN SHADOW (PAPER) Ở NHỊP 1 PHÚT

Trạng thái: **PRE-REG DEPLOY** · 2026-09-29 · branch `module` · commit code `dd8d063`
Chỉ **shadow-c3** trên Oracle (paper). **KHÔNG** chạm 242 · **KHÔNG** đổi `SHADOW_NO_PUSH=true`.

> ⚠️ **KẾT QUẢ (2026-09-29): DEPLOY FAIL → ĐÃ ROLLBACK.** Xung đột cấp thiết kế: `cascadeUniverse` cap
> `topK = min(ENTRY_CASCADE, SELECTOR_RANK_TOPK) = 16`, trong khi `S1RankerLive` cần ≥ 20 coin ⇒ S1
> warm-up fail ⇒ 0 entry. Chi tiết + hướng fix: `docs/audit/DEPLOY_R4_1M_SHADOW_20260929.md` §4–§5.
> Code B1 (`LIVE_ENTRY_GRID_MIN` + `CONC_CAP_PERCOIN` live) vẫn đúng, parity PASS — giữ nguyên.

## 0. MỤC TIÊU & PHẠM VI

Owner 09-29: *"cứ test 1 phút"* — đưa cấu hình **R4** lên shadow ở **nhịp 1'** để verify live khớp
backtest. R4 = **size ×0.5** (`SIM_F_BASE=0.015`) · **K=16** (`SELECTOR_RANK_TOPK=16`) · **gate 1.55**
(`SIM_GATE_DYN_SCALE=1.55`) · **nhịp 1'** (`LIVE_ENTRY_GRID_MIN=1` + `ENTRY_CASCADE=16` để 1 lượt rẻ).
CONC_CAP giữ nguyên (`CONC_CAP_PERCOIN_ENABLED=true`, `CONC_CAP_PERCOIN_PCT=0.15`).

**PHẠM VI CHỈ:** `shadow-c3.service`. **TUYỆT ĐỐI KHÔNG** deploy/restart 242.

## 1. CODE (B1 — đã commit `dd8d063`, gated, mặc định byte-identical)

1. **Key mới `LIVE_ENTRY_GRID_MIN`** (int, `Configs.java`): thay hằng `ENTRY_GRID_MIN = 15L` ở
   `DetectEntrySignal2TradeNormal.java`. Không khai / `<=0` ⇒ **15** = hành vi y nguyên.
   `isTimeProcessData()` → `selectorGrid(second, curMin, last, Configs.LIVE_ENTRY_GRID_MIN)`.
   Log verify: `[R4-1M] LIVE_ENTRY_GRID_MIN=… => SELECTOR quét mỗi … phút`.
2. **Wire `CONC_CAP_PERCOIN` vào đường LIVE** (từ trước chỉ sim đọc): port cua
   `SimulatorMarketLevelTicker1MStopLoss:~1483`, gated `CONC_CAP_PERCOIN_ENABLED` (mặc định
   `false` ⇒ byte-identical). Khi `LiveProfileC3.on()` đọc margin coin từ `ShadowBookC3.perCoinMargin`
   (method mới). Chặn HẰN (`return`) khi `(margin coin + leg mới)/equity > CONC_CAP_PERCOIN_PCT`.
3. **Kiểm knob R4 có được live đọc:**
   - `F_BASE` (`SIM_F_BASE`) ⇒ **ĐỌC** qua `TradeUtils.managerBudget` (`DetectEntry…:954`). ✅
   - `SELECTOR_RANK_TOPK` ⇒ **ĐỌC** (`DetectEntry…:394/454/475/670`). ✅
   - `SIM_GATE_DYN_SCALE` ⇒ **ĐỌC** (set `EntryGate.GATE_DYN_SCALE`, dùng chung sim+live). ✅
   - `CONC_CAP_PERCOIN` ⇒ **TRƯỚC ĐÂY KHÔNG** (chỉ sim) ⇒ đã wire (mục 1.2). ✅
   (`CONC_CAP_AGG_DCA` + `CONC_CAP_BD_RATE` vốn đã đọc bởi live qua `ConcCapLiveGuard`.)
4. **Test:** `EntryGrid1MTest` (mới, 5) + re-run `CadenceSplitTest` (5) · `CadencePriorityTest` (5) ·
   `EntryCascadeTest` (5). **Full suite: 174 test / 0 fail / 0 error.**

## 2. PARITY (B2 — cổng bắt buộc trước deploy)

Jar build từ `dd8d063`, **sha256 `8d93dad97fb4e2b8cd7b54d4e2448dc413af4c5731826d7d53088f7f5b45160d`**
(`mvn -o -DskipTests package`, arm64, java 11.0.32.1). Dataset jar: `chuyendinh/sim-jar-r4-1m`.

Chạy 2 chân trên **Kaggle** (bundle `sim-x1-2021-bundle`, 2021-07-01..2025-12-31, ticker 1826,
**0 sim Oracle**), key mới **KHÔNG khai**:

| chân | profile | override | md5 `printDone.csv` yêu cầu |
|---|---|---|---|
| `r4-par-kg0` | `x1_gs_t170` | `DCA_GRID_WEIGHTS=1,1,1,1` + `DCA_GRID_SCALE=6.0` | `99e42b75cf1a2142f9cd14dc72e371ba` (KEEPLEG0, n1085/103083) |
| `r4-par-t170` | `x1_gs_t170` | (không) | `efb793e2468ca3a7318da0f0ad23d4fc` (T170, n1089/111070) |

**Lệch ⇒ DỪNG, không deploy, báo rõ.** (Runner: `research/analysis/r4_1m_parity_run.py`.)

## 3. ENV MỚI (B3 — thêm vào `/home/ubuntu/shadow_c3/app/conf/env.sh` sau khi backup)

Giá trị hiện tại → mới (chỉ đổi 2 dòng + thêm 3 dòng; `MARKET_SCAN_MIN=1`, `MARKET_SCAN_PRIORITY=1`,
`LIVE_FEAT_DUMP=3000`, `CONC_CAP_*`, `SHADOW_NO_PUSH=true` GIỮ NGUYÊN):

```sh
export SELECTOR_RANK_TOPK=16     # 8 -> 16
export SIM_GATE_DYN_SCALE=1.55   # 1.70 -> 1.55
export SIM_F_BASE=0.015          # MOI: size x0.5 (R4)
export ENTRY_CASCADE=16          # MOI: gate-first, <=16 ung vien cho tang predict
export LIVE_ENTRY_GRID_MIN=1     # MOI: SELECTOR quet 1 PHUT (thay luoi 15')
export MARKET_SCAN_MIN=1         # GIU
export MARKET_SCAN_PRIORITY=1    # GIU
```

## 4. TIÊU CHÍ PASS SAU KHỞI ĐỘNG (đo ≥ 2 giờ)

1. **median thời gian 1 lượt selector < 45 s · p95 < 60 s** (đo từ `Start/Finish check level change`).
2. **≥ 1 dòng `[GATE]` mỗi phút (≥ 95% phút)** — gate value KHÔNG đổi (chỉ nhịp đổi).
3. **0 ERROR/Exception mới** (baseline `full.log` `grep " ERROR "` = 4699; `error.log` 24 dòng
   Aerospike timeout/legacy-scan đã biết).
4. **RSS ổn định · free mem ≥ 4G** (Oracle 23G).
5. **feat_dump/ring nạp mỗi phút** (`LIVE_FEAT_DUMP` ghi liên tục; `[S1] nạp` mỗi tick).

**FAIL bất kỳ ⇒ ROLLBACK ngay.**

## 5. ROLLBACK

```sh
cd /home/ubuntu/shadow_c3/app
cp -p target/binance-java-sdk-1.2.4.jar.bak_20260929_r4 target/binance-java-sdk-1.2.4.jar
cp -p conf/env.sh.bak_20260929_r4 conf/env.sh
sudo systemctl restart shadow-c3
# verify: jar sha = 78387f30…, env.sh = 6cc24a57…, is-active=active, [R4-1M]/[CADENCE…] hết/đổi về cũ
```

## 6. RỦI RO

- **Bỏ sót ứng viên (cascade):** `ENTRY_CASCADE=16` lọc universe trước predict ⇒ giữ held + coin chưa
  cache + topK ≥ SELECTOR_RANK_TOPK; chống bỏ sót đã test (`EntryCascadeTest`). Nhưng **ON có thể lệch
  OFF** do cross-sectional rank/quantile-map đổi tập (đã ghi trong `PLAN_CASCADE_ENTRY.md` §5). Chấp nhận
  vì đây là verify paper, không phải go-live.
- **Đĩa 93% (14G):** nhịp 1' tăng ghi `predictionSymbol`; cascade giảm ghi (chỉ ≤16 ứng viên). `feat_dump`
  có trần 200 MB tự dừng. Theo dõi `df -h /`.
- **Pool 1 thread:** `MARKET_SCAN_PRIORITY=1` chống phình hàng đợi; với cascade 1 lượt ~1,7-4,3 s nên 1'
  khả thi (xem `PLAN_CASCADE_ENTRY.md` §4).

## 7. CẦN OWNER DUYỆT

1. Bật `ENTRY_CASCADE=16` (đổi đường LIVE) trên shadow paper — **đã được owner "cứ test 1 phút"**.
2. `LIVE_ENTRY_GRID_MIN=1` (SELECTOR 1') trên shadow paper.
3. Không đụng 242 (giữ nguyên).
