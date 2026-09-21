# PREREG_REGIME_UPDOWN — TASK B2 Buoc 4: gate regime up/down theo MA200, up-gate CHAT hon (2026-09-21)

Chot: 2026-09-21, commit TRUOC khi build/chay sim. Y tuong cua Uni (thiet ke MASTER,
`TASK_B2_step4_regime_updown_gate.md`), agent thuc thi Sonnet. Tien de: Buoc 2
(`docs/RESULT_REGIME_GATE.md`, commit `54d9cdb`) da test up->1.0/down->1.70 theo MA200-trailing:
cuu duoc bear 2022 (R=T170 gan nhu tuyet doi nam do) nhung VO UW-2025 (up-gate=1.0 qua long cho
bull-nhieu 2025). Chan doan UW-2025 (`docs/DIAG_UW2025_SOURCE.md`, 0-sim) xac dinh nguon 2025 la
nen alpha-bien trong bull-run co song lon, KHONG phai BTC-bear, va R0 (gate co dinh 1.18 deu,
khong doi theo regime) lai PASS 2025 de dang (UW=126) — goi y up-gate CHAT hon se cuu duoc 2025.

## 0. Y tuong cot loi

Fix cua Uni: up-gate CHAT hon T100 (T120 ~ 1.2) thay vi giu 1.0. Gia thuyet: **up->1.2,
down->1.7** du chat de ca bull-nhieu 2025 (regime UP) khong vo UW, nhung van long hon T170 o
up-regime de lay them breadth so voi giu T170 deu. down->1.7 giu nguyen phong thu bear 2022 (da
chung minh song o Buoc 2). Day la co che PROACTIVE (dat muc gate CO DINH theo regime, KHONG giam-
khi-duoi-nuoc) — khac ban chat voi 3 co che REACTIVE da NULL truoc do (TASK B pacing-theo-size,
Buoc 2-pacing chua chay, Buoc 3 drawdown-throttle): NULL cua nhung vong do KHONG loai duoc huong
nay vi co che khac hoan toan.

## 1. CHONG OVERFIT — bat buoc, diem review MASTER (khoa TRUOC khi thay so)

- **1 cap QUYET DINH khoa truoc theo ly le doc lap voi du lieu**: up=1.2 (can cu: chan doan
  UW-2025 cho thay gate co dinh ~1.18 (R0) cuu duoc 2025 — 1.2 la muc T120 tron, gan voi 1.18 va
  van CHAT hon T100; ly le doc lap thu hai: up-regime van can mot muc phong thu vua phai vi bull
  van co drawdown/whipsaw, khong nen tha long hoan toan ve 1.00), down=1.7 (=T170, da chung minh
  song bear 2022 nguyen ven o Buoc 2, KHONG quet lai down).
- **RA12 (up=1.2, down=1.7) la BIEN THE PHAN QUYET DUY NHAT.** Tieu chi u1-u5 o muc 4 CHI ap
  dung/quyet dinh cho RA12.
- **Sweep MO TA (KHONG dung de chon winner)**: them RA14 (up=1.4, down=1.7) — R (up=1.0,
  down=1.7, tai su dung nguyen so tu Buoc 2, KHONG chay lai) la diem thu ba tren cung duong cong.
  Muc dich DUY NHAT cua RA14: cung voi R va RA12, ve duong cong breadth(n_eff)-vs-UW theo up-gate
  {1.0, 1.2, 1.4} de HIEU trade-off — bao ca 3 muc minh bach trong ket qua.
- **LUAT CAM (khoa cung, khong duoc pha o buoc 6)**: sau khi thay so RA12/RA14, TUYET DOI KHONG
  duoc doi cap quyet dinh sang mot muc up-gate khac (vd 1.15, 1.25, 1.3) du muc do co ve dep hon
  ve so — day chinh la loi 'mo bien the quanh winner' da bi cam trong power_wall/cac vong TASK
  truoc. Neu RA12 NULL va RA14 (hoac mot diem tren duong cong) trong PASS hon, KHONG duoc coi RA14
  la ung vien thay the trong vong nay — phai bao ca hai la NULL/HON HOP va de xuat mot PREREG
  MOI rieng (voi k tinh du multiplicity) neu muon theo duoi diem do.
- Cham diem PER-YEAR 2021-2025 + toan ky cho ca 5 tag (T170, gate-1.0/T100, R, RA12, RA14).
  down-gate giu 1.7 co dinh xuyen suot (khong quet).

## 2. CO CHE — 0-diff Java neu duoc, ghi ro neu phai sua

