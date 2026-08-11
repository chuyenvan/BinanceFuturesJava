"""Reader DÙNG CHUNG cho dữ liệu TOOL1 (40 feature) — đọc được CẢ BA định dạng.

    *.t1c.gz  -> T1C2 (MỚI NHẤT, 2026-08-08): như T1C1 nhưng có thêm wideMask (int64 LE ngay sau
                 stepMin); cột nào bật bit thì lưu int32 (4*R byte, byte-split 4 stream) thay vì
                 int16. Lý do: 3 cột thật (f20 fundingRateTrend range/IQR=2175, f24 fundingSum24h
                 =1319, f26 volumeZCoin =1575) có IQR cực nhỏ quanh 0 nhưng đuôi rất xa nên bước
                 lượng tử int16 quá thô, sai số 1.0e-2..1.7e-2 IQR (ngưỡng 5e-3). log1p KHÔNG cứu
                 được (đo thật). Writer tự quyết theo TỪNG CHUNK: range/IQR > 640 -> int32.
    *.t1c.gz  -> T1C1 (TASK-251): columnar + quantize int16 + byte-split + delta,
                 LITTLE-ENDIAN. Sinh bởi Tool1ColSink.java. VẪN ĐỌC ĐƯỢC (dataset cũ trên Kaggle).
    *.bin.gz  -> row-major float32 BIG-ENDIAN (CŨ): dtype [("ts",">i8"),("sym",">i2"),("f",">f4",40)]
                 itemsize 170. Giữ để đọc lại dataset cũ mà không phải re-export.
    *.bin     -> như trên nhưng không nén.

VÌ SAO ĐỔI (số đo THẬT trên 1.176.470 record quý 2024Q2, không suy đoán):
    row-major float32 sau gzip = 105.96 B/record
    T1C1            sau gzip =  27.97 B/record   -> giảm 3.79 lần quota Kaggle
Sai số lượng tử hoá xấu nhất 0.0038 IQR của cột. Kaggle tính quota private dataset theo BẢN NÉN
NỘI BỘ (≈gzip) nên chỉ có cách giảm ENTROPY THẬT mới ăn quota — nén sẵn không giúp gì.

CÁCH DÙNG (khớp chữ ký cũ để thay đúng 1 dòng đọc file):
    # CŨ:  a = read_bin(TOOL1_GLOB, TOOL1_DT, 170, grid_filter=True)
    # MỚI: a = read_tool1(TOOL1_GLOB, grid_ms=GRID_MS)
    from tool1_col import read_tool1
    a = read_tool1(".../ff_*.t1c.gz")
    a["ts"], a["sym"], a["f"][:, 7]     # y hệt structured array cũ

Trả về numpy structured array dtype [("ts","<i8"),("sym","<i2"),("f","<f4",40)] — CÙNG TÊN TRƯỜNG
với định dạng cũ (chỉ khác endianness của bộ nhớ, trong suốt với mọi phép numpy/pandas). Muốn
DataFrame cột ts/symId/f0..f39 thì dùng read_tool1_df().

BỎ QUA FILE ".part*": đó là file job export ĐANG GHI DỞ — glob khớp phải nó sẽ ném
gzip.BadGzipFile/EOFError ngẫu nhiên (bài học từ label protobuf, xem funding_label_pb.py).
"""

import glob as _glob
import gzip
import logging
import os
import struct

import numpy as np

log = logging.getLogger(__name__)

# --- hằng số định dạng T1C1/T1C2: PHẢI khớp Tool1ColSink.java, đừng sửa 1 bên ---
MAGIC_V1 = b"T1C1"
MAGIC_V2 = b"T1C2"
MAGICS = (MAGIC_V1, MAGIC_V2)
MAGIC = MAGIC_V2         # magic mà writer HIỆN TẠI sinh ra
SENTINEL = -32768        # ô NaN/Inf, cột int16
QOFFSET = 32000.0        # q = round((v-lo)*scale - 32000)
WIDE_SENTINEL = -2147483648   # ô NaN/Inf, cột int32 (Integer.MIN_VALUE)
WIDE_QOFFSET = 2.1e9          # q = round((v-lo)*scale - 2.1e9)
N_COLS_EXPECT = 40

# Header T1C1: magic(4) + rowCount(4) + nCols(4) + baseMs(8) + stepMin(4)
_HDR = struct.Struct("<4siiqi")
# Header T1C2: y hệt + wideMask(8) ngay SAU stepMin
_HDR_V2 = struct.Struct("<4siiqiq")

# dtype tương thích ngược với reader cũ (tên trường y hệt, chỉ đổi endianness bộ nhớ)
TOOL1_DT = np.dtype([("ts", "<i8"), ("sym", "<i2"), ("f", "<f4", N_COLS_EXPECT)])

# dtype định dạng CŨ trên đĩa (big-endian, 170 B/record)
LEGACY_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])
LEGACY_ITEMSIZE = 170


def _read_raw(path):
    """Đọc file, tự giải nén nếu đuôi .gz. Trả bytes."""
    with open(path, "rb") as f:
        raw = f.read()
    if path.endswith(".gz"):
        raw = gzip.decompress(raw)
    return raw


