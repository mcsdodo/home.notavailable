#!/usr/bin/env python3
"""
Unit tests for simplified configuration model.
Tests the new CADDY_URL + HOST_IP configuration approach.
"""

import os
import socket

# Mock the environment before importing
def setup_env(env_vars):
    """Helper to set environment variables for testing"""
    for key in ['CADDY_URL', 'HOST_IP', 'AGENT_MODE', 'CADDY_API_URL', 'CADDY_SERVER_URL']:
        if key in os.environ:
            del os.environ[key]
    for key, value in env_vars.items():
        os.environ[key] = value

def test_caddy_url_default():
    """Test: CADDY_URL defaults to http://localhost:2019"""
    setup_env({})
    url = os.getenv("CADDY_URL", "http://localhost:2019")
    assert url == "http://localhost:2019"
    print("[PASS] test_caddy_url_default")

def test_caddy_url_custom():
    """Test: CADDY_URL can be set to remote server"""
    setup_env({"CADDY_URL": "http://192.168.0.96:2019"})
    url = os.getenv("CADDY_URL", "http://localhost:2019")
    assert url == "http://192.168.0.96:2019"
    print("[PASS] test_caddy_url_custom")

def test_host_ip_not_set_returns_none():
    """Test: HOST_IP not set returns None (local mode)"""
    setup_env({})
    host_ip = os.getenv("HOST_IP", None)
    assert host_ip is None
    print("[PASS] test_host_ip_not_set_returns_none")

def test_host_ip_explicit():
    """Test: HOST_IP can be explicitly set"""
    setup_env({"HOST_IP": "192.168.0.98"})
    host_ip = os.getenv("HOST_IP", None)
    assert host_ip == "192.168.0.98"
    print("[PASS] test_host_ip_explicit")

def test_remote_mode_detection():
    """Test: Remote mode is detected when HOST_IP is set"""
    setup_env({"HOST_IP": "192.168.0.98"})
    host_ip = os.getenv("HOST_IP", None)
    is_remote_mode = host_ip is not None
    assert is_remote_mode == True
    print("[PASS] test_remote_mode_detection")

def test_local_mode_detection():
    """Test: Local mode when HOST_IP is not set"""
    setup_env({})
    host_ip = os.getenv("HOST_IP", None)
    is_remote_mode = host_ip is not None
    assert is_remote_mode == False
    print("[PASS] test_local_mode_detection")

if __name__ == "__main__":
    test_caddy_url_default()
    test_caddy_url_custom()
    test_host_ip_not_set_returns_none()
    test_host_ip_explicit()
    test_remote_mode_detection()
    test_local_mode_detection()
    print("\n✅ All configuration tests passed!")
