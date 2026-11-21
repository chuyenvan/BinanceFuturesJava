# OWNER_DECISION_PILOT_1121 - ADD1: bon quyet dinh cua owner cho PILOT (model cu)

Thoi diem: 2026-11-21 ~16:40 +07. Kenh: owner tra loi truc tiep 4 cau hoi cua MASTER trong phien dieu phoi.
Tham chieu: OWNER_DECISION_PILOT_1121.md (c3a9f01b); ra soat ~/claude_master/v12/PILOT_READINESS_1121.md.

## 1. Quyet dinh cua owner (nguyen van lua chon)

| # | Cau hoi | Owner chon |
|---|---------|-----------|
| Q1 | Von c3 khi pilot (tai khoan con) | **10 000 USDT** (nguong dung -40 % giu nguyen) |
| Q2 | Jar chay pilot | **Giu jar hotfix dang live (md5 01cfbb4324fb4a10b615dc3c976ddc73) + va bang script** (lo hong ha von A-02). W3B doi SAU 1-2 tuan pilot, khong doi cung luc voi doi von |
| Q3 | Hai dieu kien cong pilot thieu mau: g_exec (73/100 lenh vao), g_exit (3/20 lenh thoat); luot doi chieu thang 11 chi co 2-4/12 | **Owner duyet cho qua** (Q4_OWNER). Luat da co giu nguyen: do truot gia xau -> giam nua von |
| Q4 | 242 crash / reboot -> bot tu bat lai va mo lenh moi khong ai duyet | **Cai co che chan mo moi sau reboot**: sau khi may khoi dong lai bot chi quan ly vi the dang co, khong mo moi, toi khi owner chay 1 lenh mo lai. Script cai phai qua audit truoc |

## 2. He qua ky thuat (MASTER)

- Lo trinh (a) cua PILOT_READINESS: T1-T5 + T12b tren worktree moi c3_ops6 -> audit A1 -> MASTER ghim -> owner cai OPS5/OPS6 Oracle -> T9 / T11 (ADD24) -> du 7 ngay micro lien tuc (som nhat 2026-11-26 09:31 +07) -> gate PILOT -> owner chay pilot_on (DRY roi that).
- Q4 them viec T20: co che chan mo moi sau reboot tren 242 (ra soat co che co san, script cai 1 lenh cho owner, test tren moi truong gia, audit A1). Day la dieu kien BAT BUOC truoc pilot_on.
- Q3: gate PILOT ghi ro g_exec / g_exit = Q4_OWNER kem so mau thuc te tai thoi diem tao gate; khong coi la da dat nguong.
- Khong thay doi: moi dieu kien ky thuat khac cua pilot_on; agent chi DOC tren 242; owner chay script da audit.

## 3. CHUA co quyet dinh owner (MASTER chua hoi - phai hoi truoc khi tao gate PILOT)

Ba muc duoi day KHONG duoc coi la da mien. Script tao gate PILOT phai doi tham so mien tuong minh cho tung muc:
- X14 D-04 / D-05: ALT_EW live chua doi chieu voi Vision; X14 tat im lang 30 ngay neu thieu 1 ngay du lieu. Audit 16/11 xep P1 "chan pilot", chua sua.
- B2 (T18): bo dem gate 90 ngay tren live co du lieu xau (q live ~0.0095 vs sim ~0.0075; huong bao thu: it lenh hon), tu troi ra ~28/01.
- C1 (T21): so paper LEGACY-DCA / skipFull day co the chan lenh that.
De xuat cua MASTER (chua phai quyet dinh): mien B2 + C1; X14 chap nhan kem kiem log hang ngay, hoac sua truoc pilot neu re.
