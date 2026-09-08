# RESULT_5MGRID -- predict net015 luoi 5 phut (model 15 phut), S1 train lai 5 phut

Pre-reg: `docs/PREREG_5MGRID.md`. Diem bang `research/analysis/x1_rates.py X1_C3_FULL_PARITY
X1_C3_5M` (hieu = 5M - FULL_PARITY).

## 0. Lech so voi pre-reg goc -- PHAI neu truoc khi doc ket qua
Pre-reg goc (muc 1, 3-Buoc B) gia dinh net015 se TRAIN LAI toan bo tren GPU o luoi 5 phut.
Trong luc chay, ban train GPU tren Kaggle OOM-kill 2 lan lien tiep (fold dau tien cua 1
fold-block rieng le da vuot RAM container, khong phai loi tich luy qua cac fold). User
truc tiep chi dao doi huong: **"train luoi 15m cung duoc, predict/trade can luoi 5m cho
chuan"** -- tuc la GIU NGUYEN model net015 da train+validate o 15 phut
(`predwf_G015/model_f{0..17}_4h.json`, xac nhan 2026-08-14), chi viet script MOI
(`g015_predict5m.py`) de **predict-only** (khong train) tren feature 5-phut that
(`ds_feat5m`, doc dung 1 file quy/fold de giu RAM ngang muc da an toan o 15 phut). S1 van
train lai day du o 5 phut nhu ke hoach goc (16/16 fold co model, khac loi thieu fold cua
lan truoc). Java **khong doi**: `SIM_ENTRY_GRID_MIN` chi anh huong duong live-trading
(`isTimeProcessData()`), khong dung trong `SimulatorMarketLevelTicker1MStopLoss` offline --
khong can them config key, khong can rebuild jar.

**Buoc A (cong parity pipeline moi, muc 3 pre-reg goc) khong ap dung nguyen van** vi
khong con "pipeline moi train lai net015" de doi chieu -- thay vao do da kiem doc lap:
predict-only tren cung fold (cutoff 20251001) cho phan phoi gan giong het du doan native
15-phut cua CHINH model do (mean 0.504211 vs 0.502939, std 0.130275 vs 0.131125, sai lech
tuong doi <0.3%), va scaling dong dung 3 lan (13,501,678 dong OOS 5-phut vs ~4.5M dong
15-phut cung fold). Peak RAM predict-only 16/16 fold: 8.4GB (Oracle 23GB, an toan). Coi day
la buoc thay the hop le cho Buoc A o pham vi net015; khong co gian doan tuong duong can
kiem cho S1 vi S1 train lai hoan toan (khong phai predict-only).

## 1. Ket qua chinh (equity/CAGR KHONG phai tieu chi)

| tag | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | mMargin | maxDD% | UW | equity |
|---|---|---|---|---|---|---|---|---|---|---|
| X1_C3_FULL_PARITY (15 phut, doi chung) | 2266 | 84.69 | 14.96 | 7.333 | -19.570 | 3.308 | 1945 | -12.46 | 227 | 111,428 |
| X1_C3_5M (5 phut) | 2464 | 82.67 | 16.88 | 7.313 | -19.699 | 2.752 | 1555 | -22.73 | 234 | 74,150 |

Ca hai arm chay cung `TICKER_SOURCE=file` (khop chinh xac config chay cua doi chung, xac
nhan qua log dau `Start with TICKER_SOURCE: file` o ca hai) -- khong con lech nguon ticker
~0.01% nhu ban nhap dau (ban nhap do dung `TICKER_SOURCE=aerospike` mac dinh, da huy va
chay lai).

## 2. Tieu chi rate+CI -- KHONG dat nguong thang, nhung SAI HUONG (xau hon, khong phai tot hon)
Toan cua so 48 thang: **2/5** rate chat luong ngoai CI, CA HAI THEO HUONG XAU cho 5M:
- `win%` -2.016pp (CI [-3.856, -0.263], ngoai CI) -- 5M thang it hon.
- `TSloss%` +1.923pp (CI [0.269, 3.592], ngoai CI) -- 5M an time-stop-loss nhieu hon.
- `mP|SM`, `mP|SL`, `meanP`: trong CI (khong y nghia thong ke), nhung `meanP` -0.556 CI
  [-1.260, 0.071] gan sat 0, huong am.

Tach rieng tung nam (2022/2023/2024/2025): **0/5** rate ngoai CI o ca 4 nam -- giong het
mo hinh K12 (hieu ung "toan cua so" la gop trong so theo n, khong lap lai o nam rieng le).

Quy tac muc 6 pre-reg doi hoi **thang** (khong phai chi khac biet) tren >=2 rate cung
huong ngoai CI. O day 2 rate ngoai CI deu la **THUA**, khong phai thang. => **Khong dat
dieu kien (2), va theo huong nguoc lai voi dieu kien can de thay doi mac dinh.**

## 3. Rang buoc cung -- VI PHAM CA 4 NAM (te hon K12, K12 vi pham 2/4 nam)

