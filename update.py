#!/usr/bin/env python3
"""Fetch two years of Flintshire house sales from HM Land Registry and write data/sales.json.
Run from the repo folder. Exits without writing if the fetch fails or looks wrong."""
import csv, io, json, sys, urllib.request, urllib.parse, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "data"; OUT.mkdir(exist_ok=True)
today = datetime.date.today()
since = datetime.date(today.year - 2, today.month, 1).isoformat()  # month-anchored: data only changes when Land Registry publishes

Q = f'''PREFIX ppd: <http://landregistry.data.gov.uk/def/ppi/>
PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?date ?price ?saon ?paon ?street ?locality ?town ?postcode ?type ?newbuild ?cat WHERE {{
  ?t ppd:propertyAddress ?a ; ppd:pricePaid ?price ; ppd:transactionDate ?date ;
     ppd:propertyType ?type ; ppd:newBuild ?newbuild ; ppd:transactionCategory ?cat .
  ?a lrcommon:district "FLINTSHIRE" .
  OPTIONAL {{ ?a lrcommon:saon ?saon }} OPTIONAL {{ ?a lrcommon:paon ?paon }}
  OPTIONAL {{ ?a lrcommon:street ?street }} OPTIONAL {{ ?a lrcommon:town ?town }}
  OPTIONAL {{ ?a lrcommon:postcode ?postcode }} OPTIONAL {{ ?a lrcommon:locality ?locality }}
  FILTER (?date >= "{since}"^^xsd:date)
}} ORDER BY DESC(?date)'''

req = urllib.request.Request("https://landregistry.data.gov.uk/landregistry/query",
    data=urllib.parse.urlencode({"query": Q}).encode(),
    headers={"Accept": "text/csv", "User-Agent": "DeesideNewsroom/1.0"})
rows = list(csv.DictReader(io.StringIO(urllib.request.urlopen(req, timeout=300).read().decode())))
if len(rows) < 1000:
    sys.exit(f"only {len(rows)} rows back, not writing")

FIX = {"Connahs Quay": "Connah's Quay", "Bryn Y Baal": "Bryn-y-Baal", "Cefn Y Bedd": "Cefn-y-bedd"}
def nice(s):
    s = (s or "").strip().title()
    return FIX.get(s, s)
TYPES = {"detached": "Detached", "semi-detached": "Semi-detached", "terraced": "Terraced",
         "flat-maisonette": "Flat", "otherPropertyType": "Other"}

def address(r):
    saon, paon, street = nice(r["saon"]), nice(r["paon"]), nice(r["street"])
    if paon[:1].isdigit() and street:  # "19 Cestrian Street", not "19, Cestrian Street"
        paon, street = f"{paon} {street}", ""
    return ", ".join(x for x in [saon, paon, street] if x)

sales = []
for r in rows:
    sales.append({"d": r["date"][:10], "p": int(float(r["price"])),
        "a": address(r),
        "pl": nice(r["locality"] or r["town"]), "pc": r["postcode"],
        "t": TYPES.get(r["type"].rsplit("/", 1)[-1], "Other"),
        "n": r["newbuild"] == "true",
        "std": r["cat"].endswith("standardPricePaidTransaction")})
sales.sort(key=lambda s: (s["d"], s["a"], s["p"]), reverse=True)

f = OUT / "sales.json"
new = json.dumps(sales, separators=(",", ":"))
old = None
if f.exists():
    try: old = json.dumps(json.loads(f.read_text())["sales"], separators=(",", ":"))
    except Exception: pass
if new == old:
    print(f"{len(sales)} sales, no change")
else:
    f.write_text(json.dumps({"updated": today.isoformat(), "sales": sales}, separators=(",", ":")))
    print(f"{len(sales)} sales since {since}, written")
