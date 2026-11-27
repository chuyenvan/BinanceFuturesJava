# BUNDLE_REBUILD - tao lai chuyendinh/sim-x1-2021-bundle (PRIVATE, slug cu), 2026-11-27
Ly do: owner xoa tay dataset (2026-11-26) -> smoke f2b chet "MISSING /kaggle/input/**/manifest.txt". Owner dong y dung lai.
Theo docs/runbooks/KAGGLE_SIM_48M.md muc 2. Stage: ~/claude_master/w3/levz_kg/bundle_stage (file lon = HARDLINK, file nho = copy).
Khong sua repo, khong git, khong build, khong push kernel.

## Nguon tung file (24 file; ban cu 25)
| file | nguon Oracle | cach |
|---|---|---|
| market.bin, pred.bin, funding.bin | /home/ubuntu/wfo_ds_x1_2021/ | hardlink |
| manifest.txt | /home/ubuntu/wfo_ds_x1_2021/manifest.txt | copy |
| predict_wf_*.bin x16, BINS_SHA256 | /home/ubuntu/predwf_map_s1a2_x1/ | hardlink / copy |
| exchange_info_pin.json | /home/ubuntu/java/exchange_info_pin.json | copy |
| prof_x1_gs_t170.properties | `git show ba3d7ba:profiles/x1_gs_t170.properties` (~/src; ban luc tao bundle cu - file da doi commit 37fd5024 2026-09-24, chi comment) | ghi moi |
| config.properties | ~/src configs/sim_dev_file_2021.properties (commit cuoi d94f64fa 2026-09-12) + THAY dong AEROSPIKE_HOST_226 = dong trong config kernel r1-a3-a1 (161.118.212.3) | ghi moi |
| sim.jar | **BO** (khac ban cu 1 file) | xem duoi |

sim.jar: kernel_sim `jar = f1(IN + "/**/sim.jar")` chi can CO it nhat 1 sim.jar trong moi input; voi jar_ds=sim-jar-tsx (moi run r1-a3 / f2b)
kernel lay jar tu sim-jar-tsx (dataset con nguyen). => bundle khong can sim.jar. Run nao KHONG dat jar_ds ma dung bundle nay se fail
"MISSING sim.jar" (tot hon chay jar sai).

## Kiem
- config.properties stage vs out/r1-a3-a1/config.properties (ban kernel da ghi): cung thu tu key; chi khac key AEROSPIKE_HOST
  (kernel NOWRITE242 doi gia tri do thanh 127.0.0.1 trong ban WORK - dung nhu log r1-a3-a1). Kich thuoc 2463 vs 2457 khop phep doi do.
- BINS_SHA256: sha256sum -c 16/16 OK. funding.bin md5 8e57d900d5c54c744bfcaf5c9b27fc93 == manifest md5_funding.
  pred.bin md5 5dd6bb4c3f98d89d58770005c0001526 == manifest == GA.PRED0_MD5; market.bin md5 4ab691c908fc545c26243e8328d7a0a6 == manifest.
- Nhay cam: khong file *.env/key/kaggle.json/PrivateConfig; ten key chua key|secret|token|pass trong config/prof/manifest: KHONG co;
  khong chuoi BEGIN RSA/OPENSSH/apiKey.
- Ngay: manifest marketRange=1609459200000..1767225540000 (2021-01-01 .. 2025-12-31 23:59 UTC); leakFreeFrom 2021-07-01;
  bins fold cuoi predict_wf_20251001 (maxFoldSpanDays 91 -> <= 2025-12-31). Khong co du lieu >= 2026-10-01.
- Khac ban cu: thieu sim.jar; prof lay tu ba3d7ba; cac file con lai cung nguon runbook ghi (kich thuoc funding 4,446,783,456 trung runbook).

## md5 / kich thuoc stage
- BINS_SHA256 1440 65460b5c590a790f3ab730611019670a
- config.properties 2463 2f92f9a59df2146634fa97009fcf78b1
- exchange_info_pin.json 303926 5a815948d8909ea5b9615b28e28b53da
- funding.bin 4446783456 8e57d900d5c54c744bfcaf5c9b27fc93
- manifest.txt 3017 a8e0153066b2eefb6934e5fde4316ed9
- market.bin 51096244 4ab691c908fc545c26243e8328d7a0a6
- pred.bin 40004164 5dd6bb4c3f98d89d58770005c0001526
- predict_wf_20220101.bin 29220204 sha256 beb9b1ad87920837...
- predict_wf_20220401.bin 30472260 sha256 46d74f5af24408e2...
- predict_wf_20220701.bin 30898868 sha256 bba6d88bb55475d2...
- predict_wf_20221001.bin 32308276 sha256 52de4cf735a16ff3...
- predict_wf_20230101.bin 33867782 sha256 5fbeeb76e766885a...
- predict_wf_20230401.bin 39639730 sha256 9dc70e5173d55e56...
- predict_wf_20230701.bin 43461964 sha256 f34966245a911853...
- predict_wf_20231001.bin 49736934 sha256 48d51834bb718cac...
- predict_wf_20240101.bin 55665792 sha256 ac1fadf2c90836a8...
- predict_wf_20240401.bin 58669104 sha256 82d1b979cabda8aa...
- predict_wf_20240701.bin 61431266 sha256 863667cac9d14abe...
- predict_wf_20241001.bin 70705752 sha256 16438f3c14c601d8...
- predict_wf_20250101.bin 79463878 sha256 48a252b72affab2e...
- predict_wf_20250401.bin 91930410 sha256 ad86905ee22532c0...
- predict_wf_20250701.bin 106035774 sha256 a7fafe546f1ccb94...
- predict_wf_20251001.bin 117457860 sha256 618de63cdbd5db9b...
- prof_x1_gs_t170.properties 3317 5e78404b57aaaa550650f107425b812a

