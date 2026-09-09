# PREREG_GATEDYN — gate p15 DONG theo phan vi truot (rolling percentile), muc tieu: phan bo lenh deu giua cac quy

Viet TRUOC khi chay bat ky sim nao. Khong sua sau khi thay ket qua.
Yeu cau user 2026-09-09 10:02: *"gate thi truong dang fix cung 0.008 thi phai co cach nao check
phan vi roi lam gate nay dong de phan bo lenh deu hon giua cac quy. thu nghiem va toi uu no."*

## 0. Van de do duoc (chot truoc khi chay)
Gate hien tai dung nguong CO SO cung `SIM_MIN_MOMENTUM_15M=0.008` (nhan he so theo symbolPred
trong `AIRejectFilter.checkSignalDynamic`). Do `predReturn15M` drift theo thoi gian, ty le thoi
gian gate mo dao dong manh giua cac quy (do tren `wfo_gate_pred.csv`, moc 15m, p15>=0.008):
**2023Q3 = 0.5% vs 2026Q1 = 96.4% (chenh ~193x)**; median p15 0.0034 (2023Q3) -> 0.0101 (2026Q1).
=> so lenh/quy mat can bang (X1_C3_FULL_PARITY: min 76 / max 461 lenh, std 153.8 tren 8 nua-nam).
Day la phi-dung cua model gate (drift), KHONG phai tin hieu thi truong doi.

## 1. Co che — da co san trong code (nhom B4, KHONG rebuild jar)
`GateRollingThreshold.java` (commit c1785b9, da tai lap): thay nguong co so 0.008 bang **phan vi
truot**: nguong(t) = percentile `pct` cua predReturn15M trong cua so NUA MO `[t-W, t)` (chi dung
du lieu truoc t, khong nhin truoc), mau tren luoi 15m, bang gio->nguong cap nhat moi gio, truy
van `floorEntry`. Phan nhan he so theo symbolPred KHONG doi. Key qua `Cfg` (profile, khong env):
`SIM_GATE_ROLLING_PCT` (0..1; khong khai bao = TAT = hanh vi cu byte-identical),
`SIM_GATE_ROLLING_DAYS` (mac dinh 90).

## 2. Pham vi
- Nen: **X1_C3_FULL 48 thang** (2022-01-01..2025-12-31), gate p15 **33-feature goc** (quyet dinh
  GATEFEAT: giu nguyen 33 features), bins `predwf_map_s1a2_x1`, `TICKER_SOURCE=file`.
- DOI CHUNG: `X1_C3_FULL_PARITY` (md5 printDone `2478e90d…`, equity 111,428, n=2,266) — chay lai
  tren cung dataset/jar de so sanh cung nen (tool parity noi bo).
- KHAC B4: B4 chay nen C2b CU (30 thang, engine con bug B1/B2/B3, metric equity, NULL). Pre-reg
  nay: nen C3_FULL engine DA SUA + metric chinh la DO DEU phan bo lenh/quy. Khong phai tune tiep
  B4 tren cung khong gian.
- KHONG chay qua 2025-12-31, KHONG doc 2026. KHONG sua code Java (chi profile copy).
- KHONG sua bins, KHONG dung duong OI moi, KHONG chay Kaggle.

## 3. Thiet ke — 3 bien the (quota 3, khong them sau khi thay so)
Profile copy tu `x1_c3_full.properties`, chi them 2 key rolling, window 90d (B4 da xac nhan 90d
hieu luc; 180d khong tot hon):

| run | SIM_GATE_ROLLING_PCT | y nghia | tag |
|---|---|---|---|
| GD_p88 | 0.88 | gate mo ~12% thoi gian (gan muc trung binh hien tai) | X1_C3_FULL_GD88 |
| GD_p92 | 0.92 | gate mo ~8% | X1_C3_FULL_GD92 |
| GD_p96 | 0.96 | gate mo ~4% (chat nhat) | X1_C3_FULL_GD96 |

Muc tieu chon day nay: p88 ~ giu tong so lenh ngang parity, p96 ~ giong B4 rg96 de tham chieu.
Window 90d co dinh (khong quet window — quota danh cho pct).

## 4. Tieu chi (chot TRUOC)
**PRIMARY — muc tieu user (do deu):** giam do lech phan bo lenh giua cac quy so voi parity, do
bang **CV = std/mean so lenh theo QUY (16 quy 2022Q1..2025Q4) va min-quy** tren `printDone.csv`
(`time_start_format` -> quy):
- DAT neu: CV giam >= 20% tuong doi so voi parity **VA** min-quy khong thap hon parity qua 20%
  (khong hy sinh quy ngheo de lam dep so).
- Bao cao rieng: std, min/max quy, tong n, equity (KHONG phai tieu chi).

**RANG BUOC (giu chat luong — khong duoc hy sinh):** cac rate chat luong tren TOAN cua so khong
xau ngoai CI so voi parity (khuon K12/GATEFEAT, CI block 72h x1.21): `win%`, `TSloss%`,
`mean(profit|SM)`, `mean(profit|SL)`, `meanP`. Neu bat ky rate nao xau ngoai CI -> bien the do
LOAI (khong duoc chon), bat ke CV co dep.
**RANG BUOC CUNG:** maxDD <= 15% tung nam (so voi parity tung nam, khong xau hon +3pp),
khong nam nao am (parity: 2025 +16.45%), khong quy moi nao < -5% ma parity khong co.

**QUY TAC QUYET DINH:** chon bien the DAT PRIMARY va PASS het rang buoc, co CV thap nhat. Neu
khong bien the nao PASS het -> NULL, giu gate 0.008, bao cao do lech con lai + ly do. Khong chon
bien the khi chi nhin equity.

## 5. Quy trinh
1. Build dataset 1 lan: `ExportWfoDataset` WFO_SET_PRED=ai_pred_market_gate_wfo (33f goc) +
   WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2_x1 -> `wfo_ds_x1_gd` (xoa sau khi cham).
2. Chay parity lai (`X1_C3_FULL_PARITY_R` tren dataset moi) de so sanh cung nen.
3. Chay 3 bien the tuan tu (1 slot JVM), profile copy `x1_gd88/92/96.properties`.
4. Cham: parity noi bo (md5), x1_rates.py (rate + CI), script CV/min-quy (muc 6).
5. Ghi `docs/RESULT_GATEDYN.md`, commit. Xoa dataset tam.

## 6. Cong cu cham do deu (viet truoc khi chay)
`research/analysis/gd_evenness.py <tag>...`: doc printDone.csv, nhom theo quy (yyyyQn tu
`time_start_format`), in n/quy, std, mean, CV, min-quy, tong n, equity cuoi; so voi parity.
