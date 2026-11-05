# GOLIVE_SCENARIO — ADDENDUM 1: go-live trên TÀI KHOẢN CHÍNH, cổng G-MICRO / G-PILOT (2026-11-05, TRƯỚC khi viết script)

Gốc: `docs/plan/GOLIVE_SCENARIO.md` (613ff5ca). Addendum này THAY các phần nói về tài khoản con / `PILOT_EQUITY` / script S4–S6, S10.
Mọi mục khác của bản gốc (luật chung script owner §4.1, kill-switch §5.2, quy tắc dừng §5.3, mở rộng vốn §5.4) giữ nguyên.

## 1. Thay đổi so với bản gốc
- **Tài khoản:** c3_live chạy trên **tài khoản CHÍNH** cùng 44 vị thế LEGACY (ROUND4_MAIN_ACCOUNT R1–R8; tách phạm vi theo cid
  `c3-`/`c3x-`/`c3s-`, LEGACY-busy loại symbol). Tài khoản con bỏ.
- **Key:** `/root/.config/c3live/keys.env` trên 242 = key canary tài khoản chính (đặt 10-28 bằng `canary_set_key.sh`, sha256(key)[:8]
  `3ef771e0`); dùng luôn cho micro/pilot. Bản cũ (key tài khoản con `43820b5b`) chỉ là backup.
- **Vốn:** `C3_CAPITAL` (vốn c3 tách, `C3MainEquity`: min(C3_CAPITAL, equity c3, available + margin c3)) thay `PILOT_EQUITY`.
- **Canary:** canary-early tài khoản chính ĐẠT 10-31 (canary_3m, jar r4j). Jar đổi sau đó (r4n: chỉ R7 tuổi exchangeInfo) — A1 R4N:
  không chạm đường lệnh, không cần canary lại.
- **Script owner (repo v1.2/c3-live `ops/c3live/`):** `golive_check_key.sh`, `golive_micro_on.sh`, `golive_pilot_on.sh`,
  `golive_legacy_verify.sh`, `golive_monitor.sh`, `golive_live_off.sh` (thay S4/S5/S6/S9/S10). Luật §4.1 giữ: `DRY=1`, YES 1 lần,
  khung phút :10–:44, PAUSE watchdog mang token, backup, hậu kiểm, tự rollback, Telegram.

## 2. Pha
DRY r4n (từ 11-03) → re-seed + C11 (ADD6) → **7 ngày sạch** → **G-MICRO** → MICRO `C3_CAPITAL=1000` (≥ 7 ngày) → **G-PILOT** →
owner cắt LEGACY (D−1) → PILOT `C3_CAPITAL=10000` (ngày D).

## 3. G-MICRO — tất cả phải đúng (thiếu 1 ⇒ không chạy)
1. **Parity v1.2:** ≥ 7 ngày sạch liên tiếp theo PREREG_PARITY_V12_DRY + ADD6 (Nhóm H VÀ Nhóm K; ngày restart XÁM, không đếm).
2. **A1 vòng 4o** (các script `golive_*` + addendum này): PASS hoặc PASS-WITH-MINOR, 0 CRIT/MAJ.
3. **Key ĐẠT** (`golive_check_key.sh`, chạy ≤ 7 ngày trước): `enableWithdrawals=false`, `ipRestrict=true`, `enableFutures=true`,
   lời gọi ký từ 242 thành công (HTTP 200 ⇒ IP 242 nằm trong whitelist).
4. **G-EXEC:** exec-probe có verdict theo PREREG_EXEC_PROBE (|E| ≥ 100), HOẶC owner đã quyết Q4 bằng văn bản (ghi commit).
5. **Ngày sập E2E:** replay ngày 2026-10-30 (Vision 1m) qua đúng jar sẽ chạy (gate burst, DCA, trailing, kill-switch act, đối soát) ĐẠT
   theo prereg riêng viết TRƯỚC khi chạy replay.
