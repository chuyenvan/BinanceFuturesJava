# PREREG_HO5_A3_2026 - ADDENDUM 3 (CHOT 2026-11-19 22:15 +07, MASTER; van CHUA co con so 2026 nao)

Trang thai luot 3: cong tai lap DAT trung byte (equity 144 003, 3 584 lenh, md5 printDone a11ce5f9, funding -2 490,7257); overlay funding
B1 DAT (sha ee2cd3ba ca 3 ban); P1 DAT (sha 3343e8e7 == ref); P2 dat co dieu kien (ADD2 B2); P3 DAT. Chan: funding_data het sau 2026-07-07
(thang 8: 1 244 ban ghi, thang 9: 0) => Lane L se tinh phi funding = 0 cho gan tron Q3 ma khong bao loi.

## C1. Bo sung funding (F1)
- Duoc phep tai funding rate CONG KHAI (fapi /fapi/v1/fundingRate) 2025-01-01 -> 2026-10-01 ra FILE bang ban fork toi thieu cua
  HistoricalFundingCrawlerLocal: giu nguyen URL, phan trang, parse (float), quy tac merge putAll; BO phan ghi Aerospike. Coi la "cung cong cu".
  KHONG ghi Aerospike, KHONG dung 242, KHONG dung Vision (thieu symbol).
- Cong chong lan (chot truoc khi crawl), tren nam 2025: 100 % moc chung giua snapshot hien co va ban crawl trung nhau, |d| <= 1e-9 so theo
  gia tri float; bao cao so moc thua / thieu moi phia. Khong dat => R5.
- Snapshot v3 = snapshot hien co HOP ban crawl (ban crawl chi BO SUNG moc chua co; moc da co giu nguyen). Sau khi tao v3: chay lai cong tai
  lap s123 (2021-07 -> 2025-12) voi v3: phai van trung md5 printDone a11ce5f9 (v3 khong duoc doi du lieu <= 2025). Khong dat => R5.
- Do phu sau bo sung phai bao cao theo thang 2026-01..09; thang nao < 95 % so symbol TRADING co ban ghi => ghi canh bao trong ket qua Lane L.

## C2. Van DUNG truoc 2026
ADD2 B3 giu nguyen: khong sinh pred/bins 2026, khong chay Lane L cho toi khi MASTER ghi nhan loi duyet mo seal cua owner (addendum ke tiep).
Tai funding cong khai va kiem do phu KHONG phai mo seal (khong nhin hieu suat chien luoc).
