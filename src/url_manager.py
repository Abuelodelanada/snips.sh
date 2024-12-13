#!/usr/bin/env python3
# Copyright 2024 Jose C. Massón
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""URL Manager class."""

import socket
from urllib.parse import urlparse


class URLManager:
    """URL Manager class."""

    @staticmethod
    def validate_external_url(external_url: str) -> bool:
        """Validate external url."""
        parsed = urlparse(external_url)
        return bool(parsed.scheme in ["http", "https"] and parsed.hostname)

    @staticmethod
    def internal_url(http_port: int) -> str:
        """Return Snips internal url."""
        return f"http://{socket.getfqdn()}:{http_port}"
