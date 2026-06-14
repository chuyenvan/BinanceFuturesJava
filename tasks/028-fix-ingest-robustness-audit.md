# TASK-028: Sửa P1 ingest robustness (audit Cao #1/#2/#3)

- **status:** REVIEW — code DONE, compile+self-test PASS; chờ gộp deploy có soát (KHÔNG tự deploy). Nguồn: `docs/PRODUCTION_AUDIT.md` §2.
- **owner:** CCD-basis · **updated:** 2026-06-14

## ⚠️ AN TOÀN
- Live (242 / P1 ingest). Test riêng, **KHÔNG tự deploy**; gộp deploy có soát. SLF4J. Chỉ thêm guard/log/sửa watchdog, KHÔNG đổi logic ghi data.

## #1 — Funding-Polling KHÔNG qua BinanceRestGuard (`FundingIngestor:49`) **✔verify**
- Poll `premiumIndex` 30s/lần KHÔNG `awaitIfBanned`/`reportBan` (Ticker:57/131 & OI:147/153 đều có). Đang bị ban (do process khác cùng IP) vẫn bắn → gia hạn ban; `-1003` không vào cooldown global.
- Sửa: `if (BinanceRestGuard.awaitIfBanned(...)) continue;` trước call + `reportBan(response)` sau. Dùng đúng guard chung 016/019.

## #2 — Watchdog `ThreadAutoRestartProgram` DEAD (`BinanceDataIngestor:22`) **✔verify**
- Bị comment ở main:22 → P1 không có giám sát/auto-restart. Bật lại cũng hỏng: `counterMinutes` (dòng 29) không bao giờ `++` → reset-12h không bao giờ true; catch `printStackTrace`.
- **Quyết định (Desktop/user):** bật lại + fix counter++ / log đàng hoàng, HAY xóa hẳn code chết để không hiểu nhầm "có giám sát". → ghi rõ chọn gì + lý do.

## #3 — Exception nuốt câm toàn cục (`HttpRequest.java:218/328`)
- Mọi REST P1 qua đây; `catch(Exception e){}` rỗng + retry `// ex.printStackTrace()` comment → DNS/timeout/SSL/parse biến mất, trả `""`/`null` lẫn lộn → loop "chạy nhưng rỗng" không ai biết. **Vi phạm luật cấm nuốt exception câm (CLAUDE.md).**
- Sửa: LOG.warn trong catch, phân biệt timeout vs parse vs khác; giữ hành vi trả về nhưng có vết.

## Acceptance
- [x] #1: Funding-Polling qua guard (await+reportBan); test body -1003 → vào cooldown. **PASS** (self-test: -1003→isBanned, banned-until→cooldown đúng mốc, body mảng→banUntil=0).
- [x] #2: watchdog — **chọn BẬT LẠI + fix** (user chốt); counter++ chạy đúng, catch hết printStackTrace.
- [x] #3: HttpRequest hết catch rỗng; lỗi REST có log phân loại (TIMEOUT/DNS/SSL/CONNECT/CONN_NULL/IO).
- [x] Test riêng (javac11 compile PASS + self-test guard), KHÔNG tự deploy.

## (Code điền)
- **#1 guard funding** (`FundingIngestor2AerospikeNew.java`): thêm `import BinanceRestGuard`; trong `Funding-Polling-Thread` thêm `boolean wasBanned` + `awaitIfBanned(60_000L) → continue` trước call + log resume; nhánh response `{` thêm `reportBan(response)`. Theo đúng khuôn Ticker:57/131 & OI.
- **#2 watchdog** (`BinanceDataIngestor.java`): **BẬT LẠI** (bỏ comment main → `startThreadAutoRestartProgram()`); thêm `counterMinutes++` (trước không bao giờ ++ → reset-12h là code chết); `printStackTrace`/JUL → `LOG.warn/LOG.error` kèm exception; gỡ import thừa (`Level`, `DetectEntrySignal2TradeNormal`). Lý do chọn bật: P1 trước KHÔNG có giám sát chạy-nhưng-stale (checkAndComparePriceDiff>50 → reset); daemon.sh ngoài repo chỉ bắt process CHẾT.
- **#3 log HttpRequest** (`HttpRequest.java`): thêm SLF4J `LOG` (FQN, tránh đụng JUL) + helper `classifyError`; sửa 4 catch nuốt câm (2 overload `getContentFromUrl` → `LOG.warn`; 2 inner retry-loop → `LOG.warn` lần cuối + `LOG.debug` mỗi retry, giữ trả null/""); thêm cả `connect()`/`connectMp3()` (`LOG.debug` cause thật DNS/SSL thay vì chỉ NPE downstream).
- **Verify:** `javac11` compile 3 file PASS (chỉ note deprecation có sẵn); self-test `BinanceRestGuard` cooldown PASS. **CHƯA deploy** — gộp với 016/019/gỡ-crawl, 1 lần restart 242.
