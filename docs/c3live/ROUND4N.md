# v1.2/c3-live — Round 4n: A1 R4M MAJ-X — tuổi exchangeInfo theo LÚC TẢI, không theo serverTime

## Lỗi (A1 `~/claude_master/v12/A1_R4M.md`)
`serverTime` trong `/fapi/v1/exchangeInfo` là ẢNH CHỤP CACHE của sàn, không phải đồng hồ: đo trên 242 11-02 09:28 ⇒ 08:01:01
(cũ 88′), hai lần tải liền nhau LÙI 6 ms. Thử lại 09:37–09:38 (R4n, thư mục tạm): `…897 → …892 → …892 → …888`, cũ 97′.
Hậu quả trước R4n: `exinfo_validate.py:44` (đòi serverTime mới hơn file) ⇒ bước 4c "làm mới lần đầu" + cron TRƯỢT ⇒ deploy dừng;
`GatewayFactory.freshFileSource` (R7) loại file khi `now − serverTime > 45′` ⇒ universe STALE ⇒ hậu kiểm rollback.

## Sửa
- **Sidecar** `run/c3live_exchangeInfo.json.meta` = `{"fetchedAtMs","sha256","n_symbols"}`: `fetchedAtMs` = ngay sau khi tải
  (`date +%s%3N`); ghi `.meta.tmp` rồi `mv` NGAY SAU `mv` file (cron `exinfo_refresh_242.sh` + bước chuẩn bị deploy).
- **Validator** (`exinfo_validate.py`): bỏ cổng "serverTime mới hơn"; vẫn đòi có `serverTime > 0` (định dạng raw); lệch đồng hồ máy
  > 24 h ⇒ chỉ thêm `CANH_BAO_serverTime_lech=..h` vào dòng OK. Các cổng khác giữ nguyên (> 100 symbol, onboardDate/underlyingType,
  TradFi ≥ 50, giảm ≤ 10 %).
- **Java R7** `GatewayFactory.freshFileSource`: tuổi = now − fetchedAt; fetchedAt từ sidecar (sha256 + n_symbols PHẢI khớp file;
  sidecar hỏng / thiếu trường / lệch ⇒ ném = fail-closed, R7 giữ snapshot cũ) hoặc mtime khi KHÔNG có sidecar. Ngưỡng 45′ giữ nguyên;
  fetchedAt ở tương lai > 5′ ⇒ từ chối; serverTime lệch > 24 h ⇒ chỉ WARN. `C3LiveRuntime.a1SourceTick` nạp lại khi mtime file
  HOẶC sidecar đổi (cửa sổ file mới + sidecar cũ giữa 2 lệnh `mv` ⇒ lần nạp đó bị từ chối, lần sau nạp đúng).
- **Deploy**: kiểm trước restart (4b) đòi sidecar khớp file (`OK a1_meta_khop` / `FAIL a1_meta_thieu_hoac_lech` ⇒ dừng, env khôi phục);
  `c3live_status.sh` in sidecar. Pin: jar r4n, `EXV_MD5`, `EXR_MD5`.

## Rà serverTime khác trong v1.2 (không đổi)
| chỗ | dùng | kết luận |
|---|---|---|
| `C3LiveClient.syncTime/serverTime` | `/fapi/v1/time` (đồng hồ thật) | không cùng loại |
| `UniverseA1Filter:219` | symbol KHÔNG có trong snapshot mà có dữ liệu sau `serverTime` ⇒ loại | đúng nghĩa "mốc ảnh chụp"; serverTime cũ ⇒ chỉ loại THÊM (fail-closed), không phải cổng tươi |
| `UniverseA1Filter` log / `ExchangeInfo` model | chỉ ghi log | — |
| `C3LiveCanary` KEYCHECK | `/fapi/v1/time`, in ra | — |
| `DryGateway.serverTime` | đồng hồ máy | — |
| `C3LiveRuntime.a1SourceTick` KHẨN | mtime file (= lúc tải) | đúng |
| deploy CHK `exchangeInfo_tuoi` / 4b `a1_file` | mtime / chỉ in serverTime | đúng |

## Kiểm
- Java: `GatewayFactoryFreshR4nTest` (serverTime cũ 88′ vừa tải ⇒ ĐẠT; lùi 6 ms ⇒ ĐẠT; lệch 30 h ⇒ ĐẠT + WARN; tải > 45′ ⇒ CU;
  fetchedAt tương lai ⇒ CU; không sidecar ⇒ mtime; sidecar hỏng / thiếu trường / sha256 lệch / n_symbols lệch / fetchedAt=0 ⇒ từ chối);
  `UniverseA1ListingRefreshTest` cập nhật mtime theo đồng hồ test. mvn 916 test 0 fail (bỏ `Live242WriteGuardTest#mode242_envMissing…`:
  `~/.mavenrc` Oracle đặt guard chống ghi 242).
- Jar `binance-java-sdk-1.2.4.jar_v12_r4n` md5 `fb6711efe473e0e0a5b0ca9813c62af3` (so r4j: `GatewayFactory*`, `C3LiveRuntime`,
  + `UserStreamSoak*` của R4l đã có trong HEAD — chỉ dùng bởi công cụ soak).
- fake242 §25 (thay ca "KHÔNG mới hơn" bằng "chỉ 50 symbol") + §30 (serverTime cũ 88′ / lùi 6 ms / lệch 30 h ⇒ ĐẠT, sidecar khớp,
  lỗi ⇒ giữ file+sidecar cũ, sidecar lệch trước restart ⇒ dừng, deploy XONG có sidecar, status).
- 242 thật: `DRY=1 FORCE=1` DRY PASS; thử làm mới 3 lần trong thư mục tạm (đã xoá): 3/3 rc 0 dù serverTime lùi; bộ kiểm cũ với lần
  tải kế tiếp ⇒ "KHONG moi hon" (tái hiện lỗi), bộ kiểm mới ⇒ ĐẠT.
