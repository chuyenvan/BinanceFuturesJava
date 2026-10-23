# GOLIVE_SCENARIO — kịch bản go-live gói v1.1 (K24 + skipFull + TS_MKT_EXT X14) từ shadow tới pilot 10 000 USDT và sau pilot

- **Ngày:** 2026-10-23 (+07). Tác giả: agent `golive` (Opus) cho MASTER. **Chỉ là kế hoạch** — không chạy, không deploy, không sửa code.
- **Nguồn đã đọc và kiểm:** `exec_probe/wt/docs/plan/GOLIVE_GAP_C3LIVE.md` (16 gap; nằm ở nhánh `v1.1/exec-probe`, KHÔNG có trong
  `vz_e1_wt/docs/plan/`), `docs/audit/OC1023_AUDIT.md` (2d4afd53), `docs/prereg/PREREG_PARITY_V11_WINDOW.md` (481701b2),
  `docs/prereg/PREREG_SHADOW2_PROMOTION.md` (+ ADDENDUM 10-16, c, d), `exec_probe/wt/docs/prereg/PREREG_EXEC_PROBE.md`,
  `~/claude_master/audit_oc1023/audD/failclosed.patch`, `~/claude_master/deploy/deploy_dcae2e2b.sh` + `rollback_v11c.sh` (học format),
  source `~/claude_master/exec_probe/wt` @ `16de49a6` (= jar dcae2e2b đang chạy shadow trên 242), project memory (golive_1009,
  killsw_1018, parity_v11_window, parity_1020, iso_risk_1018, hold_dca_1019, audit_1021, openclaw_dispatch).
- **Không đọc:** server 242, `PrivateConfig.java`, `config.properties`.
- Ký hiệu: **[XM]** = đã xác minh trên source/tài liệu (ghi file:dòng); **CHƯA XÁC MINH** = chưa kiểm được.

## 0. Tóm tắt rủi ro trước (risk-first)

1. **Hôm nay KHÔNG được bật `LIVE_PROFILE=c3_live`.** [XM] `DetectEntrySignal2TradeNormal.createOrderBuyRequest`
   (~:1146–1166, :1300–1316): khi c3_live và cổng push mở, lệnh đi `rpush` Redis queue → `BinanceOrderTradingManager.processOrderNewMarketNew`
   (:170–226) → `OrderHelper.newOrderMarket` — **không** gọi `ShadowBookC3.openPos`, và `BudgetManager.addMarginRunning` bị bỏ qua khi
   `LiveProfileC3.on()` ⇒ `marginRunning`/`equity` dùng cho sizing là của **sổ giấy không bao giờ nhận leg thật** ⇒ U/U_MAX không bao giờ
   chặn. Mỗi leg chỉ bị trần 4,5 % equity (`LiveProfileC3.SIZE_CAP_OF_EQUITY = 0.045f`, :57) ⇒ một đợt 24 leg ≈ **108 % equity** trong
   một tick (sim ≤ 60 %). Trước đây ghi PLAUSIBLE, nay **[XM] bằng đọc code**. Cộng thêm: retry `rpush` mù tới 5′ khi exception (:209–216)
   ⇒ lệnh trùng; không `newClientOrderId` (`OrderHelper.newOrderMarket(symbol, side, quantity)` :34).
2. **Kill-switch chưa có răng.** [XM] `KillSwitchEngine.ACT_IMPLEMENTED = false` (:48); `act` bị hạ về `log` (:103–106).
   C2 tính `|fill/ref − 1|` (:127–130) = **trị tuyệt đối** ⇒ khớp *có lợi* lúc sập (giá mua thấp hơn close M) cũng kích hoạt C2 — phải đổi
   thành trượt bất lợi có dấu.
3. **Lỗ fail-open NaN ở gate** (audD, chưa kích hoạt): `AIRejectFilter.evaluate` `pred15M < thres15M` với NaN ⇒ PASS;
   `LiveGateRollingRatio` nạp/persist r NaN. Patch có sẵn, chưa build/commit.
4. **Pha tiền thật đầu tiên chưa bao giờ chạy tải thật**: canary + micro-live chỉ thử vài leg; đợt sập đầu tiên trong pilot (24 leg/tick,
   dời SL trên sàn, rate limit IP chung ingest 242) là lần chịu tải đầu. Đây là **rủi ro lớn nhất còn lại sau khi đóng P0** (mục 6).
5. **Cửa sổ shadow 4 tuần nhiều khả năng không có đợt sập** ⇒ P2 (lật gate) có thể "chưa được thử" (r/q max 0,891 ở D1), skipFull (iv)
   và TS-EXT (vi-b/c) "chưa quan sát". Prereg cho phép không chặn — nhưng phải ghi rõ: **logic entry lúc sập chưa được kiểm forward**.

## 1. Sơ đồ pha (ngày +07, dự kiến; phụ thuộc ghi ở cột cuối)

```
10-23 ─┬─ P0 CODE (v1.2-rc, 2 luồng agent) ───────────── 10-26 → 11-11 ── audit độc lập 11-12/13
       │
       ├─ SHADOW WINDOW v1.1 (đang chạy từ 10-21 07:53:59) ─────────────── tối thiểu → 11-18 07:53:59 ── chấm 11-18→11-20
       │      parity lượt D hằng ngày · lượt M tháng 10 (~11-02→11-05) · lượt M tháng 11 (~12-02→12-04)
       │      exec-probe: chấm khi |E| ≥ 100, hạn cứng 11-22 09:37 (30 ngày sau deploy)
       │
       ├─ DRY-RUN adapter trên 242 (c3_shadow + LIVE_ADAPTER=dry, ADDENDUM d) ── 11-16 → 11-23 (≥ 7 ngày)
       ├─ CANARY e2e tài khoản con (~200 USDT, min size) ─────────────────── 11-17 (lặp lại 11-24)
       │
       ├─ MICRO-LIVE c3_live tài khoản con, PILOT_EQUITY=1 000 ───────────── 11-24 → 12-01 (≥ 7 ngày)
       │
       ├─ NGÀY D — PILOT 10 000 USDT ─────────────────────────────────────── dự kiến 2026-12-08 (Thứ Ba); sớm nhất 12-03
       │
       └─ PILOT ≥ 8 tuần ──── xét mở rộng sớm nhất ~2027-02-02 (và chỉ khi đủ điều kiện mục 5.4)
```

