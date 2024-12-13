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
from typing import List

from charms.traefik_k8s.v1.ingress import (
    IngressPerAppRequirer,
)
from ops import main
from ops.charm import CharmBase
from ops.model import ActiveStatus

from secret_manager import SecretManager
from snips import CONTAINER_NAME, HTTP_PORT, Snips
from tasks import (
    HandleIngresMessagesTask,
    Task,
    UpdatePebbleLayerTask,
    ValidateCanConnectTask,
    ValidateExternalURLTask,
)
from url_manager import URLManager

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


class SnipsK8SOperatorCharm(CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        self._initialise_components()
        self._observe_events()

    def _initialise_components(self):
        self._container = self.unit.get_container(CONTAINER_NAME)
        self._secret_manager = self._create_secret_manager()
        self._ingress = self._create_ingress()
        self._snips = self._create_snips()

    def _create_secret_manager(self):
        """Create a SecretManager instance."""
        return SecretManager(self)

    def _create_ingress(self):
        """Create a IngressPerAppRequirer instance."""
        return IngressPerAppRequirer(self, port=HTTP_PORT, strip_prefix=True)

    def _create_snips(self):
        """Create a Snips instance."""
        return Snips(self._container, self._ingress, self._secret_manager.hmac_key)

    def _observe_events(self):
        self.framework.observe(self.on.snips_pebble_ready, self._reconcile)
        self.framework.observe(self._ingress.on.ready, self._reconcile)
        self.framework.observe(self._ingress.on.revoked, self._reconcile)

    def _task_factory(self) -> List[Task]:
        return [
            HandleIngresMessagesTask(self._ingress.url, logger),
            ValidateCanConnectTask(self, self._container),
            ValidateExternalURLTask(
                self, self._ingress.url, URLManager.internal_url(HTTP_PORT), logger
            ),
            UpdatePebbleLayerTask(self._snips),
        ]

    def _reconcile(self, _) -> None:
        """Event processing hook that is common to all events to ensure idempotency."""
        tasks = self._task_factory()
        for task in tasks:
            if not task.execute():
                return
        self.unit.status = ActiveStatus()


if __name__ == "__main__":  # pragma: nocover
    main(SnipsK8SOperatorCharm)
