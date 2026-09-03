# MOC SO SANH CHO GS WAVE-1 — DOC TRUOC KHI PHAN TICH

**Diem neo cua vong nay la `id=-1` trong ket qua Kaggle (equity 60395), KHONG phai 60390.**

`60390` la so cua run C2b tren Oracle voi `TICKER_SOURCE=aerospike`. Wave 1 chay tren Kaggle voi
`TICKER_SOURCE=file`. Hai duong doc ticker KHONG bit-exact — da do truc tiep 2026-09-03:

| moi truong | TICKER_SOURCE | equity cuoi |
|---|---|---|
| Oracle | aerospike | 60390 |
| **Oracle** | **file** | **60395** |
| **Kaggle** | **file** | **60395** |

Oracle+file == Kaggle+file (tung dong printDone.csv giong het, PROFILE_HASH `7081c357ca12bdd6`)
=> lech den TU DUONG DOC TICKER, moi truong Kaggle vo can.

Nguyen nhan cu the: dung **1 lenh / 970** khac nhau — FTT BUY vao 2022-11-09 01:00 (giai doan FTX sup).
Duong aerospike cham SL luc 2022-11-14 11:00 (giu 130h); duong file khong cham, lenh song tiep den
loser-time-stop 168h va dong 2022-11-16 01:01. PnL -1084.85 vs -1080.39. Sai lech day len +5 USDT
o cuoi ky = **0.008%**. 8/10 quy khop tro 2 chu so thap phan; 2 quy lech 0.01pp (2022Q4, 2024Q2).

## Hau qua khi phan tich

1. **Phan vi cua C2b** trong 256 mau phai tinh voi `id=-1` (60395 / CAGR DEV-A 27.49%), khong dung 60390.
2. Moi so sanh so hoc giua run Oracle va run Kaggle chi tin duoc toi **~0.01%**. Chenh lech nho hon
   nguong nay KHONG duoc coi la tin hieu.
3. Trong noi bo 256 diem: tat ca cung chay Kaggle + `TICKER_SOURCE=file` => nhat quan, so sanh giua
   cac diem khong bi anh huong.

Bang chung: `/home/ubuntu/java/logs/gs_filetest.log`, `devrun/GS_FILE15/`, `devrun/GS_FILE24/`.