def _decode_t1c(raw, path=""):
    """Giải mã chuỗi chunk T1C1/T1C2 (đã giải nén gzip) -> structured array TOOL1_DT.

    Mỗi chunk TỰ MÔ TẢ nên 1 file trộn lẫn chunk T1C1 và T1C2 vẫn đọc đúng (trường hợp nối byte
    file part cũ với part mới).
    """
    parts = []
    pos = 0
    n = len(raw)
    while pos < n:
        if n - pos < _HDR.size:
            raise ValueError("%s: còn %d byte thừa ở cuối, không đủ 1 header chunk — file hỏng "
                             "hoặc bị cắt giữa chừng" % (path, n - pos))
        magic = raw[pos:pos + 4]
        if magic not in MAGICS:
            raise ValueError("%s: magic sai tại offset %d (%r, chờ %r) — không phải file T1C "
                             "hoặc file hỏng" % (path, pos, magic, MAGICS))
        if magic == MAGIC_V2:
            if n - pos < _HDR_V2.size:
                raise ValueError("%s: header T1C2 bị cắt cụt tại offset %d" % (path, pos))
            _, row_count, n_cols, base_ms, step_min, wide_mask = _HDR_V2.unpack_from(raw, pos)
            pos += _HDR_V2.size
        else:
            _, row_count, n_cols, base_ms, step_min = _HDR.unpack_from(raw, pos)
            wide_mask = 0
            pos += _HDR.size
        if n_cols != N_COLS_EXPECT:
            raise ValueError("%s: nCols=%d, reader này chỉ hỗ trợ %d (thứ tự cột khoá theo "
                             "ExportFeaturesForPythonTool.convertFeaturesToArray)"
                             % (path, n_cols, N_COLS_EXPECT))

        # colMeta: (lo, scale) float64 LE cho từng cột
        meta = np.frombuffer(raw, dtype="<f8", count=2 * n_cols, offset=pos)
        pos += 16 * n_cols
        lo = meta[0::2]
        scale = meta[1::2]

        # dTidx / dSym: int32 CÓ DẤU (dTidx âm khi sang symbol mới)
        d_tidx = np.frombuffer(raw, dtype="<i4", count=row_count, offset=pos)
        pos += 4 * row_count
        d_sym = np.frombuffer(raw, dtype="<i4", count=row_count, offset=pos)
        pos += 4 * row_count
        t_idx = np.cumsum(d_tidx.astype(np.int64))
        sym = np.cumsum(d_sym.astype(np.int64))

        out = np.empty(row_count, dtype=TOOL1_DT)
        out["ts"] = base_ms + t_idx * (step_min * 60_000)
        out["sym"] = sym.astype(np.int16)

        for j in range(n_cols):
            if (wide_mask >> j) & 1:
                # --- cột WIDE (int32): 4 stream byte liên tiếp, cao -> thấp ---
                b3 = np.frombuffer(raw, dtype=np.uint8, count=row_count, offset=pos)
                b2 = np.frombuffer(raw, dtype=np.uint8, count=row_count, offset=pos + row_count)
                b1 = np.frombuffer(raw, dtype=np.uint8, count=row_count, offset=pos + 2 * row_count)
                b0 = np.frombuffer(raw, dtype=np.uint8, count=row_count, offset=pos + 3 * row_count)
                pos += 4 * row_count
                d = ((b3.astype(np.uint32) << np.uint32(24))
                     | (b2.astype(np.uint32) << np.uint32(16))
                     | (b1.astype(np.uint32) << np.uint32(8))
                     | b0.astype(np.uint32)).view(np.int32)
                # cumsum WRAPAROUND mod 2^32 — cùng lý do như int16: hiệu 2 ô liền nhau (ô NaN
                # = -2^31 cạnh ô +2.1e9) tràn int32, chỉ mod-2^32 mới phục hồi đúng.
                q = np.cumsum(d.astype(np.int64))
                q = ((q + 0x80000000) & 0xFFFFFFFF) - 0x80000000
                v = (q.astype(np.float64) + WIDE_QOFFSET) / scale[j] + lo[j]
                v = v.astype(np.float32)
                v[q == WIDE_SENTINEL] = np.nan
                out["f"][:, j] = v
                continue

            hi_b = np.frombuffer(raw, dtype=np.uint8, count=row_count, offset=pos)
            pos += row_count
            lo_b = np.frombuffer(raw, dtype=np.uint8, count=row_count, offset=pos)
            pos += row_count
            # ghép byte cao/thấp -> delta int16 (byte-split ngược lại)
            d = ((hi_b.astype(np.uint16) << 8) | lo_b.astype(np.uint16)).astype(np.int16)
            # cumsum PHẢI theo số học int16 WRAPAROUND (writer dùng (short) cast, không clamp):
            # hiệu 2 ô liền nhau có thể tới ±64768 (ô NaN = -32768 cạnh ô +32000) nên chỉ mod-65536
            # mới phục hồi đúng. Cộng trong int64 rồi ép về [-32768, 32767] chính là phép đó.
            q = np.cumsum(d.astype(np.int64))
            q = ((q + 32768) & 0xFFFF) - 32768

            v = (q.astype(np.float64) + QOFFSET) / scale[j] + lo[j]
            v = v.astype(np.float32)
            v[q == SENTINEL] = np.nan
            out["f"][:, j] = v

        parts.append(out)

    if not parts:
        return np.empty(0, dtype=TOOL1_DT)
    return parts[0] if len(parts) == 1 else np.concatenate(parts)