| pha | bắt đầu | kết thúc (sớm nhất) | điều kiện vào | điều kiện ra (cổng, mục 3) |
|---|---|---|---|---|
| **P0** sửa code bắt buộc | 10-26 | 11-11 code, 11-13 audit | owner xác nhận 3 khuyến nghị (mục 6, Q1) trước 10-27 — G2/G7/sizing phụ thuộc | G-CODE |
| **SW** shadow window v1.1 | 10-21 07:53:59 (đang chạy) | 11-18 07:53:59; gia hạn từng khối 4 tuần nếu XÁM | — | G-PARITY + G-OPS + G-PROMO |
| **XP** exec-probe | 10-23 09:37 (đang chạy) | khi \|E\| ≥ 100 hoặc 11-22 09:37 | — | G-EXEC (verdict quyết size, không chặn) |
| **DR** dry-run adapter | 11-16 (owner chạy `deploy_v12rc_dry.sh`) | ≥ 7 ngày, ≥ 11-23 | G-CODE | G-DRY |
| **CN** canary | 11-17 | 1 lượt đạt + 1 lượt lặp trước micro | G-CODE, tài khoản con + key (Q2, Q3) | G-CANARY |
| **MC** micro-live | 11-24 | ≥ 7 ngày, ≥ 12-01 | G-PROMO + G-DRY + G-CANARY + G-EXEC có kết luận size | G-MICRO |
| **D** pilot 10k | 12-03…12-08 | — | G-MICRO + lượt M tháng 11 ĐẠT + Q4/Q5 owner chốt | giám sát mục 5 |
| **SC** mở rộng | ≥ 8 tuần sau D | — | mục 5.4 | — |

Ghi chú lịch:
- **Vì sao D không phải 11-20:** (a) P0 ≈ 23–33 ngày công (mục 2) — 2 luồng song song ⇒ ~12–17 ngày làm việc; (b) prereg 481701b2 §3:
  phán quyết **chính thức** P1/P2 phần funding lấy từ **lượt M**; Vision `monthly/fundingRate` tháng 11 chỉ có đầu tháng 12 ⇒ chờ lượt M
  tháng 11 thì không cần ADDENDUM nới prereg. Micro-live kết thúc 12-01 ≈ cùng lúc ⇒ chờ lượt M gần như không tốn thêm ngày.
- Trượt 1 tuần ở P0 ⇒ DR/CN/MC/D trượt 1 tuần (D ~12-15). Không nén micro-live dưới 7 ngày.
- Mọi restart/deploy trên 242: chỉ phút :10–:44, tránh 07:xx và 19:xx (tính cờ TS-EXT 00:00 UTC + lịch tự-restart cũ),
  **tránh 12:50–13:20 và 00:50–01:20** (luật đã dùng trong `deploy_dcae2e2b.sh` `time_ok()`). Thứ Ba–Thứ Năm, giờ owner thức.
- Cửa sổ shadow có thể bị **mất log**: SHADOW_AUDIT_1020 cảnh báo đĩa 242 82 %, nguy cơ mất log ~11-17; `pull242.sh` CHƯA cài
  (parity_1020). Prereg §7: thiếu file 1 ngày = KHÔNG ĐO ĐƯỢC (không phải ĐẠT) ⇒ việc O1 (mục 2) là P0 **gấp nhất, làm tuần này**.

## 2. Việc code BẮT BUỘC trước tiền thật (P0)

Nhánh mới `v1.2/c3-live` từ `v1.1/exec-probe` @ `16de49a6`. **Nguyên tắc:** mọi hành vi mới sau cờ (`LIVE_PROFILE=c3_live`,
`LIVE_ADAPTER=dry|live`, `LIVE_C3_*`); đường `c3_shadow` phải **byte-identical** về quyết định (bytecode diff + harness offline
`ops/verify/harness_*.sh` + `research/parity_v11` HARNESS_OFFLINE=1) để deploy lên 242 trong cửa sổ theo **ADDENDUM d** mà không
reset. Ngoại lệ có khai: C10 (chỉ khác khi NaN — phải chứng minh 0 sự kiện NaN trong cửa sổ bằng replay buffer), C11 (sau cờ, OFF tới ngày D).
Công = ngày công 1 dev/agent, chưa gồm review; GAP doc ước G1–G7, G9, G15 ≈ 14–19 — bảng dưới thêm các việc audit 10-23 + P1 được nâng lên P0.

