# -*- coding: utf-8 -*-
__author__ = "Dinesh Pinto"
__email__ = "d.pinto@fkf.mpg.de"
"""
This file contains the Qudi hardware file to control R&S SMF100a devices.

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import visa
import serial
from core.module import Base
from core.configoption import ConfigOption
from interface.process_interface import ProcessInterface


class PfeifferTPG366(Base, ProcessInterface):
    """

    Example config for copy-paste:

    pfeiffer_tpg366:
    module.Class: 'pressure.pfeiffer_pressure_controller.PfeifferTPG266'
    com_port : 'COM2'
    timeout : 2
    """
    _modclass = 'PfeifferTPG266'
    _modtype = 'hardware'
    _com_port = ConfigOption('com_port', default='COM2', missing='error')
    _timeout = ConfigOption('timeout', default=2, missing='warn')
    _main_guage = ConfigOption('main_gauge', default=1, missing='warn')
    _prep_guage = ConfigOption('prep_guage', default=2, missing='warn')
    _back_guage = ConfigOption('back_guage', default=3, missing='warn')

    def on_activate(self):
        # TODO Connect over serial interface and test
        self.rm = visa.ResourceManager()
        self.tpg = self.rm.open_resource(
            resource_name=self._com_port,
            timeout=self._timeout,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            xonxoff=False,
            write_termination='\r\n',
            read_termination='\r\n',
            send_end=True
        )

    def on_deactivate(self):
        """ Close the connection to the instrument.
        """
        self.off()
        self.tpg.close()

    def off(self, gauge=None):
        """"
        0 - No change
        1 - Gauge off
        2 - Gauge on
        """
        gauge_states = ['0'] * 6

        if gauge is None:
            # Switch off all gauges
            gauge_states = ['1'] * 6
        elif gauge == "main_gauge":
            gauge_states[self._main_guage-1] = '1'
        elif gauge == "prep_gauge":
            gauge_states[self._prep_guage-1] = '1'
        elif gauge == "back_gauge":
            gauge_states[self._back_guage-1] = '1'
        else:
            self.log.error("Invalid pressure gauge specified.")
            return -1

        command = ','.join(gauge_states)
        self._inst.write('SEN,{}'.format(command))
        return 0

    def on(self, gauge=None):
        """"
         0 - No change
         1 - Gauge off
         2 - Gauge on
         """
        gauge_states = ['0'] * 6

        if gauge is None:
            # Switch off all gauges
            gauge_states = ['2'] * 6
        elif gauge == "main_gauge":
            gauge_states[self._main_guage - 1] = '2'
        elif gauge == "prep_gauge":
            gauge_states[self._prep_guage - 1] = '2'
        elif gauge == "back_gauge":
            gauge_states[self._back_guage - 1] = '2'
        else:
            self.log.error("Invalid pressure gauge specified.")
            return -1

        command = ','.join(gauge_states)
        self._inst.write('SEN,{}'.format(command))
        return 0

    def get_pressure(self, channel):
        """ Get pressure of a specific channel """
        if channel == "main_gauge":
            channel = self._main_guage
        elif channel == "prep_gauge":
            channel = self._prep_guage
        elif channel == "back_gauge":
            channel = self._back_guage

        response = self._inst.query('PR{}'.format(channel))
        status, pressure = response.split(",")

        if status == "0":
            # Measuring data okay
            pass
        elif status == "1":
            # Measuring range underrange
            pressure = "UNDER"
        elif status == "2":
            # Measuring range overrange
            pressure = "OVER"
        elif status == "3":
            # Sensor Error
            pressure = "ERROR"
        elif status == "4":
            # Sensor switched off
            pressure = "OFF"
        elif status == "5":
            # No gauge
            pressure = "NOGAUGE"
        elif status == "6":
            # Identification Error
            pressure = "IDERROR"
        return pressure

    # ProcessInterface methods
    def get_process_value(self, channel=None):
        """ Get measured value of the pressure """
        return self.get_pressure(channel)

    def get_process_unit(self, channel=None):
        """ Return the unit of measured temperature """
        return 'mbar', 'milibar'
