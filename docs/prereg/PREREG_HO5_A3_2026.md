# PREREG_HO5_A3_2026 - holdout 2026 cua cau hinh sim ky vong (A3) voi model LIVE dong bang (CHOT 2026-11-19 ~10:00 +07, MASTER; TRUOC khi chay)

Loai: CHI DO. Khong doi tham so chien luoc, khong chon lai cau hinh. Ly do: ky vong hien co (sim A3, 8 seed, 2021-07-01 -> 2025-12-30,
CAGR 37,72 %, maxDD -22,72 %) chua tung duoc kiem tren 2026; holdout HO4 dung cau hinh k24/b0 (khong phai A3) va model khac ban live.
Micro-live bat 2026-11-19 09:31 +07 voi model: p15 WFO fold_20 (md5 8ec99757, train toi 2026-03-31), S1 s1a2x1_cut20251231 (511add62),
net015 g015x26_f15_cut20251231 (e65e683b). Chua co con so nao cua HO5 khi viet file nay.

## 1. Cau hinh (co dinh truoc)
- Sim: DUNG cau hinh luot r1-a3 (profile r4_kg0_k16_f015_g155, profile_hash 0738cca9159a78a5, cung bo overrides ghi trong
  ~/kaggle_sim/out/r1-a3-*/result.json va config.properties; cung jar sim sha256 cc0f9d11... neu con dung duoc, neu phai build lai thi
  ghi ro commit va chay lai 1 seed r1-a3 tren 2025 de chung minh tai lap: equity_final lech <= 0,5 %). Khong them stress.
- Seed: dung DANH SACH 8 tag r1-a3-* da co. Von dau 35 000 nhu r1-a3.
- Cua so cham diem W = 2026-01-01 -> ngay cuoi du lieu sim san co (ghi ro ngay cuoi; ky vong >= 2026-09-30). Khoi dong gate lan 90 ngay:
  dung dung cach HO4 da lam (ghi ro); neu khong ap dung duoc thi chay tu 2025-07-01 va chi cham W.
- Lane L (CHINH): model dong bang = dung 3 model live o tren cho ca cua so (kiem md5).
- Lane W (mo ta, neu chay duoc): model WFO theo quy nhu DEV (moi quy dung fold train toi dau quy). Khong co du fold/pred => ghi "KHONG CO".
- Khong dung jar co key; Kaggle chi dung jar STUB; theo docs/runbooks/KAGGLE_RULES.md.

## 2. Chi so
Theo seed va trung binh 8 seed, cho W va tung quy (Q1, Q2, Q3, Q4-dang-do neu co): so lenh, SigmaPnL, ROI, maxDD, Sharpe, % ngay co lenh.
Vung NGOAI MAU cua CA 3 model live = OOS = 2026-04-01 -> cuoi W (Q1-2026 nam trong tap train cua p15 fold_20 => chi bao cao, KHONG dung cho luat).
So sanh mo ta voi DEV (r1-a3 2021-07 -> 2025-12): ti le Sharpe, CAGR quy nam, maxDD.

## 3. Luat (ghi truoc)
- E0 (nhu HO4): tren OOS cua Lane L, trung binh SigmaPnL > 0 VA >= 6/8 seed co SigmaPnL > 0 => PASS; nguoc lai FAIL.
- R1: E0 PASS => ky vong dung cho PILOT = so HO5 Lane L tren OOS (quy nam), khong dung 37,72 % nua. Van phai train lai truoc pilot
  (luat 3 cua PREREG_DIAG_NOTRADE_1117).
- R2: E0 FAIL => PILOT bi chan cho toi khi model train lai qua holdout rieng (prereg rieng). Micro giu nguyen 1 000 (khong nang von);
  dung hay tiep tuc micro la quyet dinh cua owner, MASTER trinh so.
- R3: maxDD trung binh tren W sau hon -22,72 % (maxDD cua DEV) => ghi canh bao rieng, trinh owner, khong tu doi gi.
- R4: Lane W - Lane L (SigmaPnL tren OOS) chi mo ta "chi phi model gia"; khong dan toi thay doi tham so.
- R5: khong chay duoc dung cau hinh (thieu du lieu / pred / jar) => ghi "KHONG CHAY DUOC" + thieu gi; KHONG thay bang cau hinh gan dung
  roi goi la HO5. Ket qua cau hinh gan dung (neu co) phai dat ten khac va khong ap luat E0.
- Moi luot chay phai qua kiem chung (md5 dau vao, so ngay, so lenh > 0, khong NaN) truoc khi bao cao; so da thay thi khong doi luat.
