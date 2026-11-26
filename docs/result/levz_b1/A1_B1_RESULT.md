# A1_B1_RESULT - audit KET QUA LEVZ B1 (grid_b1 7 020, select_b1, rand_b1 reduced 100) - A1 (Opus) 2026-11-26 06:44-07:20Z
Code A1: a1/ref2.py (engine tham chieu doc lap: parquet goc + funding goc + ung vien tu sig + vong lap phut/gio; KHONG import DEV),
a1/res_rule.py (luat chon/WFO/ti le/spearman/bien - code rieng), a1/rcheck.py, a1/bd.py; ket qua a1/res_rule.json, rcheck.json, bd_out.json, ref2_out.pkl.
Code DEV van khop SHA256SUMS (0 lech) => ket qua sinh tu code da audit (A1_B1_ENGINE.md).

## 1. Engine tham chieu vs grid_b1.parquet - 12/12 TRUNG
5204, 4107, 3550 x DEV/F1/F2/F3: so lenh, ret, maxDD, maxDD worst, ti le SL/trailing/time trung (|lech| <= 2e-15).

## 2. Tinh lai doc lap (a)(b)(c)(d)(f) - so MASTER DUNG
(a) 600/7 020 hop le; chon 5204 (diem 1,508; cao nguyen 8/9 = 0,89 - hang xom lo duy nhat: E1 (F2 -5,5 %)); DEV +24,5 %, DDw 5,3 %, CAGR 5,6 %, fold +5,2/+6,7/+10,9 %, lenh 47/97/55.
(b) 4107: DEV +71,9 %, CAGR 14,5 %, DDw 21,6 %, fold +22,4/+27,4/+10,7 %, 293 lenh, SL 12,6 % / trail 21,8 % / time 65,5 %.
(c) lai: DEV 60,7 / F1 64,4 / F2 19,6 / F3 84,0 %; ca 3 fold 10,0 %. Spearman diem fold F1-F2 +0,03, F2-F3 -0,49, F1-F3 -0,01.
(d) WFO 2024: 4 295 hop le, top-1 3550 (hoa diem voi 3563 = cung tham so, H720; F2 gan nhu nhau) => F2 -36,3 % (DDw 45,0 %, 196 lenh); top-20 trung vi -23,0 %, 10 % duong; luoi F2 trung vi -11,8 %.
    WFO 2025: 976 hop le, top-1 5204 => F3 +10,9 % (DDw 3,4 %); top-20 trung vi +6,1 %, 75 % duong; luoi F3 trung vi +15,5 %, 84 % duong.
    top20_valid == top20_rule ca hai nam (khong anh huong). Ca 2 nam top-1/top-20 THAP HON trung vi toan luoi => luat chon khong them gia tri OOS.
(f) khop (W7 +10,1 %/499 vs W14 -0,1 %/101; E0 557 vs E1 43 hop le - nhung trung vi DEV E1 +4,5 % > E0 +2,9 %; z, H, arm nhu MASTER).
SAI: (e) nhan rand_max_q = [q5, q50, q95] (da dinh chinh). Them: so hop le cua luot ngau nhien trung vi 0 nhung TB 0,6-9,9, max toi 200 (W7_3,5; that 246).

## 3. Doi chung ngau nhien
- 6 lop x 100 luot: so dot / thang dung bang so dot that (tinh lai doc lap) 600/600; moi ung vien trong universe & co nen 1m; seed khac nhau.
- max qua 585 cau hinh: tinh lai 2 luot day du (W7_3,5 r0; W7_2,5 luot 1,46) bang diem rieng => trung parquet (ca so hop le).
- So lenh luot ngau nhien ~ that (W7_3,5: trung vi 47/95/55 vs 5204 47/97/55) => khong lech do so lenh.
- p_max tai lap: W7_2,5 1/100; W7_3,0 0/100; W7_3,5 0/100; W14_2,5 5/100; W14_3,0 1/100; W14_3,5 5/100.
  DUOC noi: "p <= 0,01 (0/100)" cho W7_3,0, W7_3,5; uoc +1: (0+1)/101 = 0,0099. KHONG noi "p = 0". W14_2,5 / W14_3,5: (5+1)/101 = 0,059 => bien, khong ben.
  6 lop: Bonferroni cho lop tot nhat 6 x 0,0099 = 0,059. Tieu chi prereg chi dung lop cua WFO-2025 top-1 (W7_E0_3,5): 0/100 => dat.
