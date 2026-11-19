# PREREG_HO5_A3_2026 - ADDENDUM 1 (CHOT 2026-11-19 ~16:40 +07, MASTER; TRUOC khi co bat ky con so 2026 nao)

Trang thai luc viet: luot dau = R5 "KHONG CHAY DUOC" (bao cao ~/claude_master/v12/HO5_A3_2026.md): (A) kernel sim khong toi duoc Aerospike
Oracle 161.118.212.3:3222 (owner dong cong sau 11-11) => SYMBOL_MAPPER_PREFLIGHT_FAIL truoc khi sim chay; (B) chua co pred/bins 2026 cua
3 model live; (C) agent chi ra loi thiet ke E0. CHUA co con so 2026 nao => addendum nay KHONG phai sua sau khi thay ket qua.

## A1. Ha tang (thay cho ket noi Aerospike truc tiep)
- Duoc phep dong goi SNAPSHOT symbol mapper vao bundle kernel (doc tu Aerospike tren Oracle, noi bo) thay cho ket noi truc tiep. KHONG mo
  cong 3222, KHONG doi firewall.
- Vi doi kernel: kiem tai lap muc 1 cua prereg goc la BAT BUOC truoc moi luot 2026: chay lai 1 seed r1-a3 (s123) tren cua so cu,
  equity_final lech <= 0,5 % so voi 144 003 VA so lenh lech <= 0,5 % so voi 3 584. Khong dat => dung.
- Cam fetch output co funding.bin (4,4 GB) ve Oracle; chi tai result.json, printDone.csv, log.

## A2. Pred / bins 2026 cua model live (chuoi cong cu moi)
- Duoc phep viet chuoi moi (fork ho4p1_chain + a3_build cho 2026) de tao: pred p15 tu ONNX fold_20 (md5 8ec99757...), net015 RAW tu
  g015x26_f15_cut20251231 (e65e683b...), bins A3 2026 voi S1 s1a2x1_cut20251231 (511add62...).
- Cong parity BAT BUOC cua chuoi moi, chay TRUOC khi tao 2026 (khong dat => R5):
  (P1) chuoi moi dung lai bins A3 cua 1 fold DEV (fold 20251001) phai TRUNG bins r1-a3 da dung (sha256 bang nhau; neu dinh dang khien
       sha khong so duoc thi so tung o: 100 % o trung, sai lech so thuc <= 1e-6);
  (P2) pred p15 cua ONNX fold_20 tren 1 000 dong mau cua tap train phai khop du doan cua model goc (json/booster) <= 1e-6;
  (P3) net015: du doan ONNX tren mau >= 1 000 dong khop ban goc <= 1e-5 (GPU khong tat dinh o khau train, khong lien quan suy luan).
- Du lieu 2026: dung artefact Vision cua HO4-P1 (2026-01-01 -> 2026-09-30). Bao cao phai nhac lai gioi han da biet: du lieu 2026 dung tu
  Vision khop DEV o muc thanh phan chi 13,9-96,5 % so o (HO4_P1.md:6) => HO5 do "model live tren du lieu Vision", khong phai tai lap DEV.

## A3. Sua luat E0 (ly do: Lane L dung 1 model p15 dong bang => 8 "seed" chi khac nhau o lich su <= 2025, KHONG doc lap)
- E0 giu nguyen chu (trung binh SigmaPnL OOS > 0 VA >= 6/8 seed > 0) nhung chi mang nghia "khong am".
- THEM E0b: bootstrap theo TUAN (10 000 lan, lay lai cac tuan cua OOS, tren PnL trung binh 8 seed): bao cao khoang tin cay 80 % cua
  SigmaPnL OOS. Can duoi > 0 => "duong co y nghia"; can duoi <= 0 => "chua phan biet duoc voi 0".
- R1 sua: ky vong cho PILOT = so HO5 Lane L tren OOS CHI khi E0 PASS; neu E0b "chua phan biet duoc voi 0" thi ghi ro va PILOT giu von
  <= 10 000, khong nang, cho toi khi co holdout cua model train lai. R2-R5 giu nguyen.
- Lane W: "KHONG CO" (S1 / net015 khong co model cut 2026-03-31, 2026-06-30) - khong lam trong HO5.
