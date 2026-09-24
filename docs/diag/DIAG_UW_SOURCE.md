# DIAG_UW_SOURCE - TASK B2 Buoc 1: UW that su den tu dau? (2026-09-21)

Ket qua cho `docs/prereg/PREREG_UW_DIAG.md`. Script: `research/analysis/uw_source.py` (tai dung
`bigdown_struct.py`/`c3_rates.py` NGUYEN VAN). Output day du: `research/analysis/out/uw_source.json`.

## Q1 - Chuoi UW dai nhat: T170 va gate-1.0 KHONG cung mot bien co

| Tag | Chuoi dai nhat | Do dai | Do sau (maxDD trong chuoi) | Trough |
|---|---|---:|---:|---|
| T170 | 2024-04-10 -> 2024-07-10 | 92 ngay | -6.60% | 2024-04-14 |
| T100 (gate 1.0) | 2021-11-16 -> 2022-07-21 | 248 ngay | -16.13% | 2022-05-12 |
| P3 (pacing BD1a) | 2021-11-16 -> 2022-07-21 (Y HET T100) | 248 ngay | -14.28% | 2022-05-12 |

**Phat hien then chot**: chuoi UW dai nhat cua T170 (92 ngay, 2024-Q2) va cua gate-1.0/P3
(248 ngay, 2021-11 -> 2022-07) la **HAI GIAI DOAN LICH SU KHAC HAN NHAU**, cach nhau ~1.5-2 nam.
Trough cua gate-1.0 (2022-05-12) trung ngay voi su sup do UST/LUNA (~2022-05-09/13). Doi chieu
CUNG lich voi T170: trong dung cua so 2021-11-16 -> 2022-07-21, chuoi UW rieng cua T170 (hang #2
trong top-5) chi la 2022-02-27 -> 2022-05-09 (72 ngay) sau **-0.29%** - gan nhu KHONG mat gi.
T170 "song sot" qua chinh giai doan LUNA/bear-2022 ma gate-1.0 vo UW 248 ngay/-16.13%.

## Q2 - Regime BTC trong chuoi UW: gate-1.0 vo dung mot bear thi truong that, T170 thi KHONG

| Chi so (trailing, causal) | T100/P3 (248 ngay, 2021-11-16..2022-07-21) | T170 (92 ngay, 2024-04-10..2024-07-10) |
|---|---:|---:|
| % ngay BTC < MA200 | **89.11%** | 7.61% |
| dd trung binh tu dinh-365d | **-43.96%** | -10.78% |
| dd sau nhat tu dinh-365d | -72.15% | -23.04% |
| ret30 trung binh | -11.42% | -2.61% |
| ret60 trung binh | -16.01% | **+3.71%** (duong!) |
| % ngay ret30 am | 78.63% | 59.78% |
| BTC dau -> cuoi cua so | $60,929 -> $22,553 (**-62.99%**) | $68,743 -> $57,686 (-16.08%) |

**Ket luan Q2**: chuoi UW dai nhat cua gate-1.0/P3 nam **GON TRONG mot bear thi truong da xac
nhan** (BTC duoi MA200 89% so ngay, giam -63% tu dinh, 8 thang lien tuc) - day KHONG phai mot
cu flash-24h (da loai o TASK B) ma la mot **bear-multi-month co cau truc**. Chuoi UW dai nhat cua
T170 (92 ngay, 2024-Q2) nguoc lai **KHONG nam trong bear** theo tieu chi nay (chi 7.6% ngay duoi
MA200, ret60 con DUONG) - day la mot dot dieu chinh/choi ngang nong, khong phai bear that. Hai
UW dai nhat cua hai he thong co CO CHE KHAC NHAU HOAN TOAN, khong so sanh truc tiep duoc - nhung
dieu do CHINH LA cau tra loi: **UW cua gate-1.0 la van de rieng cua bear-multi-month, khong phai
mot dac tinh chung cua "chuoi UW dai" noi chung**.

