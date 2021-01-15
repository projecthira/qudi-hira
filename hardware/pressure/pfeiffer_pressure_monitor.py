# -*- coding: utf-8 -*-
"""
This file contains the Qudi module to control the TPG366 pressure gauge from Pfeiffer.
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

import serial
from core.module import Base
from core.configoption import ConfigOption
from interface.process_interface import ProcessInterface
import time

# Unicode characters returned by device
ETX = chr(3)  # \x03
CR = chr(13)
LF = chr(10)
ENQ = chr(5)  # \x05
ACK = chr(6)  # \x06
NAK = chr(21)  # \x15
ERR = "0001"

# Code translations constants
MEASUREMENT_STATUS = {
    0: 'Measurement data okay',
    1: 'Underrange',
    2: 'Overrange',
    3: 'Sensor error',
    4: 'Sensor off (IKR, PKR, IMR, PBR)',
    5: 'No sensor',
    6: 'Identification error',
    7: 'Data error'
}
GAUGE_IDS = {
    'TPR': 'Pirani Gauge or Pirani Capacitive gauge',
    'IKR9': 'Cold Cathode Gauge 10E-9 ',
    'IKR11': 'Cold Cathode Gauge 10E-11 ',
    'PKR': 'FullRange CC Gauge',
    'PBR': 'FullRange BA Gauge',
    'IMR': 'Pirani / High Pressure Gauge',
    'CMR': 'Linear gauge',
    'noSEn': 'no SEnsor',
    'noid': 'no identifier'
}
PRESSURE_UNITS = {0: 'mbar', 1: 'Torr', 2: 'hPa'}
PRESSURE_UNITS_FULL = {'mbar': 'millibar', 'Torr': 'torr', 'hPa': 'hectopascals'}


class PfeifferTPG366(Base, ProcessInterface):
    """
    Hardware control class to control Pfeiffer TPG366 devices.

    The easiest way to connect the device is to use Ethernet.
    - Install a Virtual COM driver, such as
            NetBurner: https://www.netburner.com/download/virtual-comm-port-driver-windows-xp-10/
    - Map the device <IP> with port 8000 to an unused serial port within the software.
    - Enter the com_port in the config.

    Example config for copy-paste:

    pfeiffer_tpg366:
        module.Class: 'pressure.pfeiffer_pressure_controller.PfeifferTPG266'
        com_port : 'COM11'
        timeout : 2
        main_gauge : 1
        prep_gauge : 2
        back_gauge : 3
    """
    _com_port = ConfigOption('com_port', default='COM3', missing='error')
    _timeout = ConfigOption('timeout', default=2, missing='warn')
    _main_guage_number = ConfigOption('main_gauge_number', default=1, missing='warn')
    _prep_guage_number = ConfigOption('prep_gauge_number', default=2, missing='warn')
    _back_guage_number = ConfigOption('back_gauge_number', default=3, missing='warn')

    def on_activate(self):
        self._tpg = serial.Serial(
            self._com_port,
            timeout=self._timeout,
            baudrate=9600,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            xonxoff=False,
            rtscts=False
        )
        return 0

    def on_deactivate(self):
        """ Close the connection to the instrument.
        """
        self._tpg.close()

    def get_channels(self):
        """ A dict of the temperature monitor channels """
        return {"main": self._main_guage_number, "prep": self._prep_guage_number, "back": self._back_guage_number}

    def off(self, gauge=None):
        """"
        Switch off specific pressure gauges, or all if gauge=None

        Gauge state values:
            0 - No change
            1 - Gauge off
            2 - Gauge on
        @return float: 0 if successful, -1 if not
        """
        gauge_states = ['0'] * 6

        if gauge is None:
            # Switch off all gauges
            gauge_states = ['1'] * 6
        elif gauge == "main_gauge":
            gauge_states[self._main_guage_number - 1] = '1'
        elif gauge == "prep_gauge":
            gauge_states[self._prep_guage_number - 1] = '1'
        elif gauge == "back_gauge":
            gauge_states[self._back_guage_number - 1] = '1'
        else:
            self.log.error("Invalid pressure gauge specified.")
            return -1

        command = ','.join(gauge_states)
        self._communicate('SEN,{}'.format(command))
        return 0

    def on(self, gauge=None):
        """"
        Switch on specific pressure gauges, or all if gauge=None

        Gauge state values:
            0 - No change
            1 - Gauge off
            2 - Gauge on
        @return 0:if successful
        """
        gauge_states = ['0'] * 6

        if gauge is None:
            # Switch off all gauges
            gauge_states = ['2'] * 6
        elif gauge == "main_gauge":
            gauge_states[self._main_guage_number - 1] = '2'
        elif gauge == "prep_gauge":
            gauge_states[self._prep_guage_number - 1] = '2'
        elif gauge == "back_gauge":
            gauge_states[self._back_guage_number - 1] = '2'
        else:
            self.log.error("Invalid pressure gauge specified.")
            return -1

        command = ','.join(gauge_states)
        self._communicate('SEN,{}'.format(command))
        return 0

    def get_pressure(self, channel):
        """ Get pressure of a specific channel

        @param channel: String for which channel to query
        @return float: channel pressure in mbar
        """
        channel_number = self.get_channels()[channel]
        response = self._communicate('PR{}'.format(channel_number))
        status, pressure = response.split(",")

        if status == "0":
            # Measuring data okay
            pressure = float(pressure)
        else:
            # Measuring data not okay (see MEASUREMENT_STATUS)
            pressure = MEASUREMENT_STATUS[int(status)]
        return pressure

    def get_sensor_states(self):
        """ Get state of sensors

        @return list: list of sensor states
        """
        sensor_states = []
        for ch in range(1, 7):
            status, _ = self._communicate('PR{}'.format(ch)).split(",")
            sensor_states.append(MEASUREMENT_STATUS[int(status)])
        return sensor_states

    def get_sensor_names(self):
        """ Get names of sensors

        @return list: list of sensor names
        """
        sensor_names = self._communicate('TID').split(",")
        return sensor_names

    def get_pressure_unit(self):
        """Return the pressure unit
        :return: Pressure unit (mbar/Torr/hPa)
        :rtype: str
        """
        unit_code = self._communicate('UNI')
        return PRESSURE_UNITS[int(unit_code)]

    # ProcessInterface methods
    def get_process_value(self, channel=None):
        """ Get measured value of the pressure """
        return self.get_pressure(channel)

    def get_process_unit(self, channel=None):
        """ Return the unit of measured temperature """
        unit = self.get_pressure_unit()
        return unit, PRESSURE_UNITS_FULL[unit]

    def _send(self, message):
        """ Send a message to to HDI

        @param string message: message to be delivered to the HDI
        """
        eol = '\r\n'
        new_message = message + eol
        self._tpg.write(new_message.encode())

    def _communicate(self, message):
        """ Sends and receive messages with the TPG.
        Since the TPG often seems to reply with nonsensical messages,
        we keep querying it until it gives reasonable data.

        @param string message: message to be delivered to the TPG
        @return string response: message received from the TPG
        """
        response = []
        while True:
            try:
                self._send(message)
                # TODO: Listen for ACKnowledgement from device instead of sleeping
                time.sleep(0.05)
                self._send(ENQ)

                response_len = self._tpg.inWaiting()
                response = []

                if response_len == 0:
                    # If there is no data in the device buffer
                    raise ValueError

                while response_len > 0:
                    this_response_line = self._tpg.readline().decode().strip("\r\n")
                    response.append(this_response_line)
                    time.sleep(0.05)
                    response_len = self._tpg.inWaiting()
                if response[1] == ACK or response[1] == NAK or response[1] == ERR:
                    # If the response just consists of an ACKnowledge or No ACKnowlegde or ERRor
                    raise ValueError
            except Exception as exc:
                # This message doesn't really mean anything, but its still good to have it in the debug log
                self.log.debug(exc)
                continue
            break

        return response[1]
