# Multi-Snippet Import Support

**Date:** 2025-11-28
**Status:** IMPLEMENTED

## Problem

Using multiple snippets with comma-separated imports didn't work:

```yaml
caddy.import: wildcard, https  # Looked for snippet named "wildcard, https"
```

Error: "Bad Request - This combination of host and port requires TLS."

## Root Cause

The import logic treated the entire value as a single snippet name instead of parsing multiple comma-separated names.

```python
# Before (buggy)
snippet_name = config['import']  # "wildcard, https" as single name
if snippet_name in snippets:     # Not found!
```

## Fix

**File:** `caddy-agent-watch.py` lines 270-284

Split import value by comma and apply each snippet in order:

```python
# After (fixed)
import_value = config['import']
snippet_names = [s.strip() for s in import_value.split(',')]
merged_config = {}
for snippet_name in snippet_names:
    if snippet_name in snippets:
        merged_config = {**merged_config, **snippets[snippet_name]}
# Route config overrides all snippets
config = {**merged_config, **config}
```

## Usage

Now works correctly:

```yaml
labels:
  caddy: omada.lacny.me
  caddy.import: wildcard, https
  caddy.reverse_proxy: 192.168.0.238:8043
```

Where snippets are defined as:
- `(wildcard)` - Cloudflare DNS challenge for TLS
- `(https)` - Transport TLS with insecure skip verify

## Merge Order

1. First snippet directives
2. Second snippet directives (override first)
3. Route-specific labels (override all snippets)
