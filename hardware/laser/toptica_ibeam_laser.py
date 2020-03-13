# -*- coding: utf-8 -*-
"""
This file contains the Qudi hardware file to control Toptica iBeam Smart lasers.

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
from interface.simple_laser_interface import SimpleLaserInterface, ControlMode, LaserState, ShutterState
import visa
from pyvisa.constants import Parity, StopBits


class TopticaIBeamLaser(Base, SimpleLaserInterface):
    """ Toptica iBeam Smart laser.

    Example config for copy-paste:

    millennia_laser:
        module.Class: 'laser.toptica_ibeam_laser.TopticaIBeamLaser'
        interface: 'ASRL1::INSTR'
        maxpower: 100 # in mW
        maxcurrent: 200.0 # in mA
    """

    interface = ConfigOption('interface', 'ASRL1::INSTR', missing='error')
    maxpower = ConfigOption('maxpower', 0.1, missing='warn')
    maxcurrent = ConfigOption('maxcurrent', 0.2, missing='warn')
    current = 0.001
    power = 0.001
    temperature = 25.0

    def on_activate(self):
        """ Activate Module. Connect to Instrument.

            @param str interface: visa interface identifier

            @return bool: connection success
        """
        try:
            self.rm = visa.ResourceManager()
            self.inst = self.rm.open_resource(
                self.interface,
                baud_rate=115200,
                data_bits=8,
                parity=Parity.none,
                stop_bits=StopBits.one,
                write_termination='\r\n',
                read_termination='\r\n'
            )
            self.inst.timeout = 1000
            self.inst.write('ini la')
        except visa.VisaIOError as e:
            self.log.exception('Communication Failure:', e)
            return False
        else:
            return True

    def on_deactivate(self):
        """ Close the connection to the instrument.
        """
        self.inst.close()
        self.rm.close()

    def allowed_control_modes(self):
        """ Control modes for this laser

            @return ControlMode: available control modes
        """
        return [ControlMode.POWER]

    def get_control_mode(self):
        """ Get active control mode

        @return ControlMode: active control mode
        """
        return ControlMode.POWER

    def set_control_mode(self, control_mode):
        """ Set actve control mode

        @param ControlMode mode: desired control mode
        @return ControlMode: actual control mode
        """
        return ControlMode.POWER

    def get_power(self):
        """ Current laser power

        @return float: laser power in watts
        """
        return self.power

    def get_power_setpoint(self):
        """ Current laser power setpoint

        @return float: power setpoint in watts
        """
        return self.power

    def get_power_range(self):
        """ Laser power range

        @return (float, float): laser power range
        """
        return 0, self.maxpower

    def set_power(self, power):
        """ Set laser power setpoint

        @param float power: desired laser power in mW

        @return float: actual laser power setpoint
        """
        power_mW = power * 1e3
        self.inst.write('ch 1 pow {}'.format(power_mW))
        self.power = power
        return self.get_power()

    def get_current_unit(self):
        """ Get unit for current

            return str: unit for laser current
        """
        return 'A'

    def get_current_range(self):
        """ Get range for laser current

            @return (float, float): range for laser current
        """
        return 0, self.maxcurrent

    def get_current(self):
        """ Get current laser current

        @return float: current laser current
        """
        return self.current

    def get_current_setpoint(self):
        """ Get laser current setpoint

        @return float: laser current setpoint
        """
        return self.current

    def set_current(self, current):
        """ Set laser current setpoint

        @param float current_mA: Laser current setpoint in amperes
        @return float: Laser current setpoint in amperes
        """
        if current > self.maxcurrent:
            self.log.error("Laser current {} above maxcurrent {}".format(current))
        elif current < 0:
            self.log.error("Laser current {} too low".format(current))
        else:
            current_mA = current * 1e3
            self.inst.write('ch 1 cur {}'.format(current_mA))

        self.current = current
        return self.get_current()

    def get_shutter_state(self):
        """ Get laser shutter state

        @return ShutterState: current laser shutter state
        """
        return ShutterState.NOSHUTTER

    def set_shutter_state(self, state):
        """ Set laser shutter state.

        @param ShuterState state: desired laser shutter state
        @return ShutterState: actual laser shutter state
        """
        return ShutterState.NOSHUTTER

    def get_heatsink_temperature(self):
        """ Get heatsink temperature.

            @return float: SHG crystal temperature in degrees Celsius
        """
        pass

    def get_diode_temperature(self):
        """ Get laser diode temperature.

            @return float: laser diode temperature in degrees Celsius
        """
        pass

    def get_temperatures(self):
        """ Get all available temperatures

            @return dict: tict of temperature names and values
        """
        return self.temperature

    def set_temperatures(self, temp):
        """ Set temperatures for lasers wth tunable temperatures

        """
        self.inst.write('set 1 temp {} celsi'.format(temp))
        self.temperature = temp
        return self.get_temperatures()

    def get_temperature_setpoints(self):
        """ Get tepmerature setpoints.

            @return dict: setpoint name and value
        """
        return self.temperature

    def get_laser_state(self):
        """ Get laser state.
        @return LaserState: current laser state
        """
        if LaserState.ON:
            return LaserState.ON
        elif LaserState.OFF:
            return LaserState.OFF
        else:
            return LaserState.UNKNOWN

    def set_laser_state(self, state):
        """ Set laser state

        @param LaserState state: desired laser state
        @return LaserState: actual laser state
        """
        actual_state = self.get_laser_state()

        if actual_state != state:
            if state == LaserState.ON:
                self.inst.write('la on')
            elif state == LaserState.OFF:
                self.inst.write('la off')

        return self.get_laser_state()

    def on(self):
        """ Turn laser on.

            @return LaserState: actual laser state
        """
        return self.set_laser_state(LaserState.ON)

    def off(self):
        """ Turn laser off.

            @return LaserState: actual laser state
        """
        return self.set_laser_state(LaserState.OFF)

    def get_extra_info(self):
        pass
