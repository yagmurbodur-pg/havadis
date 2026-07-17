import json
ids = ['8fe39edf','85cdb4a3','45a4595f','e723c4e7','6f16a999','08ffed92','08f77354','252ccc31','01bb588c','976e25fe','9be1570d','4cd6d663','b82b19a7','f2d4f0d1','d4ca69cf','9d6f1edd','79ed56fa','49d8cb27','61dced22','fd8d69ff','ad18a56b','c599c61e','5f22dfb9','e433f753','ba15284a','d322af2b']
known = set()
with open('veri/haberler.jsonl') as f:
    for line in f:
        line=line.strip()
        if not line: continue
        known.add(json.loads(line)['id'])
for i in ids:
    print(i, 'OK' if i in known else 'MISSING')
