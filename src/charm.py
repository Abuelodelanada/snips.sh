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
from ops.framework import StoredState
from ops.main import main
from ops.model import (
    ActiveStatus,
    BlockedStatus,
    MaintenanceStatus,
)
from ops.pebble import ChangeError, Layer

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


class SnipsK8SOperatorCharm(CharmBase):
    """Charm the service."""

    _log_path: str = "/var/log/snips.log"
    _http_port: int = 8080
    _ssh_port: int = 2222
    _container_name = _layer_name = _service_name = "snips"
    _stored = StoredState()

    def __init__(self, *args):
        super().__init__(*args)
        self._stored.set_default(hmac_key="")
        self.container = self.unit.get_container(self._container_name)
        self.ingress = IngressPerAppRequirer(self, port=self._http_port, strip_prefix=True)
        self.framework.observe(self.on.snips_pebble_ready, self._on_snips_pebble_ready)
        self.framework.observe(self.ingress.on.ready, self._handle_ingress)
        self.framework.observe(self.ingress.on.revoked, self._handle_ingress)

    def _on_snips_pebble_ready(self, event: PebbleReadyEvent):
        self._common_exit_hook()

    def _handle_ingress(self, _):
        if url := self.ingress.url:
            logger.info("Ingress is ready: '%s'.", url)
        else:
            logger.info("Ingress revoked.")
        self._common_exit_hook()

    def _common_exit_hook(self) -> None:
        """Event processing hook that is common to all events to ensure idempotency."""
        if not self.container.can_connect():
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
        overlay = self._pebble_layer
        plan = self.container.get_plan()

        if self._service_name not in plan.services or overlay.services != plan.services:
            self.container.add_layer(self._layer_name, overlay, combine=True)
            try:
                self.container.replan()
                return True
            except ChangeError as e:
                logger.error(
                    "Failed to replan; pebble plan: %s; %s",
                    self.container.get_plan().to_dict(),
                    str(e),
                )
                return False

        return False

    @property
    def _pebble_layer(self) -> Layer:
        return Layer(
            {
                "summary": "snips layer",
                "description": "pebble config layer for snips",
                "services": {
                    "snips": {
                        "override": "replace",
                        "summary": "snips",
                        "command": '/bin/sh -c "/usr/bin/snips.sh | tee {}"'.format(
                            self._log_path
                        ),
                        "startup": "enabled",
                        "environment": self._env_vars,
                    }
                },
            }
        )

    @property
    def _env_vars(self) -> dict:
        env_vars = {
            "SNIPS_DEBUG": True,
            "SNIPS_HMACKEY": self._hmac_key,
        }

        if self.ingress.url:
            env_vars["SNIPS_HTTP_EXTERNAL"] = self.ingress.url

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

    @property
    def _internal_url(self) -> str:
        """Return the fqdn dns-based in-cluster (private) address."""
        return f"http://{socket.getfqdn()}:{self._http_port}"

    @property
    def _external_url(self) -> str:
        """Return the externally-reachable (public) address."""
        return self.ingress.url or self._internal_url


if __name__ == "__main__":  # pragma: nocover
    main(SnipsK8SOperatorCharm, use_juju_for_storage=True)
