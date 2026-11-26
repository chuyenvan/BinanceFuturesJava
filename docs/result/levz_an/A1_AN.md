# A1_AN - Audit doc lap REPORT_AN.md (2026-11-26)
Code + output cua A1: `a1/code/{l1_long,s1_grid,p1_pool,c1_combo,x1_conf}.py`, `a1/out/*`. Long ledger tu parse lai (-7 h), MTM tu close1m;
short = engine levz_b1 port (da audit) chay lai CA 7 020 cfg (assert DEV_ret khop grid 1e-9) + fold F2 (3550), F3 (5204). Khong tham so moi.

## VERDICT: FAIL (ve dien giai muc 7; so lieu tinh dung)
Hau het con so tai lap khop. Nhung thong diep quyet dinh "ghep short co loi / khong tang DD" chi dung voi cau hinh chon in-sample;
phien ban KHONG chon sau khi nhin (WFO top-1) lam ghep TE HON long rieng; maxDD long 12,7-17,7 % la MTM lay mau NGAY (thap gia ~4 pp).

## Tung ket luan
1. DUNG: 4107 trail +19 143 / time +6 269 / SL -18 221; bo top-15 = -910; top-5 coin 4 415/7 192 = 61 % (bao cao "~43 %" la so cua HO 50, khong phai 4107).
2. DUNG: % cfg am 2024 = 79,9 % (F2_ret grid 80,4 %); thang 10/90/73/12/72/13/46/12/2/18/86/79 (lech 1-2 diem do moc thang). EW alt = MEAN: Feb +41, Mar +27, Nov +60;
   median thap hon (+28/+16/+49). Khong co survivorship (coin chet trong thang 0-1). NHUNG cau chuyen "lo khi alt tang" bi phan vi du: Sep alt +27 % chi 2 % cfg am;
   Dec alt -20 % ma 79 % cfg am. Bao cao chi neu Apr/Jun (chon loc).
3. DUNG: 5 612 cfg lo 2024, 92,1 % co phan khong-SL duong, trung vi SL -4 925 / con lai +3 125. 3550: 42 SL, trung vi 23,4 h, p10 3,4, p90 86,9, 2/42 < 1 h, 8/42 < 6 h.
4. DUNG (tai lap chinh xac n, win, mean, SE). Luu y: dot doc lap theo coin nhung trung thoi diem (cung nhip thi truong) => SE thuc lon hon.
5. DUNG cho s, z_oi, z_f, f, r24 (khop 3 chu so). Khong tinh lai dOI24/qv30/ew7/btc7 Spearman. Nhan qua: OI tsr <= h-10m (100 % dong, kiem 2024-03);
   qv30 dung bar dong truoc T_k; r24/btc7/ew7 dung CLH[k] = close nen 1m mo tai T_k (biet tai T_k+1m = luc vao lenh) => khong nhin truoc ket qua,
   nhung SAU moc quyet dinh T_k 1 phut; dung lam dac trung xep hang tai T_k thi nen doi sang CLH tai T_k-1m (anh huong ~0, sua cho sach).
6. DUNG: W7 z2,5 6/174/419/158; z1,5 25/577/1 440/391; z1,0 42/917/2 276/597; W14 khop. Doi quy tac cooldown >72 vs >=72: lech <= 8 dot.
7. So 4107 DUNG; ket luan tong the SAI/QUA MUC - xem bang.
   (i) tz -7 h: kiem tren c0s7/c0s123/c0s13 (300 leg/lan): entry khop close1m +-1 phut trong 0,2 %: 98,0-99,6 % (-8 h: 2-3 %, -6 h: 6-8 %, 0 h: 2-6 %). DUNG.
   (ii) long ngay = MTM (realized + qty x (close - entry)), chia equity sim; pnl rong (phi+funding) cho realized, MTM leg mo bo qua phi/funding.
        sum pnl = equity_final - equity_start (4/4). CAGR 2022-25 35,0-39,8 % DUNG. maxDD: realized ngay 8,3-15,6 %; MTM ngay 12,7-17,7 % (= bao cao);
        MTM GIO 18,2-21,4 % (day 2022-05-12 07:00 UTC). => so cua bao cao thap gia 3,6-5,5 pp so voi MTM gio; realized thap gia 5,8-9,9 pp.
        MTM gio moi khop "-20..-23 %" da biet. Calmar long (DD gio) 1,64-2,19, khong phai 1,99-3,14.
   (iii) Ghep tuyen tinh can bang ngay = moi sleeve size theo von chung, hop ly xap xi. Gross gio (long MTM notional/eq + m x short): 4107 m1 max 0,93-0,97 (0 gio > 1),
        m1,5 1,22-1,28 (36-62 gio > 1). Long rieng max 0,46-0,48. Toan luoi m1: gross max trung vi 0,95-0,98, 22-40 % cfg co gio > 1.
   (iv) 4107 m1 loi them theo nam (pp, c0s42): 2022 +6,5; 2023 +26; 2024 +38; 2025 +13 => 2024 dong gop lon nhat (nam 80 % luoi lo - dau hieu chon in-sample).
        Thang tot nhat cua short 2025-11 (+22,6 %); bo no: CAGR ghep 46,9-52,1 % van > long. (Chi dung cho 4107 in-sample.)
   (v) Bang ghep do A1 tinh, m = 1, 2022-2025, khoang qua 4 lan lap long (DD = MTM; Calmar = CAGR/DD gio):
