# KAGGLE_REQUIRED — dataset PHẢI còn (kiểm sau khi owner tự xoá; P1, MASTER 10-15)

Kiểm 2026-10-15 (nguồn: `kaggle datasets list -m`; còn **140** dataset, trước đó 170).

## PHẢI CÒN — ĐÃ KIỂM: CÒN ĐỦ ✓
| slug | ai dùng |
|---|---|
| `vz-kline1m-2023` `vz-kline1m-2024` `vz-kline1m-2025` | VZ lake (E1) |
| `vz-basis1m-2023` `vz-basis1m-2024` `vz-basis1m-2025` | VZ lake (E1) |
| `vz-metrics5m` `vz-funding` | VZ lake (E1) |
| `vz-pilot-202408` | pilot lake |
| `vz-marketdata` | dump Aerospike (B4 parity f=0) |
| `bcast-2020-2021h1-p1` | backcast 2020 (B1) |
| `sim-ho26-bundle` `sim-ho26a-bundle` | sim HO26 |
| `ho4p1-code` `ho4p1-jar-exp` | HO4-P1 |
| `sim-jar-ecost` (sha 246087fb) | ECMEAS entry-cost |
| `wfo-ticker-2021/2022/2023/2024h1/2024h2/2025h1/2025h2` | WFO sim |

## CẦN XÁC MINH THÊM (chưa kết luận — đang làm)
- **Jar nền ECMEAS/HO4 sha `b7c89f09…` và `0944841c…`**: chưa map được sang slug nào trong 140 còn lại ⇒ **có thể ĐÃ BỊ XOÁ**. Nếu mất ⇒ build lại từ commit trong docs + so sha256 (khác ⇒ **BLOCKED**, KHÔNG thay thế).
- **"bundle Vision A/B"** (dataset HO4): chưa xác định slug.
- **Dataset mà template sim hiện hành (K24 + skipFull, `PARITY["ho4p1-c2"]`) khai**: chưa tìm thấy `kernel-metadata.json` chứa `skipFull`/`ho4p1-c2` trong repo.
- Jar dùng bởi `ho4p1_queue` / `ec_parity.py` / `ecm_q.py` / `bcast_sim`.
