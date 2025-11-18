#!/usr/bin/env python3
"""
Unit tests for Phase 1 features: numbered labels and multiple domains
"""

import re

DOCKER_LABEL_PREFIX = "caddy"

def parse_labels_test(labels):
    """Test version of parse_container_labels logic"""
    route_configs = {}

    # Find all numbered and non-numbered caddy labels
    for label_key, label_value in labels.items():
        if not label_key.startswith(DOCKER_LABEL_PREFIX):
            continue

        # Match: caddy_N or caddy_N.directive or caddy or caddy.directive
        match = re.match(f"^{re.escape(DOCKER_LABEL_PREFIX)}(?:_(\\d+))?(?:\\.(.+))?$", label_key)
        if not match:
            continue

        route_num = match.group(1) or "0"  # Default to "0" for simple labels
        directive = match.group(2) or ""  # Empty string for base domain label

        if route_num not in route_configs:
            route_configs[route_num] = {}

        if not directive:
            # Base label: caddy or caddy_N
            route_configs[route_num]['domain'] = label_value
        else:
            # Directive label: caddy.reverse_proxy or caddy_N.reverse_proxy
            route_configs[route_num][directive] = label_value

    return route_configs

def test_numbered_labels():
    """Test: Numbered labels create separate routes"""
    labels = {
        "caddy_0": "test-0.local",
        "caddy_0.reverse_proxy": "test-numbered:8080",
        "caddy_1": "test-1.local",
        "caddy_1.reverse_proxy": "test-numbered:8081",
    }

    routes = parse_labels_test(labels)

    assert len(routes) == 2, f"Expected 2 routes, got {len(routes)}"
    assert "0" in routes, "Route 0 not found"
    assert "1" in routes, "Route 1 not found"
    assert routes["0"]["domain"] == "test-0.local"
    assert routes["0"]["reverse_proxy"] == "test-numbered:8080"
    assert routes["1"]["domain"] == "test-1.local"
    assert routes["1"]["reverse_proxy"] == "test-numbered:8081"

    print("[PASS] test_numbered_labels")

def test_multiple_domains():
    """Test: Multiple comma-separated domains"""
    labels = {
        "caddy": "test-a.local, test-b.local",
        "caddy.reverse_proxy": "test-multi:9000",
    }

    routes = parse_labels_test(labels)

    assert len(routes) == 1, f"Expected 1 route, got {len(routes)}"
    assert "0" in routes, "Route 0 not found"
    assert routes["0"]["domain"] == "test-a.local, test-b.local"

    # Parse multiple domains
    domains = [d.strip() for d in routes["0"]["domain"].split(',')]
    assert len(domains) == 2, f"Expected 2 domains, got {len(domains)}"
    assert "test-a.local" in domains
    assert "test-b.local" in domains

    print("[PASS] test_multiple_domains PASSED")

def test_backward_compatibility():
    """Test: Simple labels still work (backward compatible)"""
    labels = {
        "caddy": "simple.local",
        "caddy.reverse_proxy": "simple:3000",
    }

    routes = parse_labels_test(labels)

    assert len(routes) == 1, f"Expected 1 route, got {len(routes)}"
    assert "0" in routes, "Route 0 not found (simple labels should default to 0)"
    assert routes["0"]["domain"] == "simple.local"
    assert routes["0"]["reverse_proxy"] == "simple:3000"

    print("[PASS] test_backward_compatibility PASSED")

def test_mixed_labels():
    """Test: Mix of simple and numbered labels"""
    labels = {
        "caddy": "simple.local",
        "caddy.reverse_proxy": "simple:3000",
        "caddy_1": "numbered.local",
        "caddy_1.reverse_proxy": "numbered:4000",
    }

    routes = parse_labels_test(labels)

    # Simple label should be route 0, numbered should be route 1
    assert len(routes) == 2, f"Expected 2 routes, got {len(routes)}"
    assert routes["0"]["domain"] == "simple.local"
    assert routes["1"]["domain"] == "numbered.local"

    print("[PASS] test_mixed_labels PASSED")

def test_high_numbered_labels():
    """Test: High numbers like caddy_10, caddy_111"""
    labels = {
        "caddy_10": "ten.local",
        "caddy_10.reverse_proxy": "ten:1000",
        "caddy_111": "onehundred.local",
        "caddy_111.reverse_proxy": "hundred:1111",
    }

    routes = parse_labels_test(labels)

    assert len(routes) == 2, f"Expected 2 routes, got {len(routes)}"
    assert "10" in routes
    assert "111" in routes
    assert routes["10"]["domain"] == "ten.local"
    assert routes["111"]["domain"] == "onehundred.local"

    print("[PASS] test_high_numbered_labels PASSED")

def test_multiple_domains_with_numbered():
    """Test: Multiple domains with numbered labels"""
    labels = {
        "caddy_0": "a.local, b.local, c.local",
        "caddy_0.reverse_proxy": "abc:8000",
        "caddy_1": "x.local, y.local",
        "caddy_1.reverse_proxy": "xy:9000",
    }

    routes = parse_labels_test(labels)

    assert len(routes) == 2

    # Route 0 - 3 domains
    domains_0 = [d.strip() for d in routes["0"]["domain"].split(',')]
    assert len(domains_0) == 3
    assert set(domains_0) == {"a.local", "b.local", "c.local"}

    # Route 1 - 2 domains
    domains_1 = [d.strip() for d in routes["1"]["domain"].split(',')]
    assert len(domains_1) == 2
    assert set(domains_1) == {"x.local", "y.local"}

    print("[PASS] test_multiple_domains_with_numbered PASSED")

def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("Phase 1 Feature Tests")
    print("=" * 50)

    tests = [
        test_numbered_labels,
        test_multiple_domains,
        test_backward_compatibility,
        test_mixed_labels,
        test_high_numbered_labels,
        test_multiple_domains_with_numbered,
    ]

    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"[FAIL] {test.__name__} FAILED: {e}")
            return False

    print("=" * 50)
    print("[PASS] All Phase 1 tests PASSED!")
    print("=" * 50)
    return True

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
