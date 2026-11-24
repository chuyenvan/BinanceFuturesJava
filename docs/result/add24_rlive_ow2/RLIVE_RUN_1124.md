# ADD24 R-LIVE official - agent RUN - 2026-11-24 - TRANG THAI: DUNG O B1, CHUA CHAY
## B1 (kiem luc 2026-11-24T08:30:17+07)
| Muc | Ket qua |
|---|---|
| pull242/2026-11-23/COMPLETE | DAT |
| COMPLETE 11-18,20,21,22,23 | DAT |
| COMPLETE 11-19 | KHONG DAT: khong co file COMPLETE; check.txt STATUS=INCOMPLETE, fails=feat/sel/psym_pred/psym_feat 1165/1440 phut; log_minutes=1440, errors= rong |
| add24_wt HEAD 3e6da6eb..., nhanh v1.2/add24-harness, porcelain rong | DAT |
| stub ton tai, md5 cf0f4792...6866 | DAT (khong can make_stub) |
| EXINFO sha256 dcfa03c7...1684 | DAT |
| Dia / | 16 577 064 960 B = 15,44 GiB >= 15,3 GiB: DAT (bien mong ~0,14 GiB) |
| RAM MemAvailable | ~19 613 MB: DAT |
| Chua co official | DAT: khong process run_rlive, khong ~/claude_master/w3/add24/a/OFFICIAL_ADD24_RLIVE.lock, khong /dev/shm/add24/rlive_official_* |
| oracle_heavy.lock | DAT: flock -n lay duoc (trong) |
## Quyet dinh
Theo lenh MASTER (bat ky muc B1 khong dat => DUNG): KHONG chay B2. Khong tao khoa, khong output official.
## Ghi chu cho MASTER (khong tu dien giai thay)
- Prereg s5 da ghi truoc: "pull 2026-11-19 INCOMPLETE (feat/sel 1165/1440) => phut khong co sel_dump = NO_INPUT (N1)". Harness tcut() chi doi 11-23 COMPLETE. Tieu chi B1 cua MASTER chat hon prereg -> MASTER quyet co mien muc 11-19 hay khong.
- run_rlive.sh tu lay oracle_heavy.lock cho tung lane java (bien H) va build_wt.sh tu lay lock rieng => KHONG duoc boc flock ngoai (se tu khoa/long). Script tu export LIVE_IS_SHADOW_HOST=true.
- Cua so harness official: START 2026-11-19 09:31 (khong phai 11-18 09:31), END = T_cut 2026-11-24 07:00.
- Harness official goi build_wt.sh (mvn -o test-compile, cho phep boi P11) va rlive_fixture tai kline/mark Vision qua mang.

# CAP NHAT 2026-11-24 ~09:06 - MASTER mien muc 11-19 -> B2 da chay 1 lan -> EXIT 11 (LOI KY THUAT HARNESS), DUNG
## Mien tru
MASTER bo tieu chi "11-19 phai COMPLETE" (MASTER viet chat hon prereg). Can cu prereg PILOTFID dong 90 (T_cut chot theo pull 2026-11-23 COMPLETE) va dong 103 ("pull 2026-11-19 INCOMPLETE (feat/sel 1165/1440) => phut khong co sel_dump = NO_INPUT (nhan N1)").
## Kiem lai ngay truoc khi chay
- 08:43: oracle_heavy.lock BI GIU boi parity run_day.sh 2026-11-22 (pid 2945540) -> cho. Waiter nohup cua agent tu chan nham luc 08:59 (pgrep -f khop dong lenh cua chinh waiter) -> khong chay gi.
- 09:02:35: DF=15584 MB >= 15300; 0 process run_rlive; chua co khoa/output official; lock trong -> chay.
## Lenh (KHONG boc flock ngoai: script tu lay oracle_heavy.lock theo lane; build_wt.sh tu lay lock; script tu export LIVE_IS_SHADOW_HOST=true)
nohup bash -c 'ADD24_P1_APPROVED=e451154e A1_APPROVED=3e6da6eb... EXINFO=$HOME/claude_master/w3/add24/exinfo/c3live_exchangeInfo_242_20261122_195538.json bash .../run_rlive.sh official' > rlive_1124_run.log
## Ket qua
- Bat dau 09:02:35, ket thuc 09:02:51 +07. EXIT_CODE=11.
- Truoc khi loi: P1 gate OK (e451154e:docs/prereg/OWNER_DECISION_PILOT_1121_ADD4.md); KHOA OFFICIAL DA GHI; build_wt RC=0 (build_wt_1124_090235.log).
- Khoa: ~/claude_master/w3/add24/a/OFFICIAL_ADD24_RLIVE.lock (sha256 3956d04f44f670ddf8c4a6a7d8fe4500699d743e432b961b54699537a122f009), noi dung: 2026-11-24T09:02:35+07:00 head=3e6da6eb a1=3e6da6eb...fd3 p1=e451154e errata= exinfo_sha256=dcfa03c7...1684 out=/dev/shm/add24/rlive_official_1124_090235
- Output: /dev/shm/add24/rlive_official_1124_090235 RONG (0 file). Khong co thu muc keep a/rlive_official_*. Khong co gates/score/conclusion.
- Log rlive_1124_run.log sha256 b59141db3ffe035e9d065e1ce3a561c5a856ed5fa4d4c85b551ff681513353d6.
## Trieu chung (nguyen van log)
ValueError: Invalid isoformat string: '07:00 2026-11-23'  (python -c tinh DAYS)
live_log_parse.py: error: argument --days: expected one argument  -> exit 11
## Phan tich nguyen nhan (agent RUN, de A1 kiem; KHONG sua)
run_rlive.sh: `read TCUT TDAY < <(python3 -c "...print(*F.tcut())")`. tcut() tra ('2026-11-24 07:00','2026-11-23') -> in ra "2026-11-24 07:00 2026-11-23" -> read tach theo khoang trang: TCUT='2026-11-24', TDAY='07:00 2026-11-23' -> python DAYS loi -> DAYS rong -> live_log_parse thieu --days -> exit 11. Nhanh official chua tung duoc chay o dev1105 (dev dung ngay hardcode).
He qua: harness dung TRUOC khi doc log/kline/mark -> khong du lieu thi truong nao duoc doc, khong java lane nao chay. Nhung khoa official da ton tai -> script se TU CHOI moi lan chay sau tru khi co E2E_ERRATA moi (theo thiet ke). Worktree add24_wt van sach, HEAD 3e6da6eb.
Agent DUNG: khong chay lai, khong sua, khong errata.
