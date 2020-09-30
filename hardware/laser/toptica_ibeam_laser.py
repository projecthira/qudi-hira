# -*- coding: utf-8 -*-
"""
This file contains the Qudi hardware module to control the Toptica iBeam Smart Laser.
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
from interface.simple_laser_interface import SimpleLaserInterface, LaserState, ShutterState, ControlMode

import re
import serial
import time


class TopticaIBeamLaser(Base, SimpleLaserInterface):
    """ Implements the Toptica iBeam Smart Laser.

    Example config for copy-paste:

    laser_toptica:
        module.Class: 'laser.toptica_laser.TopticaIBeamLaser'
        com_port: 'COM1'
        maxpower: 0.1
        maxcurrent: 0.2
    """

    _modclass = 'TopticaIBeamLaser'
    _modtype = 'hardware'
    _com_port = ConfigOption('com_port', 'COM1', missing='error')
    _maxpower = ConfigOption('maxpower', 0.1, missing='warn')
    _maxcurrent = ConfigOption('maxcurrent', 0.246, missing='warn')
    ibeam = None

    def on_activate(self):
        """ Activate module.
        """
        try:
            self.ibeam = serial.Serial(
                self._com_port,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
                timeout=5,
                write_timeout=5
            )
        except Exception as e:
            self.log.error(e)
            return -1

        connected = self._connect_laser()

        if not connected:
            self.log.error('Laser does not seem to be connected.')
            return -1
        else:
            self._communicate("ini la")
            self._model_name = 'SN: iBEAM-SMART-515-S-A3-15384'
            self.init_channel_1()
            self.set_external_state(True)
            return 0

    def on_deactivate(self):
        """ Deactivate module.
        """
        self.off()
        self.ibeam.close()

    def _connect_laser(self):
        """ Connect to Instrument.

        @return bool: connection success
        """
        response = self._communicate('serial')
        if 'SN: iBEAM-SMART' in response:
            return True
        else:
            return False

    def init_channel_1(self):
        """
        Required for pulsing the laser externally. Pulsing only happens on channel 2 with channel 1 as the baseline.
        It is thus set to a power of 0 mW.
        @return:
        """
        self._communicate('en 1')
        self._communicate('ch 1 pow 0')
        self._communicate('en 2')

    def allowed_control_modes(self):
        """ Get available control mode of laser
          @return list: list with enum control modes
        """
        return [ControlMode.POWER]

    def get_control_mode(self):
        """ Get control mode of laser
          @return enum ControlMode: control mode
        """
        # self.log.warning(self._model_name + ' only has power control.')
        return ControlMode.POWER

    def set_control_mode(self, control_mode):
        """ Set laser control mode.
          @param enum control_mode: desired control mode
          @return enum ControlMode: actual control mode
        """
        # self.log.warning(self._model_name + ' only has power control, cannot set to mode {}'.format(mode))
        return ControlMode.POWER

    def get_power(self):
        """ Get laser power.

            @return float: laser power in watts
        """
        # The present laser output power in watts
        response = self._communicate('sh pow')
        power = float(re.search('PIC  = (.*) uW', response).group(1)) * 1e-6
        return power

    def get_power_setpoint(self):
        """ Get the laser power setpoint for Channel 2.

        @return float: laser power setpoint in watts
        """
        # The present laser power level setting in watts (set level)
        response = self._communicate('sh level pow')
        power = float(re.search('CH2, PWR:(.*) mW', response).group(1)) * 1e-3
        return power

    def get_ch1_power_setpoint(self):
        """ Get the laser power setpoint for channel 1.

          @return float: laser power setpoint in watts
          """
        # The present laser power level setting in watts (set level)
        response = self._communicate('sh level pow')
        power = float(re.search('CH1, PWR: (.*)mWCH2,', response).group(1)) * 1e-3
        return power

    def get_power_range(self):
        """ Get laser power range.

        @return tuple(float, float): laser power range
        """
        return 0, self._maxpower

    def set_power(self, power):
        """ Set laser power

        @param float power: desired laser power in watts
        """
        power *= 1e3
        self._communicate('ch 2 pow {}'.format(power))
        return self.get_power()

    def get_current_unit(self):
        """ Get unit for laser current.

        @return str: unit for laser curret
        """
        return 'A'  # amps

    def get_current_range(self):
        """ Get range for laser current.

        @return tuple(flaot, float): range for laser current
        """
        return 0, self._maxcurrent

    def get_current(self):
        """ Cet current laser current

        @return float: current laser current in amps
        """
        response = self._communicate('sh cur')
        current = float(re.search('scaledLDC  = (.*) mA', response).group(1)) * 1e-3
        return current

    def get_current_setpoint(self):
        """ Current laser current setpoint.

        @return float: laser current setpoint
        """
        return self.get_current()

    def set_current(self, current):
        """ Set laser current
        @param float current: Laser current setpoint in amperes
        @return float: Laser current setpoint in amperes
        """
        self._communicate('ch 2 cur {}'.format(current * 1e3))
        return self.get_current()

    def get_shutter_state(self):
        """ Get shutter state. Has a state for no shutter present.
          @return enum ShutterState: actual shutter state
        """
        return ShutterState.NOSHUTTER

    def set_shutter_state(self, state):
        """ Set shutter state.
          @param enum state: desired shutter state
          @return enum ShutterState: actual shutter state
        """
        self.log.warning(self._model_name + ' does not have a shutter')
        return self.get_shutter_state()

    def set_external_state(self, state):
        if state:
            self.external = True
            self._communicate("en ext")
        else:
            self.external = False
            self._communicate("di ext")
        return 0

    def get_external_state(self):
        if self.external:
            return True
        else:
            return False

    def get_temperatures(self):
        """ Get all available temperatures from laser.
          @return dict: dict of name, value for temperatures
        """
        return {
            'Diode': self._get_diode_temperature(),
            # 'Base Plate': self._get_baseplate_temperature()
        }

    def set_temperatures(self, temps):
        """ Set laser temperatures.
          @param temps: dict of name, value to be set
          @return dict: dict of name, value of temperatures that were set
        """
        self._communicate("set temp {} celsi".format(temps))
        return {'Diode': self._get_diode_temperature()}

    def get_temperature_setpoints(self):
        """ Get all available temperature setpoints from laser.
          @return dict: dict of name, value for temperature setpoints
        """
        return self.get_temperatures()

    def get_laser_state(self):
        """ Get laser state.
          @return enum LaserState: laser state
        """
        state = self._communicate('sta la')
        if 'ON' in state:
            return LaserState.ON
        elif 'OFF' in state:
            return LaserState.OFF
        else:
            return LaserState.UNKNOWN

    def set_laser_state(self, status):
        """ Set laser state.
          @param enum status: desired laser state
          @return enum LaserState: actual laser state
        """
        actual_state = self.get_laser_state()
        if actual_state != status:
            if status == LaserState.ON:
                self._communicate('la on')
                # return self.get_laser_state()
            elif status == LaserState.OFF:
                self._communicate('la off')
                # return self.get_laser_state()
            return self.get_laser_state()

    def on(self):
        """ Turn on laser. Does not open shutter if one is present.
          @return enum LaserState: actual laser state
        """
        status = self.get_laser_state()
        if status == LaserState.OFF:
            self._communicate('la on')
            return self.get_laser_state()
        else:
            return self.get_laser_state()

    def off(self):
        """ Turn off laser. Does not close shutter if one is present.
          @return enum LaserState: actual laser state
        """
        self.set_laser_state(LaserState.OFF)
        return self.get_laser_state()

    def get_extra_info(self):
        """ Show dianostic information about lasers.
          @return str: diagnostic info as a string
        """
        serial_num = re.search('SN: (.*)', self._communicate('serial')).group(1)
        firmware = self._communicate('ver')
        uptime = self._communicate("sh tim")
        system_uptime = str(float(re.search('PowerUP: (.*) sLaserUP', uptime).group(1)))
        laser_uptime = str(float(re.search('LaserUP: (.*) s', uptime).group(1)))

        extra = (
                'System Serial Number: ' + serial_num +
                '\n' + 'Firmware version: ' + firmware +
                '\n' + 'System Uptime (s): ' + system_uptime +
                '\n' + 'Laser Uptime (s): ' + laser_uptime
        )
        return extra

    """
    Communication methods
    """

    def _send(self, message):
        """ Send a message to to laser

        @param string message: message to be delivered to the laser
        """
        eol = '\r\n'
        new_message = message + eol
        self.ibeam.write(new_message.encode())

    def _communicate(self, message):
        """ Send a receive messages with the laser

        @param string message: message to be delivered to the laser

        @returns string response: message received from the laser
        """
        full_response = []
        while True:
            try:
                self._send(message)
                time.sleep(0.05)

                response_len = self.ibeam.inWaiting()
                response = []

                if response_len == 0:
                    raise ValueError

                while response_len > 0:
                    this_response_line = self.ibeam.readline().decode().strip()
                    response.append(this_response_line)
                    time.sleep(0.05)
                    response_len = self.ibeam.inWaiting()
                    if response_len == 5:
                        response.append('')
                        self.ibeam.flushInput()
                        self.ibeam.flushOutput()
                        response_len = self.ibeam.inWaiting()
                if response is None or response == '':
                    raise ValueError

                full_response = ''.join(response)
            except Exception as exc:
                self.log.debug(exc)
                continue
            break
        return full_response

    """
    Internal methods
    """
    def _get_diode_temperature(self):
        """ Get laser diode temperature

        @return float: laser diode temperature
        """
        response = self._communicate('sh temp')
        temp = float(re.search('scaledTEMP = (.*)  C', response).group(1))
        return temp

    def _get_internal_temperature(self):
        """ Get internal laser temperature

        @return float: internal laser temperature
        """
        return float(self._communicate('SOUR:TEMP:INT?').split('C')[0])

    def _get_baseplate_temperature(self):
        """ Get laser base plate temperature

        @return float: laser base plate temperature
        """
        response = self._communicate('sh temp sys')
        temp = float(re.search('TEMP = (.*) C', response).group(1))
        return temp

    def _fine_on(self):
        """ Set FINE mode on
        :return:
        """
        self._communicate("fine on")
        return 0

    def _fine_off(self):
        """ Set FINE mode off
        :return:
        """
        self._communicate("fine off")
        return 0

    def _get_fine_state(self):
        responce = self._communicate("sta fine")
        if "ON" in responce:
            return "ON"
        else:
            return "OFF"

    def _set_fine_state(self, state):
        act_state = self._get_fine_state()
        if state != act_state:
            if state == "ON":
                self._communicate("fine on")
            elif state == "OFF":
                self._communicate("fine off")
            else:
                self.log.warning("Possible FINE states are 'ON' and 'OFF'")
        return self._get_fine_state()

    def _reboot_system(self):
        """ Set FINE mode off
        :return:
        """
        self._communicate("reset sys")
        return 0
