# PREREG_K12 -- SELECTOR_RANK_TOPK 8 -> 12 tren C3_FULL 48 thang

Viet va commit TRUOC khi chay bat ky run nao. Khong sua sau khi thay ket qua.

## 0. Vi sao mo nhanh nay
`docs/F1_FLOW_RESULT.md` da quet K=8/16/24/32 tren C2b (TRUOC 3 fix B1/B2/B3, DCA off) va
DONG huong: K=8 toi uu, K>8 lam xau Sharpe/maxDD/underwater don dieu. K=12 CHUA TUNG chay
(F1 nhay 8->16, bo qua 12). Tu do he doi han: B1/B2/B3 bat, C3_FULL them DCA that
(`DCA_GRID_WEIGHTS=1,1,3,8`, `SELECTOR_ONLY_ENTRY=0`). User yeu cau lap khoang trong K=12
DUNG tren cau hinh C3_FULL 48 thang hien hanh (`profiles/x1_c3_full.properties`).

## 1. Rui ro / lo hong -- doc TRUOC
1. `sd(dCAGR)` cua so 48 thang CHUA do (`X1_EXTEND.md` muc 9: "khong tim thay so do").
   Khong dung equity de phan quyet (luat cung #3 AGENT_RUNBOOK).
2. Day la lan dau K sweep chay TREN NEN C3_FULL (co DCA that) -- co che "chet bang
   time-stop o rank sau" tim thay o F1 (tren C2b, DCA off) co the tuong tac khac voi DCA
   (lenh rank sau co duoc DCA cuu khong -- chua biet, se do them neu du du lieu).
3. Dia Oracle 94% day, 13G free (do 2026-09-07). Dataset `wfo_ds_x1` phai dung lai (da bi
   xoa sau X1) roi XOA NGAY sau khi xong ca 2 arm.
4. Chi 1 slot JVM Oracle -- 2 run (parity K8 + candidate K12) tuan tu, khong song song.
5. `n_eff` muc lenh 48 thang = 174 khoi 72h co lenh (X1_C3_FULL) -- CI hep hon 30 thang
   ~1.37 lan nhung van nho; du phat hien lech rate ro, KHONG du dao nguoc ket luan cau truc.

## 2. Thiet ke -- CHI doi mot bien
`profiles/x1_c3_full_k12.properties` = ban sao NGUYEN VAN `profiles/x1_c3_full.properties`,
doi DUY NHAT `SELECTOR_RANK_TOPK=8` -> `SELECTOR_RANK_TOPK=12`. Khong doi DCA/gate/exit/
sizing/bins. Dataset WFO dung CHUNG mot lan build (SELECTOR_RANK_TOPK khong anh huong
`ExportWfoDataset` -- xac nhan boi F1_FLOW da dung chung 1 dataset cho ca 4 gia tri K).

Hai arm chay TUAN TU tren CUNG dataset `wfo_ds_x1` (rebuild theo dung logic
`research/pipeline/x1/run_x1_sim.sh`, buoc build dung `TRADING_PROFILE=x1_c3.properties`):
1. `X1_C3_FULL` (K=8, CONG PARITY -- bat buoc chay lai de xac nhan tai lap dung so cu)
2. `X1_C3_FULL_K12` (K=12, candidate)

## 3. Cong PARITY -- bat buoc PASS truoc khi doc K12
Re-run `X1_C3_FULL` (K=8) tren dataset build moi phai khop `docs/X1_EXTEND.md` muc 9:
equity cuoi **111,428**, n lenh **2,266**, maxDD 48 thang **-12.46%**, underwater **227 ngay**.
Sai lech bat ky so nao (ke ca 1 lenh) => DUNG, dieu tra nguyen nhan (bins troi / jar khac /
code-sha khac), KHONG doc K12.

## 4. Tieu chi -- rate + CI khoi 72h x1.21 (giu nguyen khung PREREG_X1 muc 4)
Tren TOAN cua so 2022-01..2025-12 VA tach rieng tung nam 2022/2023/2024/2025:
`TSloss%` . `win%` . `mean(profit|SM)` . `mean(profit|SL)` . phan bo `profit` theo RANK
bucket (1-8 vs 9-12, mirror co che F1 muc 7 -- do xem rank 9-12 co chet time-stop nhieu
hon rank 1-8 khong). `n` va `mean(margin)` la bien KIEM SOAT, khong dung lam bang chung
chat luong. CI: bootstrap khoi 72h, he so nhan **1.21** (`docs/PREREG_CI.md`/`F4_TIMING.md`).

## 5. Rang buoc CUNG -- SO VOI baseline K=8 (chay lai o buoc 3), tren TUNG nam
- `maxDD` cua K12 khong duoc vuot `maxDD` cua K8 (cung nam) qua **+3 diem phan tram tuyet doi**
- `underwater` cua K12 khong duoc dai hon `underwater` cua K8 (cung nam) qua **+30 ngay**
- khong nam nao am (ap dung ca K8 va K12)
- khong quy nao `< -5%` MOI xuat hien o K12 ma K8 khong co (neu K8 da vi pham san o nam/quy
  nao thi chi tinh K12 co vi pham THEM cho moi khong, khong tinh lai vi pham co san)
Dung so RELATIVE (so voi K8 chay lai o buoc 3), KHONG dung so tuyet doi co dinh truoc --
vi baseline K=8/48-thang da tu no vuot nguong 120 ngay cu cua F1 (UW=227), nen nguong tuyet
doi cu khong con y nghia phan biet.

## 6. Quy tac quyet dinh -- chot TRUOC khi thay so
K=12 thay K=8 lam cau hinh C3_FULL CHI KHI ca 3 dung:
1. thang **>= 2 rate cung huong, ngoai CI**, tren toan cua so 48 thang; VA
2. PASS toan bo rang buoc cung muc 5 o MOI nam; VA
3. co che TSloss%-theo-rank-sau (rank 9-12 tach rieng, neu do duoc) KHONG cho bang chung
   "rank 9-12 chet time-stop nhieu hon han rank 1-8" theo huong don dieu da thay o F1 --
   neu co, do la bang chung cau truc CHONG lai K12 du rate tong co thang do nhieu.
Khong dat (1) hoac (2) => NULL, DONG huong K12, giu K=8. Null co tinh thong tin -- bao cao
null, KHONG tune them gia tri K khac sau khi thay so (vd thu K=10, K=9...).

## 7. Equity/CAGR -- bao rieng, KHONG phai tieu chi
Ghi ro nhan "khong phai tieu chi" theo luat cung #3 AGENT_RUNBOOK.

## 8. Pham vi
DEV only (`SIM_END_DATE=20251231`). Khong dung 2026 (`HoldoutSeal`). Khong sua code Java,
chi them 1 file profile + 1 doc + chay sim.
