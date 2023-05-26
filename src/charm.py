#!/usr/bin/env python3
# Copyright 2023 Jose C. Massón
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

"""Charm the service.

Refer to the following post for a quick-start guide that will help you
develop a new k8s charm using the Operator Framework:

https://discourse.charmhub.io/t/4208
"""

import logging
import secrets
import string

import ops
from ops.framework import StoredState

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


class SnipsK8SOperatorCharm(ops.CharmBase):
    """Charm the service."""

    _log_path: str = "/var/log/snips.log"
    _port: int = 80
    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)
        self._stored.set_default(hmac_key="")
        self.framework.observe(self.on.snips_pebble_ready, self._on_snips_pebble_ready)

    def _on_snips_pebble_ready(self, event: ops.PebbleReadyEvent):
        container = event.workload
        container.add_layer("snips", self._pebble_layer, combine=True)
        container.replan()
        self.unit.status = ops.ActiveStatus()

    @property
    def _pebble_layer(self):
        return {
            "summary": "snips layer",
            "description": "pebble config layer for snips",
            "services": {
                "snips": {
                    "override": "replace",
                    "summary": "snips",
                    "command": '/bin/sh -c "/usr/bin/snips.sh | tee {}"'.format(self._log_path),
                    "startup": "enabled",
                    "environment": self._env_vars,
                }
            },
        }

    @property
    def _env_vars(self) -> dict:
        env_vars = {
            "SNIPS_DEBUG": True,
            "SNIPS_HMACKEY": self._hmac_key,
        }

        return env_vars

    @property
    def _hmac_key(self) -> str:
        if not self._stored.hmac_key:  # type: ignore[truthy-function]
            self._stored.hmac_key = self._generate_hmac_key()

        return self._stored.hmac_key  # type: ignore

    def _generate_hmac_key(self) -> str:
        """Generate a random 24 character symmetric key used to sign URLs."""
        chars = string.ascii_letters + string.digits
        return "".join(secrets.choice(chars) for _ in range(24))


if __name__ == "__main__":  # pragma: nocover
    ops.main(SnipsK8SOperatorCharm, use_juju_for_storage=True)
