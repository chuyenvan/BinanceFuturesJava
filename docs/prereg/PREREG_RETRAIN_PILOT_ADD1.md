# PREREG_RETRAIN_PILOT_ADD1 - quyet dinh MASTER tai STOP-1 (2026-11-21) - TRUOC khi train bat ky model T1 nao
Bo sung docs/prereg/PREREG_RETRAIN_PILOT.md (c796c7b3). Bao cao buoc 2: v12/RETRAIN_PILOT_RUN.md (sha256 89c49bb4...).
## 1. Ket qua cong tai lap 3a
P15-A PASS (cay / node trung het b68563fe, ORT max|d| 0,0 tren 20 000 dong; md5 ONNX khac CHI do graph.name la uuid ngau nhien cua
onnxmltools). S1-A PASS (sha256 JSON cc0924f1... trung). NET-A PASS (khoa trung 100 %, spearman 0,9999999999999, max|d| 4,77e-7).
NET-B PASS (2 lan CPU trung byte ff591c49...; spearman 0,991128 so voi ban goc GPU; train 24-26 phut).
P15-B FAIL theo nguong: retrain fold_20 trung 100 % thuoc tinh voi ban retrain cua HO5 (24e99ef8) nhung so voi fold_20 live 8ec99757:
|d| q99,9 = 1,6e-8, max 6,75e-5 o 1 / 20 000 dong (nguong 1e-6).
## 2. Quyet dinh
A1-1 P15-B: ghi nhan FAIL; KHONG chan. Ly do (khai truoc khi co bat ky so T1 nao): (i) fold_20 goc train tu wfo_feature_store.csv DA MAT ->
     khong the tai lap byte theo cau tao; (ii) P15-A chung minh script + gate_dataset_full.csv (a1c78e2f) + xgb-env tai lap DUNG noi dung
     model cung recipe; (iii) fold_20 KHONG nam trong chuoi tao model T1 / T2 (Lane N dung pred fold_20 cua Lane L theo byte cho ts < S3).
     He qua: khong dung "retrain fold_20" lam vat thay the cho model live o bat ky buoc nao.
A1-2 Cac cong md5 ONNX ve sau: so thuoc tinh cay / node + ORT max|d| <= 1e-6 (md5 ONNX khong tai lap duoc do uuid graph.name).
A1-3 D4: net015 dung CPU (tat dinh, ~25 phut / model) cho moi model.
A1-4 P14: them "20260701", "20261001" vao cuoi CUT_DATES cua research/pipeline/g015_net_train.py (diff 1 dong; md5 moi
     3de89b98339d1c46b267f4e92d10314f) - commit cung addendum nay.
A1-5 PHAT HIEN: g015_net_train.load_labels (:144) loc cung file nhan co ten < "20260701" => voi T2 (cut20261001) file nhan Q3 bi bo qua
     im lang. QUYET DINH: cho phep sua DUNG 1 cho nay ("P14b"): can loc = cut cua fold dang train (file nhan co ngay bat dau < cut), kem
     assert max(ts nhan dung de train) < cut - purge 72 h. Day la sua duong ong du lieu, khong doi feature / nhan / hyperparam.
     Cong tuong duong BAT BUOC (NET-EQ): train net015 T1 (cut20260701) HAI lan tren CPU - ban P14 (loc cu) va ban P14b (loc moi) - model
     phai TRUNG BYTE (voi cut20260701 hai cach loc tuong duong). Khong trung -> DUNG. Model T1 chinh thuc = ban P14. T2 dung ban P14b;
     T2 phai ghi so dong nhan Q3 > 0 trong manifest. Agent ap P14b trong ban copy, bao md5 + diff; MASTER commit tai STOP-2.
A1-6 Tiep tuc buoc 3-4 toi STOP-2. Moi thu khac giu nguyen prereg.
