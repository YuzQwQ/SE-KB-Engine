"""Subprocess guard loaded through PYTHONPATH by offline smoke tests."""

import ipaddress
import socket

_ORIGINAL_CONNECT = socket.socket.connect
_ORIGINAL_CREATE_CONNECTION = socket.create_connection


def _is_loopback(address):
    if not isinstance(address, tuple) or not address:
        return True
    host = address[0]
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _guarded_connect(sock, address):
    if not _is_loopback(address):
        raise RuntimeError("External network is disabled for offline smoke tests")
    return _ORIGINAL_CONNECT(sock, address)


def _guarded_create_connection(address, *args, **kwargs):
    if not _is_loopback(address):
        raise RuntimeError("External network is disabled for offline smoke tests")
    return _ORIGINAL_CREATE_CONNECTION(address, *args, **kwargs)


socket.create_connection = _guarded_create_connection
socket.socket.connect = _guarded_connect  # type: ignore[method-assign]
