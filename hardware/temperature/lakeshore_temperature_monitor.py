from lakeshore import PrecisionSource

from core.module import Base
from core.configoption import ConfigOption

from interface.process_interface import ProcessInterface
from .Model224 import Model224, InstrumentException


class Lakeshore224TM(Base, ProcessInterface):
    """
        Main class for the Lakeshore 224 Temperature Monitor.

        Example config:

        lakeshore_224tm:
            module.Class: 'temperature.lakeshore_temperature_monitor.Lakeshore224TM'
            ip_address : '192.168.0.12'
            ip_port : 7777
            timeout : 2
        """

    _modtype = 'lakeshore_224tm'
    _modclass = 'hardware'

    _ip_address = ConfigOption('ip_address', default="192.168.0.12", missing="error")
    _ip_port = ConfigOption('ip_port',  default="7777", missing="error")
    _timeout = ConfigOption('timeout', default="2", missing="warn")

    _inst = None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        try:
            self._inst = Model224(ip_address=self._ip_address, tcp_port=self._ip_port, timeout=self._timeout)
        except InstrumentException:
            self.log.error("Lakeshore controller found but unable to communicate, check IP and port.")

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._inst.disconnect_tcp()

    def get_temperature(self, channel):
        """ Get temperature of a specific channel """
        if channel is None:
            channel = "C4"
        temperature = float(self._inst.query('KRDG? {}'.format(channel)))
        return temperature

    # ProcessInterface methods

    def get_process_value(self, channel=None):
        """ Get measured value of the temperature """
        return self.get_temperature(channel)

    def get_process_unit(self, channel=None):
        """ Return the unit of measured temperature """
        return 'K', 'Kelvin'
