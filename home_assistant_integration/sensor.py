import logging
from datetime import timedelta
from typing import Any, Callable, Dict, Optional

import voluptuous as vol
from aiohttp import ClientError

from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)

from homeassistant.const import CONF_HOST, POWER_KILO_WATT

from .const import DOMAIN

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
    }
)


_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)



async def async_setup_platform(
    hass: HomeAssistantType,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the sensor platform."""

    session = async_get_clientsession(hass)

    hostname = config[CONF_HOST]

    sensors = [PiIREmeterSensor(session, hostname)]

    async_add_entities(sensors, update_before_add=True)


class PiIREmeterSensor(SensorEntity):
    def __init__(self, session, hostname):
        super().__init__()
        self.session = session
        self.hostname = hostname
        self.endpoint = 'kw'

    _attr_native_unit_of_measurement = POWER_KILO_WATT
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def name(self):
        return f"Pi IR Emeter Sensor ({self.endpoint})"

    @property
    def url(self):
        return 'http://' + self.hostname + '/' + self.endpoint

    async def async_update(self):
        try:
            async with self.session.get(self.url) as resp:
                if resp.status == 200:
                    j = await resp.json()
                    self._attr_native_value = j['value']
                else:
                    _LOGGER.error(f"Error retrieving data from Pi IR Emeter - got URL status code {resp.status}.")

        except:
            _LOGGER.exception("Error retrieving data from Pi IR Emeter.")