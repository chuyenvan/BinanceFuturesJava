#!/usr/bin/env python3
"""ADD24 s3/P5: tao jar STUB tu jar pilot 01cfbb43.
- Chep NGUYEN BYTE NEN (khong giai nen) moi entry theo dung thu tu; CHI cac entry co ten khop KEYRX (8) duoc THAY bang class bien dich
  tu nguon 76134a52 + PrivateConfig STUB (khong key). Khong doc / giai nen noi dung entry key cua jar goc (chi ten + metadata central dir).
- Manifest TEN entry key ghi ra file TRUOC khi tao stub.
- Tat dinh: entry thay dung date_time cua entry goc (metadata), DEFLATED zlib mac dinh => chay lai cho cung md5.
- Khong ghi ban sao jar goc o dau ca; output chi o /dev/shm/add24/jar (chmod 600).
usage: make_stub.py --classes <target/classes> --keys-manifest <json> --out-manifest <json> [--out <jar>]
"""
import argparse, copy, hashlib, json, logging, os, struct, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyrx import KEYRX, ORIG, ORIG_MD5, STUB

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('make_stub')


def fmd5(p, algo='md5'):
    h = hashlib.new(algo)
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--classes', required=True)
    ap.add_argument('--keys-manifest', required=True)
    ap.add_argument('--out-manifest', required=True)
    ap.add_argument('--out', default=STUB)
    a = ap.parse_args()
    if not os.path.abspath(a.out).startswith('/dev/shm/add24/'):
        log.error('TU CHOI: stub chi duoc o /dev/shm/add24/'); return 2
    m = fmd5(ORIG)
    if m != ORIG_MD5:
        log.error('TU CHOI: md5 jar goc %s != %s', m, ORIG_MD5); return 3
    zin = zipfile.ZipFile(ORIG)
    infos = zin.infolist()
    keys = [i.filename for i in infos if KEYRX.match(i.filename)]
    # 1) manifest TEN truoc khi tao
    json.dump({'orig': ORIG, 'orig_md5': m, 'n_entries': len(infos), 'key_entries_by_name': keys, 'n_key': len(keys),
               'rule': KEYRX.pattern}, open(a.keys_manifest, 'w'), indent=1)
    log.info('manifest ten key: %d entry -> %s', len(keys), a.keys_manifest)
    if len(keys) != 8:
        log.error('TU CHOI: so entry key %d != 8 (prereg s3)', len(keys)); return 4
    # class stub cho moi entry key; khong co class key nao THUA (inner moi) trong ban bien dich
    repl = {}
    for k in keys:
        p = os.path.join(a.classes, k)
        if not os.path.isfile(p):
            log.error('TU CHOI: thieu class bien dich %s', k); return 5
        repl[k] = open(p, 'rb').read()
    extra = []
    for root, _, files in os.walk(a.classes):
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), a.classes)
            if KEYRX.match(rel) and rel not in repl:
                extra.append(rel)
    if extra:
        log.error('TU CHOI: class key bien dich khong co trong jar goc: %s', extra); return 6
    if os.path.exists(a.out):
        os.remove(a.out)
    fd = os.fdopen(os.open(a.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb')
    zout = zipfile.ZipFile(fd, 'w')
    done = 0
    for info in infos:
        if info.filename in repl:
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = info.external_attr
            zi.create_system = info.create_system
            zout.writestr(zi, repl[info.filename]); done += 1
            continue
        zin.fp.seek(info.header_offset)
        h = zin.fp.read(30)
        sig, _, _, _, _, _, _, _, _, nlen, xlen = struct.unpack('<4sHHHHHIIIHH', h)
        if sig != b'PK\x03\x04':
            log.error('local header sai %s', info.filename); return 7
        zin.fp.seek(info.header_offset + 30 + nlen + xlen)
        raw = zin.fp.read(info.compress_size)
        ni = copy.copy(info)
        ni.flag_bits &= ~0x08
        ni.header_offset = zout.fp.tell()
        zout.fp.write(ni.FileHeader())
        zout.fp.write(raw)
        zout.filelist.append(ni); zout.NameToInfo[ni.filename] = ni
        zout.start_dir = zout.fp.tell()
    zout.close(); fd.close()
    os.chmod(a.out, 0o600)
    zs = zipfile.ZipFile(a.out)
    st = {i.filename: i for i in zs.infolist()}
    oi = {i.filename: i for i in infos}
    kinfo = []
    for k in keys:
        # chi metadata (CRC/size) cua entry goc - khong doc noi dung
        kinfo.append({'name': k, 'stub_md5': hashlib.md5(zs.read(k)).hexdigest(), 'stub_size': st[k].file_size,
                      'crc_size_equal_orig': (st[k].CRC == oi[k].CRC and st[k].file_size == oi[k].file_size)})
    res = {'stub': a.out, 'stub_md5': fmd5(a.out), 'stub_sha256': fmd5(a.out, 'sha256'), 'stub_bytes': os.path.getsize(a.out),
           'orig_md5': m, 'n_entries': len(zs.infolist()), 'replaced': done, 'key_entries': kinfo,
           'classes_dir': os.path.abspath(a.classes)}
    json.dump(res, open(a.out_manifest, 'w'), indent=1)
    log.info('STUB OK md5=%s replaced=%d', res['stub_md5'], done)
    return 0


if __name__ == '__main__':
    sys.exit(main())
