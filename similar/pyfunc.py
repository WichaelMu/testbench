import sys
from functools import reduce
from functional import seq
import json

def exec ():
	f = open ("payloads/similar-courses-collapsed.json")
	d = json.load (f)
	hits = d["hits"]["hits"]
	
	result1 = seq (hits) \
		.map (lambda r: r["inner_hits"]["latest"]["hits"]["hits"]) \
		.reduce (lambda l, r: l + r) \
		.map (lambda s: s["_source"])
	result2 = seq (hits) \
		.map (lambda x: { "M" : x["_score" ] })
	result = seq (result1.zip (result2)) \
		.map (lambda p: { **p[1], **p[0] }) \
		.to_list ()
	cs = seq (result2).map (lambda x:x["M"]).to_list()
	print (result)

if (__name__ == "__main__"):
	exec ()
	sys.exit(0)
