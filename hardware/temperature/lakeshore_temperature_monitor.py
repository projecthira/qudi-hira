# -*- coding: utf-8 -*-
"""
This file contains the Qudi hardware module to control Lakeshore 224 Temperature Monitor.
author: Dinesh Pinto
email: d.pinto@fkf.mpg.de

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <http://www.gnu.org/licenses/>.

Copyright (c) 2020 Dinesh Pinto. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/projecthira/qudi-hira/>
"""

from lakeshore import Model224, InstrumentException

from core.configoption import ConfigOption
from core.module import Base
from interface.process_interface import ProcessInterface


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
    _ip_address = ConfigOption('ip_address', default="192.168.0.12", missing="error")
    _ip_port = ConfigOption('ip_port', default="7777", missing="error")
    _timeout = ConfigOption('timeout', default="2", missing="warn")
    _baseplate_channel = ConfigOption("baseplate_channel", default="C1", missing="warn")
    _tip_channel = ConfigOption("tip_channel", default="A", missing="warn")
    _magnet_channel = ConfigOption("magnet_channel", default="B", missing="warn")
    _z_braid_channel = ConfigOption("z_braid_channel", default="C3", missing="warn")

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        try:
            self._inst = Model224(ip_address=self._ip_address, tcp_port=self._ip_port, timeout=self._timeout)
            return 0
        except InstrumentException:
            self.log.error("Lakeshore controller found but unable to communicate, check IP and port.")
            return -1

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._inst.disconnect_tcp()
        return 0

    def get_channels(self):
        """ A dict of the temperature monitor channels """
        return {"baseplate": self._baseplate_channel,
                "tip": self._tip_channel,
                "magnet": self._magnet_channel,
                "z_braid": self._z_braid_channel}

    def get_temperature(self, channel):
        """ Get temperature of a specific channel """
        channel_number = self.get_channels()[channel]
        temperature = float(self._inst.query('KRDG? {}'.format(channel_number)))
        return temperature

    # ProcessInterface methods

    def get_process_value(self, channel=None):
        """ Get measured value of the temperature """
        return self.get_temperature(channel)

    def get_process_unit(self, channel=None):
        """ Return the unit of measured temperature """
        return 'K', 'Kelvin'