| mã | việc (gap) | file / vị trí | tiêu chí xong (đo được) | công | rủi ro |
|---|---|---|---|---|---|
| **C1** | **Sổ LIVE C3 `LiveBookC3` + kiểm U_MAX trong cùng tick** (G1, G6, audD-U_MAX) | lớp mới `tradecore/selector/LiveBookC3`; nối ở `DetectEntrySignal2TradeNormal.createOrderBuyRequest` ~:1146–1166 (nguồn margin/equity), :1300–1316 (push); `LiveDcaGridC3.candidates`; `LegacySymbols` | (a) leg được **giữ chỗ margin đồng bộ** trong sổ live trước `rpush`/gửi (pending), xác nhận/huỷ theo fill ⇒ unit test: 24 ứng viên PASS cùng tick, equity 10 000 ⇒ tổng margin ≤ U_MAX·equity = 6 000 và leg thứ k có throttle `1 − U/U_MAX` đúng `TradeUtils.managerBudget` (:130–138) tới 1e-6; (b) DCA grid đọc `LiveBookC3` ⇒ test DCA −50/−75/−90 % trên vị thế thật giả lập; (c) vị thế C3 thật KHÔNG bị `LegacySymbols` phân loại LEGACY (test với tập real ∖ (paper ∪ owned)); (d) guard trùng coin thấy vị thế thật; (e) sổ giấy vẫn chạy song song làm twin | 4–6 | lõi tiền thật; sai ⇒ over-size/thoát sai |
| **C2** | **Key c3_live từ file root-only, client riêng tài khoản con** | lớp mới `client/C3LiveClient` (không sửa `ClientSingleton`/`BinanceFuturesClientSingleton` của LEGACY — chúng dùng `PrivateConfig.API_KEY/SECRET_KEY` :87, :116, :49) | đọc `C3_LIVE_API_KEY/SECRET` từ `/root/.config/c3live/keys.env` (600, owner root) source trong `env.sh`; thiếu/quyền ≠ 600 ⇒ c3_live **từ chối khởi động push** (log, không in key); test: grep jar mới không có chuỗi key c3_live; mọi call c3_live đi qua client này (test: mock đếm) | 0,5–1 | lẫn key ⇒ lệnh vào tài khoản LEGACY |
| **C3** | **Idempotency / clientOrderId / retry** (G3) | `OrderHelper.newOrderMarket` (:34), `processOrderNewMarketNew` catch (:209–216) | `newClientOrderId = c3-<sym>-<barMin>-<leg>` (≤ 36 ký tự); retry chỉ sau `GET order?origClientOrderId` trả không tồn tại; bỏ `rpush` mù cho c3_live; test mock: timeout sau khi sàn nhận ⇒ **0 lệnh trùng** ở 1 000 lượt ngẫu nhiên; khoá xử lý persist qua restart | 1–2 | lệnh gấp đôi/ba |
| **C4** | **Làm tròn qty / filter sàn** (G4) | `Utils.calQuantity` → `ClientSingleton.normalizeQuantity`; `symbol2Notional` | bước = `LOT_SIZE.stepSize` (MARKET: `MARKET_LOT_SIZE`), kiểm `minNotional`, `maxQty`; không đạt ⇒ BỎ leg + log (không nới budget, bỏ ép BTC 0.002 cho c3_live); exchangeInfo nạp lúc start + mỗi 6h; test trên snapshot exchangeInfo thật: 100 % symbol universe, qty·price ≤ budget và ≥ minNotional hoặc bị bỏ | 1 | -1111/-4164; size lệch |
| **C5** | **Leverage / margin mode / position mode** (G5) — owner đã chốt CROSS 1x | khởi động c3_live + trước leg đầu mỗi symbol | đọc dual-side = false (one-way), margin type = CROSSED, leverage = 1 = `Configs.LEVERAGE_ORDER` (:102); sai ⇒ đặt lại 1 lần, vẫn sai ⇒ không vào lệnh symbol đó + Telegram; test mock 3 trạng thái sai | 0,5–1 | margin thật ≠ sổ |
| **C6** | **Thoát thật** (G2): sau arm đặt `STOP_MARKET` reduce-only trên sàn (khuyến nghị MASTER, chờ owner Q1), ratchet có ngưỡng, time-stop 168h + X14 đóng thật | `BinanceOrderTradingManager.initSLFirst/processDynamicTP_SL` (đường LEGACY, không dùng cho c3_live) → đường c3_live riêng dùng `TradeUtils.calRateLossDynamicBuyPNoPump` + `TsMktExt` | arm 0,07 như sổ giấy; chỉ dời SL khi mới cao hơn ≥ 1 tick VÀ ≥ 0,1 %; time-stop/X14 đóng market reduce-only idempotent (C3); test replay: trên 3 đợt DEV (vd 2025-02-03) quyết định arm/SL/time-stop của đường live trùng sổ giấy 100 % (trừ chênh giá khớp) | 2–3 | lệch sim ở chân ra; SL mồ côi |
| **C7** | **Kế toán fill** (G8, nâng P1→P0: cần cho C2 và đối soát) | response `RESULT` + user-data stream `ORDER_TRADE_UPDATE` (listenKey của **tài khoản con**) | `LiveBookC3` ghi qty/avgPrice/phí/orderId thật; sổ lệch sàn ≤ 1 nhịp (≤ 10 s) trong test mock; mất stream ⇒ fallback REST + WARN | 1–2 | không đo được trượt thật |
| **C8** | **Kill-switch ACT** (G7) + C2 có dấu + C3 đếm lỗi đặt lệnh + C6 trên equity tài khoản con | `ops/KillSwitchEngine` (:48 `ACT_IMPLEMENTED`, :127–135 c2/c3, :330 `onFill`), `OpsHooks` | C1–C5 ⇒ latch `NO_NEW_ENTRY` (chặn ở `createOrderBuyRequest` trước push VÀ ở cửa gửi lệnh), vẫn quản lý vị thế; C6/A40 ⇒ đóng hết C3 reduce-only chia lô + dừng + Telegram; latch persist file, chỉ script owner xoá; C2 = trượt **bất lợi** (mua: `fill/ref − 1 > 0`), cảnh báo 1,7 %, dừng mở mới khi > 2,5 % lặp lại (vd 3 lần/24h — chờ owner Q1); test: mỗi C1–C6 một kịch bản mock ⇒ đúng hành động, 0 hành động ở c3_shadow | 2–3 | không có bảo vệ tự động |
| **C9** | **Reconcile khởi động + hằng giờ** (G9 + khuyến nghị equity) | pha start c3_live; job hằng giờ | start: `positionRisk` + `openAlgoOrders` + `LiveBookC3` persisted ⇒ sàn thắng qty/giá, thiếu SL ⇒ tạo, SL mồ côi ⇒ huỷ, lệch ⇒ chặn entry tới khi khớp; hằng giờ: \|equity sổ − margin balance tài khoản con\| / margin balance ≤ 1 % else báo động; test mock: restart giữa vị thế (có/không SL, leg DCA dở) ⇒ khôi phục `tsFirstLeg/legCount/peak/priceSL` 100 % | 2–3 | SL thiếu sau restart, mất time-stop |
| **C10** | **Patch fail-closed NaN** (audD) + log `n_pass` đúng | `AIRejectFilter.evaluate` (:181), `LiveGateRollingRatio.threshold` (:136–147), `DetectEntrySignal2TradeNormal` (:348, :506, :558) — áp `failclosed.patch` | `git apply --check` + build; unit test NaN/±Inf ⇒ REJECT, không nạp buffer; sim byte-identical (key LIVE tắt); replay `gate_ratio_live.bin` cửa sổ: **0 record không hữu hạn** (điều kiện để coi là ADDENDUM d); `[GATE] n_pass = 0` khi `predictData == null` | 0,5 | patch nằm trên đường mọi tick |
| **C11** | **Race seed/tick đầu sau restart** | `LiveFeaturePipeline.seed` (seed nạp tới phút đã đóng mới nhất ⇒ `onTick` :228–232 `minute <= lastFed` trả `last` = null ⇒ `createOrderBuyRequest` :1078 return ⇒ mất trọn tick, kể cả DCA) | cờ `LIVE_SEED_EXCLUDE_DECISION_MIN` (mặc định 0 trong cửa sổ, 1 từ micro-live): seed chỉ tới phút < phút quyết định đầu; harness NEW2 seed theo giờ restart thật: tick đầu có feature, các tick sau trùng bản cũ 100 % | 0,5–1 | đụng parity — sau cờ, MASTER quyết bật |
| **C12** | **Adapter dry + mock sàn e2e + canary** (G15) | `LIVE_ADAPTER=dry`: đi hết size/round/clientOrderId/SL/kill-switch, ghi `[LIVE-DRY]`, không gửi; main class `C3LiveCanary` cho canary | dry: 1 dòng `[LIVE-DRY]` cho 100 % leg sổ giấy; mock e2e chạy CI: mở/DCA/arm/dời SL/time-stop/X14/restart/kill-switch đều xanh | 2–3 | lỗi adapter chỉ lộ khi tiền thật |
| **C13** | **Rate guard REST signed** (G11, nâng P0 vì SL trên sàn) | bọc mọi call c3_live (ngoài `BinanceRestGuard` public) | ngân sách weight/phút + order/10s/phút; đợt giả lập 24 leg + 80 vị thế dời SL ⇒ ≤ 50 % giới hạn sàn (số giới hạn: CHƯA XÁC MINH tại thời điểm code — đọc `exchangeInfo.rateLimits`) | 1 | ban IP ⇒ mất ingest cả 242 |
| **C14** | **Log/audit lệnh** (G13) | đường c3_live | mỗi request/response: clientOrderId, orderId, latency, status, lỗi; bỏ `printStackTrace` trên đường c3_live; 1 dòng `[C3-LIVE-ORDER]` cố định cột | 0,5–1 | không truy vết sự cố |
| **O1** | **Kéo log/dump 242 về Oracle hằng ngày** (prereg §7) | `pull242.sh` (chỉ đọc qua ssh+pipe, cron Oracle — MASTER tự cài được) | mỗi ngày đủ `feat_dump/sel_dump/s1_dump/predictionSymbol/full.log*/gate_ratio_live.bin`; báo thiếu ⇒ Telegram | 0,5 | **mất log ~11-17 ⇒ ngày KHÔNG ĐO ĐƯỢC** |
| **O2** | **Bộ script owner + monitor** (mục 4, 5) | `~/claude_master/deploy/golive_*.sh` | mỗi script: DRY=1, YES, chốt giờ, tự kiểm sau chạy, rollback tương ứng; chạy thử DRY trên Oracle | 2–3 | owner chạy sai |
| **A1** | **Audit độc lập + chứng minh byte-identical c3_shadow** | agent Opus khác người code | bytecode diff + harness; checklist mục 3 G-CODE | 2 | — |

