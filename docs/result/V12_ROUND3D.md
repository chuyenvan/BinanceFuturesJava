# V12_ROUND3D — canary-early MỘT lệnh (`canary_early_all.sh`) + dùng lại keepAlive K0 (prereg §ADD-3)

Branch `v1.2/c3-live`, agent v12exit, 2026-10-27. Chỉ code + test + script; không gọi Binance, không đụng 242, không push.
A1 re-audit delta `5ab3a8ab..HEAD` (Java nhỏ: `CanaryEngine` keepAlive reuse, `C3LiveCanary` keycheck + env).

## 1. Hash, addendum, jar

| mục | giá trị |
|---|---|
| addendum prereg §ADD-3 (commit riêng, TRƯỚC code) | `5ab3a8ab` — `docs/prereg/GCANARY_PREREG.md` sha256 `7348a9234f463e9c54d3fb6aa94a5d78e671347ec6f9e4527da13f1b7cb13814` |
| Java: keepAlive reuse (engine) + keycheck pos/orders/algos + test | `b4c4cca2` |
| script: `canary_early_all.sh`, lib (`cl_flat_read`, `cl_tg`, `cl_early_old/jar/reset`, `cl_run` ssh trả về ngay), test_fake242 mục 17 | `cde0c7f6` |
| pin jar 3d | `61d5e6f5` |
| jar (canary-early + dry) | `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_3d`, md5 **`ddd8fe17ffe0405a6a49a7c7e7e377a5`** (pin `canary_lib.sh` + `deploy_v12_dry.sh`) |
| build | 648 test, 0 fail (646 + 2 mới) |
| test script | `test_fake242.sh` **134/134 PASS** (115 cũ — chạy trong khung giờ nên 1 kiểm "ngoài giờ" tự bỏ qua như 3c — + 19 mới mục 17); chạy trên bản sao `git archive` + file mới (không chạy trong worktree khi owner đang dùng) |
| parity 10-23 (c3_shadow, jar 3d vs dcae2e2b) | **PASS** — out_BT `e0918a33` khớp, out_NEW2 `e0918a33` khớp, fund_BT `a81b3b03` khớp, fund_NEW2 `8dea3f70` khớp; ctl only_ref = only_new = 0; strace AF_INET non-loopback = 0 (`docs/result/round3d/r3d_compare.json`) |

Delta `src/main` chỉ trong `c3live/canary/` (CanaryEngine, C3LiveCanary). Đường c3_shadow / runtime không đổi.

## 2. Owner chạy đúng 1 lệnh (trên Oracle)

```
bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_early_all.sh
```
gõ `YES` một lần. Sau đó toàn bộ chạy nền (`setsid nohup`), đóng terminal không dừng phiên; kết thúc ⇒ Telegram.
Dừng khẩn cấp: `touch ~/claude_master/canary/CANARY_STOP` hoặc `bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_early_flatten.sh`.

Thứ tự (mọi bước giữ nguyên kiểm v_t_m không đổi, RAM ≥ 1 GB đầu / ≥ 768 MB mỗi bước, file STOP, trần lỗ 2 USDT, trần cộng dồn 4 USDT,
stop bảo vệ −4,5 %, kill JVM treo):

| bước | làm gì | dừng khi |
|---|---|---|
| 0 chuẩn bị | gate CODE, jar Oracle = pin, 242 chỉ đọc (v_t_m c3_shadow + SHADOW_NO_PUSH, không LIVE_ADAPTER, RAM, đĩa, không JVM canary khác), lỗ cộng dồn, chụp v_t_m, phiên cũ (có giao dịch ⇒ cần `CANARY_RESET=1`), copy jar 3d vào `c3canary`, LEGACY, logback | bất kỳ kiểm nào sai |
| 1 chờ khung giờ | CHỈ khi tài khoản phẳng: `keycheck` chỉ đọc in `pos= orders= algos=` toàn tài khoản; phẳng lúc vào, kiểm lại mỗi 600 s và ngay trước khi qua; khung phút :10–:40 (để `canary_early_run` kịp chốt giờ :10–:44), tránh 07/19 h, 00:50–01:20, 12:50–13:20; tối đa 2 h | không phẳng (không bao giờ chờ khi có vị thế/lệnh/stop), STOP, v_t_m đổi, RAM, quá 2 h |
| 2 SETUP | CROSSED/1x cho 2 symbol của phiên (nếu phiên chưa chọn symbol ⇒ K0 chọn trước) | SETUP không ĐẠT |
| 3 K0 | `CANARY_EXPECT_TMB` = tmb đọc bằng keycheck NGAY lúc đó (log `CANARY_EXPECT_TMB=<tmb>`), phải trong [9 500, 12 000]; `CANARY_K0_REUSE_KEEPALIVE=1` | tmb ngoài khoảng; K0 TRƯỢT. K0 TRƯỢT **chỉ** vì marginType/leverage (symbol theo luật vừa đổi) ⇒ chờ khung giờ → SETUP → K0 lại 1 lần |
| 4 phiên | chờ khung giờ lại (phẳng) → `canary_early_run.sh` với `CANARY_INJECT_TIMEOUT=1`: K1..K8, report, cleanup, đổi tên `canary_done_<TS>` khi ĐẠT | như 3c |
| 5 Telegram | `CANARY-EARLY DAT/TRUOT/LOI (<TS>)` + 1 dòng tóm tắt + `File ket qua: <đường dẫn>` (+ `Tom tat: canary_early_all_<TS>.txt`) | — |
| 6 lỗi | bất kỳ bước nào ⇒ (jar pin đã trên 242) kiểm phẳng chỉ đọc; không phẳng hoặc không đọc được ⇒ kill JVM treo (MIN-C3) + `flatten` mode early; rồi dừng + Telegram | — |

