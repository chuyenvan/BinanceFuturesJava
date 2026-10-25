# A1_DELTA_2C — audit delta `v1.2/c3-live` vòng 2c (a896595f → 9c5a786f)

Auditor: a1audit (Claude Opus, độc lập), 2026-10-25. Chỉ đọc branch c3-live; build/test trong worktree tách riêng `~/claude_master/v12/a1d`
(detached 9c5a786f). Không đụng 242/Binance, không push. Bằng chứng: `~/claude_master/v12/a1d_parity/` (proof sao lưu: `docs/result/a1audit/2c/`).

## 0. Kết luận risk-first

**G-CODE: TRƯỢT (sát), vì còn 1 MAJ mở: MAJ-2b.** CRIT-1 và MAJ-1 đã ĐÓNG. MAJ-2 mới đóng một phần: hết ca 1 lần đọc rỗng, nhưng còn hở ca 2 lần đọc rỗng.
Đường byte-identical của c3_shadow ĐẠT, universe ĐẠT, MIN-6/7 ĐẠT.

| mã | trạng thái | bằng chứng |
|---|---|---|
| CRIT-1 | **ĐÓNG** | ProofKs đi qua đường thật `OpsHooks.build` (c3_live, PAPER_EQUITY=35000, `run/killsw_peak`=35015,29, tmb=10000): `action=NONE`. File đỉnh của c3_shadow không bị đổi nội dung lẫn mtime. Chi tiết §1 |
| MAJ-1 | **ĐÓNG** | `Reconciler` khởi tạo với `BLOCK_STARTUP`: `allowsEntry` trước `startup()` = false, sau startup OK thì gỡ |
| MAJ-2 | **MỞ MỘT PHẦN → MAJ-2b** | ProofFlat: stream mất, positionRisk trả 200 nhưng RỖNG 2 lần cách 10 s ⇒ FlatConfirm (iii) xác nhận "phẳng" ⇒ **huỷ stop c3s- + xoá cụm trong khi vị thế THẬT 100 XRP vẫn còn**. Ngay trước lần đọc thứ 2, `openStops(XRP)` vẫn có 1 stop c3s- NEW, nhưng (iii) không xét tới |
| MIN mới (MIN-18) | mở | Cùng proof: chỉ 1 lần đọc rỗng là `unknownCheck` đã **gỡ chặn UNKNOWN_POSITION** (`allowsEntry=true` giữa lúc glitch); lần đọc thật kế tiếp mới chặn lại |

Sửa MAJ-2b (rẻ, an toàn một chiều vì để stop sống khi vị thế đã phẳng là vô hại): trong FlatConfirm (iii), thêm điều kiện **"không còn stop c3s- của cụm ở trạng thái NEW
trong `openStops(sym)`"**. Nếu còn ⇒ giữ cụm + stop, WARN và Telegram một lần, chờ stream (`pa=0`) hoặc owner xử lý. Đề nghị thêm một trong hai nguồn đối chứng:
`account().positions` (`/fapi/v3/account`), hoặc ≥ 3 lần đọc cách ≥ 30 s. MIN-18: `unknownCheck` không được gỡ chặn khi danh sách positions rỗng.
Nhận xét: DryGateway không bao giờ trả positions rỗng, nên MAJ-2b không ảnh hưởng **dry**. Nếu MASTER muốn cho dry chạy trước khi sửa thì phải ghi ngoại lệ có chủ đích;
canary/live thì bắt buộc sửa trước.

## 1. CRIT-1 (a577b1ef) — ĐÓNG