| nam | maxDD control | maxDD 5M | chenh | han +3pp | UW control | UW 5M | chenh | han +30d | ret 5M | quy_min 5M |
|---|---|---|---|---|---|---|---|---|---|---|
| 2022 | -12.46 | -15.03 | -2.57 | OK | 64 | 103 | +39 | VI PHAM | 8.97 | -1.17 |
| 2023 | -2.51 | -6.14 | -3.63 | VI PHAM | 45 | 68 | +23 | OK | 42.61 | 7.02 |
| 2024 | -11.36 | -10.23 | +1.13 | OK | 121 | 218 | +97 | VI PHAM | 42.25 | -4.55 |
| 2025 | -10.60 | -22.73 | -12.13 | VI PHAM manh | 227 | 234 | +7 | OK | -3.68 | -5.78 |

2025: nam AM (vi pham rieng "khong nam nao am"), quy_min -5.78% vuot -5% MA doi chung
khong vi pham (quy MOI, vi pham rieng). => **Dieu kien (3) FAIL toan dien o ca 4 nam** --
nam nao cung vi pham it nhat 1 tieu chi, rieng 2025 vi pham ca 3 (maxDD, nam am, quy moi).

## 4. Co che -- nghi ngo cu the, khong chi la "xau hon chung chung"
`STRONG%` (ty le candidate leg-1 duoc gan STRONG, symbolPred<=0.29) TANG 76.5% -> 80.8%:
luoi min hon bat duoc nhieu diem ung vien "manh" hon **ve so luong**, nhung ket qua thuc te
la win% giam + TSloss% tang -- goi y mot phan cac ung vien moi nay la tin hieu yeu/gia
(model net015 van train tren phan phoi 15-phut, du predict tren tick 5-phut moi). Co che
nay lap lai dang da thay o K12 (F1_FLOW_RESULT.md): them ung vien rank-thap -> loang
`mMargin` (1945 -> 1555, -20%) -> DCA leg2+ mat kha nang "cuu lo" dung luc.

Bang chung ro nhat: DCA leg2+ PnL nam 2025 **DAO CHIEU HOAN TOAN** -- doi chung +4,813.2,
5M **-7,031.2** (chenh ~-11,844). Day nhieu kha nang la nguyen nhan chinh khien nam 2025
tu +16.45% (doi chung) thanh -3.68% (5M): margin moi vi the mong hon khi co them nhieu
lenh rank-thap, nen khi thi truong di nguoc, DCA khong con du "dan" de cuu ma con lam sau
them lo. Day la GIA THUYET co co so tu du lieu quan sat duoc, chua phai chung minh nhan
qua day du.

## 5. Buoc A (thay the) -- xem muc 0, KHONG can lap lai o day

## 6. Phan quyet -- NULL, GIU luoi 15 phut
Dieu kien (2) va (3) deu KHONG dat (va (3) that bai toan dien, nang hon ca K12). **Luoi 5
phut KHONG thay luoi 15 phut lam mac dinh cho `X1_C3_FULL`.** Giu nguyen
`WFO_FUNDING_PRED_DIR=predwf_map_s1a2_x1` (15 phut) cho profile san xuat.

GIU LAI toan bo cong cu da xac nhan dung (khong xoa code, theo dung quy tac muc 6 pre-reg):
- `research/pipeline/x1/g015_predict5m.py` (predict-only net015 tren luoi 5 phut, da xac
  thuc doc lap tren fold 20251001)
- S1 5-phut da train (16/16 fold, `pred_s1a2x1_5m.parquet`)
- `profiles/x1_c3_full_5m.properties` (profile luoi 5 phut, da xac minh chi 1 dong khac
  ban goc)

Ket luan: **kien truc predict-mismatch (train 15m / predict 5m) la kha thi ve mat ky
thuat** (khong OOM, so lieu nhat quan voi model goc) nhung **khong sinh loi thuc te tai
thoi diem nay** -- co the vi net015 chua duoc train lai tren phan phoi 5-phut that (chi
predict tren phan phoi 15-phut cu), trong khi S1 da doi phan giai nhung mot minh S1 khong
du de bu lai. Khong tune them tham so nao (K, threshold STRONG, v.v.) tren nen 5-phut sau
ket qua nay.

## 7. Equity -- KHONG phai tieu chi, bao rieng
Doi chung 15 phut: 111,428. 5M: 74,150 (thap hon 33.5%). Huong trung voi rate/rang buoc
cung o tren nhung KHONG dung de phan quyet (luat cung #3 AGENT_RUNBOOK).

## 8. Don dep
`/home/ubuntu/wfo_ds_x1_5m` (4.0G) da xoa sau khi cham diem xong. Cac artifact trung gian
da xoa truoc do trong qua trinh chay (`kg5m`, `g5m_predtest`, `predwf_G015x26_5m` -- deu
tai tao duoc trong vai phut tu code da commit). Giu lai: `predwf_map_s1a2_x1_5m/` (bins
cuoi, 2.6GB) va `pred_s1a2x1_5m.parquet` (S1 output) cho tham chieu/tai su dung sau nay
neu can dieu tra them co che that bai.
