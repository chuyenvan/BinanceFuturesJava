# NUP3 — cổng kỹ thuật trước Pha 1 (2026-10-27)

Prereg `docs/prereg/PREREG_NUP3.md` (c2b4c462) + `PREREG_NUP3_ADDENDUM_TECH.md` (ab2391e4). Code `research/nup3-sleeve`
**c80d87c2**, jar sha256 `b269f96b…` (PrivateConfig STUB; `jar_sec.json` ok). Số máy: `gates.json`. Không có số PnL nào ở đây.

| cổng | kết quả | chi tiết |
|---|---|---|
| G-OFF a1 (`nup3-goff-a1`, SLEEVE_ENABLED=false) | **PASS** | md5 printDone `dc62609b…` = `tsx-x14-a1` |
| G-OFF s7 (`nup3-goff-s7`) | **PASS** | md5 `622b03e2…` = `tsx-x14-s7` |
| G-INV a1 (`nup3-v0-a1`, V0) | **PASS** | lọc `book=sleeve` ⇒ md5 `dc62609b…` = B0 a1; 2 778 dòng sleeve (2 740 cụm) |
| Smoke V2 (`nup3-smk-v2`, a1 tới 2021-07-31) | PASS | sim nạp `nup3_mkt_flag.csv` trên Kaggle: 2 121 khoảng / 91 482 phút (khớp meta) |
| Unit test | PASS | `Nup3SleeveTest` 19/19, `Nup3SleeveGateTest` 4/4; `mvn package` 253 test, 0 fail |

Kiểm run (orchestrator): `java_ok`, jar sha = b269f96b, `prof_run` khác B0 cùng seed ĐÚNG tập key sleeve — 4/4 run.

Đo lường kỹ thuật của `nup3-v0-a1` (từ `storage/sleeve_summary.json`, không phải chấm điểm):
- ứng viên qua q2: 9 292 (trong đó 14 lúc sổ nền đầy); mở 2 740; bỏ vì sleeve đang giữ 6 489; không mở được (U_s/cap) 63.
- overlap (nền mở cụm mới trên symbol sleeve đang giữ): **1 704** (sổ nền có 3 468 cụm) ⇒ giới hạn live one-way §7 là lớn.
- U tổng theo notional@close / equity MTM: max **0,809** (0 tick > 1,0). U theo margin@entry / equity: max **1,093** (> 1,0) —
  hai cách đo khác nhau khi giá giảm; MASTER chọn cách đọc cho G3.
- số vị thế đồng thời max (nền + sleeve) 119.
- Chạy 2 533 s (B0 a1 ~2 622 s).