Proof `ProofKs2.java` gọi bằng reflection `OpsHooks.build`, đúng đường mà `newEngine` dùng:
- S1 c3_live + PAPER_EQUITY=35000 + `run/killsw_peak`=35015,29, tmb=10000 ⇒ **NONE**.
- S2 tmb 10000→5900 (−41 %) ⇒ C6 **và** A40 cùng latch FLATTEN (cùng nguồn tmb, cùng −40 %; hai mã chung một hành động, một Telegram nâng mức). Không double-action.
- S3 `reset_peak=0` ⇒ latch lại ngay (đúng, DD vẫn −41 %). S4 `reset_peak=1` ⇒ cả acctPeak (A40) lẫn đỉnh C6 (RAM + file) đặt lại ⇒ không latch lại. Không sót đỉnh nào.
- S5 restart ⇒ đỉnh C6 nạp từ `run/c3live_killsw_peak` (riêng), A40 nạp từ `acct_peak` trong file latch. Hai đỉnh có thể lệch nhẹ do onBook và periodic lấy mẫu tmb ở thời điểm khác nhau
  (vd 6000 vs 5900); chấp nhận được.
- S6 equity NaN/0 ⇒ giữ nguyên trạng thái C6. S7 file đỉnh của c3_shadow: nội dung 35015,29, mtime không đổi.
- S8 `LIVE_C3_KILLSW_PEAK_FILE` trỏ trùng file sổ giấy (kể cả dạng `./run/../run/killsw_peak`) ⇒ tự fallback về `run/c3live_killsw_peak`.
- S9 đường c3_shadow (`c3live=false`) giữ ngữ nghĩa v1.1 (sàn PAPER_EQUITY, file đỉnh sổ giấy).
- ProofKs GỐC (dựng engine trực tiếp, `c6OwnPeak=false` = ngữ nghĩa v1.1) vẫn ra FLATTEN. Điều này đúng kỳ vọng, vì proof gốc bỏ qua `OpsHooks`; đường thật là S1.
- Tìm đường khác chạm `run/killsw_peak`/PAPER_EQUITY ở c3_live: `newEngine` chỉ truyền `c3LivePeakFile()` + `paperEquity=null` khi C3LIVE;
  `onPaperBook/onPaperTick` no-op ở C3LIVE; reset/restart/A40 dùng file latch c3_live. **Không tìm thấy đường nào.**
- Ngưỡng C6 c3_live = `C6_DD = −0,40` (hằng số, không đổi), khớp killsw_1018.
- Hậu kiểm LATCH 120 s (`deploy_v12_dry.sh` 4b): có ≥1 dòng `[KILLSW] LATCH|NAP LATCH|FAIL-CLOSED` hoặc ssh lỗi ⇒ **rollback thật**
  (`YES_AUTO=1 FORCE_TIME=1 rollback_v12.sh`, khôi phục jar/env/start, đổi tên sổ + latch + `c3live_killsw_peak`). fake242 kiểm đủ luồng
  (31/31 theo tác giả). Có thể PASS giả khi: (a) `logs/full.log` không tồn tại ⇒ `grep -c` = 0. Không nguy hiểm, vì CHK sau đó WAIT/FAIL và script exit 1 (nhưng không tự rollback);
  (b) log quay vòng trong 120 s ⇒ dòng LATCH rơi vào file cũ (hiếm); (c) latch xảy ra sau 120 s (C1 > 180 s) ⇒ CHK có `FAIL KILLSW_LATCH` nhưng chỉ nhắc owner chạy rollback.
  Trên log 242 sau lần restart 10-23 09:37 (KS mode log): 0 dòng `WOULD_TRIGGER` ⇒ khả năng C1/C5 lúc khởi động làm FAIL giả là thấp (mới có 1 mẫu restart). MIN.
- MIN-19: đi từ dry sang canary mà KHÔNG rollback thì `run/c3live_killsw_peak` (đỉnh tmb DRY giả lập) sẽ bị dùng tiếp cho tiền thật. Deploy canary nên đổi tên file này (rollback đã có).

