# A1_DELTA_2H — audit delta `v1.2/c3-live` vòng 2h (05b04165 → 05f55fac)

Auditor: a1audit (Claude Opus, độc lập), 2026-10-25. Chỉ đọc branch c3-live; build + proof trong worktree detached tạm (đã xoá). Không ssh 242/Binance, không push.

## 0. Kết luận
**G-CODE: ĐẠT** (0 CRIT, 0 MAJ). MIN-23 ĐÓNG. Byte-identity c3_shadow ĐẠT. Jar dry pin `e1b1b7ec…` (deploy_v12_dry.sh); jar A1 tự build khác md5
(không tái lập byte) nhưng lớp so được, xem §3.

## 1. MIN-23 (181b6e14) — ĐÓNG
- `escalateStaleKnown()` chạy trong `drainUnknown()`, tức mỗi lần gọi `allowsEntry` / `blocks` / `confirmPendingFlat` / `checkPositions`. Mục (B) có tuổi ≥ 10′,
  tính từ mốc `removeCluster`, thì chuyển sang (A) mà **không cần đọc sàn thành công**; kèm Telegram ngay. `remindUnknown` nhắc lại mỗi 6 h cho mọi symbol (A).
- ProofB (jar 2h), 16′, sàn thật còn 100, stop luôn GIỮ:

| ca | 0–8′ | ≥ 10′ |
|---|---|---|
| R5 đọc OK | B (symbol khác vào được) | A |
| R6 positionRisk lỗi kéo dài | B | **A** (2g: kẹt B) |
| R7 account lỗi kéo dài | B | A |
| R8 cả hai lỗi | B | **A** (2g: kẹt B) |

## 2. Không ăn vào đường thường
ProofCrash (jar 2h): 3 cụm chốt cùng lúc, REST trễ 60 s, 24 leg ở symbol khác:

| ca | 24 leg | gỡ (B) |
|---|---|---|
| R1 | 24/24 | ~2′ |
| R2 | 24/24 | ~2′ |
| R3 (REST lỗi lúc chốt) | 24/24 | ~2′ |
| R4 (restart) | 0/24 (A, an toàn) | ~2′ |

Mọi ca gỡ **trước 10′** ⇒ leo thang theo thời gian không chạm đường thường. ProofFlat2 A–F không đổi (giữ stop).

## 3. Byte-identity c3_shadow — ĐẠT
- Build 05f55fac: **621 test, 0 fail, 1 skip** (có sẵn).
- Bytecode `dcae2e2b` ↔ 2h: 622 → 740 lớp, 0 xoá, 5 lớp thêm ngoài c3live, **26 lớp đổi = đúng tập cũ**, số dòng `javap` khác **y hệt 2f/2g**. 2h chỉ đổi
  `c3live/recon/Reconciler.java`.
- **Parity cờ TẮT 2026-10-23** (jar tự build): md5 out_BT/out_NEW2/fund_BT/fund_NEW2 = e0918a33/e0918a33/a81b3b03/8dea3f70 **4/4 trùng dcae2e2b**; CTL gate 1440/1440 bit; CTL fund y hệt lượt ref; strace 0 AF_INET / 0 tới 242; rc 0.

## 4. Còn mở (không chặn)
MIN-3/4/8/9/14/15/16 (lần 1), adopt stop kiểu qty (2c). Runtime không kiểm stop active có còn sống trên sàn, chỉ startup mới kiểm (2g). Các điểm CHƯA XÁC MINH ⇒ `docs/prereg/GCANARY_PREREG.md` (bản nháp).
