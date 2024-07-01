#!/usr/bin/env python3

"""Snips workload manager class."""

import logging
from typing import Dict

from charms.traefik_k8s.v1.ingress import IngressPerAppRequirer
from ops import Container
from ops.pebble import Layer

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

CONTAINER_NAME = "snips"
HTTP_PORT = 8080
SSH_PORT = 2222


class Snips:
    """Snips workload container facade."""

    def __init__(self, container: Container, ingress: IngressPerAppRequirer, hmac_key: str):
        self._container = container
        self._ingress = ingress
        self._hmac_key = hmac_key

    @property
    def pebble_layer(self) -> Layer:
        """Pebble layer for the snips service."""
        return Layer(
            {
                "summary": "snips layer",
                "description": "pebble config layer for snips",
                "services": {
                    "snips": {
                        "override": "replace",
                        "summary": "snips",
                        "command": "/usr/bin/snips.sh",
                        "startup": "enabled",
                        "environment": self._env_vars,
                    }
                },
            }
        )

    @property
    def _env_vars(self) -> Dict:
        env_vars = {
            "SNIPS_DEBUG": True,
            "SNIPS_HMACKEY": self._hmac_key,
        }

        if self._ingress.url:
            env_vars["SNIPS_HTTP_EXTERNAL"] = self._ingress.url

        return env_vars