Telegram: kênh sẵn có `~/.config/health242/tg.env` (đọc như `ops/health_242.sh`, `TG_TOKEN`/`TG_CHAT` hoặc `tele-token:`/`tele-chat-id:`);
token không vào argv/log (`curl -K -` đọc url từ stdin); tin nhắn che mẫu bí mật trước khi gửi; không có key trong tin.
Kết quả: `~/claude_master/canary/canary_early_all_<TS>.txt` (tóm tắt) + `canary_early_result_<TS>.txt` (phiên K1..K8, như 3c).
Một phiên một-lệnh tại một thời điểm (`flock` `~/claude_master/canary/.canary_early_all.lock`).

**Chủ ý lệch so với chữ "flatten mọi lỗi":** khi lỗi xảy ra lúc tài khoản đã phẳng thật (keycheck 0/0/0 toàn tài khoản) script KHÔNG
gọi `flatten`, vì `flatten` ghi bước `FLATTEN` vào phiên ⇒ phiên bị tính "có giao dịch" (engine `hasTradeSteps` giữ tmb0 cũ + cấm đổi
symbol; script đòi `CANARY_RESET`). Không phẳng / không đọc được ⇒ luôn kill JVM treo + flatten.

## 3. Java (A1 xem)

- `CanaryEngine.preflight`: ghi `jar.md5`, `jar.mtimeMs` vào K0. `cfg.reuseKeepAlive` (env `CANARY_K0_REUSE_KEEPALIVE=1`, mặc định tắt) ⇒
  `keepAliveReuse(prevK0, jar)`: chỉ "OK" khi K0 trước **chạy thật** phần keepAlive (không phải bản dùng lại — không nối tiếp),
  `ws.keepAliveOk ≥ 2`, `ws.openMs` trong [0, 5 s], cách ≤ 24 h, **cùng jar** (md5 ghi trong K0 trước = md5 jar đang chạy; K0 cũ không ghi
  md5 ⇒ chỉ khi mtime jar hiện tại ≤ lúc K0 đó). OK ⇒ bỏ `pump(65')`, ghi `ws.keepAliveSkipped=<lý do>` + journal `K0_KEEPALIVE_REUSED`;
  không ⇒ chạy đủ 65', ghi `ws.keepAliveReuse="khong dung lai duoc: <vì sao>"`. Mọi kiểm khác của K0 (WS mở ≤ 5 s, tmb ±1 %, mode, 0 vị
  thế/lệnh/algo, 0 lệnh ghi) giữ nguyên, chạy mỗi lần.
- `C3LiveCanary.keycheck`: thêm `pos= orders= algos=` (positionRisk ≠ 0, openOrders, openAlgo toàn tài khoản — chỉ đọc, không ghi bước vào
  state). `runningJarId()` = md5 + mtime của jar code-source.
- Test: `k0ReusesKeepAliveOnlyFromRealK0SameJarWithin24h`, `k0LegacyRecordWithoutJarMd5ReusesOnlyIfJarUnchangedSince`.

## 4. Sửa lỗi có sẵn trong `cl_run` (phát hiện khi xem phiên owner 20:25)