**Dinh nghia regime de xuat cho Buoc 2 (khac han BD1a)**: `bear-multi-week` = BTC daily-close
duoi MA200-trailing (vd lien tuc >=N ngay hoac ty le >=X% trong cua so truot M ngay) VA/HOAC
`dd_from_peak365 <= nguong am sau (vd -25%)`. Ca hai deu **TRAILING/CAUSAL** (dung duoc real-time,
khong nhin truoc), va khac han BD1a (BTC ret24h<=-5%, flash) - da bi TASK B chung minh KHONG
nham dung muc tieu (t4 FAIL, bd_share P3 > P0).

## Q3 - Kenh giu he duoi nuoc: KHOI LUONG lenh-bien, KHONG PHAI chat luong lenh-bien te hon

Phan loai CHINH XAC (cong thuc EntryGate, khong khoa key) tren T100, trong cua so UW dai nhat:

| Nhom | n TRONG cua so | % dong gop PnL AM trong cua so | ROI TB trong cua so (CI90) | ROI TB NGOAI cua so (CI90) |
|---|---:|---:|---|---|
| **marginal** (chi qua gate 1.0) | **335** (83.5% cua 401) | **95.6%** | -0.24% [-3.30,+2.76] | +1.91% [+1.19,+2.58] |
| core (qua ca gate 1.70) | 33 (8.2%) | 2.6% | -0.45% [-6.17,+3.67] | +6.76% [+3.56,+11.21] |
| unscaled (BIG_DOWN/DCA, khong bi gate) | 33 (8.2%) | 1.7% | +7.94% [+4.91,+9.68] | +6.84% [+2.10,+10.40] |

(P3: cung ty le 335/33/33 - vi P3 chi doi SIZE, khong doi tap admit; ROI% cua marginal/core
trong cua so gan nhu giong het T100, chi khac o pnl_sum tuyet doi do size nho hon.)

**Phat hien then chot**: ROI trung binh moi lenh cua marginal (-0.24%) trong bear **KHONG te hon**
core (-0.45%, thuc ra am hon, tuy CI rong chua tach biet duoc thong ke) - ca hai nhom deu quay tu
duong (+1.9%/+6.8% ngoai cua so) sang gan-0/am TRONG bear, tuc **CA HE THONG (ke ca phan T170
giu) deu bi bear keo xuong nhu nhau ve % ROI**. Cai khac nhau la **SO LUONG**: marginal chiem
83.5% hoat dong trong cua so (cao hon ty trong 79.9% cua no O NGOAI cua so - bear khong lam
marginal it di, ma con CHIEM TY TRONG CAO HON) va vi the **95.6% tong PnL am trong cua so den tu
marginal** don gian vi no dong 10x so luong lenh dong thoi so voi core. Day la **van de KHOI
LUONG/DON BAY VON dong thoi (bao trum), khong phai van de "tin hieu bien la tin hieu te"** -
khop voi phat hien TASK A M7 (ROI lenh bien CI90 hoan toan duong khi tinh CA KY) va TASK A M3
(Sigma-notional/equity T100 = 0.270 trong-bigdown vs T170 0.058, T100 luon chay gan bao hoa).

## Q4 - Dao sau hay khong phuc hoi: KHONG dao sau (holding ngan, exit nhanh) - la CHUM/NAP LAI LIEN TUC o muc phoi nhiem cao

| Chi so (T100, 248 ngay) | Gia tri |
|---|---:|
| % ngay tang / giam (tren ngay co bien dong) | 55.5% / 44.5% |
| do lech chuan return ngay trong cua so vs ca ky | 0.969% vs 0.986% (gan nhu bang) |
| so dot hoi >=3 ngay lien tuc | 7 |
| hoi phuc toi da so voi do sau (max_partial_recovery) | **94.5%** (P3: 98.7%) |
| lenh mo/ngay TRONG cua so vs CA KY | 1.556 vs 1.576 (ty le 0.987 - **gan nhu khong doi**) |
| thoi gian giu lenh TB (ngay), mo TRONG cua so vs NGOAI | 1.80 vs 1.68 (**chi dai hon ~7%**) |

