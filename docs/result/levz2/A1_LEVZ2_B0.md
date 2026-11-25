# A1_LEVZ2_B0 - audit KET QUA luoi B0 (grid.parquet 1 296, select, rand). Agent A1 (Opus), 2026-11-25. Khong sua/commit.
Artefact: a1/refsim3.py, a1/ana.py, a1/out/b0_ana.json, a1/out/v2ref_g759|g758|gf1_*.

## 0. Tom tat
So cua MASTER (a)-(d): DUNG het (khong so nao sai). Nhung ket qua 759 la IN-SAMPLE, dua vao rat it su kien (87 % lai rong DEV den tu
1 thang 2025-11; top 5 % lenh = 142 % lai rong), lop DCA chi co loi o F3, va p_rand = 0 bi thien lech chon loc (max cua 1 296 vs 1 bo thoat).
B0 khong cho bang chung edge; chi la "ban do tho".

## 1. Tinh lai doc lap (refsim3: python thuan, khong import levz2)
759, 758, 654 (top-1 WFO theo F1) x DEV/F1/F2/F3: so lenh trung, ret/maxDD/maxDD-worst lech <= 4e-15 so grid.parquet; 759 DEV: 294/294 lenh
trung, ly do trung, PnL lech <= 3e-12 USD. Bat bien ke toan ca luoi <= 1.4e-10 (4 ky).

## 2. (a)(c)(d) tinh lai tu grid.parquet bang code rieng (khong dung select.py)
(a) 69 hop le; xep hang: 759 (1.163) > 758 (0.758) > 806 > 770 > 919; 759 qua cao nguyen ngay lan dau: 6/9 = 0.667 >= 0.60.
 Hang xom 759 (dau F1/F2/F3): W14 (111) +++; E1 (1083) --+; z2.5 (651) +-+; z3.5 (867) +++ [F2 +0.06 %]; K5 (795) +++ [F2 +0.41 %];
 SL30 (771) +++; H72 (763) +++; trail tat (757) +-+ [F2 -0.59 %]; DCA tat (758) +++. => cao nguyen MONG: 2 hang xom qua voi F2 ~0, 1 truot
 voi F2 -0.6 %; chi can 1 dau doi la 5/9 < 60 %.
 759: DEV 294 lenh, +102.4 %, CAGR 19.3 %, maxDD worst 24.2 % (= F3), fold +21.1/+21.6/+37.9 %, win 63.6 %, mean 1.82 %/lenh, te nhat
 -15.7 %, phoi nhiem TB 3.1 % (co vi the 10 % so gio), PnL nam (equity) 581/1 526/2 617/5 513, Sharpe ngay 0.89. 758: CAGR 15.7 %, DD 19.7 %. DUNG.
(c) >0: DEV 54.6 %, F1 61.0 %, F2 18.9 %, F3 77.1 %, ca 3 fold 8.1 %; DEV_ret trung vi +2.2 %. Spearman diem fold: F1-F2 +0.12, F2-F3 -0.58,
 F1-F3 -0.12 (tren ret: +0.21/-0.50/-0.16). DUNG. => xep hang cau hinh KHONG ben qua thoi gian (F2 va F3 dao nguoc).
(d) Chon theo F1 (761 ung vien): top-1 = 654 (W7 E0 z2.5 K3 SL15 H72 trail, DCA tat) F2 +7.6 % (DD 29.7 %); top-20 F2 trung vi -9.0 %,
 40 % duong; top-50 -12.7 %, 24 %. Chon maximin F1+F2 (178): top-1 = 758 F3 +14.3 % (DD 18.8 %); top-20 F3 trung vi -5.6 %, 35 %
 duong (toan luoi F3 trung vi +18.8 %, 77 %); top-50 +0.3 %, 50 %. DUNG. => chon theo qua khu kem hon chon ngau nhien o F3.

## 3. p_rand
500 luot: diem 0..100 % = -0.995 / -0.944 / -0.811 / -0.515 / -0.073; 0 hop le; DEV ret trung vi -32.6 %; so lenh DEV ~359 (that 294).
Toan luoi: 72 % cau hinh > trung vi ngau nhien; 10.2 % (132) > MAX ngau nhien. Cung bo thoat voi 759 (SL15 H24 trail DCA; 36 cau hinh khac
W/E/z/K): trung vi o phan vi 80 % cua phan bo ngau nhien; 6/36 (deu E0, 6/18) > max ngau nhien, E1 0/18; DEV ret trung vi +4.9 %.
Danh gia: p_rand = 0 so 1 cau hinh TOT NHAT trong 1 296 voi ngau nhien cua 1 bo thoat => p khong hieu chinh cho chon loc, KHONG duoc doc la
"xac suat may man 0". Duoc noi: o cung bo thoat, tin hieu E0 (z>=3) cho ket qua tot hon short ngau nhien cung so dot (6/18 cau hinh E0
vuot moi luot ngau nhien; ngau nhien lo ~33 % tren DEV). Khong duoc noi: "759 thang ngau nhien voi p < 0.002". Kiem dung phai so voi
max-qua-luoi cua ngau nhien (chua co).

