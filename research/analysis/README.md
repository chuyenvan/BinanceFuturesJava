# Script phan tich (2026-09-03)

Chay tren Oracle bang `python3`. Doc du lieu tu `/home/ubuntu/ledger/` va
`/home/ubuntu/java/devrun/*/storage/printDone.csv`.

## HAI BAY PHAI NHO KHI VIET SCRIPT MOI

1. **Huong score**: `pred_s1*.parquet` co `score` **THAP = TOT** (sim dung `1 - slot0`).
   Xep `ascending=False` la dao nguoc moi ket luan. Da mac loi nay.
2. **Mui gio**: `printDone.csv` ghi gio **GMT+7** (sim ep `Asia/Ho_Chi_Minh`);
   ledger dung **epoch UTC**. Ghep dung: `ts = ((ms_GMT7 - 7*3600000) // 900000) * 900000`.
   Ghep thang lam do phu tut tu 76% xuong 29.5%. Da mac loi nay.
   => Moi script ghep printDone <-> ledger PHAI in ti le ghep truoc khi doc ket qua.

## Cac script

| file | tra loi cau hoi gi |
|---|---|
| `sim_truth.py` | S1 thang G015 nho chon coin tot hon hay nho so lenh? (so lenh CHI-S1 vs CHI-G015) |
| `gate_vs_rank3.py` | rank-IC cua S1/G015 trong tick; top-K vs random-K; chat luong vung bien gate |
| `proxy_fidelity3.py` | nhan offline nao du bao tot nhat ROI THAT cua sim |
| `calib_check.py` | do tu tin tuyet doi cua G015 co hieu chuan tot khong + tran ly thuyet cua gate |
| `p6_analyze.py` | CONF_SIZE: sizing theo do tu tin selector co gia tri khong (KHONG) |
| `size_signal.py` | quet 9 bien trong printDone xem bien nao dang de size |
| `conc_check.py` | he bi gioi han boi VON hay boi CO HOI (co hoi) |
| `p15_robust.py` | hieu ung "p15 qua nong" co ben qua tung nam khong (KHONG) |
| `cov_diag2.py` | do phu cua ledger so voi lenh that (kiem tra bay mui gio) |
| `struct_check.py` | kiem cau truc ledger truoc khi ket luan (p15 theo tick hay theo coin...) |
