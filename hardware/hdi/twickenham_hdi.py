# -*- coding: utf-8 -*-
__author__ = "Dinesh Pinto"
__email__ = "d.pinto@fkf.mpg.de"
"""
This file contains the Qudi hardware file to readout the Twickenham Helium Depth Indicator.
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

import time
import re

import serial

from core.configoption import ConfigOption
from core.module import Base
from interface.process_interface import ProcessInterface


class TwickenhamHDI(Base, ProcessInterface):
    """ Implements the HW file for Twickenham Helium Depth Indicator (HDI).

    Example config for copy-paste:

    twickenham_hdi:
        module.Class: 'hdi.twickenham_hdi.TwickenhamHDI'
        com_port: 'COM1'
    """

    _modclass = 'TwickenhamHDI'
    _modtype = 'hardware'
    _com_port = ConfigOption('com_port', missing='error')
    _channel = ConfigOption('channel', default="P0", missing='warn')
    _meas_speed = ConfigOption('meas_speed', default="M2", missing='warn')
    _max_depth = ConfigOption("max_depth", default=600, missing='warn')

    _hdi = None

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
            return -1
        return 0

    def on_deactivate(self):
        """ Deactivate module.
        """
        self.goto_standby()
        self._hdi.close()

    def get_helium_level(self):
        self.log.info("HDI query sent")

        # Choose channel A or B (most likely A)
        self._communicate(self._channel)
        time.sleep(0.1)

        # Fast measurement
        self._communicate(self._meas_speed)
        time.sleep(2.5)

        # Readout display
        level_string = self._communicate("G")
        time.sleep(0.1)

        try:
            # The device returns an astrix when it is performing a measurement
            level = float(re.search('A\*(.*)mm', level_string).group(1))
        except AttributeError:
            level = float(re.search('A (.*)mm', level_string).group(1))

        # Go to STANDBY mode
        self.goto_standby()

        self.log.info("HDI level={:.1f} mm. Now in standby".format(level))
        return level

    def goto_standby(self):
        return self._communicate("M0")

    def get_process_value_maximum(self):
        return self._max_depth

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
