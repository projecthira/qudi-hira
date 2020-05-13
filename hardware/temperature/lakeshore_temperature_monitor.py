# -*- coding: utf-8 -*-
__author__ = "Dinesh Pinto"
__email__ = "d.pinto@fkf.mpg.de"
"""
This file contains the Qudi hardware file to control Lakeshore 224 Temperature Monitor.
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
    _ip_port = ConfigOption('ip_port', default="7777", missing="error")
    _timeout = ConfigOption('timeout', default="2", missing="warn")
    _baseplate_channel = ConfigOption("baseplate_channel", default="C4", missing="warn")
    _tip_channel = ConfigOption("tip_channel", default="C2", missing="warn")
    _sample_channel = ConfigOption("sample_channel", default="C0", missing="warn")

    _inst = None

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

    def get_temperature(self, channel):
        """ Get temperature of a specific channel """
        if channel == "baseplate":
            channel = self._baseplate_channel
        elif channel == "tip":
            channel = self._tip_channel
        elif channel == "sample":
            channel = self._sample_channel

        temperature = float(self._inst.query('KRDG? {}'.format(channel)))
        return temperature

    # ProcessInterface methods

    def get_process_value(self, channel=None):
        """ Get measured value of the temperature """
        return self.get_temperature(channel)

    def get_process_unit(self, channel=None):
        """ Return the unit of measured temperature """
        return 'K', 'Kelvin'
