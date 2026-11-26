# DEV_S2 - huong dan chay (PREREG_LEVZ_S2 @74ec941e; CHOICES_S2.md da duoc MASTER quyet #1-#6; CHUA AUDIT A1)
Thu muc: ~/claude_master/w3/levz_s2/{code,work,out}. Python /usr/bin/python3. B1/B0/tier-1 chi import theo duong dan (khong sua).
Kiem toan ven code: `cd ~/claude_master/w3/levz_s2 && sha256sum -c SHA256SUMS.txt`

## Da chay (du lieu that, duoc phep)
1. Ung vien (~45 s):        `cd ~/claude_master/w3/levz_s2/code && nice -n 15 /usr/bin/python3 cand_s2.py`
2. Bang thoat (~45 s + gop): `cd ~/claude_master/w3/levz_s2/code && nice -n 15 /usr/bin/python3 exits_s2.py all`
   (exits_s2.py check = hoi quy voi exits.npz B1 + ve sinh -> out/exits_s2.json)
3. Test: `cd ~/claude_master/w3/levz_s2/code && for t in b a c c2 d e e2 f g h; do nice -n 15 /usr/bin/python3 test_s2.py $t; done`
   (a ~20 s; b ~5 s; c ~3 phut; c2 ~20 phut; d ~10 s; e ~2 phut; e2 ~30 s; f ~8 phut; g ~1 phut; h ~1 phut) -> out/test_<x>.json

## SAU A1 PASS + ERRATA2 (KHOA --real I_HAVE_A1_PASS). grid / select / report: 1 tien trinh nice -n 15, khong can lock
4. Luoi 2 925 cau hinh x 5 fold (~3-5 phut):
   `cd ~/claude_master/w3/levz_s2/code && nice -n 15 /usr/bin/python3 grid_s2.py --real I_HAVE_A1_PASS`
5. WFO (~10 s):
   `cd ~/claude_master/w3/levz_s2/code && nice -n 15 /usr/bin/python3 select_s2.py --real I_HAVE_A1_PASS`
6. Doi chung 5 tap x 100 luot (~40 s / luot; 500 luot ~5-6 gio 1 tien trinh) - chia shard, moi shard 1 tien trinh nice -n 15, vd 4 shard:
   `cd ~/claude_master/w3/levz_s2/code && nice -n 15 /usr/bin/python3 rand_s2.py --real I_HAVE_A1_PASS --shard 0/4`
   `cd ~/claude_master/w3/levz_s2/code && nice -n 15 /usr/bin/python3 rand_s2.py --real I_HAVE_A1_PASS --shard 1/4`
   `cd ~/claude_master/w3/levz_s2/code && nice -n 15 /usr/bin/python3 rand_s2.py --real I_HAVE_A1_PASS --shard 2/4`
   `cd ~/claude_master/w3/levz_s2/code && nice -n 15 /usr/bin/python3 rand_s2.py --real I_HAVE_A1_PASS --shard 3/4`
   (seed = (SEED, chi so tap, luot) => ket qua khong phu thuoc cach chia; shard nao xong cuoi se ghi out/rand_s2.json khi du 500 part;
   chay lai bat ky lenh shard nao la an toan - resumable. So shard chay DONG THOI <= so CPU duoc cap.)
7. Bao cao (~1 phut):
   `cd ~/claude_master/w3/levz_s2/code && nice -n 15 /usr/bin/python3 report_s2.py --real I_HAVE_A1_PASS`
   -> out/report_s2.json, out/REPORT_S2.md (REF khong cham du nam => in doi chieu B1 theo ERRATA2 F2)
