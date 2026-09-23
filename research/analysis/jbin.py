"""Streaming parser for Java ObjectOutputStream ticker bins.

Format: TreeMap<Long minute_ms, Map<String symbol, KlineObjectSimple>>
(KlineObjectSimple = com.binance.chuyennd.object.sw.KlineObjectSimple, fields
 startTime:Long, priceOpen, maxPrice, minPrice, priceClose, totalUsdt: float).

Pure Python (no JVM).  Used because reading the corpus needs no Java run.
API: iter_minutes(bytes) -> generator of (minute_ms, {symbol: (o,h,l,c,v)})
"""
import struct

TC_NULL = 0x70
TC_REFERENCE = 0x71
TC_CLASSDESC = 0x72
TC_OBJECT = 0x73
TC_STRING = 0x74
TC_ARRAY = 0x75
TC_CLASS = 0x76
TC_BLOCKDATA = 0x77
TC_ENDBLOCKDATA = 0x78
TC_RESET = 0x79
TC_BLOCKDATALONG = 0x7A
TC_EXCEPTION = 0x7B
TC_LONGSTRING = 0x7C
TC_PROXYCLASSDESC = 0x7D
TC_ENUM = 0x7E

BASE = 0x7E0000
PRIM = {'B': 1, 'C': 2, 'D': 8, 'F': 4, 'I': 4, 'J': 8, 'S': 2, 'Z': 1}

KL = 'com.binance.chuyennd.object.sw.KlineObjectSimple'


