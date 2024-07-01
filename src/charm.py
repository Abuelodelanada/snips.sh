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
import socket
import string
from urllib.parse import urlparse

from charms.traefik_k8s.v1.ingress import IngressPerAppRequirer
from ops import PebbleReadyEvent
from ops.charm import CharmBase
from ops.main import main
from ops.model import (
    ActiveStatus,
    BlockedStatus,
    MaintenanceStatus,
    SecretNotFoundError,
)
from ops.pebble import ChangeError
from snips import CONTAINER_NAME, HTTP_PORT, Snips

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

LAYER_NAME = CONTAINER_NAME
SERVICE_NAME = CONTAINER_NAME


class SnipsK8SOperatorCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        self._container = self.unit.get_container(CONTAINER_NAME)
        self._ingress = IngressPerAppRequirer(self, port=HTTP_PORT, strip_prefix=True)
        self._snips = Snips(self._container, self._ingress, self._hmac_key)

        self.framework.observe(self.on.snips_pebble_ready, self._on_snips_pebble_ready)
        self.framework.observe(self._ingress.on.ready, self._handle_ingress)
        self.framework.observe(self._ingress.on.revoked, self._handle_ingress)

    def _on_snips_pebble_ready(self, _: PebbleReadyEvent):
        self._common_exit_hook()

    def _handle_ingress(self, _):
        if url := self._ingress.url:
            logger.info("Ingress is ready: '%s'.", url)
        else:
            logger.info("Ingress revoked.")
        self._common_exit_hook()

    def _common_exit_hook(self) -> None:
        """Event processing hook that is common to all events to ensure idempotency."""
        if not self._container.can_connect():
            self.unit.status = MaintenanceStatus("Waiting for pod startup to complete")
            return

        # Make sure the external url is valid
        if external_url := self._external_url:
            parsed = urlparse(external_url)
            if not (parsed.scheme in ["http", "https"] and parsed.hostname):
                # This shouldn't happen
                logger.error(
                    "Invalid external url: '%s'; must include scheme and hostname.",
                    external_url,
                )
                self.unit.status = BlockedStatus(
                    f"Invalid external url: '{external_url}'; must include scheme and hostname."
                )
                return

        # Update pebble layer
        self._update_layer()
        self.unit.status = ActiveStatus()

    def _update_layer(self) -> bool:
        """Update service layer.

        Returns:
          True if anything changed; False otherwise
        """
        overlay = self._snips.pebble_layer
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

        return False

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
    def _internal_url(self) -> str:
        """Return the fqdn dns-based in-cluster (private) address."""
        return f"http://{socket.getfqdn()}:{HTTP_PORT}"

    @property
    def _external_url(self) -> str:
        """Return the externally-reachable (public) address."""
        return self._ingress.url or self._internal_url


if __name__ == "__main__":  # pragma: nocover
    main(SnipsK8SOperatorCharm)
