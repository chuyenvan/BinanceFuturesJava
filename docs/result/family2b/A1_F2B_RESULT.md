# A1 audit KET QUA FAMILY2B (2026-11-28) - PHAN QUYET: PASS-CO-LUU-Y ; "DAT 0/24" XAC NHAN
Code rieng (khong import driver), chi doc out/f2b-<o>-<seed>, out/r1-a3-<seed>, f2b_state/pushed. Khong chay sim, khong Kaggle, khong git.

1. Toan ven: sha driver 8310d262.., F2B_SCORE.md 67082d37.., .json 52156fc3.. KHOP. 48 thu muc o + nen 2 (khong _stale/smk). Moi o: result.ok true,
   jar cc0f9d11.. (full sha khop), mapper 863, java_rc 1 (= r1-a3 ca 2 seed), md5 printDone tren dia = marker: 50/50. Ngay sim 20210701..20251230, 1644 ngay, moi o = nen.
   Seed khong lan: pred_md5_used A1 = None (template) cho moi o A1 + r1-a3-a1; S7 = b737fb6d.. cho moi o S7. NEN md5 = r1-a3 (8986d332 / 083e3de0), eq 145391 / 138042.
   Luu y: driver sha 8310d262 (commit b70e3dbe "v4") KHAC sha ghi trong ERRATA2 (ddf97c3c) - chua co errata ghi sha v4 (thieu so sach, khong anh huong so).
2. Cau hinh: prof_run.properties + marker 48/48 dung bang muc 4 (SL, TP = R x |SL|, TP_ONLY "true", A bo X14 / B giu X14 336h, S1 1,1,1,1/0.015, S2 1,0,0,0/0.0075,
   WFO_DISABLE_DCA=1, DCA_GRID_ENABLED true, SCALE 6, time-stop 168). printDone: 0 dong DCA_LEVEL* o 48 o (NEN co 63 / 57). Status: A chi TP/STOP_LOSS; B chi STOP_LOSS/STOP_MARKET.
   Log: A khong co "[TSX] extHours>0", B + NEN co; 0 HARD SL, 0 parse error. TP: p1/p50/p99 profit = dung nguong TP o moi o A (0 lenh lech > 1e-3); so dong log TAKEPROFIT = so TP.
   STOP_LOSS (A) = PREARM_SL log + time-stop 168h (dem khop dung: vd A20R2 a1 1037 + 1418 = 2455). SL p50 = dung nguong; SL khop min(stop,open,close) => 30-37% lenh SL
   te hon nguong > 0.5 diem % (p1 -22..-32%) - THEO PREREG nhung la gia dinh BI QUAN. TP khop dung muc khi close vuot = gia dinh LAC QUAN.
   Doc tay 20 TP + 20 SL (A10R1-S1 a1, A20R2-S2 s7): exit = entry x (1+TP) / x (1+SL) chinh xac; pnl = margin x profit - phi ~0.112% - funding. Hop le.
   Cuoi ky: equity cuoi = tong pnl dong (lech <= 1) => khong lenh mo cuoi ky; lenh cuoi dong 2025-11-21..28 (ca NEN).
3. Tai lap chi so (MTM b+unP cuoi ngay, sim.out; sim.out == sim.out.gz): lech toi da so voi F2B_SCORE.json: CAGR 0, maxDD 0, Calmar 0, n lenh 0, PnL nam 0.5 (lam tron).
4. Tieu chi: tinh lai 24/24 TRUOT, trung bang diem. Calmar < NEN o CA 2 seed cho CA 24 o => truot doc lap voi cach doc tieu chi nam (tung seed hay cung nam) va DD.
   Gan nhat: B20-S2 (Calmar 2.123/2.211, 1.880/2.016; S7 DD -18.41 vs -17.69); B20-S1 (chi truot Calmar 1.813/1.677); A20R2-S2 (Calmar 1.609/1.499 + DD -24.2/-26.0).
   Chieu nguoc: khong thay sai dau / don vi / seed / baseline. Tieu chi nam MTM cho cung ket qua tieu chi nam PnL dong.
5. Mo ta: A cai thien don dieu khi SL rong + R lon; SL -5% am/~0. B: SL rong tot hon. S2 ~ S1 x1.4-1.5 CAGR, DD sau hon. A20R2-S2 CAGR 39.0/39.0 > NEN 37.2/35.7 nhung DD -24/-26.
   2025 MTM: NEN +28.8/+31.4%, B20-S2 +15.8/+12.8, A20R2-S2 +5.9/+6.0.
6. Thoi gian: 2021-07..2025-12 (DEV, khong du lieu 2026). TOAN BO LA IN-SAMPLE; NEN (gate, topk, X14 days) cung chon tren cua so nay. Khong co phan ngoai mau.
7. Spearman thu hang 24 o A1 vs S7: Calmar 0.983, CAGR 0.984, maxDD 0.990; lech hang toi da 3; khong o nao doi dau.