Dung nguyen ha tang `GATE_REGIME_ADAPTIVE` + `RegimeSchedule` (TreeMap nap causal tu file CSV
ngoai, KHONG hardcode lich) + CSV regime MA200-trailing da sinh o Buoc 2
(`/home/ubuntu/regime_work/regime_daily_ma200_x1_2021.csv`, KHONG sinh lai, tai su dung nguyen
van — cot `scale` trong CSV nay CHI de audit, RegimeSchedule.load() chi doc cot 0 (utcDay) va cot
3 (nhan UP/NOTUP), khong doc cot scale). `not_up(D)` = BTC `close[D-1] < MA200_trailing(D)` (200
ngay, causal) — dinh nghia CHINH khong doi tu Buoc 2.

**Phat hien recon quan trong (khac gia dinh ban dau cua nhiem vu)**: doc lai
`EntryGate.java` xac nhan `REGIME_SCALE_UP`/`REGIME_SCALE_NOTUP` la **hang so Java
`public static final float`**, KHONG phai key doc tu profile qua `Configs` (chi
`GATE_REGIME_ADAPTIVE`/`SIM_REGIME_FILE`/`SIM_REGIME_FORCE` la key profile doc duoc; up/notup
scale la hang so cung trong code = 1.00f/1.70f). Vay **KHONG THE** chi doi profile de co
up-gate=1.2/1.4 nhu gia dinh ban dau cua nhiem vu — day la truong hop 'buoc phai sua Java' ma
thiet ke da luong truoc va cho phep (muc 2 cua tai lieu nhiem vu: 'neu buoc phai sua Java de nhan
SCALE_UP!=1.0 -> ghi ro + giu OFF byte-identical').

**Thay doi Java toi thieu (khoa truoc khi build/chay, KHONG hoi to sau khi thay so)**:
1. `EntryGate.java`: bo `final` khoi `REGIME_SCALE_UP` (van gia tri mac dinh 1.00f) de co the gan
   lai luc chay.
2. `Configs.java`: them doc key moi `SIM_REGIME_SCALE_UP` (float) — neu khai bao va > 0 thi gan
   `EntryGate.REGIME_SCALE_UP = gia tri do`; khong khai bao / <=0 => giu nguyen 1.00f. Chen ngay
   sau nhanh doc `SIM_REGIME_FORCE` hien co, cung khoi if-block `SIM_GATE_REGIME_ADAPTIVE`.
   `REGIME_SCALE_NOTUP` KHONG doi (van la hang so `final` 1.70f, dung nguyen thiet ke — down
   khong quet nen khong can cho doi duoc).

**Vi sao khong anh huong OFF/khong anh huong ket qua Buoc 2 cu**: nhanh OFF (`GATE_REGIME_ADAPTIVE
= false`, mac dinh) dung `x * GATE_DYN_SCALE` (mot field HOAN TOAN khac, khong lien quan
`REGIME_SCALE_UP`) — `EntryGate.threshold()` co dieu kien `gateScale = GATE_REGIME_ADAPTIVE ?
CURRENT_REGIME_SCALE : GATE_DYN_SCALE`, nen bo `final` cua `REGIME_SCALE_UP` va them key doc
Configs KHONG DUNG CHAM toi bat ky bieu thuc nao tren duong OFF => ky vong OFF van byte-identical
(kiem chung thuc te o cong muc 5). Vong R cua Buoc 2 (up=1.0) khong khai bao `SIM_REGIME_SCALE_UP`
trong profile cu (`x1_c3_full_regime_r.properties`) nen van chay dung 1.00f mac dinh y het truoc
— KHONG can chay lai R, so cu (`docs/RESULT_REGIME_GATE.md`) van dung duoc nguyen ven.

## 3. BIEN THE

- **T170** (moc, gate 1.70 deu) — dung lai `X1_GS_T170_2021` (so tu Buoc 2), VA chay lai 1 lan
  OFF-verify (`X1_GS_T170_2021_REGIMEUPDOWN_OFFCHECK`) sau khi build jar moi tu HEAD hien tai,
  de xac nhan md5 = `efb793e2468ca3a7318da0f0ad23d4fc` VOI CODE DA SUA cua vong nay.
- **gate-1.0** (T100, deu 1.00) — dung lai nguyen `X1_C3_FULL_2021` (khong chay lai).
- **R** (up=1.0, down=1.7) — dung lai nguyen `X1_C3_FULL_2021_REGIME_R` va so tu
  `docs/RESULT_REGIME_GATE.md` (khong chay lai).
- **RA12 (QUYET DINH)**: profile `profiles/x1_c3_full_regime_ra12.properties` =
  `x1_c3_full_regime_r.properties` (Buoc 2) + dong `SIM_REGIME_SCALE_UP=1.2` (down giu nguyen
  `REGIME_SCALE_NOTUP=1.70` hang so, khong doi qua profile). Tag `X1_C3_FULL_2021_REGIME_RA12`.
- **RA14 (sweep mo ta)**: profile `profiles/x1_c3_full_regime_ra14.properties`, giong RA12 tru
  `SIM_REGIME_SCALE_UP=1.4`. Tag `X1_C3_FULL_2021_REGIME_RA14`.
- Ca RA12/RA14 dung CHUNG file regime CSV cua Buoc 2 (khong sinh lai) — cot `scale` trong CSV do
  chi de audit, gia tri up-gate thuc te lay tu `EntryGate.REGIME_SCALE_UP` (Java) tai thoi diem
  `RegimeSchedule.load()` chay, nen chi can doi `SIM_REGIME_SCALE_UP` trong profile la du, khong
  can sua/sinh lai CSV.

## 4. TIEU CHI — khoa truoc, CHI cho RA12 (u1-u5, UW la chinh)

- **u1 breadth**: `n_eff_total(RA12) >= 1.5 * n_eff_total(T170)`. (n_eff_total(T170) = 606.26 tu
  Buoc 2 — se doc lai tu `regime_gate_metrics`-style script cua vong nay de xac nhan khong doi vi
  T170 khong chay lai voi so lieu khac, chi OFF-verify de kiem cong an toan.) Nguong =
  `1.5 * 606.26 = 909.39`.
- **u2 khau vi hien hanh + san CAGR**: PASS toan bo rang buoc `x1_rates.py --appetite current
  --k 1` (maxDD<=30%, UW<=200/nam, quy>=-15%, nam khong am) O MOI NAM 2021-2025 VA toan ky, dac
  biet **UW<=200** (chi so chinh cua vong nay); VA `CAGR(RA12) >= CI-floor(T170, k=1)` (can duoi
  CI95 khoi-72h cua T170 tinh bang `cagr_ci_t170.py --k 1`, k=1 vi RA12 la UNG VIEN PHAN QUYET
  DUY NHAT trong vong nay theo luat khoa muc 1). Bao co them CI-floor(T170, k=3) de doi chieu neu
  MASTER muon coi day la 1-trong-3 lua chon (RA12/RA14/R) — KHONG dung k=3 lam can cu phan quyet
  chinh, chi de minh bach.
- **u3 so voi T170 (khong xau hon 25%)**: `maxDD(RA12) >= -14.8%` (=`-11.84 * 1.25`) VA
  `UW(RA12) <= 115` (=`92 * 1.25`), dung so T170 goc (khong doi) tu Buoc 2/OFF-verify vong nay.
- **u4 hieu luc up-gate (nham dung 2025, khong pha 2022)**: `UW(RA12, nam 2025) < UW(R, nam
  2025)` (up-gate chat hon THUC SU cuu duoc 2025 so voi up=1.0 cua R) VA `UW(RA12, nam 2022)`
  XAP XI `UW(T170, nam 2022)` (sai khac tuong doi <=5%, ky vong bang tuyet doi vi MA200 phan loai
  2022 100% NOT-UP nen up-gate khong duoc ap dung ngay nao trong nam do — dung ket qua nay de xac
  nhan co che dung nhu thiet ke, giong cach R=T170 tuyet doi o 2022 trong Buoc 2).
- **u5 khong pha uptrend tot**: `CAGR_nam(RA12, 2023) >= 0.90 * CAGR_nam(gate-1.0, 2023)` VA
  `CAGR_nam(RA12, 2024) >= 0.90 * CAGR_nam(gate-1.0, 2024)` (return theo nam duong lich, cot
  `ret_nam%` cua `x1_rates.py::hard_by_year`, dung gate-1.0/T100 lam moc uptrend-toi-da nhu Buoc
  2, KHONG dung T170 vi T170 la moc PHONG THU khong phai moc breadth).
- **THANG** = RA12 dat CA u1-u5. **NULL** = u2 vo (`UW(RA12)` van > 200 o bat ky nam nao hoac
  toan ky) HOAC u1 vo (mat breadth). **HON HOP** = con lai (dat mot phan, khong roi vao dieu kien
  NULL/THANG ro rang).

## 5. DO LUONG

Metric tong hop/phan phoi tren CUNG CUA SO 2021-07-01..2025-12-31, Oracle ARM64, per-year (KHONG
khoa sym/start rieng). Tai su dung nguyen van `research/analysis/bigdown_struct.py` (n_eff, ICC,
maxDD-decomp, uw-longest) va `research/analysis/c3_rates.py`/`x1_rates.py` (rate theo nam, rang
buoc cung theo nam, CAGR+CI) — KHONG sua 2 file goc nay. Viet MOI mot script
`research/analysis/regime_updown_metrics.py` (theo mau `regime_gate_metrics.py` cua Buoc 2,
KHONG sua file cu) de tinh u1/u3/u4 cho 5 tag va xuat JSON; u2/u5 doc truc tiep tu output cua
`x1_rates.py --appetite current --k 1` (va `--k 3` de doi chieu) chay tren ca 5 tag.

## 6. CONG BAT BUOC — fail thi DUNG, bao MASTER, KHONG chay tiep, KHONG sua nguong

- **(a) OFF byte-identical**: build jar moi tu HEAD hien tai (bao gom 2 thay doi Java muc 2,
  `mvn -o package`) -> chay lai T170
  (`X1_GS_T170_2021_REGIMEUPDOWN_OFFCHECK`, profile `x1_gs_t170.properties`, flag
  `GATE_REGIME_ADAPTIVE` van mac dinh false, khong khai bao `SIM_REGIME_SCALE_UP`) ->
  `printDone.csv` md5 PHAI = `efb793e2468ca3a7318da0f0ad23d4fc`. Fail => DUNG ngay, KHONG chay
  RA12/RA14, bao MASTER, giu nguyen code hien trang de MASTER xem xet.
- Khong lap lai 2 cuc FORCE UP/NOTUP (da PASS o vong 09-14 va tai xac nhan gian tiep o Buoc 2 —
  logic `RegimeSchedule.force()`/`scaleForTime()` khong doi tu do; chi them field
  `REGIME_SCALE_UP` co the gan duoc va 1 nhanh doc Configs, khong cham `force()`/`scaleForTime()`)
  — quyet dinh GIAM 1 luot sim de tiet kiem tai nguyen, ghi ro day la sai lech co chu dich, khong
  anh huong an toan.

## 7. QUY TRINH — thu tu bat buoc

1. Commit file nay (TRUOC khi build/chay). 2. Sua Java toi thieu (muc 2) + tao profile RA12/RA14
(muc 3, tai su dung CSV regime Buoc 2 nguyen van). 3. `mvn -o package`. 4. Kiem tra 1-job-nang:
`free -g` avail >=12G, `pgrep -af Simulator|ExportWfo|s1_hpo|xgboost` rong, `pgrep java` rong (tru
shadow-c3 sap dung o buoc sau). 5. `sudo systemctl stop shadow-c3`, ghi moc gio. 6. Sim TUAN TU
(1 JVM/lan): (i) T170 OFF-verify (cong muc 6a) — fail thi DUNG, bat lai shadow-c3 ngay, bao
MASTER; (ii) RA12; (iii) RA14. 7. `sudo systemctl start shadow-c3`, ghi moc gio, verify active +
log sach (0 loi -2014, -2015 IP-whitelist binh thuong). 8. Tinh u1-u5 (muc 5) — per-nam
2021-2025 + toan ky cho ca 5 tag, ve duong cong breadth-vs-UW theo up-gate {1.0(R), 1.2(RA12),
1.4(RA14)}. 9. Viet `docs/RESULT_REGIME_UPDOWN.md` voi phan quyet CHI cho RA12 (RA14 chi mo ta,
khong phan quyet — nhac lai luat cam muc 1). 10. Commit code+docs nhanh `module` (KHONG push).
11. Don tag `OFFCHECK` tam (giu `printDone.csv`/`sim.out` cua RA12/RA14 chinh va cua T170/R/T100
da co), khong dung wfo_ds_x1_2021 (dataset dung chung, khong xoa).

Sua thiet ke luc thuc thi (neu co) -> ghi ro TRUOC/SAU khi thay ket qua tuong ung, khong hoi to.
OFF khong byte-identical => DUNG, bao MASTER, khong ep chay tiep.

## 8. Y NGHIA — theo khung MASTER (khong doi)

- **THANG** (RA12 dat u1-u5) => breadth CO giai duoc bang regime-gate up/down dung muc => shadow
  paper song song >=1 thang truoc khi ban doi incumbent; day la tin lon (huong dau tien trong 4
  vong pacing/regime/dd-throttle/regime-updown cho ket qua duong) — nhan manh trong bao cao.
- **NULL** => up-gate chat de cuu 2025 thi mat breadth, hoac van vo UW => cung voi 3 co che
  reactive truoc (TASK B, Buoc 3 dd-throttle) va Buoc 2 (up=1.0) => DONG huong breadth long-only
  bang dieu chinh gate/pacing don gian theo BTC-macro, ghi vao `power_wall.md`, chuyen TASK D
  (alpha moi) hoac admission-filter theo tin hieu noi tai (khong phai macro BTC).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
