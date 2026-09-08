# L3/REV6 (c3_shadow) — kiem tra live 242, 08/09/2026 19:xx

Doc nay CHOT lai: goi rev6/L3 (`docs/QUEUE.md` Q8, runbook muc 12) **DA DEPLOY THANH CONG**
tren 242 tu **07/09/2026 06:29:57**, khac voi trang thai "CHUA DEPLOY" con ghi trong QUEUE.md/
runbook. Kiem tra nay la READ-ONLY (chi doc log/env qua SSH, khong sua gi tren 242).

## 1. Xac nhan logic dung spec
Dong log dau tien sau deploy:
`[LIVE_PROFILE=c3_shadow] BAT — arm=0.07 timeStop=168h ratchet=LIEN TUC paperEquity=35000.0 sizeCap=4.5%. SHADOW_NO_PUSH=true (hardcode, khong doc env).`
Khop 100% muc 12.1/12.2 runbook. Env song (`/proc/<pid>/environ`): `LIVE_PROFILE=c3_shadow`,
`SELECTOR_RANK_TOPK=8`, `SHADOW_NO_PUSH=true`, `PAPER_EQUITY=35000`, `SHADOW_C3_DIR` dung.
`SIM_RATE_PROFIT_STOP_MARKET=0.05` (arm LEGACY) **khong doi** — dung yeu cau "KHONG DUNG".

Lech nho so voi draft: model path thuc te la `storage/c3_models/s1a2x1_cut20251001.onnx`
(draft ghi `storage/s1_c3/...`) — chi khac ten thu muc, khong gay loi (S1 van score binh thuong
moi ~15 phut, vi du 615/605/640 coin).

## 2. LEGACY (tien that) — on dinh
`[LEGACY] managed 65` va `Update all position:65` khop nhau lien tuc qua nhieu tick (khong mo coi,
khong lech N0 ~66). 0 exception/ERROR ke tu thoi diem deploy.

## 3. Chi so van hanh (checklist SHADOW-HEALTH, QUEUE.md)
- n_jvm=1 (dung). PID 4349, RSS=1.77G (< cap 5G). RAM box: used 4.5G/7.6G, available 2.8G.
- `[MAP]` p50 (96 tick gan nhat): min=0.4295 med=0.4892 max=0.5842 — nam trong nguong [0.20,0.70],
  KHONG vi pham. `[MAP]` cuoi cung luc 19:15:39 hom nay (trong 2h).
- OutOfMemory: 0 lan ke tu deploy (07-08/09). Co 1 dot 229 loi OOM (`DataManagerAerospikeFloatSim`)
  hoi **28-29/08/2026**, da het han, khong tai dien tu do den nay.
- API-key format invalid: 0.

## 4. SO GIAY C3 sau ~37h
Ledger 23 lenh DA DONG, ca 23 deu TRAILING_STOP co lai (khong lenh nao lo), tong PnL +$1,182.79
(trung binh +$51.4/lenh tren paperEquity gia dinh $35,000). **Khong phai "100% win rate" theo
nghia thong thuong**: co che arm 7%/ratchet chi dong lenh sau khi da vuot +7% roi trailing xuong —
lenh chua toi +7% van dang MO (hien 19 lenh mo, chi AKEUSDT da arm o dinh +16.9%). Time-stop 168h
(7 ngay) chua co lenh nao cham toi nen chua thay case xau (kep hang qua han). Mau qua nho (23 lenh,
1.5 ngay) de ket luan hieu nang that.

## 5. VAN DE PHAT HIEN — CAN SUA
1. **Docs sai trang thai deploy**: QUEUE.md Q8 va runbook muc 12 con ghi "242 CHUA DEPLOY" —
   da sua status trong QUEUE.md (commit nay). Runbook file rev6 draft header cung nen cap nhat
   khi co dip.
2. **SOP SHADOW-HEALTH loi thoi, se bao dong GIA**: dieu kien "would-BUY phai = 0" va
   "Create order market phai = 0" duoc viet TRUOC khi co c3_shadow/that song song. Thuc te:
   `would-BUY` = 1071 dong (chinh la log hop le cua so giay C3, dung thiet ke muc 12.5),
   `Create order market` = 1506 dong (log dat lenh THAT hop le cua LEGACY dang chay that tu
   21/08). Neu de nguyen, job SHADOW-HEALTH tu dong se bao CANH BAO GIA moi ngay. Da sua dieu
   kien trong QUEUE.md (commit nay) — chi con giu OOM/API-key-invalid la nguong "phai = 0" that su,
   would-BUY/Create-order-market chuyen thanh chi so theo doi (khong phai bao dong).
3. **`docs/SHADOW_LOG.md` dang trong** — job SHADOW-HEALTH du danh dau READY/lap moi ngay
   nhung co ve chua tung thuc su chay/ghi log lan nao. Dong dau tien da ghi trong commit nay.
4. **Quyet dinh con mo (chua lam, cho user)**: sau khi 242 verify PASS (~37h chay sach), co tat
   "shadow Oracle" (`/home/ubuntu/shadow_c3/app` + cron health) nhu muc Q8 runbook de xuat khong?
   Chua kiem tra shadow Oracle con chay hay khong trong dot nay.