**Ket luan Q4**: day KHONG phai "giu lenh lo khong thoat" (thoi gian giu lenh van rat ngan, ~1.7-1.8
ngay, gan nhu khong doi so voi ca ky - co che stop-loss/trailing van hoat dong binh thuong trong
bear). Cung KHONG phai bien do sut giam bat thuong (do lech chuan return ngay trong cua so THAP
HON ca ky, khong phai mot giai doan "hoang loan" bien dong cao). Dieu xay ra la: he thong **tiep
tuc admit lenh moi voi TOC DO GAN NHU KHONG DOI** (1.556 vs 1.576 lenh/ngay, chi giam 1.3%) trong
suot 8 thang bear, lien tuc THAY THE lenh vua dong (thua, exit nhanh) bang lenh moi (cung it tot
hon trong bear) - mot vong lap "dong-mo lien tuc o muc phoi nhiem cao" hon la mot khoi lo dung
yen. `max_partial_recovery=94.5%` cho thay equity co it nhat 1 lan hoi gan sat dinh cu (chi con
cach ~5.5%) truoc khi rot xuong day sau (2022-05-12) va cuoi cung moi vuot dinh o ngay 248 -
mot chu ky "gan-hoi-phuc-roi-lai-rot" dien hinh cua viec tiep tuc mo vi the moi vao dung luc bear
chua ket thuc, KHONG phai vi giu lenh cu qua lau.
**=> Co che dung la ADMISSION-FILTER (giam SO LUONG/TAN SUAT lenh moi khi dang trong bear-multi-week),
KHONG PHAI exit nhanh hon (da nhanh san) va cung KHONG PHAI rut ngan holding (da ngan san).**

## Q5 - T170 lam gi khac: KHONG giam admission (ca T170 cung khong "nep") - no khac o QUY MO PHOI NHIEM DONG THOI, khong o hanh vi vao/ra

| Chi so T170 | Trong cua so (2021-11-16..2022-07-21) | Ca ky |
|---|---:|---:|
| lenh mo/ngay | 0.698 | 0.686 |
| ty le admission trong-cua-so/ca-ky | **1.017** (CAO HON mot chut, khong thap hon!) | - |
| thoi gian giu lenh TB (ngay) cua lenh mo trong cua so | 1.314 | 1.194 (ca ky) |

**Phat hien bat ngo va quan trong**: T170 **KHONG** giam toc do vao lenh trong giai doan nay (ty
le 1.017x - thuc te con cao hon binh thuong mot chut) va **KHONG** thoat nhanh hon (giu lenh TB
1.31 ngay trong cua so, DAI HON ca ky 1.19 ngay). Tuc la **gate 1.70 khong "tu loc bear" bang
cach dung vao lenh hay thoat som hon trong CHINH giai doan nay** - day la doi chieu Q3: ly do
T170 chi mat -0.29% trong khi gate-1.0 mat -16.13% **KHONG phai vi T170 hanh xu khac trong bear**,
ma vi **T170 CHUA BAO GIO co nhieu lenh dong thoi nhu gate-1.0** (k_bar=3.55 vs T100 gap doi, TASK A
M3: Sigma-notional/equity T170 = 0.058 vs T100 = 0.270 MOI LUC, khong rieng bear) - bear chi lam
LO RA su khac biet quy mo phoi nhiem co san, khong phai T170 co mot "phan xa phong thu" dac biet
kich hoat trong bear. Day la bang chung mot lan nua ung ho co che ADMISSION/EXPOSURE-CAP theo
regime (hien nay T170 dat gate chat MOI LUC nen luon it phoi nhiem; muon breadth o pha up ma van
an toan o pha bear, phai CHU DONG siet admission KHI bear, khong the trong cay vao hanh vi tu
nhien cua he thong nhu no dang co).

## KET LUAN THEN CHOT cho MASTER

