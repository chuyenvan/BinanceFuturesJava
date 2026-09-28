import re, sys, statistics
L = sys.argv[1] if len(sys.argv) > 1 else "/home/ubuntu/shadow_c3/app/logs/full.log"
ts_re = re.compile(r'^(\d{2}/\d{2}/\d{4}) (\d{2}:\d{2}:\d{2}\.\d{3}) INFO  \[([^\]]+)\] ([^:]+): (.*)$')

def to_ms(d, t):
    dd, mm, yy = d.split('/')
    h, m, s = t.split(':')
    return int(h)*3600000 + int(m)*60000 + int(round(float(s)*1000)) + 0  # same day only; fine

ticks = []
cur = None
def close(c):
    if c and c.get('start') is not None and c.get('finish') is not None:
        ticks.append(c)

with open(L, 'r', errors='ignore') as f:
    for line in f:
        m = ts_re.match(line)
        if not m: continue
        d, t, thr, cls, msg = m.groups()
        if thr != 'pool-1-thread-1': continue
        ms = to_ms(d, t)
        if msg.startswith('Start check level change'):
            close(cur); cur = {'start': ms}
            continue
        if cur is None: continue
        if msg.startswith('Read ticker from Aerospike'): cur['read'] = ms
        elif msg.startswith('Btc ticker size'): cur['btc'] = ms
        elif msg.startswith('Check level market'): cur['lvl'] = ms
        elif msg.startswith('Market level change'): cur['mkt'] = ms
        elif msg.startswith('[S1] nap OI'): cur['s1oi'] = ms
        elif msg.startswith('[S1] score'): cur['s1'] = ms
        elif msg.startswith('[MAP] tick='): cur['map'] = ms
        elif msg.startswith('[GATE]'): cur['gate'] = ms
        elif msg.startswith('Predict: '): cur['pred'] = ms
        elif msg.startswith('Finish check level change'): cur['finish'] = ms; close(cur); cur = None
close(cur)

def pc(k): 
    v=[x[k] for x in ticks if x.get(k) is not None and x.get('start') is not None]
    return v

# Only ticks that fully reached all markers
full = [x for x in ticks if all(x.get(k) is not None for k in ('start','read','btc','lvl','mkt','s1','map','gate','pred','finish'))]
sel  = [x for x in full if x.get('gate') is not None]
print("ticks parsed:", len(ticks), "| full (all markers):", len(full))

def d(x,a,b): return x[b]-x[a]

phases = [
    ('prep: START->btc(read1000min+rates)', lambda x: d(x,'start','btc')),
    ('levelcalc: btc->CheckLevel',          lambda x: d(x,'btc','lvl')),
    ('level->MarketLevelChange',            lambda x: d(x,'lvl','mkt')),
    ('SELECTOR: mkt->S1score(funding+S1)',  lambda x: d(x,'mkt','s1')),
    ('net015map: S1score->MAP',             lambda x: d(x,'s1','map')),
    ('gateLoop: MAP->GATE',                 lambda x: d(x,'map','gate')),
    ('writes: GATE->Predict',               lambda x: d(x,'gate','pred')),
    ('tail: Predict->Finish',               lambda x: d(x,'pred','finish')),
    ('TOTAL: START->Finish',                lambda x: d(x,'start','finish')),
]
print("\n% -32s %8s %8s %8s" % ("phase", "median", "mean", "p90"))
for name, fn in phases:
    vals = sorted(fn(x) for x in sel)
    med = statistics.median(vals); mean = sum(vals)/len(vals)
    p90 = vals[int(0.9*(len(vals)-1))]
    print("%-32s %8d %8.0f %8d" % (name, med, mean, p90))

tot = [d(x,'start','finish') for x in sel]
heavy = [d(x,'mkt','pred') for x in sel]   # funding+S1+net015+gate+writes
print("\n%% 'dat' (mkt->Predict) over TOTAL: %.1f%%" % (100*sum(heavy)/sum(tot)))
fund_s1 = [d(x,'mkt','s1') for x in sel]
print("%% selector(mkt->S1score) over TOTAL: %.1f%%" % (100*sum(fund_s1)/sum(tot)))
