#!/usr/bin/env python3
"""Balloon & Tusk error report from Sentry.

Reads a Sentry auth token from ~/.config/bt-marketing/sentry_token
Needs scopes: org:read, project:read, event:read
Usage: python3 sentry_report.py [days]   (default 14)
"""
import json, os, sys, urllib.request, urllib.parse, collections
from datetime import datetime, timedelta, timezone

TOKEN_PATH = os.path.expanduser("~/.config/bt-marketing/sentry_token")
BASE = "https://us.sentry.io/api/0"
DAYS = sys.argv[1] if len(sys.argv) > 1 else "14"

if not os.path.exists(TOKEN_PATH):
    sys.exit(f"No token at {TOKEN_PATH} — create one in Sentry, then save it there.")
TOKEN = open(TOKEN_PATH).read().strip()

def get(path, **params):
    url = f"{BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    return json.load(urllib.request.urlopen(req, timeout=30))

orgs = get("/organizations/")
if not orgs:
    sys.exit("Token is valid but sees no organizations — check its scopes.")
org = orgs[0]["slug"]
print(f"Organization: {org}\n")

cutoff = datetime.now(timezone.utc) - timedelta(days=int(DAYS))

for proj in get(f"/organizations/{org}/projects/"):
    slug = proj["slug"]
    # NOTE: statsPeriod only scopes the stats graph — it does NOT filter the
    # list, and "count" is the issue's LIFETIME total. Filter on lastSeen
    # ourselves or long-dead issues get reported as if they fired this week.
    everything = get(f"/projects/{org}/{slug}/issues/",
                     query="is:unresolved", limit=100)
    issues, stale = [], []
    for i in everything:
        last = i.get("lastSeen")
        when = datetime.fromisoformat(last.replace("Z", "+00:00")) if last else None
        (issues if (when and when >= cutoff) else stale).append(i)
    total = sum(int(i.get("count", 0)) for i in issues)
    print(f"=== {slug}: {len(issues)} issue types active in the last {DAYS}d "
          f"({total} lifetime events on those issues)")
    if stale:
        print(f"    ({len(stale)} other unresolved issues had no events in the window: "
              + ", ".join((i.get('title') or '')[:34] for i in stale[:4]) + ")")
    if not issues:
        print("    clean — nothing fired in the window\n"); continue
    for i in sorted(issues, key=lambda x: -int(x.get("count", 0)))[:12]:
        users = i.get("userCount", 0)
        title = (i.get("title") or "")[:72]
        culprit = (i.get("culprit") or "")[:60]
        seen = (i.get("lastSeen") or "")[:16]
        print(f"    {int(i['count']):>5} events  {users:>3} users  last {seen}  {title}")
        if culprit:
            print(f"                              in {culprit}")
        print(f"                              {i.get('permalink','')}")
    print()
