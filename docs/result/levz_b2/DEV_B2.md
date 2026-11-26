# DEV_B2 - LEVZ B2 gate + filter (PREREG_LEVZ_B2 @da636b28) - CHUA CHAY LUOI (cho A1 audit)
Ngay 2026-11-26, DEV (Opus). Khong sua levz / levz2 / levz_b1. Khong doc du lieu >= 2026-01-01 (reader tang 1 / B1 + assert).

## Da lam (da kiem bang test / chay that)
- code/mkt.py build: work/mkt.npz (376 MB) - EW3/7/14 (+ so coin), BTC7/20, BR (+ do phu), BRmed, R24 [gio x coin], F, QV30 / AGE [ngay x coin], NU.
  Build 10 s. f W7 == f W14 (assert).
- code/opts.py: 12 phuong an + NONE; mat na tai gio ung vien; placebo transforms (gate_shift/draw_shift, coin_perm_map); describe.
- code/grid_b2.py: luoi 7 020 / phuong an (fork <= 3, resume, check_acct); check_none: 300/300 cau hinh TRUNG TUYET DOI voi grid_b1
  (moi cot tru 'sec'; out/check_none.json; parts tam trong work/ xoa ngay).
- code/report_b2.py: muc 3 + tieu chi (a)-(d). Chay tren ban goc: tai lap dung select_b1.json cua B1 (n_valid, chosen, WFO top1 / top20 x2).
  File report tren ban goc da xoa (chi la smoke).
- code/placebo_b2.py: muc 4(e). CHUA chay tren du lieu that (khong duoc phep truoc (a)-(d)); co che kiem bang test tong hop + test F2-only
  == grid_b1 F2_ret (30 cau hinh).
- test/test_b2.py: 44/44 PASS (test/test_report.json).
- out/describe_b2.md|json: muc 7 (ti le chan theo nam lop W7 E0 z2,5; ti le gate mo theo nam) - KHONG loi nhuan.

## Toc do (do that)
- port.run_all 4 fold: ~0,039 s / cau hinh (1 tien trinh) => 7 020 cau hinh / 3 tien trinh ~ 1,5-2 phut / phuong an => 12 phuong an ~ 20-25 phut.
- report_b2: vai giay / phuong an. Placebo: ~0,01 s / cau hinh fold F2 => ~3-6 s / luot => 500 luot / 3 tien trinh ~ 10-17 phut / phuong an (UOC).

## KHONG kiem duoc / suy doan
- Placebo end-to-end tren du lieu that (co y khong chay). Thoi gian placebo la uoc.
- Tinh dung cua tier-1 hr tables / sig (dung lai, da audit o tang truoc - khong kiem lai toan bo).
- "Hop ly kinh te" cua G_BRhi / G_BRlo: suy bien (CHOICES_B2 A).

## VONG 2 (ADDENDUM1 d1241f48) - 2026-11-26 12:59-13:02 +07
- D: mkt.ewr can >= 50 % universe co gia (khong thi NaN => gate dong). Dung lai mkt.npz: 0 gio that bi anh huong; file trung byte (sha256 giu nguyen).
- B: opts.rate_ok / draw_filter_perm; placebo_b2 rut lai luot FILTER lech > 20 % tuong doi ve ti le loai tren ung vien (gop 12 lop), ghi n_redraw.
  Chua chay tren du lieu that (khong duoc phep truoc (a)-(d)).
- Test them 5 ca (D: 50 % bien, < 50 % => gate dong; B: bien +-20 %, rut lai dung luot, tat dinh theo seed, het luot => loi): 49/49 PASS.
- Kiem NONE = B1 chay lai: 300/300 trung tuyet doi.