## 2. MAJ-1 / MAJ-2 (e6d4a356)
- MAJ-1: `blocks.put(BLOCK_STARTUP, …)` trong constructor, chỉ `startup()` thành công mới gỡ. **ĐÓNG** (ProofKs, ProofFlat: false trước startup).
- MAJ-2: `reconcileClusters` + `C3LiveFlattener.closeOne/checkPrevClose` không còn coi "vắng" là phẳng. Bằng chứng dương: (i) stream `pa=0`;
  (ii) stop FINISHED/FILLED hoặc lệnh đóng FILLED đủ qty; (iii) FlatConfirm: 2 lần đọc cách ≥ 5 s + `openOrders(sym)` (lệnh THƯỜNG) rỗng.
  **Lỗ hổng MAJ-2b:** c3_live không bao giờ có lệnh thường mở (MARKET khớp ngay, stop là algo) ⇒ điều kiện `openOrders` rỗng luôn đúng, nên (iii) thực chất chỉ còn
  "2 lần đọc rỗng". ProofFlat (`chk/ProofFlat.java`, Mock của repo + glitch positions rỗng) tái hiện được: cụm bị xoá, stop bị huỷ, vị thế thật còn nguyên.
  **Nên thêm điều kiện "0 algo c3s- NEW"** như đề xuất ở §0.
- Race OPS / stream / Flattener: `FlatConfirm` synchronized và dùng chung. `Reconciler` synchronized (fallback chạy trên luồng STREAM, `confirmPendingFlat`
  chạy trên OPS) ⇒ tuần tự. `closedOnExchange` (acct) và `finalizeClosed` (flattener) có thể chạy chồng nhau cho cùng symbol, nhưng huỷ stop/xoá cụm idempotent ⇒ vô hại.
  `Flattener.step` đọc positions TRƯỚC khi chụp cụm ⇒ một cụm vừa khớp có thể bị đánh dấu nghi phẳng ở lần đầu, nhưng lần đọc thứ 2 thấy vị thế thì xoá mốc ⇒ an toàn.
  Không thấy race nào đáng kể ngoài MAJ-2b.
- Adopt stop c3s- lúc restart (MIN-6): chỉ nhận khi cùng `symbol` của lệnh sàn, cụm đã arm, chưa có stop active/pending, không flatPending; lấy stop có giá cao nhất,
  phần còn lại huỷ. Tài khoản con không chứa LEGACY (LEGACY nằm ở tài khoản CHÍNH) và chỉ xét prefix `c3s-` ⇒ không nhận nhầm LEGACY/stop ngoại lai.
  Có thể nhận stop mồ côi của cụm CŨ cùng symbol (giá cũ thấp hơn) — trailing sẽ dời lên ở nhịp kế. Stop kiểu qty (`!isClosePosition`) có qty khác vị thế ⇒ bảo vệ một phần
  cho tới lần dời. MIN.

## 3. MIN-5/6/7 (dcf45e29)
- MIN-5: nạp sẵn `GET /fapi/v1/symbolConfig` toàn bộ (1 call, start + mỗi giờ, lỗi thì thử lại sau 5′). Leg đầu dùng cache chỉ khi `globalOk` và TTL ≤ 70′.
  CHƯA XÁC MINH sàn có trả đủ mọi symbol không; symbol vắng thì quay về kiểm riêng ⇒ an toàn. Đưa vào canary K0.
- MIN-6: sổ không ghi được ⇒ VẪN đặt/dời stop + ERROR + Telegram (giới hạn 10′/lần). Trạng thái chỉ còn trong RAM; restart thì adopt (trên). ĐẠT (đọc code + `TrailingStopBookFailTest`).
- MIN-7: `get()` lỗi ⇒ thử lại mỗi 60 s + ERROR/Telegram ở mọi nhánh. Phần VÀO LỆNH (universe/modeGuard/entry) lỗi ⇒ MANAGE-ONLY: hook `onLeg` thoát sớm vì
  `entry()==null`; ops vẫn chạy trailing/time-stop/X14/reconcile/FLATTEN; mọi chỗ dùng universe/modeGuard đều có kiểm null.
  **Gateway lỗi (vd key file) vẫn KHÔNG quản lý vị thế** — không có gateway thì không thể làm gì; stop trên sàn vẫn bảo vệ các cụm đã arm. Chấp nhận.
  Không dựng được proof đứng riêng cho nhánh manage-only: nhánh này chỉ kích được khi constructor `SymbolUniverseLive`/`AccountModeGuard`/`C3LiveEntry.build` ném lỗi, và
  điều đó không xảy ra với cấu hình hợp lệ (code phòng thủ, gần như không bao giờ chạm tới). Thiếu unit test (MIN, ghi nhận). `attachEquitySource` dời vào `start()` ⇒ lần thử lại không gắn nguồn cũ.

