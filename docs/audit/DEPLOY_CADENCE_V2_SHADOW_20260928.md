# AUDIT — DEPLOY CADENCE-SPLIT-V2 LÊN SHADOW (Oracle) — 2026-09-28

Phạm vi được duyệt (owner 28/09 08:14): *"ok duyệt mấy lần rồi. làm cho shadow chạy giống backtest
để kiểm backtest đi… cứ triển khai thôi mục tiêu là shadow phục vụ verify live khớp backtest và
audit backtest"* ⇒ Mục tiêu: shadow **chạy giống backtest** (SELECTOR **15'** + BIG_DOWN/DCA **1'**)
và **ghi được feature để audit**.

Bản deploy: **`bd7c4cd`** (branch `module`) — image HEAD+patch `MARKET_SCAN_MIN` + `MARKET_SCAN_PRIORITY`
+ instrument `LIVE_FEAT_DUMP`. Chỉ **SHADOW** (`shadow-c3.service`, paper). **KHÔNG** chạm **242** ·
**KHÔNG** đổi gate/ONNX · **KHÔNG** sửa `config.properties`.

---

## 0. CỔNG PARITY (bắt buộc trước deploy) — PASS

`docs/result/RESULT_CADENCE_V2_PARITY.md` (phiên khác tạo) — trạng thái **PASS**, md5 kiểm lại độc lập:

| chân | md5 `printDone.csv` | yêu cầu | khớp |
|---|---|---|---|
| `par-kg0` | `99e42b75cf1a2142f9cd14dc72e371ba` | `99e42b75…` | ✅ |
| `par-t170` | `efb793e2468ca3a7318da0f0ad23d4fc` | `efb793e2…` | ✅ |
| `par-bb` (khai RÕ `=0`) | `99e42b75cf1a2142f9cd14dc72e371ba` | = `par-kg0` | ✅ |

⇒ "OFF ⇒ y nguyên" có **bằng chứng THỰC NGHIỆM** trên jar build từ `bd7c4cd`. **ĐỦ ĐIỀU KIỆN DEPLOY.**

---

## 1. BACKUP (trước mọi thay đổi) — `/home/ubuntu/shadow_c3/`

| Đối tượng | sha256 TRƯỚC | Backup |
|---|---|---|
| jar đang chạy (`target/binance-java-sdk-1.2.4.jar`) | `e3bf2d21cdce72cc81c72f0d917c15642afba28348beb316b94b651f6a6b79d0` | `…jar.bak_20260928` |
| `app/conf/env.sh` | `cfe2c8fdc812d22797bbdaa62bb899a7fd9acffc28fc459f26eecc8b6e7992c6` | `conf/env.sh.bak_20260928` |
| `app/config.properties` (**không sửa**) | `d8d5e87a4964ba292703dc03d6d544d494b009db1613685333d7ffd36b0b1b28` | `config.properties.bak_20260928` |
| `bin/health.sh` | `7bf106544baa19ff3dafb89b2eaa5a6e353db3b02a5637a405c015025259b491` | `bin/health.sh.bak_20260928` |
| ONNX `s1_model/s1a2x1_cut20251001.onnx` | md5 `afaa2828a6d8c73e4b32c3f9a6d0c79b` | (baseline) |

- `systemctl show shadow-c3 -p MainPID,ExecMainStartTimestamp,ActiveState` TRƯỚC:
  **MainPID=2011017 · 2026-09-28 07:51:47 · active**.
- `df -h /` TRƯỚC: `194G size · 180G used · 15G avail · 93%`.

---

## 2. BUILD + ĐẶT KEY (chỉ shadow)

1. **Jar**: build local từ HEAD `bd7c4cd` (`mvn -o -DskipTests clean package`),
   sha256 = **`78387f301c41d2e282fd28c187e1b84de2cdb881bd0b55f6082e3640abcd3c71`**, copy vào shadow.
   (Ghi chú: `git diff bd7c4cd..HEAD -- src/main` = **rỗng** ⇒ HEAD mọi lúc build đều cùng `src/main`.)
