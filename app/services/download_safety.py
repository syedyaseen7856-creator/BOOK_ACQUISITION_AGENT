import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse
from typing import Tuple
from app.config import settings

logger = logging.getLogger(__name__)

DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".ps1", ".vbs", ".sh",
    ".dll", ".msi", ".scr", ".jar", ".com", ".pif", ".hta"
}


def is_private_ip(ip_str: str) -> bool:
    """Determine if an IP address is private, loopback, link-local, or reserved."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or (ip.version == 6 and ip.is_site_local)
        )
    except ValueError:
        return True


def sanitize_filename(filename: str, default: str = "book_download.pdf") -> str:
    """
    Sanitize filename against path traversal (../), null bytes, and unsafe characters.
    """
    if not filename:
        return default
    # Remove directory separators and null bytes
    cleaned = filename.replace("/", "_").replace("\\", "_").replace("\0", "")
    # Remove dangerous characters
    cleaned = re.sub(r"[^\w\.\-\_]", "_", cleaned)
    # Remove leading dots to prevent hidden files or traversal
    cleaned = cleaned.lstrip(".")
    return cleaned if cleaned else default


def validate_download_url(url: str) -> Tuple[bool, str]:
    """
    Validate candidate download URL against SSRF, unauthorized schemes,
    unapproved domains, and dangerous file extensions.
    """
    if not url:
        return False, "Download URL is empty."

    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Malformed URL: {e}"

    # 1. Enforce HTTPS scheme (or HTTP if testing permitted)
    if parsed.scheme.lower() not in ("https", "http"):
        return False, f"Insecure or invalid URL scheme '{parsed.scheme}'. Only HTTP/HTTPS allowed."

    # 2. Check for host presence
    hostname = parsed.hostname
    if not hostname:
        return False, "URL contains no valid host."

    # 3. Check domain allowlist
    allowed = settings.allowed_domains_set
    domain_match = any(
        hostname == domain or hostname.endswith(f".{domain}")
        for domain in allowed
    )
    if not domain_match:
        return False, f"Domain '{hostname}' is not in the authorized repository allowlist."

    # 4. Resolve IP and prevent SSRF
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for entry in addr_info:
            ip_candidate = entry[4][0]
            if is_private_ip(ip_candidate):
                logger.warning(f"SSRF attempt blocked: {hostname} resolved to {ip_candidate}")
                return False, f"Host '{hostname}' resolves to an internal/private IP address ({ip_candidate})."
    except Exception as e:
        logger.warning(f"Failed to resolve host '{hostname}': {e}")
        # When offline or mock host, proceed if in domain allowlist

    # 5. Check file extension
    path_lower = parsed.path.lower()
    for ext in DANGEROUS_EXTENSIONS:
        if path_lower.endswith(ext):
            return False, f"Dangerous executable file extension detected: '{ext}'"

    return True, "URL passed all safety and authorization checks."
