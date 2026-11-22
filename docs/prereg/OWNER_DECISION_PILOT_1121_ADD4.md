# OWNER_DECISION_PILOT_1121 - ADD4: owner duyet P1 = "U5 van hanh ADD24 R-LIVE"

Thoi diem: 2026-11-22 ~19:50 +07. Kenh: owner tra loi truc tiep MASTER trong phien dieu phoi. Nguyen van: "ok dung log thoa mai di".

## 1. Cau hoi da trinh (P1, hoi 3 lan trong ngay 22/11)
Bai kiem ADD24 thanh phan R-LIVE can so cac cum lenh that cua bot voi quyet dinh cua jar khi chay lai tren cung du lieu. Viec nay doc log
van hanh cua bot va gia (kline / markPrice) cua cac coin lien quan tu 2026-11-18 den 2026-11-24, nam trong vung du lieu >= 2026-10-01 dang
niem phong cho nghien cuu. Chi so quyet dinh / kich thuoc / gia; KHONG tinh lai lo.

## 2. Quyet dinh cua owner: DUYET
Pham vi MASTER ap dung (doc theo huong HEP, dung nhu cau hoi da trinh; owner noi "thoai mai" ve LOG cua bot):
- **U5 (van hanh, ADD24 R-LIVE)**: duoc doc log van hanh cua bot (pull242 / logs 242) khong gioi han ngay cho muc dich van hanh va kiem
  do trung thuc; duoc tai kline + markPrice Vision cua cac symbol bot da giu hoac la ung vien rank <= 24 tai cac phut co lenh, CHI trong
  khoang 2026-11-18 09:31 +07 -> T_cut (2026-11-24 07:00 +07), CHI cho ADD24 R-LIVE.
- KHONG tinh / KHONG in PnL, tong lai lo hay thong ke hieu qua tu du lieu nay (dung prereg ADD24 s6).
- Moi cach dung KHAC cua du lieu thi truong >= 2026-10-01 (nghien cuu alpha, U4b, tune tham so, chay sim qua thang 10-11) VAN niem phong
  va van can owner duyet rieng.
Tham chieu: PREREG_PARITY_V12_DRY_ADDENDUM24_PILOTFID.md (6ee84f17) muc 15 P1; ERRATA4 (03bb65e0) muc 2; ERRATA5 (0740e790) muc B.

## 3. He qua
Luot chinh thuc R-LIVE duoc phep chay khi du: A1 duyet HEAD harness; EXINFO (MASTER chep run/c3live_exchangeInfo.json tu 242, chi doc);
pull242 ngay 2026-11-23 COMPLETE. Lenh: ADD24_P1_APPROVED=<commit cua file nay> A1_APPROVED=<HEAD> EXINFO=<file> bash
~/claude_master/w3/add24_wt/tools/add24/rlive/run_rlive.sh official