class Reader(object):
    __slots__ = ('b', 'p', 'h')

    def __init__(self, b):
        self.b = b
        self.p = 0
        self.h = []

    # ---- primitives -------------------------------------------------
    def string(self):
        b = self.b
        t = b[self.p]
        self.p += 1
        if t == TC_STRING:
            n = (b[self.p] << 8) | b[self.p + 1]
            self.p += 2
            s = b[self.p:self.p + n].decode('utf-8', 'replace')
            self.p += n
            self.h.append(s)
            return s
        if t == TC_LONGSTRING:
            n = struct.unpack_from('>Q', b, self.p)[0]
            self.p += 8
            s = b[self.p:self.p + n].decode('utf-8', 'replace')
            self.p += n
            self.h.append(s)
            return s
        if t == TC_REFERENCE:
            i = struct.unpack_from('>I', b, self.p)[0] - BASE
            self.p += 4
            return self.h[i]
        raise ValueError('str tag %02x @%d' % (t, self.p - 1))

    def annotations(self):
        b = self.b
        while True:
            t = b[self.p]
            if t == TC_ENDBLOCKDATA:
                self.p += 1
                return
            if t == TC_BLOCKDATA:
                self.p += 2 + b[self.p + 1]
            elif t == TC_BLOCKDATALONG:
                self.p += 5 + struct.unpack_from('>I', b, self.p + 1)[0]
            elif t == TC_RESET:
                self.p += 1
            else:
                raise ValueError('annot tag %02x @%d' % (t, self.p))

    def utf(self):
        """modified-UTF8 with 2-byte length prefix (class/field names) - NO handle."""
        n = (self.b[self.p] << 8) | self.b[self.p + 1]
        self.p += 2
        s = self.b[self.p:self.p + n].decode('utf-8', 'replace')
        self.p += n
        return s

    def classdesc(self):
        b = self.b
        t = b[self.p]
        self.p += 1
        if t == TC_NULL:
            return None
        if t == TC_REFERENCE:
            i = struct.unpack_from('>I', b, self.p)[0] - BASE
            self.p += 4
            return self.h[i]
        if t == TC_PROXYCLASSDESC:
            n = struct.unpack_from('>I', b, self.p)[0]
            self.p += 4
            self.p += 4 * n
            self.p += 8
            d = {'name': '<proxy>', 'fields': (), 'super': None}
            self.h.append(d)
            self.annotations()
            d = dict(d)
            d['super'] = self.classdesc()
            return d
        if t != TC_CLASSDESC:
            raise ValueError('cd tag %02x @%d' % (t, self.p - 1))
        # handle assigned BEFORE name/field strings (java.io.ObjectOutputStream
        # writeNonProxyDesc calls handles.assign(desc) right after the tag byte)
        d = {'name': None, 'fields': (), 'flags': 0, 'super': None}
        self.h.append(d)
        d['name'] = self.utf()
        self.p += 8
        d['flags'] = b[self.p]
        self.p += 1
        nf = (b[self.p] << 8) | b[self.p + 1]
        self.p += 2
        fields = []
        for _ in range(nf):
            tc = chr(b[self.p])
            self.p += 1
            fn = self.utf()
            if tc in 'L[':
                self.string()
            fields.append((fn, tc))
        d['fields'] = tuple(fields)
        self.annotations()
        d['super'] = self.classdesc()
        return d

    # ---- objects ----------------------------------------------------
    def skip_fields(self, desc):
        b = self.b
        while desc is not None:
            for fn, tc in desc['fields']:
                if tc in PRIM:
                    self.p += PRIM[tc]
                else:
                    self.obj()
            desc = desc['super']

    def read_fields(self, desc, tgt):
        """Java order: primitive fields first, then object fields.
        Superclass data (if any) precedes subclass data."""
        b = self.b
        if desc['super'] is not None and desc['super'].get('fields'):
            self.read_fields(desc['super'], tgt)
        for fn, tc in desc['fields']:
            if tc in PRIM:
                raw = b[self.p:self.p + PRIM[tc]]
                self.p += PRIM[tc]
                if tc == 'F':
                    tgt[fn] = struct.unpack('>f', raw)[0]
                elif tc == 'D':
                    tgt[fn] = struct.unpack('>d', raw)[0]
                elif tc == 'Z':
                    tgt[fn] = raw[0] != 0
                else:
                    tgt[fn] = int.from_bytes(raw, 'big', signed=tc not in 'BC')
        for fn, tc in desc['fields']:
            if tc not in PRIM:
                tgt[fn] = self.obj()

    def obj(self):
        b = self.b
        t = b[self.p]
        if t == TC_NULL:
            self.p += 1
            return None
        if t == TC_REFERENCE:
            i = struct.unpack_from('>I', b, self.p)[0] - BASE
            self.p += 4
            v = self.h[i]
            if isinstance(v, tuple) and len(v) == 2 and v[0] == 'OBJREF':
                return v[1]
            return v
        if t == TC_STRING or t == TC_LONGSTRING:
            return self.string()
        if t == TC_OBJECT:
            self.p += 1
            desc = self.classdesc()
            if desc is None:
                return None
            name = desc['name']
            hi = len(self.h)
            self.h.append(None)
            if name == 'java.lang.Long':
                self.p += 8
                v = struct.unpack_from('>q', b, self.p - 8)[0]
                self.h[hi] = ('OBJREF', v)
                if desc['super'] is not None:
                    self.skip_fields(desc['super'])
                return v
            if name == 'java.util.HashMap':
                self.p += 8
                if desc['super'] is not None:
                    self.skip_fields(desc['super'])
                size = 0
                while b[self.p] == TC_BLOCKDATA:
                    n = b[self.p + 1]
                    size = int.from_bytes(b[self.p + 2 + n - 4:self.p + 2 + n], 'big')
                    self.p += 2 + n
                m = {}
                for _ in range(size):
                    k = self.obj()
                    m[k] = self.obj()
                if b[self.p] == TC_ENDBLOCKDATA:
                    self.p += 1
                self.h[hi] = ('OBJREF', m)
                return m
            if name == KL:
                vals = struct.unpack_from('>5f', b, self.p)
                self.p += 20
                st = self.obj()
                v = (st,) + vals
                self.h[hi] = ('OBJREF', v)
                return v
            tgt = {}
            self.read_fields(desc, tgt)
            self.h[hi] = ('OBJREF', tgt)
            return tgt
        if t == TC_ARRAY:
            self.p += 1
            desc = self.classdesc()
            hi = len(self.h)
            self.h.append(None)
            n = struct.unpack_from('>i', b, self.p)[0]
            self.p += 4
            cn = desc['name'] if desc else ''
            if cn[:1] == '[' and cn[1:2] in PRIM:
                sz = PRIM[cn[1]] * n
                vals = b[self.p:self.p + sz]
                self.p += sz
                self.h[hi] = ('OBJREF', vals)
                return vals
            out = [self.obj() for _ in range(n)]
            self.h[hi] = ('OBJREF', out)
            return out
        if t == TC_CLASS:
            self.p += 1
            d = self.classdesc()
            self.h.append(('OBJREF', d))
            return d
        if t == TC_ENUM:
            self.p += 1
            desc = self.classdesc()
            hi = len(self.h)
            self.h.append(None)
            self.obj()
            self.h[hi] = ('OBJREF', None)
            return None
        raise ValueError('obj tag %02x @%d' % (t, self.p))


def iter_minutes(b):
    """Yield (minute_ms, {sym: (o,h,l,c,v)}) for a TreeMap ticker stream."""
    r = Reader(b)
    if b[0:4] != b'\xac\xed\x00\x05':
        raise ValueError('bad stream header')
    r.p = 4
    t = b[r.p]
    if t != TC_OBJECT:
        raise ValueError('top tag %02x' % t)
    r.p += 1
    desc = r.classdesc()
    r.h.append(('OBJREF', 'TREEMAP'))
    _tm = {}
    r.read_fields(desc, _tm)
    size = 0
    while b[r.p] == TC_BLOCKDATA:
        n = b[r.p + 1]
        size = int.from_bytes(b[r.p + 2:r.p + 2 + n], 'big')
        r.p += 2 + n
    for _ in range(size):
        k = r.obj()
        v = r.obj()
        yield k, v
    if r.b[r.p] == TC_ENDBLOCKDATA:
        r.p += 1
