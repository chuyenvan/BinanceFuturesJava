# So md5 tung entry .class (jar vs thu muc classes HOAC jar vs jar). Entry co the chua key (theo TEN) KHONG doc: chi so CRC/size tu central directory.
import hashlib, os, re, sys, zipfile
KEYRX = re.compile(r'^com/binance/(chuyennd/config/PrivateConfig|client/impl/BinanceApiInternalFactory|chuyennd/client/ClientSingleton|chuyennd/client/BinanceFuturesClientSingleton|chuyennd/c3live/client/C3LiveClient|chuyennd/c3live/canary/C3LiveCanary)(\$[^/]*)?\.class$')
a = zipfile.ZipFile(sys.argv[1]); other = sys.argv[2]
isjar = other.endswith('.jar') or os.path.isfile(other)
b = zipfile.ZipFile(other) if isjar else None
an = {i.filename: i for i in a.infolist()}
bn = {i.filename: i for i in b.infolist()} if b else None
same = diff = key_same = key_diff = 0; dl = []; miss = []
names = sorted(an) if b else sorted(n for n in an if n.startswith('com/binance/') and n.endswith('.class'))
for n in names:
    if KEYRX.match(n):
        if b is None: continue
        if n in bn and an[n].CRC == bn[n].CRC and an[n].file_size == bn[n].file_size: key_same += 1
        else: key_diff += 1; dl.append('KEYENTRY_CRC ' + n)
        continue
    if b is not None:
        if n not in bn: miss.append(n); continue
        if an[n].is_dir(): continue
        x = hashlib.md5(a.read(n)).hexdigest(); y = hashlib.md5(b.read(n)).hexdigest()
    else:
        p = os.path.join(other, n)
        if not os.path.exists(p): miss.append(n); continue
        x = hashlib.md5(a.read(n)).hexdigest(); y = hashlib.md5(open(p, 'rb').read()).hexdigest()
    if x == y: same += 1
    else: diff += 1; dl.append('%s %s -> %s' % (n, x, y))
extra = sorted(set(bn) - set(an)) if b else []
print('ENTRIES_A=%d SAME=%d DIFF=%d MISSING_IN_B=%d EXTRA_IN_B=%d KEYENTRY_CRC_SAME=%d KEYENTRY_CRC_DIFF=%d' % (len(names), same, diff, len(miss), len(extra), key_same, key_diff))
for d in dl: print('DIFF ' + d)
for m in miss[:20]: print('MISS ' + m)
for e in extra[:20]: print('EXTRA ' + e)
