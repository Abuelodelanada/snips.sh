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
from typing import Dict

from ops import PebbleReadyEvent
from ops.charm import CharmBase
from ops.main import main
from ops.model import (
    ActiveStatus,
    BlockedStatus,
    MaintenanceStatus,
    SecretNotFoundError,
)
from ops.pebble import ChangeError, Layer

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


CONTAINER_NAME = "snips"
HTTP_PORT = 8080
SSH_PORT = 2222
LAYER_NAME = CONTAINER_NAME
SERVICE_NAME = CONTAINER_NAME


class SnipsK8SOperatorCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        self._container = self.unit.get_container(CONTAINER_NAME)
        self.framework.observe(self.on.snips_pebble_ready, self._on_snips_pebble_ready)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

    def _on_snips_pebble_ready(self, _: PebbleReadyEvent):
        self._common_exit_hook()

    def _on_config_changed(self, _):
        self._common_exit_hook()

    def _common_exit_hook(self) -> None:
        """Event processing hook that is common to all events to ensure idempotency."""
        if not self._container.can_connect():
            self.unit.status = MaintenanceStatus("Waiting for pod startup to complete")
            return

        # Update pebble layer
        if not self._update_layer():
            self.unit.status = BlockedStatus("Failed to update pebble layer. Check juju debug-log")
            return

        self.unit.status = ActiveStatus()

    def _update_layer(self) -> bool:
        """Update service layer.

        Returns:
          True if anything changed; False otherwise
        """
        overlay = self.pebble_layer
        plan = self._container.get_plan()

        if SERVICE_NAME not in plan.services or overlay.services != plan.services:
            self._container.add_layer(LAYER_NAME, overlay, combine=True)
            try:
                self._container.replan()
                return True
            except ChangeError as e:
                logger.error(
                    "Failed to replan; pebble plan: %s; %s",
                    self._container.get_plan().to_dict(),
                    str(e),
                )
                return False

        return True

    @property
    def _hmac_key(self) -> str:
        try:
            secret = self.model.get_secret(label="hmac-key")
        except SecretNotFoundError:
            secret = self.app.add_secret({"hmac-key": self._generate_hmac_key()}, label="hmac-key")

        return secret.get_content()["hmac-key"]

    def _generate_hmac_key(self) -> str:
        """Generate a random 24 character symmetric key used to sign URLs."""
        chars = string.ascii_letters + string.digits
        return "".join(secrets.choice(chars) for _ in range(24))

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
        return env_vars


if __name__ == "__main__":  # pragma: nocover
    main(SnipsK8SOperatorCharm)
