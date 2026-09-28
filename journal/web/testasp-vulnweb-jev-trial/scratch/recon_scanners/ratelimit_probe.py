
import time, urllib.request, collections
codes = collections.Counter()
times = []
start = time.time()
for i in range(40):
    t0 = time.time()
    try:
        req = urllib.request.Request("http://testasp.vulnweb.com/", method="GET")
        req.add_header("User-Agent", "recon-ratelimit-probe/1.0")
        with urllib.request.urlopen(req, timeout=15) as r:
            codes[r.status] += 1
    except urllib.error.HTTPError as e:
        codes[e.code] += 1
    except Exception as e:
        codes["ERR:" + type(e).__name__] += 1
    times.append(time.time() - t0)
elapsed = time.time() - start
print("requests:", 40, "elapsed_s: %.2f" % elapsed, "avg_rps: %.1f" % (40/elapsed))
print("status codes:", dict(codes))
print("latency min/avg/max: %.3f / %.3f / %.3f s" % (min(times), sum(times)/len(times), max(times)))
