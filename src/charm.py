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

from charms.traefik_k8s.v1.ingress import IngressPerAppRequirer
from ops import PebbleReadyEvent, main
from ops.charm import CharmBase
from ops.model import ActiveStatus

from secret_manager import SecretManager
from snips import CONTAINER_NAME, HTTP_PORT, Snips
from tasks import UpdatePebbleLayerTask, ValidateCanConnectTask, ValidateExternalURLTask
from url_manager import URLManager

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


class SnipsK8SOperatorCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        self._container = self.unit.get_container(CONTAINER_NAME)
        self.secret_manager = SecretManager(self)
        self._ingress = IngressPerAppRequirer(self, port=HTTP_PORT, strip_prefix=True)
        self._snips = Snips(self._container, self._ingress, self.secret_manager.hmac_key)

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
        tasks = [
            ValidateCanConnectTask(self, self._container),
            ValidateExternalURLTask(self, self._external_url, logger),
            UpdatePebbleLayerTask(self._snips),
        ]
        for task in tasks:
            if not task.execute():
                return
        self.unit.status = ActiveStatus()

    @property
    def _external_url(self) -> str:
        """Return the externally-reachable (public) address."""
        return self._ingress.url or URLManager.internal_url(HTTP_PORT)


if __name__ == "__main__":  # pragma: nocover
    main(SnipsK8SOperatorCharm)