6. **MIN chặn = 0:** MASTER liệt kê MIN còn mở và đánh dấu chặn/không chặn trong file gate; số chặn = 0.
7. **Vận hành lúc bật:** latch kill-switch NONE; sổ dry không vào live (script đổi tên sổ/trạng thái dry `.dry_<TS>`); RAM 242 ≥ 1 000 MB;
   không canary/soak/PAUSE; jar đang chạy = jar trong file gate.
- **File gate:** `~/claude_master/deploy/gates/GOLIVE_GATE_MICRO.ok` (Oracle, MASTER tạo khi 1–6 đạt), PHẢI có dòng
  `jar_md5=<md5 jar dang chay>` và dẫn chứng từng mục (commit / log / ngày). Script từ chối khi thiếu file / thiếu dòng / md5 khác.

## 4. G-PILOT — tất cả phải đúng
1. MICRO ≥ 7 ngày liên tục, trong đó: 0 latch C2/C6/A40 chưa xử lý; đối soát hằng giờ lệch ≤ 1 %; 0 cụm ma chưa xử lý; 0 KHẨN chưa có
   nguyên nhân ghi sổ; mọi leg micro có stop c3s- đúng sau arm (soát log).
2. Lượt M tháng 11 ĐẠT (bản gốc §3) hoặc MASTER ghi lý do bỏ.
3. Owner đã chốt size (Q4, mặc định 10 000) và số dư khả dụng tài khoản chính ≥ size (sau khi cắt LEGACY).
4. **LEGACY đã cắt:** `golive_legacy_verify.sh` ĐẠT ≤ 24 h trước (file `LEGACY_CUT_VERIFIED.ok` do script ghi).
5. Jar đang chạy = jar trong file gate; latch NONE.
- **File gate:** `~/claude_master/deploy/gates/GOLIVE_GATE_PILOT.ok` (MASTER tạo), có `jar_md5=` và `size=<số>`; script dùng `size`.

## 5. Cắt LEGACY (D−1, trước 12:50)
- Owner đóng tay 44 vị thế LEGACY + huỷ lệnh/algo LEGACY trên UI (đã quyết 10-21). v_t_m vẫn là cùng JVM với c3: sau khi đóng, phần
  quản lý LEGACY tự còn 0 (`[LEGACY] managed 0`); không cần restart.
- Ngay sau đó chạy `golive_legacy_verify.sh` (chỉ đọc): vị thế / lệnh / algo NGOÀI phạm vi c3 = 0 trên sàn VÀ log `[LEGACY] managed 0`
  mới (≤ 10′). ĐẠT ⇒ ghi `LEGACY_CUT_VERIFIED.ok`. TRƯỢT ⇒ owner đóng nốt, chạy lại. `golive_pilot_on.sh` từ chối khi chưa có file này.

## 6. Rollback
- **pilot → micro:** `golive_pilot_on.sh` tự rollback khi hậu kiểm trượt (env `C3_CAPITAL` về giá trị trước; adapter vẫn live, vị thế c3
  giữ nguyên, sổ không đổi).
- **live → dry:** `golive_live_off.sh MODE=drain` (đặt `run/KILL_SWITCH`: dừng mở mới, KHÔNG restart, vị thế c3 vẫn được quản lý tới khi
  đóng) → khi c3 phẳng (sổ 0 cụm + sàn 0 vị thế/lệnh c3) `MODE=dry` (env về dry, đổi tên sổ live `.live_<TS>`, restart). KHÔNG BAO GIỜ đổi
  adapter khi c3 còn vị thế. Cần đóng gấp: owner đóng tay vị thế c3 trên UI rồi `MODE=dry`.
- **micro_on trượt hậu kiểm:** nếu c3 CHƯA có lệnh nào ⇒ tự rollback về dry (env + sổ dry khôi phục); nếu ĐÃ có lệnh c3 ⇒ KHÔNG về dry,
  đặt `run/KILL_SWITCH` (dừng mở mới) + KHẨN, owner/MASTER xử lý.