**Tổng P0 ≈ 23–33 ngày công** (C1–C14 ≈ 18,5–27,5; O1–O2 ≈ 2,5–3,5; A1 2). Với 2 luồng song song (luồng 1: C1, C3, C7, C9, C8;
luồng 2: C2, C4, C5, C6, C10–C14, O1–O2) ⇒ code xong ~11-11, audit ~11-13.
P1 còn lại (làm trong tuần pilot đầu, không chặn): G10 funding vào equity sổ (0,5 — nếu equity lấy từ margin balance thì đã gồm funding),
G12 đối soát live↔twin tự động hằng ngày (1–2), G16 vị thế bị sàn đóng cưỡng bức (0,5).
**Không làm** trước pilot: đổi size (B15 không CONFIRM HO — iso_risk_1018), DD bậc/R1 (killsw_1018), bất kỳ thay đổi logic quyết định.

## 3. Cổng đạt/trượt định lượng từng pha

Nguyên tắc: ngưỡng ĐÃ có trong prereg thì dùng nguyên chữ prereg, không đổi. Ngưỡng MỚI (đánh dấu **[MỚI]**) phải được MASTER commit
thành prereg/ADDENDUM **trước khi pha đó bắt đầu** và trước khi nhìn số của pha đó; không tune sau khi thấy kết quả.
Mọi pha: một chỉ số "không đo được" (thiếu file/log) = **không ĐẠT**, không phải "bỏ qua".

### G-CODE (ra khỏi P0)
- 100 % tiêu chí xong của C1–C14, O1–O2 (mục 2) có test/bằng chứng ghi trong `docs/result/V12RC_BUILD.md`.
- Bytecode diff + harness offline: đường `c3_shadow` **byte-identical** với dcae2e2b về out/fund/ledger/state ở mọi lượt (như bằng chứng
  ADDENDUM d (1) của exec-probe); ngoại lệ duy nhất C10 với chứng minh 0 record NaN/Inf trong buffer cửa sổ.
- Audit A1: 0 phát hiện CRIT/MAJ mở. Có bất kỳ CRIT ⇒ không deploy.

### G-PARITY (cửa sổ shadow; prereg 481701b2 — nguyên chữ)
- Mỗi lượt D (mọi ngày UTC 10-21 → 11-17 có trong cửa sổ, **không bỏ ngày**): **P1** median rel p15 ≤ 1e-4 VÀ rel ≤ 1e-3 ở ≥ 98 % phút;
  **P2** lật nặng = 0; **P3** rel q_t ≤ 1e-6 **mọi giờ**; **TSX** cờ trùng; **S1-I** 100 %; **GV-I** 100 %; **CTL** 100 %; **K5 = 0**
  (K5 > 0 ⇒ XÁM, điều tra trước lượt kế).
- **Lượt M** tháng 10 và tháng 11 (không tiêm funding): P1, P2 như trên = phán quyết chính thức phần funding.
- **Việc còn thiếu cụ thể:** (a) ADDENDUM verdict D1: sửa map giờ P3 + nhãn K3 + bỏ match6 (OC1023_AUDIT CRIT-1/2), chấm lại **P2 đủ 1386 phút**
  + **P3 đủ 24 giờ** — cần log 10-22 00:00–07:05 (owner chạy `check_242_failopen.sh`, md5 e3d0b94d — CHƯA XÁC MINH đã chạy);
  (b) lượt D2… cho 10-22 → 11-17 (mới có D1); (c) điều tra 7 phút psym thiếu 10-22 00:00–00:06 và 3 phút lệch "15′ reference"; (d) lượt M ×2.
- TRƯỢT bất kỳ ⇒ dừng đường promote, điều tra; sửa logic ⇒ **reset cửa sổ** (ADDENDUM d không áp dụng).

### G-OPS (cửa sổ shadow; tiêu chí (i') PREREG_SHADOW2_PROMOTION ADDENDUM 10-16 — nguyên chữ, áp lên 242)
- 0 `OutOfMemoryError`; RSS java ≤ 3,6 G (nay không còn reset 12h — theo dõi xu hướng; RSS 3,12 G ở giây 294 sau deploy 10-23).
- Restart chỉ: có chủ đích + ghi sổ C (ADDENDUM d (2)(3)). **Restart do watchdog = crash ⇒ TRƯỢT (i')** (watchdog chỉ giảm downtime,
  không biến crash thành hợp lệ). Báo số restart theo loại.
