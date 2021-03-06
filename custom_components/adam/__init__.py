"""Plugwise Adam Climate component for Home Assistant Core."""

from datetime import timedelta
import logging

import voluptuous as vol
import plugwise

from homeassistant.helpers.discovery import load_platform
from homeassistant.helpers import config_validation as cv

from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)

from homeassistant.exceptions import PlatformNotReady
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

# Configuration directives
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"

# Default directives
DEFAULT_NAME = "Anna"
DEFAULT_USERNAME = "smile"
DEFAULT_TIMEOUT = 10
DEFAULT_PORT = 80
DEFAULT_ICON = "mdi:thermometer"
DEFAULT_MIN_TEMP = 4
DEFAULT_MAX_TEMP = 30
DOMAIN = 'adam'
DATA = 'adam_data'
SCAN_INTERVAL = timedelta(seconds=30)

COMPONENTS = [ 'climate' ]

# Read configuration
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
                vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
                vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
            }
        )
    }, 
    extra=vol.ALLOW_EXTRA,
)


def setup(hass, config):
    """Set up the Plugwise (Anna) Thermostat."""
    api = plugwise.Plugwise(
        config[DOMAIN][CONF_USERNAME],
        config[DOMAIN][CONF_PASSWORD],
        config[DOMAIN][CONF_HOST],
        config[DOMAIN][CONF_PORT],
    )

    try:
        api.ping_gateway()
    except OSError:
        _LOGGER.debug("Can't connect to the Plugwise API")
        return False

    hass.data[DATA] = DataStore(api)

    for component in COMPONENTS:
        load_platform(hass, component, DOMAIN, {}, config)

    return True


class DataStore:
    """An object to store the Plugwise data."""

    def __init__(self, api):
        """Initialize Tado data store."""
        self.api = api

        self.devices = {}
        self.domain_objects = None
        self.data = {}


    @Throttle(SCAN_INTERVAL)
    def update(self):
        """Update the internal data from the API"""
        try:
            appliances = self.api.get_appliances()
            domain_objects = self.api.get_domain_objects()
            _LOGGER.debug("Device data collected from Plugwise API")
        except RuntimeError:
            _LOGGER.error("Unable to connect to the Plugwise API.")

        self.domain_objects = domain_objects

        for id, device in list(self.devices.items()):
            #data = None
            data = self.api.get_device_data(appliances, domain_objects, id, device['ctrl_id'])
            self.data[id] = data

    def add_device(self, id, device):
        """Add a sensor to update in _update()."""
        self.devices[id] = device
        self.data[id] = None

    def get_data(self, id):
        """Get the cached data."""
        data = {'error': 'no data'}

        if id in self.data:
            data = self.data[id]
        return data

    def get_domain_data(self):
        """Get the cached domain_objects data."""
        domain = self.domain_objects
        return domain

    def getDevices(self):
        """Wrap for get_devices()."""
        return self.api.get_devices()

    def setScheduleState(self, domain_obj, id, name, state):
        """Wrap for set_schedule_state()."""
        self.api.set_schedule_state(domain_obj, id, name, state)
        self.update(no_throttle=True)  # pylint: disable=unexpected-keyword-arg
        
    def setPreset(self, domain_obj, id, dev_type, preset):
        """Wrap for set_preset()."""
        self.api.set_preset(domain_obj, id, dev_type, preset)
        self.update(no_throttle=True)  # pylint: disable=unexpected-keyword-arg
        
    def setTemperature(self, domain_obj, id, dev_type, temperature):
        """Wrap for set_temperature()."""
        self.api.set_temperature(domain_obj, id, dev_type, temperature)
        self.update(no_throttle=True)  # pylint: disable=unexpected-keyword-arg

