#!/usr/bin/env python3
# Copyright 2024 Jose C. Massón
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk


"""Tasks executed by the charm."""

from typing import Protocol

from ops.model import (
    MaintenanceStatus,
)


class Task(Protocol):
    """Task interface."""

    def execute(self) -> bool:
        """Task execution.

        Return True if the execution is successful otherwise False.
        """
        ...


class ValidateCanConnectTask:
    """Validate Can Connect task class."""

    def __init__(self, charm, container):
        self.charm = charm
        self._container = container

    def execute(self) -> bool:
        """Task execution."""
        if not self._container.can_connect():
            self.charm.unit.status = MaintenanceStatus("Waiting for pod startup to complete")
            return False

        return True


class UpdatePebbleLayerTask:
    """Update Pebble Layer task class."""

    def __init__(self, snips):
        self.snips = snips

    def execute(self) -> bool:
        """Task execution."""
        return self.snips.update_layer()