2. **`app/conf/env.sh`**: thêm 3 dòng (KHÔNG sửa `config.properties`; KHÔNG đổi `SHADOW_NO_PUSH=true`):
   ```sh
   export MARKET_SCAN_MIN=1        # BIG_DOWN/DCA quét mỗi phút
   export MARKET_SCAN_PRIORITY=1   # ưu tiên + hàng đợi có chặn (SEL ≤1 chỗ; MKT bỏ qua khi bận)
   export LIVE_FEAT_DUMP=3000      # instrument: ~3000 tick, trần 200 MB tự dừng
   ```
   `env.sh` sha: `cfe2c8fd…` → **`6cc24a5765cff4248f873340e6453790b3a19b254f1d0709b24b471f6ab0f24f`** · `bash -n` PASS.
3. `systemctl restart shadow-c3` lúc **08:40:26** → rc=0; `MainPID=2017092`,
   ExecMainStartTimestamp **2026-09-28 08:40:27**, `is-active=active`. **Lên trong ~1s** (không cần rollback).

---

## 3. XÁC MINH (cửa sổ 08:40:27 → 09:12, ~31,5 phút)

- **`[CADENCE-SPLIT]`**: CÓ — `[CADENCE-SPLIT] MARKET_SCAN_MIN=1 => MARKET-LEVEL(BIG_DOWN/DCA) quét 1 PHÚT, SELECTOR luôn 15'`
  + `[CADENCE-SPLIT-V2] MARKET_SCAN_PRIORITY=1 => BẬT: SEL luôn xếp hàng (≤1 chỗ), MKT chỉ nộp khi RẢNH` (08:40:34).
- **ERROR mới**: **0** (trước 4675 → sau 4675; `grep " ERROR " logs/full.log` trên cửa sổ = 0).
- **`[GATE]` vẫn 15'**: chỉ **2 GATE** trong 31,5' (`08:49:41`, `09:06:28`) ⇒ **~3,8 lượt/giờ**.
  Mỗi GATE ứng với **1 tick SELECTOR ở mốc lưới 15'** (08:45:06 và 09:00:06), KHÔNG có GATE ở tick 1'
  (đối chứng tồi tệ: nếu selector bị giãn/bơm theo phút sẽ thấy ~30 GATE).
  *Lưu ý kỹ thuật*: log `[GATE]` phát ra ~4' SAU khi tick bắt đầu (sau khối `[MAP]`/predict, ngay trước `Finish`),
  nên mốc log GATE bị offset; **bằng chứng "15'" nằm ở mốc tick START = `isTimeProcessData()` (`ENTRY_GRID_MIN=15`, second 6–10)**.
- **`Start check level change`**: **7 lượt**/31,5' ⇒ **~13,3 lượt/giờ** (bao gồm 2 SEL + 5 MKT).
  Thấp hơn ước lượng mô hình 16–20 (`PLAN_CADENCE_SPLIT_V2.md` §3) vì **1 lượt chạy ~4,3'** (mô hình giả định 2,8')
  ⇒ trần ~14 lượt/giờ. **KHÔNG có dấu hiệu dồn hàng đợi**:
  - Start: `08:41:06, 08:45:07, 08:50:06, 08:54:06, 08:58:06, 09:02:09, 09:07:06` — cách đều ~4–5', nối tiếp nhau (không co lại rồi bùng).
  - Số **Finish ≈ số Start** (5 MKT-only + 2 SEL = 7) ⇒ **không tích luỹ** (hàng đợi ≤1).
  - Cách kiểm "số lần chạy vs số lần nộp": vòng lặp nộp 1 tick/phút nhưng chỉ **7 lượt được chạy** trong 31,5'
    ⇒ 24 lượt bị **bỏ qua có chủ đích** (skip-if-busy), không xếp hàng.
- **MARKET-LEVEL(BIG_DOWN/DCA) ở phút LẺ**: TRƯỚC restart `Market level change` chỉ ở mốc 15' (`08:00:07/08:15:07/08:30:07`);
  SAU restart quét cả phút lẻ: `08:54:07, 08:58:08, 09:02:11, 09:07:…` ⇒ nhịp MARKET 1' đã hoạt động.
