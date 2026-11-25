# A1_PILOT_M_V2 - audit PREREG_PILOT_M v2 (sha256 3cc4f815...c358bce, 332 dong) - 2026-11-25
Chi doc. Khong doc du lieu >= 2026-11-24 07:00. Nguon them: pull242/2026-11-19..20 (log + check.txt).

VERDICT: FAIL (hep) - B1-B9 va m1-m13 da sua dung; con 4 loi chac chan sinh DO/VANG gia ngay 26-27/11. Dan NGUYEN VAN R1-R4 => commit duoc, khong can A1 vong 3.

R1 (dong 215-216, M-S muc cung) eq_lo lay 2 dong [KILLSW] HOURLY bao quanh SUBMIT: 26/11 restart 09:31, SUBMIT truoc 10:00 => dong 09:00 cua JVM cu (eq ~1000) => r ~ 5 => VI_PHAM => DO gia.
 Thay: "eq_lo = min truong eq= cua cac dong [KILLSW] HOURLY CUNG JVM voi SUBMIT (sau banner khoi dong cua JVM dang chay) bao quanh SUBMIT; chi co 1 dong cung JVM => dung dong do; khong co dong nao cung JVM => chi xet r_cap = C_ngam / C3_CAPITAL > 1 + 1e-6, nhanh r < 0,98 = KHONG_CHAM_DUOC cho leg do."
R2 (dong 269-270, K5) restart lam mat phut feat/sel: 19/11 (24 restart) check.txt STATUS=INCOMPLETE, fails=feat_minutes=1165/1440;sel_minutes=1165/1440;psym_* (log_minutes=1440, log_max_gap_min=0). => 26/11 K5 VI_PHAM => VANG gia.
 Thay: "Ngay 2026-11-26: chap nhan STATUS=INCOMPLETE neu fails CHI gom feat_minutes / sel_minutes / psym_feat_minutes / psym_pred_minutes va moi gia tri >= 1440 - 20 x (so banner khoi dong C3LiveRuntime trong ngay); log_minutes=1440 va log_max_gap_min <= 15 van bat buoc."
R3 (dong 222-223, M-S (4)(5)) run/c3live_exchangeInfo.json KHONG co trong pull242/<D>/run (chi gate_ratio_live.bin.gz) => KHONG_CHAM_DUOC moi ngay => tu 27/11 VANG "thieu du lieu > 1 ngay" => luat 2 ngay.
 Thay: "thieu => (4)(5) KCD_CAU_TRUC cho toi khi co quy trinh chep exchangeInfo hang ngay duoc MASTER ghi vao prereg bang ERRATA; sau do thieu = KHONG_CHAM_DUOC."
R4 (dong 259-262, K2) 26/11 pilot_on dat KILL_SWITCH/PAUSE, doi env C3_CAPITAL truoc restart, co the 2 process trong luc swap => TOM TAT push=OFF / C3_CAPITAL lech / khan_canh_bao lien tiep => VANG gia.
 Them: "Ngoai le 2026-11-26: cac dong TOM TAT trong khung [lenh pilot_on bat dau ; dong TOM TAT dau tien co push=ON VA C3_CAPITAL=5000] (toi da 60 phut, ghi gio pilot_on tu PILOT_DAY_1126 / ghi chep owner) KHONG xet; qua 60 phut chua ve => VI_PHAM."

MINOR (ERRATA sau duoc):
n1 (6) M-T dong 141-144: thread xac dinh duoc. TrailingStopManager tick goi defer.defer cung ham voi dong arm (:207-231); TsMktExt.track log o thread goi (:363-371); moi dong TrailingStopManager truoc T_cut co thread [C3LIVE-OPS]. Cau chot: "defer-START cua cum THAT = dong co thread [C3LIVE-OPS]; thread khac = so giay, bo qua; dong khong co truong thread => KHONG_CHAM_DUOC."
n2 D1(a): avg leg 0 dung gia sau PX_CORRECTED neu co (nhu M-X).
n3 SKIP ORDER that: "SKIP ORDER [<SYM> DCA_LEVEL1] due to AI REJECT: BAD MOMENTUM: ... symbolPred: null" - so khop tien to la du; 0 dong truoc T_cut (chi kiem code :1333).
n4 M-X: median luy ke >= 10 leg gom leg micro (von 1.000) - ghi ro, khong tach.

Tra loi:
(1) B1-B9 dung + du; m1-m13 du (m3 I2 dung 2 phut; m10 o Q1). Khong thay loi moi ngoai R1-R4.
(3) KCD_CAU_TRUC chi gan cho muc can Vision / rig / 242 (I1,I2,I5,I6,I7,D2,D3,D4,M-E,L-S,L-S2,M-G,K7) - khong muc chi-log nao bi gan; R3 la truong hop nguoc (dang phai la KCD). Muc 10: moi trang thai co dung 1 bac, khong chong cheo (K3 chi o DO; K1/2/4/5/6 o VANG; I1/D2 DATA tach ro).
(4) "AI PASS [SYM] Reason: PERFECT: 15M(x%) symbolPred: null" khop code :1338 + AIRejectFilter :202-203 va dong that 20/11 08:54:06 (35 dong 1.03%). Nhanh due= truyen symbolPred=null (:1235/:1246), log PASS cung thread TRUOC onLeg => cua so [dts+60 s ; t_SUBMIT] hop ly.
(5) K5 15 phut: hop ly (24 restart 19-20/11: 0 khoang trong log > 60 s) nhung thieu STATUS (R2). D1(e): hop ly. M-X >= 10 leg: hop ly.
(6) xem n1.
(7) Muc 13 nhat quan voi than.
(8) Ngay 24-26/11: R1 (DO gia 26/11), R2, R4 (VANG gia 26/11), R3 (VANG tu 27/11). Ngoai ra khong thay.
Dieu kien commit: dan R1-R4; ghi sha commit vao dong dau moi D_*.md; tools/pilot_m/* qua A1 truoc khi dung.
