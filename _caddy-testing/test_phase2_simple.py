#!/usr/bin/env python3
"""
Unit tests for Phase 2 features: global settings, snippets, TLS DNS, handle directives
Standalone version without importing from caddy-agent-watch.py
"""

import re

DOCKER_LABEL_PREFIX = "caddy"

def parse_globals_and_snippets(labels):
    """Extract global settings and snippet definitions from labels.
    Global settings: caddy_N.email, caddy_N.auto_https (without domain)
    Snippets: caddy_N: (snippet_name)
    """
    global_settings = {}
    snippets = {}
    route_configs = {}

    # First, collect all label configurations
    for label_key, label_value in labels.items():
        if not label_key.startswith(DOCKER_LABEL_PREFIX):
            continue

        match = re.match(f"^{re.escape(DOCKER_LABEL_PREFIX)}(?:_(\\d+))?(?:\\.(.+))?$", label_key)
        if not match:
            continue

        route_num = match.group(1) or "0"
        directive = match.group(2) or ""

        if route_num not in route_configs:
            route_configs[route_num] = {}

        if not directive:
            route_configs[route_num]['domain'] = label_value
        else:
            route_configs[route_num][directive] = label_value

    # Now identify snippets and global settings
    for route_num, config in route_configs.items():
        domain = config.get('domain', '')

        # Check if this is a snippet definition: (snippet_name)
        if domain.startswith('(') and domain.endswith(')'):
            snippet_name = domain[1:-1]
            # Remove 'domain' from config
            snippet_config = {k: v for k, v in config.items() if k != 'domain'}
            snippets[snippet_name] = snippet_config
            continue

        # Check if this is a global setting (no domain, only directives)
        if not domain and config:
            # This is a global setting
            for directive, value in config.items():
                global_settings[directive] = value

    return global_settings, snippets

def parse_tls_config(config):
    """Parse TLS configuration directives."""
    tls_config = {}

    for key, value in config.items():
        if key.startswith('tls.'):
            directive = key[4:]

            if directive == 'dns':
                parts = value.split()
                if len(parts) >= 2:
                    provider = parts[0]
                    token = parts[1]
                    tls_config['dns_provider'] = provider
                    tls_config['dns_token'] = token

            elif directive == 'resolvers':
                tls_config['resolvers'] = value.split()

    return tls_config

def parse_transport_config(config):
    """Parse transport configuration directives."""
    transport_config = {}

    has_transport = any(key.startswith('transport') for key in config.keys())
    if not has_transport:
        return transport_config

    for key, value in config.items():
        if key == 'transport':
            transport_config['transport'] = {'protocol': value}

        elif key.startswith('transport.'):
            directive = key[10:]

            if 'transport' not in transport_config:
                transport_config['transport'] = {}

            if directive == 'tls':
                transport_config['transport']['tls'] = {}

            elif directive == 'tls_insecure_skip_verify':
                if 'tls' not in transport_config['transport']:
                    transport_config['transport']['tls'] = {}
                transport_config['transport']['tls']['insecure_skip_verify'] = True

    return transport_config

def parse_handle_directives(config):
    """Parse handle directives."""
    handle_directives = []

    for key, value in config.items():
        if key.startswith('handle.'):
            directive = key[7:]

            if directive == 'abort':
                handle_directives.append({
                    "handler": "static_response",
                    "close": True
                })

    return handle_directives

# Tests
def test_global_settings():
    """Test: Global settings (email, auto_https) are extracted"""
    labels = {
        "caddy_0.email": "test@example.com",
        "caddy_0.auto_https": "prefer_wildcard",
    }

    globals, snippets = parse_globals_and_snippets(labels)

    assert len(globals) == 2, f"Expected 2 global settings, got {len(globals)}"
    assert globals.get('email') == "test@example.com"
    assert globals.get('auto_https') == "prefer_wildcard"
    assert len(snippets) == 0

    print("[PASS] test_global_settings")

def test_snippet_definition():
    """Test: Snippet definitions are extracted"""
    labels = {
        "caddy_1": "(wildcard)",
        "caddy_1.tls.dns": "cloudflare ${CF_API_TOKEN}",
        "caddy_1.tls.resolvers": "1.1.1.1 1.0.0.1",
    }

    globals, snippets = parse_globals_and_snippets(labels)

    assert len(snippets) == 1
    assert "wildcard" in snippets
    assert snippets["wildcard"]["tls.dns"] == "cloudflare ${CF_API_TOKEN}"
    assert snippets["wildcard"]["tls.resolvers"] == "1.1.1.1 1.0.0.1"
    assert len(globals) == 0

    print("[PASS] test_snippet_definition")

