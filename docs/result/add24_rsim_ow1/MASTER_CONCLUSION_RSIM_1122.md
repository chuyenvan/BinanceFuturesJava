# ADD24 R-SIM OW1 - KET LUAN MASTER (2026-11-22 ~21:10 +07)
Prereg 6ee84f17 + ERRATA1-5 (29152e39, bb91e639, 050912ca, 03bb65e0, 0740e790). Luot chinh thuc chay 1 lan 2026-11-22 19:21-19:59 +07,
A1_REF 78f5b74f..., sha 50 file + DEV2W khop danh sach A1 duyet truoc khi chay. A1 kiem ket qua doc lap: A1_ADD24_RSIM_RESULT.md.

## Ket qua: R-SIM = FAIL (giu nguyen; KHONG sua nguong, KHONG chay lai de doi ket luan)
| Chi so | Ket qua | So |
|---|---|---|
| S-G (jar PASS tai moi lenh PREDICT cua sim) | PASS | 67 / 67 quyet dinh, 16 phut |
| S-G2 (so pass gate ca quy 2026Q3, tho) | FAIL | jar 101 vs sim 94; seen +1,18e-3 |
| S-SZ (ham size) | PASS | n 79, max 2,3e-5, 0 N11 |
| S-X (a) ly do thoat | PASS | 79 / 79 |
| S-X (b) phut thoat | FAIL | 65 cung phut + 14 N8 (17,7 % > tran 10 %); 0 cum khong co co che |
| S-X (c) gia thoat | FAIL | TB Delta(rig - sim) +0,528 % (bien +-0,2 %); 0 cum vuot nguong rieng |
| S-D | INSUFFICIENT_CO_PHU | 0 su kien hai phia; rig_extra 0 |
| V-TIER / N10 / cong V / lap dat | PASS | TIER_DIV 0; N10 0; V1-V3, V5, V6, V9; L3, L12 |
Lane do nhay (chi bao cao): 23 / 79 cum doi phut thoat; Delta gia thoat so voi lane chinh TB -0,30 %, p05 -2,75 %, min -6,19 %.

## Phan xu (A1, MASTER dong y)
- S-X: loai (III) - KHAC BIET THAT DA BIET (K8): jar doi stop theo nhip trong nen, sim ap stop moi tu nen sau. Ca 14 cum N8 co REF-nhip xac nhan
  (REF-sim trung phut sim 14/14, REF-nhip trung phut rig 14/14); 10 / 14 roi vao ngay sap 2026-08-22 (nen bien do lon). Voi duong gia quy uoc
  sim (O-L-H-C) gia thoat cua jar >= sim o ca 14 cum (TB +2,96 % tren cac cum do); 65 cum cung phut: TB +0,0035 % (khong lech he thong).
  Khong phai loi harness, khong phai loi jar. Tran N8 10 % va bien +-0,2 % (MASTER chot tu cua so DEV quy 2: 6,1 % / +0,07 %) bi vuot o quy 3.
  FAIL theo chu la DUNG; khong co can cu errata.
- S-G2: 7 pass du deu ngay 08-22 va deu nam trong khoang sim con giu chinh symbol do (6 do rig thoat som 1 phut theo K8, 1 do thu tu su
  kien); 3 654 dong seen du do rig khong khoi tao 2 cum sim con mo luc 07-01 (GUA, BICO, leg 0 ngay 06-25) => loi HARNESS (trang thai giu
  ban dau) + day chuyen K8; khong thay bang chung gate quyet dinh khac tren dong chung. Gia thuyet "sau 09-16 rig khong bam sim" cua MASTER SAI.
  Co the errata + chay lai (bao ca hai luot) nhung KHONG doi duoc ket luan chung.

## He qua theo prereg s10
ADD24 = FAIL (R-SIM) => KHONG pilot theo luat da ghi; khong tune; khong doi tieu chi. Moi buoc tiep (vd do K8 tren lenh that; mo hinh hoa nhip
trong nen trong sim) phai la prereg MOI. R-LIVE (so voi lenh that, OW2) van chay theo ke hoach sang 2026-11-24 de co bang chung day du, nhung
khong doi ket luan FAIL cua R-SIM. Quyet dinh pilot thuoc owner sau khi MASTER trinh du so.

## Y nghia (khong phai ket luan thong ke)
- Phan vao lenh (gate, size) cua jar trung backtest tren quy 3. Phan thoat KHAC backtest o ~18 % cum vao ngay bien dong manh: jar thoat som
  ~1 phut tai stop da nang. Dau cua tac dong gia phu thuoc thu tu gia trong nen (khong biet): quy 3 lane chinh +0,53 %, lane do nhay
  +0,53 - 0,30 ~ +0,23 % so voi sim; cua so DEV quy 2: +0,07 % / ~-0,84 %. => con so backtest khong chuyen 1:1 sang bot that vao ngay sap.
- Uoc tinh "14-23 %/nam" MASTER dua owner luc 15:40 (tu quy 2) KHONG vung - da dinh chinh voi owner 20:25.