## 4. Byte-identity c3_shadow — ĐẠT
- Build lại 9c5a786f: **593 test, 0 fail, 1 skip** (có sẵn). Jar A1 md5 `6b9efc6f…` (khác `ff717f38` của tác giả vì jar không tái lập byte; đã so lớp).
- Bytecode jar `dcae2e2b` ↔ jar A1 2c: 622 → 737 lớp, 0 xoá, thêm 5 lớp ngoài c3live (y như lần 1) + lớp c3live, **26 lớp đổi = đúng tập lần audit 1**.
  `javap` (bỏ chỉ số pool): 10 lớp inner 0 khác. Các lớp cũ khác có số dòng khác **y hệt lần 1**, trừ `KillSwitchEngine` (2942→3296), `OpsConfig` (283→368), `OpsHooks` (556→600) = CRIT-1.
  Ở cả 3 lớp này, mọi nhánh mới đều chặn bởi `prm.c6OwnPeak` (mặc định false; chỉ `build(c3live=true)` bật) hoặc `C3LIVE`. Nhánh c3_shadow của `build` gọi đúng constructor
  và đối số như trước (proof S9). Utils: diff nguồn với 16de49a6 nay còn **2 dòng thật** (EOL CRLF đã trả lại).
- `SymbolUniverseLive`/`TradFiClassifier`/`FlatConfirm` chỉ được dùng trong `c3live.*` ⇒ c3_shadow/sim không bị ảnh hưởng.
- **Parity offline cờ TẮT, jar A1 2c, 2026-10-22 VÀ 2026-10-23** (driver `drv.py` của lần 1, cache tự dựng): md5 (giải nén) của out_BT/out_NEW2/fund_BT/fund_NEW2
  **trùng 8/8** với md5 jar dcae2e2b đã đo ở lần 1 (10-22: 2c7c336d/2c7c336d/1a6d1521/f4acab23; 10-23: e0918a33/e0918a33/a81b3b03/8dea3f70).
  CTL gate 1440/1440 bit, 0 only_ref/only_new; CTL fund y hệt lượt ref (10-22: f3 0,94425; 10-23: f3 0,94586 + cand 0,99750 — có sẵn từ trước).
  strace: 0 AF_INET không-loopback, 0 tới 242, rc 0 (BT + 3 segment × 2 ngày). `a1audit/2c/a1d_compare.json`.

## 5. Universe (321b7d44) — ĐẠT
Jar A1 2c trên dump thật (`UniCheck.java`): listed 932, tradable 519, **buyable 513**, market index 514 (519 − 5 non-ASCII), **TradFi lọt buyable = 0, TradFi trong index = 0**.
Lý do loại: TRADFI 224, NOT_TRADING 138, NOT_USDT 44, NON_ASCII 5, NOT_PERPETUAL 4, **INDEX 2** (ALLUSDT, BTCDOMUSDT: không buyable, **không có trong market index**),
EXCLUDED 1 (USDC), DELIVERY_SOON 1 (VELODROME). PREDICTUSDT nay được coi là crypto (PREMARKET), bị loại vì PENDING_TRADING. MDT bị loại, POWR được giữ.
Khớp với số đếm Python độc lập của lần 1 (520 − ALLUSDT = 519).

## 6. MIN còn lại
MIN-18 (gỡ chặn UNKNOWN khi đọc rỗng), MIN-19 (đỉnh C6 của dry mang sang canary), adopt stop qty/cụm cũ (§2), hậu kiểm LATCH có thể PASS giả khi thiếu log/log quay vòng (§1),
manage-only chưa có test (§3), MIN-3/4/8/9/14/15/16 của lần 1 chưa đổi (không chặn).