**(i) Dinh nghia regime UW cu the, do duoc, causal (nham cho Buoc 2)**: `bear-multi-week` dua tren
BTC daily-close so voi MA200-trailing VA/HOAC `dd_from_peak365-trailing`, KHAC HAN BD1a
(flash-24h da bi loai o TASK B). Bang chung: chuoi UW 248-ngay cua gate-1.0 nam trong mot cua so
co 89% ngay BTC<MA200 va dd trung binh -44% tu dinh-365d (bear LUNA/2022 that su, keo dai 8
thang) - trong khi chuoi UW 92-ngay cua T170 CHI co 7.6% ngay duoi MA200 (khong phai bear).
De xuat cu the: bat co bear-multi-week khi (vd) BTC duoi MA200 lien tuc >= 30-60 ngay HOAC
dd_from_peak365 <= -25%, ca hai tinh TRAILING tai moi ngay (khong nhin truoc).

**(ii) Co che dung la ADMISSION-FILTER (hoac rate-limit/exposure-cap tren SO LUONG lenh dong
thoi), KHONG PHAI exit-nhanh-hon va KHONG PHAI pacing theo SIZE (da bi TASK B loai truc tiep)**.
Bang chung hoi tu tu ca Q3/Q4/Q5: (a) exit da nhanh san (~1.7-1.8 ngay, khong doi trong bear);
(b) toc do admit lenh MOI hau nhu khong doi trong suot 8 thang bear (ca gate-1.0 lan T170, ty le
~0.99-1.02x so ca ky) - nghia la TIN HIEU van phat ra deu, KHONG bi bear lam giam tu nhien; (c)
cai lam gate-1.0 vo UW la SO LUONG lenh-bien dong thoi cao (335 vs 33 core trong cua so, ty trong
marginal con TANG trong bear) nhan voi kich thuoc y het core (khong pacing theo bear) => tong
phoi nhiem/equity vuot xa T170 dung luc thi truong xau nhat. Vi vay dung nen tiep tuc thu pacing
theo size (da NULL o TASK B) hay ky vong exit tu cai thien; can **chu dong giam SO LUONG lenh
duoc admit (hoac tang lai gate ve gan 1.70) khi bear-multi-week dang bat**, dung `RegimeSchedule`/
`GATE_REGIME_ADAPTIVE` da co san trong code (`EntryGate.java`: `REGIME_SCALE_UP=1.00`,
`REGIME_SCALE_NOTUP=1.70`, hien `GATE_REGIME_ADAPTIVE=false`) nhung PHAI thay dinh nghia regime
cua no bang dinh nghia MA200/trailing-dd o (i) (chua kiem tra dinh nghia hien co cua no co khop
khong - can doc `RegimeSchedule.java` truoc khi dung buoc 2).

**(iii) KHONG phai NO-GO tuyet doi - co tin hieu ro rang de tiep tuc, nhung phai sua DUNG DON
BAY**: day KHONG phai truong hop "long-only-trong-bear la thuoc tinh khong tranh duoc" theo nghia
tuyet vong - T170 tu no da chung minh mot he thong long-only CO THE di qua chinh bear 2022 (LUNA)
voi -0.29% neu GIU PHOI NHIEM DONG THOI THAP, ma khong can "tu loc" hanh vi vao/ra dac biet nao
trong bear (Q5). Van de cua gate-1.0 la no GIU PHOI NHIEM CAO **O MOI LUC** (khong rieng bear) va
KHONG co co che tu dieu tiet xuong khi bear den - day la lo hong CO THE va DANG lap bang mot
admission-filter/exposure-cap dieu kien theo regime (i). **GO cho Buoc 2** voi dieu kien: thiet
ke phai nham vao SO LUONG/PHOI NHIEM DONG THOI (khong phai size, khong phai exit), va phai co doi
chung "giam deu khong dieu kien" (nhu P0) de tach bach hieu qua nham-dung-bear khoi hieu qua
giam-chung (bai hoc TASK B). Neu buoc 2 lai cho thay admission-filter theo dung dinh nghia bear-
multi-week nay VAN khong keo duoc UW ve <=200 ma khong giet breadth (u1), thi luc do moi la bang
chung du manh de ket luan NO-GO that su - hien tai CHUA co bang chung do (buoc 1 chi la chan
doan, chua thu co che).

