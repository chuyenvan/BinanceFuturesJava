# OWNER_DECISION_PILOT_1121 - ADD2: owner quyet ba muc X14 / B2 / C1 cho PILOT

Thoi diem: 2026-11-22 (+07). Kenh: owner tra loi truc tiep MASTER trong phien dieu phoi: "ok ca 3 lam tiep di" - dong y CA BA de xuat
cua MASTER (bang duoi, nguyen van de xuat da trinh owner). Tham chieu: OWNER_DECISION_PILOT_1121.md (c3a9f01b), _ADD1.md (8cc2704f) muc 3.

| Muc | Van de (da trinh owner) | He qua neu de nguyen (da trinh owner) | Owner quyet |
|-----|-------------------------|---------------------------------------|-------------|
| X14 (D-04 / D-05) | Chi so thi truong alt (ALT_EW) dung cho luat X14 tren live chua doi chieu voi nguon chuan; thieu 1 ngay du lieu thi X14 tu tat 30 ngay ma khong bao | Bot quay ve hanh vi khong co X14, loi nhuan ky vong thap hon; MASTER CHUA kiem he qua khi chi so sai gia tri ma khong tat. Audit 16/11 tung xep "chan pilot" | **CHAP NHAN (MIEN) cho pilot**, kem dieu kien: MASTER kiem log X14 MOI NGAY; sua han o jar W3B |
| B2 (T18) | Nguong gate tren live chat hon backtest (q ~0,0095 so voi ~0,0075) do du lieu xau trong bo dem 90 ngay | It lenh hon toi khoang 2027-01-28 (huong bao thu) | **MIEN** |
| C1 (T21) | So lenh giay cua he cu (LEGACY-DCA / skipFull) day co the chan lenh that | Bo lo lenh | **MIEN, co theo doi** |

## Rang buoc di kem (MASTER)
- X14: moi vong kiem hang ngay phai doc trang thai X14 tren log 242 (bat / tat, ngay du lieu ALT_EW moi nhat) va bao owner neu X14 tat hoac du lieu tre > 1 ngay.
  Neu phat hien ALT_EW live lech nguon chuan o muc lam doi quyet dinh X14 -> bao owner ngay; day KHONG nam trong pham vi mien.
- C1: vong kiem hang ngay dem so lan lenh that bi chan vi so giay day.
- Ba muc mien nay chi cho PILOT 10 000 tren tai khoan con voi jar hotfix md5 01cfbb4324fb4a10b615dc3c976ddc73; len von cao hon phai xet lai.
- Tham so gate PILOT: MIEN_X14 / MIEN_B2 / MIEN_C1 = "MIEN ref=<commit cua file nay>".