Lệnh ssh khởi động JVM là `cd A && mkdir -p run/canary && ( nohup … ) >/dev/null 2>&1 </dev/null &` ⇒ `&` đưa CẢ chuỗi `cd && mkdir && (…)`
ra nền với fd kênh ssh ⇒ ssh không trả về tới khi JVM xong (thấy trên Oracle: ssh K0 của owner sống từ 20:26:23 suốt 65'). Hệ quả:
poll/`STEP_MAX_S` không có tác dụng trong lúc JVM chạy; mất mạng giữa chừng ⇒ `die "khong khoi dong duoc JVM canary"` trong khi JVM vẫn
chạy. Sửa: `{ ( nohup … ) >/dev/null 2>&1 </dev/null & }` — chỉ subshell JVM ra nền, ssh trả về ngay, poll như thiết kế.
Thử trên Oracle (`bash -c '<lệnh>' | cat`, tiến trình nền 4 s): kiểu cũ trả về sau 4 007 ms, kiểu mới 5 ms.
Test fake 17j: ssh giả `bash -c "$1" | cat` (chỉ trả về khi mọi fd stdout đóng, như ssh thật), JVM giả 6 s ⇒ ssh khởi động trả về < 3 s,
trước khi JVM xong, kết quả vẫn đủ.

## 5. Test

- Java: 648 test, 0 fail.
- `test_fake242.sh` mục 17 (một lệnh): 17a không YES ⇒ không gì; 17b đường chuẩn (ngoài giờ lúc đầu + phẳng ⇒ chờ rồi vào; tmb 10 971,82 ⇒
  `CANARY_EXPECT_TMB=10971.82` cả 2 K0; K0 lần 1 cần SETUP ⇒ SETUP ⇒ K0 lần 2 BỎ chờ keepAlive + lý do; K1 `INJ=1`; Telegram DAT + đường
  dẫn file kết quả; ghi chú USDT ≠ 0; v_t_m không đổi; không key); 17c tmb 8 000 ⇒ dừng trước K0, phẳng ⇒ không flatten, Telegram LOI;
  17d không phẳng ⇒ không chờ, flatten ĐẠT, Telegram LOI; 17e khung giờ không mở trong hạn ⇒ dừng; 17f K3 TRƯỢT ⇒ flatten + cleanup trong
  phiên, Telegram TRUOT + file; 17g phiên cũ có giao dịch, không `CANARY_RESET` ⇒ từ chối; 17h K0 TRƯỢT lý do khác ⇒ không SETUP, TRUOT;
  17i file STOP ⇒ từ chối; 17j `cl_run` ssh trả về ngay.
- Các mục 1–16 (3/3b/3c) chạy lại PASS với lib mới (install dùng `cl_early_old/jar/reset` tách ra lib).

## 6. Điểm mở

1. **Jar đổi (3c → 3d) ⇒ K0 đầu tiên của lệnh mới vẫn chạy đủ 65'**: K0 17:39 / 20:25 chạy jar 3c (không ghi md5; jar 3d mtime mới hơn) ⇒
   không đủ điều kiện "cùng jar". Dùng lại keepAlive có tác dụng cho K0 lần 2 (sau SETUP) và các lần chạy sau trong 24 h với jar 3d.
2. **Phiên owner 20:25 ĐÃ ĐẠT K0 lúc 21:31:48** (jar 3c, `CANARY_EXPECT_TMB=10972`, tmb 10 972,29, ZECUSDT/QUSDT CROSSED/1x,
   ws.openMs 1000, keepAliveOk 2; v_t_m không đổi). Còn hiệu lực tới 21:31 ngày 28/10. Sau pin 3d, `canary_early_run.sh` mặc định từ chối
   jar 3c trên 242 (md5 ≠ pin). Hai đường, MASTER chọn:
   (a) dùng K0 đó, chạy ngay phiên K1..K8 trên jar 3c (không Telegram, owner gõ YES 1 lần):
   `CANARY_JAR_MD5=5de6c9899b09758965a14b91ac836ef7 CANARY_INJECT_TIMEOUT=1 bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_early_run.sh`;
   (b) lệnh một-lệnh (jar 3d, K0 lại đủ 65' vì khác jar, Telegram). Chạy (b) sẽ ghi đè jar 3c trên 242 ⇒ (a) hết dùng được.
   Jar 3c trên Oracle giữ lại cho (a) (chưa xoá).
3. USDT = 1 000 ≠ 0 trên tài khoản con ⇒ cấu hình pilot USDT = 0 (MO-2) **không được kiểm**; script ghi chú vào file tóm tắt + Telegram.
4. A1 cần re-audit delta Java (keepAlive reuse, keycheck) + `cl_run` (mục 4) + `canary_early_all.sh`.
5. MIN-C1 (lock tuyệt đối chung) vẫn để trước G-GOLIVE.