- W7_2,5: 1 luot ngau nhien 1,46 > that 0,863 (va > 5204 = 1,51 gan bang) => thong ke "max qua luoi" rat nhieu: diem ~1-1,5 dat duoc do ngau nhien.
- Thien lech con lai: (i) null giu so dot/thang, KHONG giu loai coin (tin hieu chon coin OI/funding cao: short nhan funding, coin dong dao); thang ngau nhien
  = thang "tin hieu + chon coin" chu khong tach thoi diem; (ii) in-sample 2022-2025, so max-in-sample voi max-in-sample => noi "tap ung vien co gi do"
  KHONG noi cau hinh chon truoc thang OOS; (iii) lop duoc chi dinh qua WFO-2025 (dung F1+F2, tuong quan voi diem in-sample) => lech nhe; (iv) 100 luot => do phan giai 0,01.

## 4. Phan ra DEV (engine A1)
| | 4107 | 5204 |
| net / gross / phi / funding | 7 192 / 7 582 / 1 165 / +774 (11 % net) | 2 451 / 2 534 / 181 / +98 (4 %) |
| PnL nam 22/23/24/25 | +616 / +1 626 / +3 351 / +1 599 | +45 / +474 / +708 / +1 225 |
| thang duong | 24/35; 2025-11 = +3 190 (44 % tong); te 2025-10 -1 830 | 24/30; tot 2025-09 +470; te 2025-04 -285 |
| ly do (n, net) | SL 37 -18 221; trail 64 +19 143; time 192 +6 269 | SL 2 -707; trail 129 +4 465; time 68 -1 307 |
| top 5 % lenh | 15 lenh +8 102 > tong => BO DI con -910 | 10 lenh +885 => con +1 566 |
| top 5 coin | H, 1000RATS, BIGTIME, SWARMS, USELESS (~4 400); bo coin top con 6 116 | H, AVAAI, TIA, XLM, JELLYJELLY; bo top con 2 184 |
| lenh te nhat | -21,5 % = 1,44 x SL15 (close 1m vuot SL 1,41x) | -52,4 % = 1,05 x SL50 |
| win / TB / trung vi lenh | 62 % / +1,0 % / +2,4 % | 77 % / +1,9 % / +3,5 % |
| tuong quan ngay voi EW alt | -0,14 (ngay co vi the -0,37) | -0,10 (-0,33) |
4107: loi nhuan phu thuoc duoi (15 lenh) va 1 thang; SL cat it hon muc 15 % nhieu (squeeze trong phut). 5204: rai deu hon nhung CAGR 5,6 %, phoi sang thap.

## 5. Tieu chi prereg muc 5 "DI TIEP B2"
1. WFO top-1 lai 2024: -36,3 % => TRUOT. 2025: +10,9 % => dat.
2. Trung vi top-20 WFO > 0: 2024 -23,0 % => TRUOT; 2025 +6,1 % => dat.
3. p_max lop WFO-2025 top-1 (W7_E0_3,5) <= 0,05: 0/100 => dat.
=> KHONG DAT. Ap luat dung som: MASTER bao so thuc va KHUYEN DUNG truoc B2/B3; owner quyet. (Ghi nhan: luc 06:47Z thay grid_b2.py dang chay - neu owner chua quyet thi la lech quy trinh.)

## 6. Duoc noi / KHONG duoc noi
DUOC: "Tap ung vien W7 E0 (z 3,0-3,5) cho diem in-sample tot nhat cao hon 100/100 lan rut ngau nhien cung so dot (p <= 0,01) - co dau hieu tap
ung vien khac ngau nhien, CHUA tach duoc thoi diem voi loai coin/funding." "Chon cau hinh theo qua khu KHONG ben: 2024 top-1 -36 %, top-20 trung vi -23 %;
xep hang cau hinh giua cac nam ~0 hoac am (F2-F3 -0,49); 2025 chon duoc van thua trung vi luoi." "B1 khong dat tieu chi di tiep."
KHONG DUOC: goi 5204/4107 la ky vong (in-sample); "p = 0"; "WFO 2025 duong => chien luoc chay duoc"; "4107 +72 %" khong kem "bo 15 lenh tot nhat thi am";
"tin hieu that" va "WFO am" la mau thuan - DIEN GIAI DUNG: doi chung la max-in-sample cap lop (co the den tu chon coin/funding va khop qua 3 nam),
WFO la kha nang chon cau hinh truoc - cai thu hai moi la thu dung de trien khai, va no TRUOT nam 2024.
