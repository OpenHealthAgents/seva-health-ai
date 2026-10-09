"""Input Validation, XSS Neutralization, and SSRF Defense.

Enforces deep validation on inputs, preventing Cross-Site Scripting (XSS),
Server-Side Request Forgery (SSRF), and parameter injection attacks.
"""

import re
import ipaddress
import socket
import urllib.parse
import html
from typing import Optional, List, Dict, Any


class SSRFViolationError(Exception):
    """Raised when an outbound URL points to an internal or private network address."""
    pass


class InputValidationError(Exception):
    """Raised when an input contains malicious scripting or query syntax."""
    pass


class SSRFGuard:
    """Blocks Server-Side Request Forgery by ensuring outbound URLs do not target internal networks."""

    # Disallowed private and reserved IPv4 / IPv6 subnets
    BLOCKED_NETWORKS = [
        ipaddress.ip_network("127.0.0.0/8"),          # Loopback
        ipaddress.ip_network("10.0.0.0/8"),           # RFC 1918 Private
        ipaddress.ip_network("172.16.0.0/12"),        # RFC 1918 Private
        ipaddress.ip_network("192.168.0.0/16"),       # RFC 1918 Private
        ipaddress.ip_network("169.254.0.0/16"),       # Link-Local (Cloud metadata e.g. 169.254.169.254)
        ipaddress.ip_network("0.0.0.0/8"),            # Current network
        ipaddress.ip_network("100.64.0.0/10"),        # Carrier-grade NAT
        ipaddress.ip_network("::1/128"),              # IPv6 loopback
        ipaddress.ip_network("fc00::/7"),             # IPv6 unique local
        ipaddress.ip_network("fe80::/10"),            # IPv6 link-local
    ]

    BLOCKED_HOSTNAMES = {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "instance-data",
        "metadata.google.internal",
        "metadata",
    }

    @classmethod
    def validate_url(cls, target_url: str) -> str:
        """Validates that a URL uses safe protocols and points strictly to a public IP address."""
        if not target_url or not isinstance(target_url, str):
            raise SSRFViolationError("Invalid or empty URL provided.")

        parsed = urllib.parse.urlparse(target_url.strip())

        # Protocol check: strictly HTTP or HTTPS
        if parsed.scheme.lower() not in {"http", "https"}:
            raise SSRFViolationError(f"Prohibited protocol scheme: '{parsed.scheme}'. Only HTTP and HTTPS are permitted.")

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise SSRFViolationError("URL missing valid hostname.")

        # Block reserved local hostnames
        if hostname in cls.BLOCKED_HOSTNAMES or hostname.endswith(".local") or hostname.endswith(".internal"):
            raise SSRFViolationError(f"SSRF Alert: Request to internal hostname '{hostname}' is blocked.")

        # DNS Resolution & IP Range Check
        try:
            # Resolve hostname to IPv4
            resolved_ips = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for item in resolved_ips:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)

                for blocked_net in cls.BLOCKED_NETWORKS:
                    if ip_obj in blocked_net:
                        raise SSRFViolationError(
                            f"SSRF Alert: Hostname '{hostname}' resolves to blocked private address {ip_str}."
                        )
        except socket.gaierror:
            # Host could not be resolved
            pass

        return target_url


class InputSanitizer:
    """Sanitizes user and clinical inputs to eliminate XSS and code injection vectors."""

    XSS_TAG_PATTERN = re.compile(
        r"<\s*(?:script|iframe|object|embed|applet|meta|link|style)[^>]*>.*?</\s*(?:script|iframe|object|embed|applet|meta|link|style)\s*>|"
        r"<\s*(?:script|iframe|object|embed|applet|meta|link|style)[^>]*>|"
        r"javascript\s*:|"
        r"on\w+\s*=",
        re.IGNORECASE | re.DOTALL,
    )

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Removes executable script tags, event handlers, and escapes dangerous characters."""
        if not isinstance(text, str):
            return text
        # Strip active script injection patterns
        cleaned = cls.XSS_TAG_PATTERN.sub("", text)
        # Escape remaining HTML brackets
        return html.escape(cleaned.strip())

    @classmethod
    def check_for_xss(cls, text: str) -> bool:
        """Returns True if input text contains dangerous XSS script vectors."""
        if not isinstance(text, str):
            return False
        return bool(cls.XSS_TAG_PATTERN.search(text))
