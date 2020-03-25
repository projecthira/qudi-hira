# -*- coding: utf-8 -*-
__author__ = "Dinesh Pinto"
__email__ = "d.pinto@fkf.mpg.de"
"""
This file contains the Qudi hardware file to readout the Twickenham Helium Depth Indicator.

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

from core.module import Base
from core.configoption import ConfigOption
from interface.process_interface import ProcessInterface

import re
import serial
import time


class TwickenhamHDI(Base, ProcessInterface):
    """ Implements the HW file for Twickenham Helium Depth Indicator (HDI).

    Example config for copy-paste:

    laser_toptica:
        module.Class: 'hdi.twickenham_hdi.TwickenhamHDI'
        com_port: 'COM1'
    """

    _modclass = 'TwickenhamHDI'
    _modtype = 'hardware'
    _com_port = ConfigOption('com_port', 'COM1', missing='error')

    def on_activate(self):
        """ Activate module.
        """
        try:
            self._hdi = serial.Serial(
                self._com_port,
                baudrate=9600,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_TWO,
                xonxoff=True,
                timeout=5,
                write_timeout=5
            )
        except serial.SerialException as e:
            self.log.error(e)

    def on_deactivate(self):
        """ Deactivate module.
        """
        self._hdi.close()

    def get_helium_level(self):
        # Choose channel A or B (most likely A)
        self._communicate("P0")
        # Fast measurement
        self._communicate("M2")
        # Readout display
        level = self._communicate("G")
        # Go to STANDBY mode
        self._communicate("M0")
        return level

    def get_process_value(self, channel=None):
        """ Get measured value of the depth """
        return self.get_helium_level()

    def get_process_unit(self, channel=None):
        """ Return the unit of measured depth """
        return 'mm', 'millimeter'

    def _send(self, message):
        """ Send a message to to HDI

        @param string message: message to be delivered to the HDI
        """
        eol = '\r\n'
        new_message = message + eol
        self._hdi.write(new_message.encode())

    def _communicate(self, message):
        """ Send a receive messages with the HDI

        @param string message: message to be delivered to the HDI
        @returns string response: message received from the HDI
        """
        self._send(message)
        time.sleep(0.05)
        response_len = self._hdi.inWaiting()
        response = []

        while response_len > 0:
            this_response_line = self._hdi.readline().decode().strip()
            response.append(this_response_line)
            time.sleep(0.05)

            response_len = self._hdi.inWaiting()
            if response_len == 5:
                response.append('')
                self._hdi.flushInput()
                self._hdi.flushOutput()
                response_len = self._hdi.inWaiting()

        full_response = ''.join(response)
        return full_response
