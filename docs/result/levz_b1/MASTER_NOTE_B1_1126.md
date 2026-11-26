# MASTER_NOTE LEVZ tang B1 (thoat lenh nen 1 phut) - 2026-11-26 14:41 +0700
Prereg 54f40792 + ADD1 3226e940. Engine A1 PASS-WITH-MINOR (A1_B1_ENGINE.md). Ket qua A1 xac nhan (A1_B1_RESULT.md): moi so cua MASTER dung, tru
nhan phan vi doi chung ngau nhien (rand_max_q = [5 %, trung vi, 95 %], KHONG phai min / max).
- In-sample: 600 / 7 020 hop le; chon 5204 (W7 E0 z3,5 K10 SL50 H24 arm5/gap2): DEV +24,5 %, DD 5,3 %; 4107 (cau hinh 759 cua B0 tren engine
  1 phut): DEV +71,9 % (CAGR 14,5 %), DD 21,6 %, lai ca 3 fold - NHUNG bo 15 lenh tot nhat thi -910; thang 2025-11 = 44 % lai.
- Ti le cau hinh co lai: F1 64 %, F2 (2024) 20 %, F3 84 %; Spearman diem fold F2-F3 -0,49.
- WFO (so dang tin): chon theo F1 -> 2024: top-1 (3550) -36,3 %, top-20 trung vi -23,0 %; chon theo F1+F2 -> 2025: top-1 (5204) +10,9 %, top-20
  trung vi +6,1 %. Ca hai nam deu THAP hon trung vi toan luoi => luat chon khong them gia tri ngoai mau.
- Doi chung ngau nhien dung nghia (max qua luoi, 100 lan / lop): W7_E0 z3,0 va z3,5: 0 / 100 (duoc noi "p <= 0,01"); W7 z2,5: 1 / 100 (co lan
  ngau nhien dat 1,46 > that 0,86); W14: 5 / 100, 1 / 100, 5 / 100. Chi cho thay tap ung vien khac ngau nhien IN-SAMPLE; khong phai bang chung OOS.
- Ban do: H 24-72 > 168-720 (giu dai KEM); arm 5-10 % > arm 3 %; W7 > W14; z >= 3,0.
- TIEU CHI "DI TIEP B2": KHONG DAT (2024 top-1 va top-20 am). Luat dung som: MASTER khuyen dung; owner 2026-11-26 quyet di tiep (B2).
Phan tich ghep voi he long (docs/result/levz_an, A1_AN.md = FAIL ve ket luan ghep): voi cau hinh short chon IN-SAMPLE (4107) ghep m = 1: CAGR
long 35-40 % -> 54,5-60 %, DD gio 19,5-21,7 %; voi cau hinh chon KHONG nhin truoc (WFO top-1 tung nam): CAGR ghep 23,9-28,3 % (KEM long rieng),
nam 2024 long +39..+45 % -> ghep -7..-11 %; cau hinh trung vi toan luoi: +1,4 pp CAGR, duoi DD xau hon. maxDD long MTM theo GIO 18,2-21,4 %
(bao cao goc ghi 12,7-17,7 % la lay mau theo ngay). Tuong quan ngay long-short ~ 0; short nhan roi ~ 90 % thoi gian.
