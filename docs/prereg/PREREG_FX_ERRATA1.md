# PREREG_FX_ERRATA1 - ap cho PREREG_FX_G1 va PREREG_FX_G3 (commit 058ed482); chot sau khi TAI + KIEM KE du lieu, TRUOC khi viet code tin
# hieu / tinh bat ky loi suat nao
Chot boi MASTER 2026-11-26. Du lieu: ~/claude_master/w3/fx/data/ (43 file, PROVENANCE.md, DATA_REPORT.md, cot_release_exceptions.csv).
H1. Kiem cheo FRED vs ECB: 60 cap-nam co > 0,5 % ngay bi co (chu yeu 2008, 2022, 2004, 2009; nang nhat CAD / AUD 2008 6,05 %) - CHAP NHAN
    la lech gio chot (14:10 CET vs trua New York) khi bien dong manh; KHONG loc, KHONG sua gia. Bao kem (mo ta) ket qua khi bo cac ngay bi co.
H2. Universe G1 thuc te (so dong tien co du ty gia + lai suat thang m-1): 1994-98: 6; 1999-2001: 7-8; 2002-05: 8-9; 2006-19: 9;
    HOLDOUT: thang 2020-05 rong (thieu lai suat USD 2020-04) va tu 2026-03 con 7 dong (EUR, GBP het lai suat). Ap dung nguyen quy tac
    universe cua prereg (thieu thi dong do / thang do ngoai universe); khong thay chuoi.
H3. G3 - khop hop dong theo MA + ho ten (ten doi qua cac nam): EUR 099741 (chi tu 1999; 099741 nam 1986 la ECU => loai), GBP 096742,
    CAD 090741, CHF 092741, AUD 232741, JPY 097741, NZD 112741 - ca 7 da xac nhan tu file. Cot ngay cua TFF la
    Report_Date_as_YYYY-MM-DD (prereg ghi sai ten); Legacy: "As of Date in Form YYYY-MM-DD", "Noncommercial Positions-Long (All)" /
    "-Short (All)", "Open Interest (All)".
H4. G3 - du lieu thua: z_t chi xac dinh khi cua so W tuan co >= 95 % so tuan co bao cao; khong noi suy. He qua: NZD Legacy (thieu 292
    tuan truoc 2006-07) gan nhu khong tham gia LEG TRAIN - chap nhan, khong xu ly rieng.
H5. G3 - ngay vao lenh (THAY quy tac "ngay lam viec dau tien sau ngay cong bo that"): voi MOI tuan, lenh vao tai gia FRED cua ngay lam
    viec dau tien >= ngay chot bao cao (thu 3) + 7 ngay lich. Bao thu hon 1 ngay so voi thu 2, nhung chac chan sau moi lan cong bo binh
    thuong ke ca tuan lui do le. Cac bao cao trong danh sach cot_release_exceptions.csv (dong cua 2013, 2018-19, 2025; su co ION 2023)
    co ngay cong bo that > ngay chot + 6 ngay => LOAI khoi tin hieu.
H6. HOLDOUT giu 2020-01..2026-10 cho ca hai nghien cuu; DEV va A1 KHONG doc du lieu >= 2020-01-01 (cat khi nap) cho toi khi dong bang.
