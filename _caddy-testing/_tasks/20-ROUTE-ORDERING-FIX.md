# Route Ordering Fix

**Date:** 2025-11-28
**Status:** ✅ COMPLETE

## Problem
Agent routes are appended at the END of the route list, but wildcard routes (`*.lacny.me`) with `terminal: true` catch requests first and abort them.

**Current order:**
1. `*.lacny.me` (abort, terminal) ← catches `agent-remote.lacny.me`
2. `big-ai_webserver` (`agent-remote.lacny.me`) ← never reached

**Needed order:**
1. `big-ai_webserver` (`agent-remote.lacny.me`) ← specific first
2. `*.lacny.me` (wildcard last)

## Fix
Sort routes by specificity after merging:
1. Specific domains first (e.g., `agent-remote.lacny.me`)
2. Wildcard domains last (e.g., `*.lacny.me`)

## File to modify
`caddy-agent-watch.py` - `merge_routes()` function

## Testing
1. Deploy to test hosts (192.168.0.96, 192.168.0.98, 192.168.0.99)
2. Verify specific routes come before wildcards
3. Test end-to-end routing

## Test Results

**Route ordering verified:**
```
0 multiserver-test_test-another ['api.test.lan']     ← specific
1 multiserver-test_test-specific ['app.test.lan']    ← specific
2 multiserver-test_test-multiserver ['test-multiserver.lan'] ← specific
3 wildcard_test_lan ['*.test.lan']                   ← wildcard (LAST)
```

**End-to-end tests:**
- `app.test.lan` → SUCCESS - Specific route matched before wildcard ✅
- `api.test.lan` → SUCCESS - Another specific route ✅

**Image pushed:** `mcsdodo/caddy-agent:latest`

## Production Deployment
Restart agent on 192.168.0.115 to pull new image and test `agent-remote.lacny.me`