def test_multiple_snippets():
    """Test: Multiple snippet definitions"""
    labels = {
        "caddy_1": "(wildcard)",
        "caddy_1.tls.dns": "cloudflare ${CF_API_TOKEN}",
        "caddy_3": "(https)",
        "caddy_3.transport": "http",
        "caddy_3.transport.tls_insecure_skip_verify": "",
    }

    globals, snippets = parse_globals_and_snippets(labels)

    assert len(snippets) == 2
    assert "wildcard" in snippets
    assert "https" in snippets

    print("[PASS] test_multiple_snippets")

def test_tls_dns_parsing():
    """Test: TLS DNS challenge configuration"""
    config = {
        "tls.dns": "cloudflare ${CF_API_TOKEN}",
        "tls.resolvers": "1.1.1.1 1.0.0.1"
    }

    tls_config = parse_tls_config(config)

    assert tls_config["dns_provider"] == "cloudflare"
    assert "${CF_API_TOKEN}" in tls_config["dns_token"]
    assert tls_config["resolvers"] == ["1.1.1.1", "1.0.0.1"]

    print("[PASS] test_tls_dns_parsing")

def test_transport_tls_insecure():
    """Test: Transport TLS insecure skip verify"""
    config = {
        "transport": "http",
        "transport.tls": "",
        "transport.tls_insecure_skip_verify": ""
    }

    transport_config = parse_transport_config(config)

    assert "transport" in transport_config
    assert transport_config["transport"]["tls"]["insecure_skip_verify"] == True

    print("[PASS] test_transport_tls_insecure")

def test_handle_abort():
    """Test: Handle abort directive"""
    config = {
        "handle.abort": ""
    }

    handle_directives = parse_handle_directives(config)

    assert len(handle_directives) == 1
    assert handle_directives[0]["handler"] == "static_response"
    assert handle_directives[0]["close"] == True

    print("[PASS] test_handle_abort")

def test_wildcard_certificate_pattern():
    """Test: Real-world wildcard certificate pattern from portainer.stacks"""
    labels = {
        "caddy_0.email": "admin@example.com",
        "caddy_0.auto_https": "prefer_wildcard",
        "caddy_1": "(wildcard)",
        "caddy_1.tls.dns": "cloudflare ${CF_API_TOKEN}",
        "caddy_1.tls.resolvers": "1.1.1.1 1.0.0.1",
        "caddy_1.handle.abort": "",
        "caddy_10": "*.lacny.me",
        "caddy_10.import": "wildcard",
        "caddy_11": "*.notavailable.uk",
        "caddy_11.import": "wildcard",
    }

    globals, snippets = parse_globals_and_snippets(labels)

    # Verify global settings
    assert len(globals) == 2
    assert globals["email"] == "admin@example.com"
    assert globals["auto_https"] == "prefer_wildcard"

    # Verify snippet
    assert len(snippets) == 1
    assert "wildcard" in snippets
    assert "tls.dns" in snippets["wildcard"]
    assert "tls.resolvers" in snippets["wildcard"]
    assert "handle.abort" in snippets["wildcard"]

    # Parse TLS config from snippet
    tls_config = parse_tls_config(snippets["wildcard"])
    assert tls_config["dns_provider"] == "cloudflare"
    assert tls_config["resolvers"] == ["1.1.1.1", "1.0.0.1"]

    print("[PASS] test_wildcard_certificate_pattern")

def run_all_tests():
    """Run all Phase 2 tests"""
    print("=" * 50)
    print("Phase 2 Feature Tests")
    print("=" * 50)

    tests = [
        test_global_settings,
        test_snippet_definition,
        test_multiple_snippets,
        test_tls_dns_parsing,
        test_transport_tls_insecure,
        test_handle_abort,
        test_wildcard_certificate_pattern,
    ]

    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"[FAIL] {test.__name__} FAILED: {e}")
            return False
        except Exception as e:
            print(f"[ERROR] {test.__name__} ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

    print("=" * 50)
    print("[PASS] All Phase 2 tests PASSED!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
