import pytest
from app.services.download_safety import validate_download_url, is_private_ip


def test_private_ip_detection():
    assert is_private_ip("127.0.0.1") is True
    assert is_private_ip("10.0.0.1") is True
    assert is_private_ip("192.168.1.100") is True
    assert is_private_ip("169.254.169.254") is True
    assert is_private_ip("8.8.8.8") is False


def test_allowed_domain_passes_validation():
    url = "https://www.gutenberg.org/ebooks/84.epub.images"
    is_safe, msg = validate_download_url(url)
    assert is_safe is True
    assert "passed" in msg


def test_unauthorized_domain_fails_validation():
    url = "https://pirate-books-mirror.net/books/84.epub"
    is_safe, msg = validate_download_url(url)
    assert is_safe is False
    assert "not in the authorized repository allowlist" in msg


def test_dangerous_executable_extension_blocked():
    url = "https://www.gutenberg.org/ebooks/malware.exe"
    is_safe, msg = validate_download_url(url)
    assert is_safe is False
    assert "Dangerous executable" in msg


def test_insecure_scheme_blocked():
    url = "file:///etc/passwd"
    is_safe, msg = validate_download_url(url)
    assert is_safe is False
    assert "scheme" in msg
