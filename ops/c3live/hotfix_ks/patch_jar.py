# patch_jar.py <jar_cu> <jar_moi> <entry> <file .class moi>
# Chep NGUYEN BYTE NEN (raw, khong giai nen) moi entry cua jar cu sang jar moi theo DUNG thu tu; CHI entry <entry> thay bang file moi
# (DEFLATED). Khong doc noi dung entry nao khac (chi central directory + byte nen). Khong in noi dung.
import os, struct, sys, zipfile, copy, time
src, dst, ent, newf = sys.argv[1:5]
data = open(newf, 'rb').read()
zin = zipfile.ZipFile(src)
assert ent in zin.NameToInfo, 'thieu entry'
fd = open(dst, 'xb'); os.chmod(dst, 0o600)
zout = zipfile.ZipFile(fd, 'w')
done = 0
for info in zin.infolist():
    if info.filename == ent:
        zi = zipfile.ZipInfo(ent, date_time=time.localtime()[:6])
        zi.compress_type = zipfile.ZIP_DEFLATED; zi.external_attr = info.external_attr; zi.create_system = info.create_system
        zout.writestr(zi, data); done += 1; continue
    zin.fp.seek(info.header_offset)
    h = zin.fp.read(30)
    sig, _, _, _, _, _, _, _, _, nlen, xlen = struct.unpack('<4sHHHHHIIIHH', h)
    assert sig == b'PK\x03\x04', 'local header sai ' + info.filename
    zin.fp.seek(info.header_offset + 30 + nlen + xlen)
    raw = zin.fp.read(info.compress_size)
    ni = copy.copy(info)
    ni.flag_bits &= ~0x08
    ni.header_offset = zout.fp.tell()
    ni.extra = info.extra
    zout.fp.write(ni.FileHeader())
    zout.fp.write(raw)
    zout.filelist.append(ni); zout.NameToInfo[ni.filename] = ni
    zout.start_dir = zout.fp.tell()
zout.close(); fd.close()
print('OK entries=%d thay=%d' % (len(zin.infolist()), done))