- **`would-BUY` BIG_DOWN/DCA ở phút lẻ**: **KHÔNG quan sát được trong cửa sổ** vì **không có tín hiệu vào lệnh nào**
  (`[GATE] … n_pass=0` mọi tick; `Market level: level: null`). Đây là *không có entry*, KHÔNG phải lỗi nhịp —
  kiểm chứng nhịp MKT dùng log `Market level change` ở phút lẻ (ở trên).
- **Instrument `feat_dump`**: file `app/feat_dump/feat_dump_20260928_084006.csv.gz`
  xuất hiện (mở 08:41:07, log `[LIVE_FEAT_DUMP] BẬT … 3000 tick`). Tại 09:07: **8 dòng** (1 header + 7 data),
  **36 cột** = **33 feature** + `ts` + `symbol` + `p15_out` (đúng thiết kế), dung lượng **1,7 KB** (đang ghi,
  `syncFlush`; gzip báo "unexpected end of file" là bình thường khi file còn mở).
- **ONNX md5**: `afaa2828a6d8c73e4b32c3f9a6d0c79b` — **KHÔNG đổi**.
- **`health.log`** (cron giờ, bản 09:00:01 +07) vẫn đủ field:
  `pid=2017092 UP … disk=14G tick_cuoi="28/09/2026 08:58:06" s1_cuoi="28/09/2026 08:49:41"
  wouldBUY=60 wouldCLOSE=63 createOrder=0 errLines=4675 ledgerRows=74 gatePassCuoi=NEVER gateRejStreak=683`
  (+ ALERT `GATE_DONG_BANG` — **có sẵn từ trước**, không do deploy: 01:00Z đã 679).
- **`df -h /` SAU**: `180G used · 14G avail · 93%` (giảm 15G→14G; **93% = ngưỡng cảnh báo** — đĩa là rủi ro sẵn có).
- **242**: chỉ **ĐỌC** (không gửi lệnh thay đổi): hostname `3stech.vn`, java đang chạy (cwd `/home/chuyennd/java/v_t_m`).
  **KHÔNG chạm 242.**

---

## 4. ROLLBACK (nguyên văn — chỉ chạy khi cần)

```sh
cd /home/ubuntu/shadow_c3/app
cp -p target/binance-java-sdk-1.2.4.jar.bak_20260928 target/binance-java-sdk-1.2.4.jar
cp -p conf/env.sh.bak_20260928 conf/env.sh
sudo systemctl restart shadow-c3
# Kỳ vọng: jar sha256 = e3bf2d21…, env.sh = cfe2c8fd…, KHÔNG còn [CADENCE-SPLIT]/[CADENCE-SPLIT-V2],
# GATE trở lại chỉ ~4 lượt/giờ ở mốc lưới 15'.
```
Biến thể nhanh (không đổi jar): sửa `conf/env.sh` đặt `MARKET_SCAN_MIN=0` + `MARKET_SCAN_PRIORITY=0`
(hoặc xoá 3 dòng) rồi `sudo systemctl restart shadow-c3`.

**Tiêu chí rollback ngay** (chưa xảy ra): `[GATE]` xuất hiện ở tick 1'; entry selector ngoài mốc 15';
số entry tăng bất thường; `Exception` mới trong `checkMarketLevelChange2Trade`; hàng đợi dồn.

---

## 5. KẾT LUẬN

**DEPLOY THÀNH CÔNG.** Shadow chạy **giống backtest**: SELECTOR vẫn **15'** (2 GATE/31,5'), MARKET-LEVEL quét **1'**
(phút lẻ), hàng đợi **không phình**, 0 ERROR mới, ONNX/config không đổi, `feat_dump` (33 feature) bắt đầu ghi
⇒ phục vụ **verify live khớp backtest + audit backtest**. 242 chưa deploy (theo owner: làm riêng sau khi shadow ổn định).