| Phien ban short | CAGR long -> ghep | DD long ngay / gio | DD ghep ngay / gio | Calmar long -> ghep | gross max |
|---|---|---|---|---|---|
| 4107 (IN-SAMPLE) | 35,0-39,8 -> 54,5-60,0 % | 12,7-17,7 / 18,2-21,4 % | 17,3-18,2 / 19,5-21,7 % | 1,64-2,19 -> 2,52-3,08 | 0,93-0,97 |
| Trung vi luoi: cfg 2257 (DEV_ret = trung vi; W14 E1 z2,5 K10 SL30 H336) | -> 36,4-41,3 % | nhu tren | 24,7-25,5 / 25,8-26,8 % | -> 1,38-1,60 | 1,00-1,04 |
| Toan luoi 7 020 cfg (phan phoi) | trung vi -> 36,4-41,3 %; 61,5 % cfg tang CAGR | | DD gio trung vi 18,2-21,4 (p90 35-37 %) | Calmar tot hon long chi 43-48 % cfg | 0,95-0,98 (trung vi) |
| WFO top-1 (2022-23 khong co short; 2024 = 3550 F2; 2025 = 5204 F3) | -> 23,9-28,3 % | nhu tren | 23,4-26,2 / 25,2-28,2 % | -> 0,85-1,08 | 0,95-1,02 |
| WFO, rieng 2024-2025 | 34,3-39,6 -> 13,0-17,5 % | 6,5-7,1 / 10,3-10,9 % | 23,4-26,2 / 25,2-28,2 % | 3,1-3,7 -> 0,46-0,69 | |
   WFO 2024: long +39..+45 % -> ghep -7..-11 %. Tuong quan ngay 4107 0,012-0,023 DUNG; ca hai co vi the 3,2-3,8 % gio DUNG; 4107 khong co vi the trong 10 ngay te nhat long DUNG.
   Xung dot cung coin 4107: 15-17 lenh / 59-76 h DUNG; cfg 2257: 33-36 lenh (9-10 %), 530-610 h.

## 8. Cau can sua trong REPORT_AN.md
- Phan C "Long ... maxDD 12,7-17,7 %": ghi ro "MTM lay mau 00:00 UTC"; them MTM gio 18,2-21,4 %; Calmar long 1,6-2,2.
- QUAN SAT 12 + G4 ("sleeve nho khong tang DD, Calmar tang 100 % cap", "gia tri o tinh doc lap thoi gian"): ho 50 / 5204 chon in-sample voi luat valid buoc lai ca 3 fold.
  Toan luoi: Calmar ghep > long chi 43-48 % cfg; WFO lam ghep te hon ro. Phai them bang WFO va toan luoi canh bang in-sample.
- QUAN SAT 11 "short KHONG co vi the trong 10 ngay te nhat cua long": 7-9/10 ngay te nhat cua long la 2022 (May/Nov 2022, da kiem 4 lan lap);
  4107 chi co vi the 2,5 % so NGAY cua 2022 (17,9 % ca ky) do loc f > 0,01 % => hien tuong co hoc cua nam 2022, khong phai phong ho.
  Neu doc lap voi ti le ngay-co-vi-the 17,9 %: P(0/10) ~ 0,14 (suy ra, khong phai kiem dinh). Khong duoc goi la loi ich cau truc.
- "realized 0,05-0,09 la do lech thoi diem ghi nhan": suy doan, ghi la gia thuyet.
- QUAN SAT 2: them Sep (+27 % alt, 2 % am) va Dec (-20 % alt, 79 % am) - cau chuyen alt tang khong nhat quan.
- QUAN SAT 4 "khong phai wick": engine chi thay close 1m nen KHONG THE thay wick; bo menh de nay; n = 42, 1 cfg in-sample.
- A3 / bang A1 "Top-5 coin ~43 %": ghi ro la ho 50; 4107 la 61 %.
- B2 SE: dot trung thoi diem => SE danh gia thap.
- C1 tuong quan thang theo nam (12 diem) - bao cao da canh bao, giu.

## Chu he thong DUOC nghe
- So lieu mo ta cua bao cao tai lap duoc (sai so lam tron); khong thay look-ahead dang ke; tz -7 h dung.
- Short hien tai nhan roi ~90 % thoi gian, tuong quan ngay voi long ~0, gross ghep m1 thuong < 1.
- Mot cfg short chon ngau nhien tu luoi, m = 1: CAGR ghep trung vi +1,4 pp, DD gio khong doi o trung vi nhung duoi p90 ~ 35 %.
## Chu he thong KHONG DUOC nghe
- "Ghep 4107 nang CAGR 35-40 -> 55-60 %" nhu ky vong: la in-sample; quy trinh chon khong nhin truoc (WFO) cho 24-28 % (te hon long), Calmar 0,85-1,08 vs 1,6-2,2.
- "Ghep khong lam tang DD cua long" (ho 50 / 5204): do chon; toan luoi 38-46 % cfg tang DD gio > 1 pp.
- "maxDD long 13-18 %": MTM gio la 18-21 %.
- "Short phong ho ngay sap cua long": hien tuong co hoc nam 2022.

## Khong kiem duoc / gioi han
- Spearman dOI24, qv30, ew7, btc7, tuoi, gio; C1 ho 50 tung cfg; tuong quan tuan/thang.
- Rang buoc margin/thu tu lenh that, hedge mode; MTM short chi close 1m; MTM long bo qua phi/funding leg mo.
- Ly do chon 3550/5204 la WFO top-1 lay theo de bai (A1 khong kiem lai tieu chi chon).
