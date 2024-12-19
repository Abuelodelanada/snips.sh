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

from ops import main
from ops.charm import CharmBase
from ops.model import ActiveStatus

from secret_manager import SecretManager
from snips import CONTAINER_NAME, Snips
from tasks import (
    Task,
    UpdatePebbleLayerTask,
    ValidateCanConnectTask,
)

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)


class SnipsK8SOperatorCharm(CharmBase):
    """Charm the service."""

    def __init__(self, framework):
        super().__init__(framework)
        self._initialise_components()
        self._observe_events()

    def _initialise_components(self):
        self._container = self.unit.get_container(CONTAINER_NAME)
        self._secret_manager = self._create_secret_manager()
        self._snips = self._create_snips()

    def _create_secret_manager(self):
        """Create a SecretManager instance."""
        return SecretManager(self)

    def _create_snips(self):
        """Create a Snips instance."""
        return Snips(self._container, self._secret_manager.hmac_key)

    def _observe_events(self):
        self.framework.observe(self.on.snips_pebble_ready, self._reconcile)

    def _task_factory(self) -> List[Task]:
        return [
            ValidateCanConnectTask(self, self._container),
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