## Lenh da chay
- stage: ln (hardlink) / cp -p / git show ba3d7ba:profiles/x1_gs_t170.properties / python thay 1 dong AEROSPIKE_HOST_226.
- dataset-metadata.json {"title":"sim-x1-2021-bundle","id":"chuyendinh/sim-x1-2021-bundle",CC0}
- nohup nice python3 ~/claude_master/w3/levz_kg/upload_bundle.py > bundle_upload.log : kiem chua ton tai -> KaggleApi().dataset_create_new(
  folder=stage, public=False, dir_mode="skip") -> cho dataset_status == ready -> so dataset_list_files voi stage.
Poll: tr '\r' '\n' < ~/claude_master/w3/levz_kg/bundle_upload.log | grep -aE 'Upload successful|^20' | tail

## KET QUA LAN 1 (2026-11-27 06:29): THAT BAI - het quota
dataset_create_new upload xong 24 file (337 s) nhung Kaggle tu choi: "The size of your files is 5.093 GB, it exceeds the 4.037 GB of
remaining private quota". Dataset KHONG duoc tao (datasets files -> 403). Da dung script poll. Stage giu nguyen (hardlink, ~0 dia them).
Lua chon cho MASTER/owner: (1) giai phong them >= ~1.1 GB quota private roi chay lai y nguyen:
  cd ~/claude_master/w3/levz_kg && PATH=$HOME/.local/bin:$PATH nohup nice python3 upload_bundle.py > bundle_upload.log 2>&1 &
(2) bundle rut gon bo funding.bin (4.14 GB): duong A3 (r1-a3 / f2b) tu dung funding.bin moi tu bins (A3_BLOCK: s3_funding.py
-> a3_ds/funding.bin, chi symlink market.bin + pred.bin tu bundle) nen khong doc funding.bin bundle; NHUNG run khong-A3 (T170, x1 cu)
se hong. Can MASTER quyet; parity NEN se xac nhan.

## KET QUA LAN 2 (2026-11-27 06:50): DA TAO - ban RUT GON (MASTER chon huong 2)
Stage ~/claude_master/w3/levz_kg/bundle_stage_reduced (hardlink tu bundle_stage, BO funding.bin, THEM README_REDUCED.txt):
24 file, 1,022,381,580 bytes. Script upload_bundle_reduced.py (= upload_bundle.py doi duong dan stage), log bundle_upload_reduced.log.
dataset_create_new -> status Ok (106 s), dataset_status ready 06:50:48; PRIVATE (public=False). So 24/24 file kich thuoc trung stage
(dataset_list_files co phan trang 20 file/trang: script bao LECH 4 file cuoi do chi doc trang 1; doc trang 2 bang page_token -> 4 file
con lai trung: predict_wf_20250401/0701/1001.bin, prof_x1_gs_t170.properties). datasets list --mine: 274MB (nen).
Doc code truoc khi day (funding.bin khong duoc dung tren duong A3):
- tools/kaggle_sim.py (~/src, sha 7edd7945): 159 DS=dirname(manifest); 173 PREDWF; [A3_BLOCK chen sau 173] -> DS=a3_ds;
  177-238 khoi market_ds (chi khi CFG market_ds, f2b/r1-a3 khong dat) la cho duy nhat khac nhac funding.bin (189); 235 WFO_DATA_DIR=DS.
  Khong co buoc nao kiem danh sach file / kich thuoc bundle so voi manifest.
- r1_a3_driver.py A3_BLOCK: symlink CHI market.bin, pred.bin vao a3_ds; s3_funding.py (research/pipeline/x1/s3_funding.py:168 chi doc
  market.bin) ghi a3_ds/funding.bin moi; manifest a3_ds viet lai md5_funding moi.
- gate_ablation_driver.py PATCH_BLOCK (seed S7, chen tai kaggle_sim.py:241 SAU A3): symlink market.bin/funding.bin tu DS = a3_ds (funding moi).
- Log r1-a3-a1 xac nhan Java dung ds=/kaggle/working/a3_ds.
Ban nay THIEU funding.bin + sim.jar so voi ban cu: run khong-A3 se khong chay. Quota private con lai uoc ~3.0 GB (4.037 - 1.02).