## 4. Phan ra 759 (DEV)
- Theo nam vao lenh (lenh/net USD): 2022 5/+581; 2023 72/+1 526; 2024 131/+2 564; 2025 86/+5 566. 6.1 lenh/thang, co lenh 35/48 thang.
- Ly do: trail 80 lenh +26 908 (TB +9.9 %, giu trung vi 8.5 h); time 175 +4 916 (+1.2 %); SL 38 -21 436 (-12.4 %); time_sub 1 -152.
- Tap trung: top 5 % (15 lenh) = 142 % lai rong; bo 15 lenh do => -4 303 USD. Top 3 thang = 116 %; rieng 2025-11 = +8 913 = 87 %.
  182 coin; top 5 coin (BDXN, ARC, ZEREBRO, 1000RATS, H) = 93 %. (USD bi phong dai cuoi ky do lai kep, nhung muc tap trung van cuc doan.)
- Funding +752, phi -1 283, gross +10 767.
- DCA: 37 lenh DCA (24 ket thuc SL) net -7 953; so cung lenh o 758 (294 lenh trung 100 %), chan DCA dong gop ~ +2 550 USD; 27/37 DCA o 2025.
  759 vs 758: F1 21.1 vs 25.1 %, F2 21.6 vs 25.9 %, F3 37.9 vs 14.3 % => DCA chi co loi o F3; chon 759 thay 758 la do F3.
  G2 co hieu luc: 8 lan DCA roi SL cung nen.
- Beta: tuong quan PnL ngay voi EW alt (universe, close-close) -0.11 (ngay co vi the -0.28), beta -0.03; short EW cung phoi nhiem: -14 %
  (EW alt -89 % ca DEV) => lai KHONG den tu beta short alt; den tu vai cu sap manh. (Can lech ~1 h giua equity ngay va EW.)

## 5. Gioi han mo phong voi 759
- Trail = toan bo phan lai (+26.9k vs tong +10.2k): trailing 10/5 % tren nen gio bo qua nhip hoi >5 % trong gio sau day (gia dinh HIGH truoc
  LOW chi ap cho kiem muc cu); thuc te 1 phut co the thoat som hon o nhieu lenh => lai trail co the bi phong dai; chieu sai so khong xac dinh
  nhung do nhay CAO vi 759 phu thuoc trail + vai lenh lon. Phai kiem o B1 (nen 1 phut).
- H24: 60 % lenh thoat time, TB +1.2 % - nhay voi phi/truot (phi da tinh 0.14 %; truot ngoai SL chua tinh).
- Gia vao tre 0: lech median 0.16 %/lenh so voi tang 1 (smoke) ~ 9 % lai TB/lenh 1.82 %; nho so voi rui ro tap trung.
- SL 15 % + slip 0.5 %: lenh te nhat -15.7 % - gap > SL tren nen gio da tinh (open), nhung thanh khoan coin nho (BDXN, ARC...) chua tinh.

## 6. MASTER duoc / khong duoc noi voi owner
DUOC: "B0 chay dung prereg + 2 addendum, simulator va so lieu da audit doc lap (khop 1e-15). Luat chon may moc chon 759; 69/1 296 hop le.
In-sample toan DEV 759 +102 % / DD 24 %, nhung: 87 % lai tu 1 thang (11/2025), 15 lenh tao toan bo lai; xep hang cau hinh dao nguoc giua
2024 va 2025; WFO chon theo qua khu thua trung vi luoi. Tin hieu E0 z>=3 voi cung bo thoat tot hon short ngau nhien (6/18 vuot moi luot)."
KHONG DUOC: "co edge", "CAGR 19 % / DD 24 % la ky vong", "p_rand = 0 chung minh tin hieu", "DCA/trail giup", "san sang HO/trien khai".
Neu di tiep (B1): uu tien kiem 759/758 tren nen 1 phut va do nhay khi bo thang 2025-11 / top 15 lenh.