def _decode_legacy(raw, path=""):
    """Giải mã định dạng CŨ row-major float32 big-endian 170 B/record."""
    if len(raw) % LEGACY_ITEMSIZE != 0:
        raise ValueError("%s: %d byte không chia hết %d — file cũ hỏng hoặc ghi dở"
                         % (path, len(raw), LEGACY_ITEMSIZE))
    a = np.frombuffer(raw, dtype=LEGACY_DT)
    return a.astype(TOOL1_DT)      # đổi về little-endian, giữ nguyên giá trị


def _is_t1c(path, raw):
    """Nhận diện định dạng theo MAGIC trong NỘI DUNG (T1C1 hay T1C2); đuôi file chỉ là gợi ý."""
    if raw[:4] in MAGICS:
        return True
    if path.endswith(".t1c.gz") or path.endswith(".t1c"):
        raise ValueError("%s: tên file là .t1c nhưng 4 byte đầu là %r, không phải %r"
                         % (path, raw[:4], MAGICS))
    return False


def resolve_files(path_or_glob):
    """Khai triển glob, LOẠI file .part* đang ghi dở. Trả list đường dẫn đã sort."""
    if any(ch in path_or_glob for ch in "*?["):
        files = sorted(_glob.glob(path_or_glob, recursive=True))
        parts = [f for f in files if ".part" in os.path.basename(f)]
        if parts:
            log.warning("Bỏ qua %d file .part đang ghi dở (job export chưa xong): %s",
                        len(parts), [os.path.basename(f) for f in parts[:4]])
            files = [f for f in files if ".part" not in os.path.basename(f)]
    else:
        files = [path_or_glob]
    if not files:
        raise FileNotFoundError("Không thấy file Tool1 hoàn chỉnh nào khớp: %s "
                                "(job export có thể đang chạy)" % path_or_glob)
    return files


def read_tool1(path_or_glob, grid_ms=None):
    """Đọc 1 file hoặc glob nhiều file Tool1 -> structured array [("ts"),("sym"),("f",40)].

    Args:
        path_or_glob: đường dẫn 1 file, hoặc glob (vd ".../ff_*.t1c.gz"). Trộn lẫn định dạng
                      cũ/mới trong cùng glob VẪN chạy được — mỗi file tự nhận diện theo magic.
        grid_ms: nếu đặt, chỉ giữ record có ts % grid_ms == 0 (thay cho `grid_filter` cũ).
                 None = giữ hết.
    """
    files = resolve_files(path_or_glob)
    parts = []
    n_t1c = 0
    for fp in files:
        raw = _read_raw(fp)
        if _is_t1c(fp, raw):
            a = _decode_t1c(raw, fp)
            n_t1c += 1
        else:
            a = _decode_legacy(raw, fp)
        if grid_ms:
            a = a[(a["ts"] % grid_ms) == 0]
        parts.append(a)
    out = parts[0] if len(parts) == 1 else np.concatenate(parts)
    log.info("read_tool1: %d record từ %d file (%d T1C1/T1C2 / %d legacy) | %s",
             len(out), len(files), n_t1c, len(files) - n_t1c, os.path.basename(files[0]))
    return out


def read_tool1_df(path_or_glob, grid_ms=None):
    """Như read_tool1 nhưng trả pandas.DataFrame cột: ts, symId, f0..f39."""
    import pandas as pd
    a = read_tool1(path_or_glob, grid_ms=grid_ms)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    F = np.asarray(a["f"], dtype=np.float32)
    for j in range(F.shape[1]):
        df["f%d" % j] = F[:, j]
    return df


def meta(path):
    """Đọc metadata chunk ĐẦU TIÊN của 1 file .t1c.gz mà không giải mã hết dữ liệu."""
    raw = _read_raw(path)
    if not _is_t1c(path, raw):
        return {"format": "legacy-bin", "records": len(raw) // LEGACY_ITEMSIZE}
    if raw[:4] == MAGIC_V2:
        _, row_count, n_cols, base_ms, step_min, wide_mask = _HDR_V2.unpack_from(raw, 0)
        fmt = "T1C2"
    else:
        _, row_count, n_cols, base_ms, step_min = _HDR.unpack_from(raw, 0)
        wide_mask = 0
        fmt = "T1C1"
    return {"format": fmt, "rows_in_first_chunk": row_count, "n_cols": n_cols,
            "base_ms": base_ms, "step_min": step_min, "raw_bytes": len(raw),
            "wide_cols": [j for j in range(n_cols) if (wide_mask >> j) & 1]}