- `[GATE] topk=24` ≥ 95 % phút chạy; `selector tick total` p95 ≤ 3 000 ms; `Update all position:44` (hoặc số LEGACY hiện hành) ≥ 99 % phút;
  0 lệnh thật; 0 thay đổi LEGACY do code shadow; (vi-a) 0 `[TS-EXT] defer-START` cho LEGACY.
- **[MỚI, chỉ báo cáo]** uptime theo phút ≥ 99,5 %; heartbeat tuổi > 180 s ≤ 0 lần ngoài restart có chủ đích; đĩa 242 `/` < 90 %.

### G-PROMO (chấm 11-18 → 11-20)
- (iii) sizing: **100 % leg** sai lệch tương đối ≤ 1e-3 so với công thức tính lại; (iv) skipFull nhất quán (hoặc "chưa quan sát", ghi rõ);
  **(v) real-book adapter = CHẶN CỨNG** — chỉ thoả bằng C1 (`LiveBookC3`) + test, không thoả bằng shadow đạt (i')–(iv);
  (vi-b/c) TS-EXT (hoặc "chưa quan sát").
- **PnL shadow:** prereg nói rõ **chỉ báo cáo, không ngưỡng** (4 tuần không đủ power). Đề xuất **[MỚI, XÁM-only]**, MASTER commit trước 11-18:
  (1) chạy sim jar `sim-jar-tsx` trên Vision cùng kỳ 10-21→11-18, cùng cờ (prereg ADDENDUM c B) ⇒ so danh sách lệnh giấy↔sim:
  Jaccard tập (symbol, phút vào) ≥ 0,95 và ≥ 95 % lệnh trùng có \|Δ giá thoát\| ≤ 0,5 % — dưới ⇒ XÁM + điều tra (không TRƯỢT);
  (2) vị trí ΣPnL 4 tuần của shadow trong phân phối khối 4 tuần DEV 2022–25 (8 seed) — < p5 ⇒ XÁM + MASTER/owner xem.
  Không có lệnh nào trong cửa sổ ⇒ (1)(2) "chưa quan sát".

### G-EXEC (exec-probe; PREREG_EXEC_PROBE — nguyên chữ)
- Chấm 1 lần khi |E| ≥ 100 (E = leg ENTRY/DCA, status ok|short, src ws); hạn cứng **11-22 09:37** — chưa đủ ⇒ chỉ mô tả, **không verdict**.
- Hợp lệ V1–V5 (phủ ≥ 90 %, median lat_snap ≤ 3 000 ms, median |ex_lag| ≤ 2 000 ms, 0 mock, lệch số leg ≤ 5 %).
- Cột chính `slip_x025` (PAPER_EQUITY 242 ≥ 20 000 — CHƯA XÁC MINH giá trị trên 242, prereg quy định cách chọn).
- Verdict: **GREEN** ⇒ pilot 10 000; **AMBER** (W1 ∨ W4) ⇒ 10 000 + ưu tiên C6 nếu W4; **RED_SIZE** (W2 ∨ W3 ∨ W5 ∨ W6) ⇒ đề xuất 5 000
  hoặc hoãn — **owner quyết** (Q4). Không verdict ⇒ luật cũ: pilot 10 000 với C2 1,7 %/2,5 % và đo trượt thật trong micro-live/pilot.
- Rủi ro lịch: lệnh K24 dồn theo đợt sập (prereg shadow: trung vị tuần K16 = 0 lệnh) ⇒ **nhiều khả năng không đủ 100 leg trước 11-22**.

### G-DRY (dry-run adapter trên 242, ≥ 7 ngày, 11-16 → ≥ 11-23)
- **[MỚI]** 100 % leg sổ giấy trong kỳ có đúng 1 dòng `[LIVE-DRY]` khớp symbol/side/clientOrderId (đúng mẫu C3); qty = round_down(budget/price, stepSize)
  chính xác; qty·price ≤ budget (dung sai 1 stepSize·price) và ≥ minNotional (leg không đạt ⇒ dòng SKIP có lý do, không gửi).
- 0 exception trên đường adapter; 0 dòng gửi thật (`[C3-LIVE-ORDER]` = 0); G-OPS vẫn đạt (dry không làm chậm tick: p95 selector tick không tăng > 10 %).
- Nếu kỳ dry không có leg giấy nào: thay bằng replay 3 đợt DEV qua adapter dry trên Oracle (mock sàn) — 100 % request khớp quyết định sim.

### G-CANARY (tài khoản con, ~200 USDT, min size; `golive_canary.sh`)
- **[MỚI]** Chuỗi bắt buộc, mỗi bước PASS: (1) đọc tài khoản: one-way, CROSSED, leverage 1, 0 vị thế, 0 lệnh mở; (2) mua MARKET min qty 3 symbol
  thanh khoản cao có minNotional ≤ 20 USDT (không dùng BTCUSDT vì min notional cao — CHƯA XÁC MINH giá trị hiện tại); (3) fill nhận qua user-data
  stream ≤ 5 s và khớp REST; (4) đặt STOP_MARKET reduce-only, dời 1 lần, huỷ; (5) tiêm lỗi timeout sau khi gửi ⇒ retry tra clientOrderId ⇒
  **0 lệnh trùng**; (6) kill JVM canary giữa chừng ⇒ khởi động lại ⇒ reconcile khôi phục sổ + SL 100 %; (7) đóng hết reduce-only ⇒ vị thế 0,
  algo order 0; (8) reconcile sổ ↔ `positionRisk` 100 %, \|equity sổ − margin balance\| ≤ 1 %.
- Chi phí canary ≤ 2 USDT (phí + trượt). Lặp lại 1 lần sau mọi thay đổi jar trước micro-live.

### G-MICRO (c3_live thật, PILOT_EQUITY=1 000, ≥ 7 ngày)
- **[MỚI]** Mọi lệnh thật: symbol/side/qty khớp quyết định twin (sổ giấy chạy song song, size co theo equity) **100 %** (trừ leg SKIP minNotional có log);
  **0 lệnh trùng**; 0 vị thế đã arm thiếu SL trên sàn > 2 phút; reconcile hằng giờ 100 % lượt với \|Δ\| ≤ max(1 %, 2 USDT);
  0 kích hoạt C1–C6 không giải thích được; 0 lỗi -2019/-4061/-1111/-4164 lặp lại; G-PARITY lượt D vẫn ĐẠT trong kỳ.
- Không có leg thật nào trong 7 ngày (thị trường êm) ⇒ không chặn nếu canary lặp lại lần 2 ĐẠT; ghi rõ "đường entry thật chưa quan sát".
- Trượt thật (nếu có leg): báo median/p90 theo bucket, so ECMEAS (chỉ thông tin — không tune).

### G-PILOT (liên tục, mục 5): DD ≤ 40 %, trượt, lệch sổ, vận hành — ngưỡng ở mục 5.2–5.3.

## 4. Kịch bản: các script owner (cả lộ trình) và ngày D

### 4.1 Luật chung cho MỌI script owner (học từ `deploy_dcae2e2b.sh` / `rollback_v11c.sh`)
- Đặt sẵn trên Oracle `~/claude_master/deploy/`, owner chỉ gõ **đúng 1 lệnh** `bash ~/claude_master/deploy/<tên>.sh`; MASTER gửi md5 kèm.
- `DRY=1` = chỉ đọc, in kế hoạch + mọi kiểm trước, không đổi gì. Chốt giờ `time_ok()` (phút :10–:44, tránh 07:xx/19:xx, 00:50–01:20,
  12:50–13:20); `FORCE_TIME=1` chỉ khi MASTER bảo.
- Kiểm trước (md5 jar, số process, env đúng mẫu, file gate do MASTER ký `GOLIVE_GATE_<pha>.ok` chứa commit result + sha256) ⇒ có FAIL là dừng,
  không đổi gì. Backup có TS; hỏi **YES** (in hoa) trước bước không đảo được; kiểm sau chạy tối đa ~10′ (OK/WAIT/FAIL); FAIL ⇒ in đúng 1 lệnh
  rollback. Log `~/claude_master/deploy/<tên>_<TS>.log`. Restart tay luôn `touch /var/lib/h242_watchdog/PAUSE` trước, xoá sau.
- Không in secret; bỏ dòng "Picked up" trước khi grep lỗi JVM (bẫy `ExitOnOutOfMemoryError`).
- Việc **không script hoá được** (Binance UI: tạo tài khoản con/KYC, tạo key, chuyển tiền, cắt tay LEGACY) ⇒ mỗi việc theo sau bởi 1 script
  **chỉ đọc** xác minh.

### 4.2 Danh mục script (chưa viết — MASTER giao agent viết ở O2)

| # | script | khi nào | làm gì | tự kiểm gì | rollback |
|---|---|---|---|---|---|
| S1 | `deploy_v12rc_dry.sh` | 11-16 | thay jar dcae2e2b → v1.2-rc trên 242, giữ `c3_shadow`, thêm `LIVE_ADAPTER=dry` (+ cờ C11 = 0); ghi sổ C theo ADDENDUM d | md5 jar qua `/proc/<pid>/fd`, env đúng +N dòng, `[LIVE-DRY] BAT`, 0 exception, LEGACY 44, heartbeat, TS-EXT | `rollback_v12rc.sh <TS>` (về dcae2e2b) |
| S2 | `golive_keys_install.sh` | sau khi owner tạo key (Q2) | hỏi key/secret bằng `read -s`, ghi `/root/.config/c3live/keys.env` (600, root) trên 242, không in | gọi chỉ-đọc từ 242 qua `C3LiveCli status`: tài khoản = tài khoản con (UID khác tài khoản chính), quyền Futures, one-way; quyền rút tắt + IP restrict — qua `apiRestrictions` (**CHƯA XÁC MINH** key chỉ-Futures gọi được endpoint này; nếu không ⇒ owner chụp màn hình cài đặt key) | `golive_keys_remove.sh` (xoá file, kiểm không còn) |
| S3 | `golive_canary.sh` | 11-17, lặp 11-24 | chạy `C3LiveCanary` (JVM riêng trên 242, không đụng JVM shadow) chuỗi 8 bước G-CANARY | in PASS/FAIL từng bước; cuối: 0 vị thế, 0 algo order | tự đóng hết khi FAIL; còn sót ⇒ `golive_flatten_c3.sh` |
| S4 | `golive_micro_on.sh` | 11-24 | đổi env: `LIVE_PROFILE=c3_live`, `PILOT_EQUITY=1000`, `SHADOW_NO_PUSH=false`, `LIVE_ENTRY_ENABLED=true`, `LIVE_ADAPTER=live`, `LIVE_KILLSW_MODE=act`, C11 = 1; restart | trước: G-PROMO/G-DRY/G-CANARY `.ok`, margin balance tài khoản con ≥ 1 000, 0 vị thế, không có `run/KILL_SWITCH`; sau: `[C3-LIVE] PUSH ... ON`, `[KILLSW] ... ACT`, reconcile start PASS, twin chạy, LEGACY đúng số | `golive_rb_to_shadow.sh <TS>` |
| S5 | `golive_legacy_verify.sh` | ngay sau khi owner cắt tay 44 LEGACY | chỉ đọc tài khoản chính (qua app 242): số vị thế, lệnh mở | 0 vị thế, 0 lệnh mở tài khoản chính; log app `[LEGACY] managed 0` | không có (chỉ đọc) |
| S6 | `golive_pilot_on.sh` | ngày D | đổi `PILOT_EQUITY=1000 → <size chốt>` (mặc định 10000) ; restart | trước: G-MICRO `.ok`, lượt M tháng 11 `.ok`, margin balance ≥ size, 0 latch kill-switch, không trong khung cấm; sau: sizing leg0 giả lập in ra = công thức trên equity mới, reconcile PASS | `golive_rb_pilot_to_micro.sh <TS>` (về 1000) hoặc S7/S9 |
| S7 | `golive_stop_new.sh` | khẩn cấp mức 1 | `touch run/KILL_SWITCH` (cổng push đọc lại mỗi 10 s — `BinanceOrderTradingManager.processManagerPosition` + `LiveProfileC3.forceNoPush` [XM]); không restart; vị thế + SL vẫn được quản lý | log `PUSH doi trang thai -> OFF` trong ≤ 20 s | `golive_resume.sh` (xoá file sau khi MASTER OK) |
| S8 | `golive_flatten_c3.sh` | khẩn cấp mức 2 | S7 + đóng hết vị thế C3 reduce-only chia lô idempotent + huỷ algo order; gõ `FLATTEN` thay YES | 0 vị thế, 0 algo order trên tài khoản con | **không đảo được** |
| S9 | `golive_rb_to_shadow.sh` | rút về shadow | từ chối nếu còn vị thế C3 (trừ khi `FLATTEN=1` ⇒ gọi S8 trước); env về c3_shadow + dry; restart | như S1 sau chạy | về trạng thái trước bằng S4/S6 |
| S10 | `golive_monitor_install.sh` | trước micro-live | cài cron root trên 242: báo cáo ngày 08:10 + cảnh báo tức thì (đọc log `[C3-LIVE-*]`, `[KILLSW]`) qua `tg.env` watchdog | gửi 1 tin TEST tới Telegram | `golive_monitor_remove.sh` |
| S11 | `golive_scale.sh <equity>` | mở rộng (mục 5.4) | như S6 với size mới | như S6 | chạy lại với size cũ |

### 4.3 Ngày D (dự kiến Thứ Ba 2026-12-08; +07)

| giờ | ai | việc | đạt ⇒ | không đạt ⇒ |
|---|---|---|---|---|
| D−3 | MASTER | ký `GOLIVE_GATE_D.ok`: G-MICRO ĐẠT, lượt M tháng 11 ĐẠT, G-EXEC đã có kết luận size, size chốt (Q4) | báo owner "sẵn sàng" | hoãn D, ghi lý do |
| D−1 trước 12:50 | owner (UI) | cắt tay 44 LEGACY trên tài khoản chính (đã quyết 10-21) | chạy **S5** | S5 FAIL ⇒ owner cắt nốt, chạy lại S5; LEGACY không chặn D (tài khoản tách) nhưng phải xong trước D |
| D−1 | owner (UI) | chuyển `size − 1 000` USDT vào tài khoản con (Futures wallet) | — | — |
| D 09:10 | owner | `DRY=1 bash .../golive_pilot_on.sh` | in "DRY PASS" | gửi log cho MASTER, dừng |
| D 09:15 | MASTER | đọc log DRY, xác nhận | báo owner "chạy thật" | sửa, D+1 |
| D 09:20–09:44 | owner | `bash .../golive_pilot_on.sh` (YES) | script in "XONG" + kiểm sau start ĐẠT | script in lệnh rollback; owner chạy đúng lệnh đó (về micro) |
| D 10:10 | MASTER | đọc 1 giờ đầu: reconcile giờ đầu, twin↔live, RSS, lỗi API | "D+1h ĐẠT" | khẩn cấp theo bảng dưới |
| D 13:30, 20:10 | MASTER | kiểm lại (sau khung 12:50–13:20) | — | — |
| D+1 08:10 | tự động | báo cáo ngày đầu (S10) | — | — |

**Tiêu chí dừng khẩn (bất kỳ thời điểm nào trong 72 giờ đầu; sau đó theo mục 5.3):**
- Mức 1 ⇒ **S7 stop-new** (giữ vị thế, SL trên sàn vẫn bảo vệ): 1 lệnh thật không khớp twin (symbol/side/qty); 1 lần reconcile \|Δ\| > 1 %;
  ≥ 3 lỗi đặt lệnh trong 1 giờ; vị thế đã arm thiếu SL > 2 phút; heartbeat mất > 5 phút; ERROR trên đường `[C3-LIVE-ORDER]` chưa giải thích;
  một leg trượt bất lợi > 2,5 %.
- Mức 2 ⇒ **S8 flatten**: 1 lệnh trùng (cùng leg 2 orderId); vị thế trên tài khoản con mà sổ không biết (vị thế ma) không giải thích được trong
  15 phút; tổng margin > U_MAX·equity + 5 %; DD ≤ −40 % (A40 tự động — script chỉ dự phòng nếu ACT lỗi).
- Rút về shadow (S9) sau S7/S8 khi lỗi cần sửa code; quay lại micro-live (không vào thẳng pilot) sau khi sửa + canary lặp lại ĐẠT.

## 5. Vận hành pilot

### 5.1 Theo dõi
- **Tức thì (Telegram, từ JVM/cron S10):** mọi kích hoạt C1–C6 (START/CONT), latch NO_NEW_ENTRY, lệnh bị từ chối, trượt bất lợi ≥ 1,7 %,
  reconcile lệch > 1 %, heartbeat > 180 s, watchdog restart, đĩa 242 > 90 %.
- **Hằng giờ (trong JVM, C9):** \|equity sổ − margin balance tài khoản con\| / margin balance; số vị thế sổ vs `positionRisk`; mọi vị thế đã arm
  có đúng 1 STOP_MARKET reduce-only.
- **Hằng ngày 08:10 (S10):** equity (margin balance), đỉnh, DD hiện tại; U = margin/equity, số vị thế; leg hôm nay (vào/DCA/thoát, theo lý do
  thoát); trượt bất lợi median/p90/max theo bucket so ECMEAS (NC 7 · C1 18 · C2 19 · C4 32 bps) và stress (23 · 33 · 41 · 101); 24/24 lượt
  reconcile; đếm C1–C6; lỗi API theo mã; RSS/heap, restart, đĩa; trạng thái parity lượt D hôm qua.
- **Hằng tuần (MASTER, thứ Hai):** sim Vision cùng tuần cùng cờ vs live (lệnh trùng, ΣPnL, chi phí thực = live − sim); phân rã chi phí
  drift/impact; G-PARITY lượt D tuần; danh sách sự cố; khuyến nghị giữ/giảm/dừng gửi owner (5–10 dòng).

### 5.2 Kill-switch (owner duyệt 10-21: A40 + C1–C6; ngưỡng killsw_1018)
| mã | điều kiện | hành động (ACT) |
|---|---|---|
| C1 | dữ liệu trễ > 3′ hoặc > 10 % symbol thiếu | NO_NEW_ENTRY (tự nhả khi hết 30′ liên tục — **[MỚI]** MASTER chốt khi code C8) |
| C2 | trượt **bất lợi** > 2,5 % (khuyến nghị: 1,7 % cảnh báo; > 2,5 % lặp 3 lần/24h ⇒ dừng mở mới — chờ owner Q1) | cảnh báo / NO_NEW_ENTRY latch |
| C3 | ≥ 5 lỗi API liên tiếp (gồm lỗi đặt lệnh) | NO_NEW_ENTRY latch |
| C4 | vị thế > 90 hoặc U ≥ U_MAX (0,60) | NO_NEW_ENTRY (tự nhả khi dưới ngưỡng — U_MAX vốn là trần của chiến lược) |
| C5 | không tick > 5′ | NO_NEW_ENTRY + watchdog |
| C6/A40 | DD ≤ −40 % trên equity tài khoản con (đỉnh tính từ lúc pilot bật, không tính tiền nạp thêm) | đóng hết C3 + dừng + latch |
Latch chỉ owner xoá bằng `golive_resume.sh` sau khi MASTER xác nhận nguyên nhân.

### 5.3 Quy tắc dừng pilot (ngoài kill-switch tự động)
- **DD 40 %** (A40) ⇒ đã đóng hết; không mở lại trong pilot này. Pilot mới = quyết định owner mới.
- **Trượt:** > 2,5 % lặp lại (3/24h) ⇒ stop-new (C2); median trượt bất lợi trên 50 leg cuộn > giả định **stress** cùng bucket ⇒ MASTER đề xuất
  giảm size một nửa (owner quyết).
- **Lệch sổ > 1 %:** 1 lần ⇒ báo động; 2 lượt hằng giờ liên tiếp ⇒ stop-new tới khi giải thích; vị thế ma ⇒ flatten (mục 4.3).
- **Parity:** lượt D TRƯỢT trong pilot ⇒ stop-new, điều tra (logic live ≠ backtest ⇒ số DEV không còn đại diện).
- **Xem lại chiến lược (không tự dừng):** DD ≤ −25 % (vượt DD tệ nhất DEV −24,7 %) hoặc 3 tháng liền âm ⇒ MASTER báo cáo regime (điểm yếu đã
  biết: 2022 ≈ 0, HO 2026 Q3 âm) cho owner.

### 5.4 Mở rộng vốn (đề xuất — owner duyệt lộ trình, Q6)
- Điều kiện đồng thời: ≥ 8 tuần pilot; ≥ 50 leg thật **và** ≥ 1 đợt sập có ≥ 12 leg cùng đợt (tải thật đã được thử); 0 sự cố mức 2; reconcile
  ≥ 99,9 % lượt; median trượt bất lợi ≤ giả định ECMEAS "thực" + 25 bps; không có latch kill-switch trong 30 ngày gần nhất; parity mọi lượt ĐẠT.
- Bước tối đa ×2 (10k → 20k → 40k), mỗi bước lại ≥ 8 tuần với cùng điều kiện; chỉ tăng bằng S11 trong khung giờ hợp lệ.
- Đổi size theo F_BASE (B15) **không** phải mở rộng vốn — là thay đổi khẩu vị rủi ro (iso_risk_1018: HO không CONFIRM) ⇒ quyết định riêng.
- Sau DD > 25 % hoặc bất kỳ latch C6: về lại size bước trước, đếm lại 8 tuần.

## 6. Rủi ro còn mở + quyết định owner cần chốt

### 6.1 Owner cần chốt (xếp theo thời điểm cần)
| # | cần trước | câu hỏi | khuyến nghị MASTER |
|---|---|---|---|
| Q1 | **10-27** (chặn code C6/C8/C9) | Xác nhận 3 khuyến nghị 10-23: (a) sau arm đặt STOP_MARKET trên sàn, dời theo giá; chưa arm/time-stop app quản lý, không SL cứng; (b) equity = margin balance tài khoản con + đối chiếu sổ mỗi giờ (lệch > 1 % báo động); (c) C2 1,7 % cảnh báo, > 2,5 % lặp 3 lần/24h dừng mở mới — và C2 chỉ tính trượt **bất lợi** | đồng ý cả 3 |
| Q2 | **11-13** | Tạo tài khoản con + key: chỉ Futures, tắt rút, IP chỉ 242; one-way; CROSS; leverage 1 (S2 kiểm) | như đã chốt 10-23 |
| Q3 | 11-16 / 11-23 | Nạp ~200 USDT (canary) rồi 1 000 USDT (micro-live) vào tài khoản con | 200 / 1 000 |
| Q4 | **D−3** | Size pilot: 10 000 với F_BASE gốc (×1,0); nếu G-EXEC RED_SIZE ⇒ 5 000 hay hoãn | ×1,0; RED ⇒ 5 000 |
| Q5 | D−1 | Giờ cắt tay 44 LEGACY (đã quyết sẽ cắt) | D−1 sáng, trước 12:50 |
| Q6 | sau 8 tuần pilot | Duyệt lộ trình mở rộng mục 5.4 | — |
(MASTER tự quyết, không hỏi owner: ngưỡng [MỚI] mục 3, bật cờ C11 từ micro-live, có/không chạy thêm sim-replay XÁM-only.)

### 6.2 Rủi ro còn mở
1. **Code tiền thật mới chưa chịu tải thật** (lớn nhất): canary/micro chỉ vài leg; lần đầu 24 leg/tick + dời SL hàng loạt + rate limit IP chung
   ingest sẽ là đợt sập đầu trong pilot. Giảm: C13 rate guard + test tải mock 24 leg/80 vị thế; stop-new tự động; theo dõi trực tiếp đợt đầu.
2. **Một host 242 duy nhất** (sự cố 10-07 sập ~8h không quản lý): SL trên sàn bảo vệ vị thế đã arm; vị thế chưa arm không có SL (thiết kế đã chọn,
   1x long không bị thanh lý thực tế) nhưng mất DCA/time-stop/X14 khi 242 chết.
3. **Cửa sổ shadow không có đợt sập** ⇒ P2/skipFull/TS-EXT chưa kiểm forward; exec-probe có thể không đủ 100 leg ⇒ size quyết theo luật cũ.
4. **Regime**: edge dồn theo đợt; HO 2026 Q3 âm; 2022 ≈ 0 ⇒ pilot có thể nhiều tháng không lãi — không phải lỗi hệ.
5. **Secret**: key tài khoản chính hardcode trong mọi jar (`PrivateConfig`), shadow_c3 trên Oracle mang key gọi signed bị -2015 ~65 lần/giờ
   (golive_1009) — key c3_live tách file root-only (C2) nhưng key chính vẫn rò nếu jar lọt; **không thêm IP Oracle vào whitelist**.
6. **Mất log cửa sổ** (đĩa 242 82 %, pull242 chưa có) ⇒ O1 làm ngay, nếu không ngày thiếu = KHÔNG ĐO ĐƯỢC ⇒ có thể phải gia hạn cửa sổ.
7. Oracle user `ubuntu` sudo không mật khẩu; OpenClaw từng sai/vi phạm ⇒ mọi chấm cổng do agent Opus độc lập audit trước khi ký `.ok`.
8. **CHƯA XÁC MINH**: giới hạn rate thật tại thời điểm code; minNotional hiện hành từng symbol; `apiRestrictions` với key chỉ-Futures;
   `PAPER_EQUITY` thực trên 242; ngày Vision phát hành monthly fundingRate tháng 10/11; `check_242_failopen.sh` đã chạy chưa.
