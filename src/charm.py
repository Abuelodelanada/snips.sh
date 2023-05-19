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

import ops
from typing import Optional

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

VALID_LOG_LEVELS = ["info", "debug", "warning", "error", "critical"]


class SnipsK8SOperatorCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.snips_pebble_ready, self._on_snips_pebble_ready)
        self.framework.observe(self.on.config_changed, self._on_config_changed)

    def _on_snips_pebble_ready(self, event: ops.PebbleReadyEvent):
        container = event.workload
        container.add_layer("snips", self._pebble_layer, combine=True)
        container.replan()
        self.unit.status = ops.ActiveStatus()

    def _on_config_changed(self, event: ops.ConfigChangedEvent):
        log_level = self.model.config["log-level"].lower()

        # Do some validation of the configuration option
        if log_level in VALID_LOG_LEVELS:
            # The config is good, so update the configuration of the workload
            container = self.unit.get_container("snips")
            # Verify that we can connect to the Pebble API in the workload container
            if container.can_connect():
                # Push an updated layer with the new config
                container.add_layer("snips", self._pebble_layer, combine=True)
                container.replan()

                logger.debug("Log level for gunicorn changed to '%s'", log_level)
                self.unit.status = ops.ActiveStatus()
            else:
                # We were unable to connect to the Pebble API, so we defer this event
                event.defer()
                self.unit.status = ops.WaitingStatus("waiting for Pebble API")
        else:
            # In this case, the config option is bad, so block the charm and notify the operator.
            self.unit.status = ops.BlockedStatus("invalid log level: '{log_level}'")

    @property
    def _pebble_layer(self):
        return {
            "summary": "snips layer",
            "description": "pebble config layer for snips",
            "services": {
                "snips": {
                    "override": "replace",
                    "summary": "snips",
                    "command": "/usr/bin/snips.sh",
                    "startup": "enabled",
                    "environment": {
                        "SNIPS_DEBUG": True,
                        "SNIPS_ENABLEGUESSER": True,
                    },
                }
            },
        }


if __name__ == "__main__":  # pragma: nocover
    ops.main(SnipsK8SOperatorCharm)
