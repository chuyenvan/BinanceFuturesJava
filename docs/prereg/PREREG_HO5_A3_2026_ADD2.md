# PREREG_HO5_A3_2026 - ADDENDUM 2 (CHOT 2026-11-19 toi, MASTER; van CHUA co con so 2026 nao)

Trang thai: luot 2 dung o cong tai lap (FAIL): equity_final 139 077 vs 144 003 (-3,42 %), so lenh 3 584 = 3 584, 3 584 lenh trung
tuyet doi (sym, start, end, status, entry), chi cot funding khac (cu tong -2 490,7; moi 0). Nguyen nhan da xac minh: sim con doc set
Aerospike `funding_data` (ns test) qua FundingFeeManager; kernel khong toi duoc Aerospike => phi funding = 0. Khong lien quan 2026.

## B1. Ha tang
- Duoc phep snapshot CHI DOC set `funding_data` va dong goi vao kernel theo cung kieu overlay nhu mapper (ADD1 A1). Khong mo cong.
- Cong tai lap (ADD1 A1) chay LAI, nguong giu nguyen (equity_final va so lenh lech <= 0,5 % so voi 144 003 / 3 584). Khong dat => dung.
- Do phu funding 2026: truoc Lane L phai bao cao do phu `funding_data` tren W (theo thang, so symbol co ban ghi). Thieu => bo sung bang
  DUNG cong cu da dung de dung funding DEV, kem kiem chong lan tren 2025 (trung 100 % ban ghi chung, sai lech <= 1e-9). Khong lam duoc
  => R5.

## B2. Cong P2
- Booster goc cua fold_20 khong ton tai (train_gate_fold.py chi ghi ONNX). Chap nhan lam "model goc" cho P2: booster train lai dung script
  + tham so + dataset md5 a1c78e2f (2 759 040 dong). Ly do: doi tuong cua P2 la CONG CU SUY LUAN (ONNX runtime trong chuoi moi), live dung
  chinh file ONNX 8ec99757; so do da co: nguong tach lech <= 5,3e-7, la <= 9,0e-9, du doan max|d| 1,96e-8 tren 1 000 dong (nguong 1e-6).
  Lane L PHAI dung file ONNX live 8ec99757 (khong dung booster tai dung).

## B3. Mo seal holdout 2026
- AGENT_RUNBOOK (HOLDOUT_UNSEAL): mo holdout 2026 can owner duyet truc tiep. Luot 3 DUNG truoc moi buoc sinh pred/bins 2026 va truoc Lane L
  cho toi khi MASTER ghi nhan loi duyet cua owner vao addendum ke tiep. Cong tai lap, P1, snapshot, kiem do phu funding KHONG phai mo seal.
