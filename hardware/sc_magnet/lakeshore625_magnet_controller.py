# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module to control the Lakshore 625 magnet controller.
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

Copyright (c) 2021 Dinesh Pinto. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/projecthira/qudi-hira/>
"""

import time

import serial

from core.configoption import ConfigOption
from core.module import Base
from interface.sc_magnet_interface import SCMagnetInterface


def float_to_xyz_dict(value):
    if isinstance(value, float):
        floatdict = {"x": value,
                     "y": value,
                     "z": value}
        return floatdict


class Lakeshore625(Base, SCMagnetInterface):
    """
    Driver for the Lakeshore Model 625 superconducting magnet power supply.

    This class uses T/A and A/s as units.

    Args:
        name (str): a name for the instrument
        coil_constant (float): Coil contant of magnet, in untis of T/A
        field_ramp_rate (float): Magnetic field ramp rate, in units of T/min
        address (str): VISA address of the device
    """
    # config opts
    com_port_x = ConfigOption('magnet_COM_port_x', missing='error')
    com_port_y = ConfigOption('magnet_COM_port_y', missing='error')
    com_port_z = ConfigOption('magnet_COM_port_z', missing='error')

    # default waiting time of the pc after a message was sent to the magnet
    waitingtime = ConfigOption('magnet_waitingtime_seconds', 0.15)

    x_constr = ConfigOption('magnet_x_constr_tesla', 0.01)
    y_constr = ConfigOption('magnet_y_constr_tesla', 0.01)
    z_constr = ConfigOption('magnet_z_constr_tesla', 0.02)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_activate(self):
        """
        loads the config file and extracts the necessary configurations for the
        superconducting magnet

        @return int: (0: Ok, -1:error)
        """
        # This is saves in which interval the input theta was in the last movement
        self._inter = 1
        self.field_dict = {}

        try:
            self.ser_x = serial.Serial(
                port=self.com_port_x,
                baudrate=57600,
                parity=serial.PARITY_ODD,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.SEVENBITS,
                xonxoff=False,
                rtscts=False
            )
        except serial.SerialException as exc:
            self.log.error("Error opening serial port {0}: {1}".format(self.com_port_x, exc))
            return -1

        try:
            self.ser_y = serial.Serial(
                port=self.com_port_y,
                baudrate=57600,
                parity=serial.PARITY_ODD,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.SEVENBITS,
                xonxoff=False,
                rtscts=False
            )
        except serial.SerialException as exc:
            self.log.error("Error opening serial port {0}: {1}".format(self.com_port_y, exc))
            return -1

        try:
            self.ser_z = serial.Serial(
                port=self.com_port_z,
                baudrate=57600,
                parity=serial.PARITY_ODD,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.SEVENBITS,
                xonxoff=False,
                rtscts=False
            )
        except serial.SerialException as exc:
            self.log.error("Error opening serial port {0}: {1}".format(self.com_port_z, exc))
            return -1

        self.get_ids()
        # self.set_magnetic_field_constant(0.07377)
        # self.set_quench_detection()

    def on_deactivate(self):
        self.ser_x.close()
        self.ser_y.close()
        self.ser_z.close()

    def ask(self, query_string):
        """Asks the magnet a 'question' and returns an answer from it.
        @param dictionary query_string: has to have one of the following keys: 'x', 'y' or 'z'
                                   the items have to be valid questions for the magnet.

        @return answer_dict: contains the same labels as the param_dict if it was set correct and the
                          corresponding items are the answers of the magnet (format is string), else
                          an empty dictionary is returned
        """
        answer_dict = {}
        if not query_string.endswith('\r\n'):
            query_string += '\r\n'

        self.ser_x.write(query_string.encode('ascii'))
        self.ser_y.write(query_string.encode('ascii'))
        self.ser_z.write(query_string.encode('ascii'))

        answer_dict['x'] = self.ser_x.readline().decode('ascii').rstrip()
        answer_dict['y'] = self.ser_y.readline().decode('ascii').rstrip()
        answer_dict['z'] = self.ser_z.readline().decode('ascii').rstrip()

        time.sleep(float(self.waitingtime))

        if len(answer_dict) == 0:
            self.log.warn('Query string returned empty')

        return answer_dict

    def tell(self, param_dict=None):
        """Send a command string to the magnet.
        @param dict param_dict: has to have one of the following keys: 'x', 'y' or 'z'
                                      with an appropriate command for the magnet
        """
        _internal_counter = 0
        if param_dict.get('x') is not None:
            if not param_dict['x'].endswith('\r\n'):
                param_dict['x'] += '\r\n'
            self.ser_x.write(param_dict['x'].encode('ascii'))
            _internal_counter += 1
        if param_dict.get('y') is not None:
            if not param_dict['y'].endswith('\r\n'):
                param_dict['y'] += '\r\n'
            self.ser_y.write(param_dict['y'].encode('ascii'))
            _internal_counter += 1
        if param_dict.get('z') is not None:
            if not param_dict['z'].endswith('\r\n'):
                param_dict['z'] += '\r\n'
            self.ser_z.write(param_dict['z'].encode('ascii'))
            _internal_counter += 1

        time.sleep(self.waitingtime)

        if _internal_counter == 0:
            self.log.warning('no parameter_dict was given therefore the '
                             'function tell() call was useless')
            return -1
        return 0

    def get_ids(self):
        ids = self.ask("*IDN?")
        self.log.info("Connected {}".format(ids.items()))

    def get_limits(self):
        limits = {'x': {}, 'y': {}, 'z': {}}
        limits_string = self.ask('LIMIT?')

        for axis in limits_string:
            current_limit, voltage_limit, current_rate_limit = limits_string[axis].split(',')
            limits[axis]['current_limit'] = float(current_limit)
            limits[axis]['voltage_limit'] = float(voltage_limit)
            limits[axis]['current_rate_limit'] = float(current_rate_limit)

        return limits

    def get_voltage_limit(self):
        voltage_limits = {'x': '', 'y': '', 'z': ''}

        limits = self.get_limits()
        for axis in limits:
            voltage_limits[axis] = limits[axis]["voltage_limit"]
        return voltage_limits

    def get_quench_detection_setup(self):
        qd = {'x': {}, 'y': {}, 'z': {}}
        qd_string = self.ask('QNCH?')

        for axis in qd_string:
            status, current_step_limit = qd_string[axis].split(',')
            qd[axis]['status'] = int(status)
            qd[axis]['current_step_limit'] = float(current_step_limit)

        return qd

    def get_field_setup(self):
        field = {'x': {}, 'y': {}, 'z': {}}
        field_string = self.ask('FLDS?')

        for axis in field_string:
            unit, coil_constant = field_string[axis].split(',')
            field[axis]['unit'] = str(unit)
            field[axis]['coil_constant'] = float(coil_constant)

        return field

    def get_current(self):
        current = self.ask("RDGI?")
        for axis in current:
            current[axis] = float(current[axis])
        return current

    def get_voltage(self):
        voltage = self.ask("RDGV?")
        for axis in voltage:
            voltage[axis] = float(voltage[axis])
        return voltage

    def get_mode(self):
        mode = self.ask("MODE?")
        return mode

    def get_ramping_state(self):
        ramping_state = {'x': False, 'y': False, 'z': False}
        operation_condition_register = self.ask('OPST?')

        for axis in operation_condition_register:
            bin_OPST = bin(int(operation_condition_register[axis]))[2:]
            if len(bin_OPST) < 2:
                rampbit = 1
            else:
                # read second bit, 0 = ramping, 1 = not ramping
                rampbit = int(bin_OPST[-2])

            if rampbit == 1:
                ramping_state[axis] = False
            else:
                ramping_state[axis] = True

        return ramping_state

    def get_quench_state(self):
        quench_state = {'x': False, 'y': False, 'z': False}
        error_status_register = self.ask('ERST?')

        for axis in error_status_register:
            # three bytes are read at the same time, the middle one is the operational error status
            operational_error_register = error_status_register[axis].split(',')[1]
            # remove the first two letters indicating binary
            bin_ERST = bin(int(operational_error_register))[2:]
            if len(bin_ERST) < 6:
                # quench bit appears at position 6
                quench_state[axis] = False
            else:
                # read sixth bit, 0 = not quenched, 1 = quenched
                quench_state[axis] = bool(int(bin_ERST[-6]))

        return quench_state

    def get_current_ramp_rate(self):
        current_ramp_rate = self.ask('RATE?')
        for axis in current_ramp_rate:
            current_ramp_rate[axis] = float(current_ramp_rate[axis])
        return current_ramp_rate

    def get_current_setpoint(self):
        current_setpoint = self.ask('SETI?')
        for axis in current_setpoint:
            current_setpoint[axis] = float(current_setpoint[axis])
        return current_setpoint

    def set_current_limit(self, current_limit_setpoint):
        current_limit = {'x': '', 'y': '', 'z': ''}

        if not isinstance(current_limit_setpoint, dict):
            current_limit_setpoint = float_to_xyz_dict(current_limit_setpoint)

        limits = self.get_limits()

        for axis in limits:
            current_limit[axis] = 'LIMIT {}, {}, {}'.format(current_limit_setpoint[axis],
                                                            limits[axis]['voltage_limit'],
                                                            limits[axis]['current_rate_limit'])

        self.tell(current_limit)

    def set_voltage_limit(self, voltage_limit_setpoint):
        # TODO: Does not seem to work, even though device reports set voltage limit
        voltage_limit = {'x': '', 'y': '', 'z': ''}

        if not isinstance(voltage_limit_setpoint, dict):
            voltage_limit_setpoint = float_to_xyz_dict(voltage_limit_setpoint)

        limits = self.get_limits()

        for axis in limits:
            voltage_limit[axis] = 'LIMIT {},{},{}'.format(limits[axis]['current_limit'],
                                                          voltage_limit_setpoint[axis],
                                                          limits[axis]['current_rate_limit'])

        self.tell(voltage_limit)

    def set_current_setpoint(self, current_setpoint):
        current_setpoint_dict = {'x': '', 'y': '', 'z': ''}

        if not isinstance(current_setpoint, dict):
            current_setpoint = float_to_xyz_dict(current_setpoint)

        for axis in current_setpoint_dict:
            current_setpoint_dict[axis] = 'SETI {}'.format(current_setpoint[axis])

        self.tell(current_setpoint_dict)

    def set_current_rate_limit(self, current_rate_limit_setpoint):
        current_rate_limit = {'x': '', 'y': '', 'z': ''}

        if not isinstance(current_rate_limit_setpoint, dict):
            current_rate_limit_setpoint = float_to_xyz_dict(current_rate_limit_setpoint)

        limits = self.get_limits()

        for axis in limits:
            current_rate_limit[axis] = 'LIMIT {}, {}, {}'.format(limits[axis]['current_limit'],
                                                                 limits[axis]['voltage_limit'],
                                                                 current_rate_limit_setpoint[axis])

        self.tell(current_rate_limit)

    def set_quench_detection_status(self, quench_detection_setpoint):
        quench_detection_status = {'x': '', 'y': '', 'z': ''}

        if not isinstance(quench_detection_setpoint, dict):
            quench_detection_setpoint = float_to_xyz_dict(quench_detection_setpoint)

        quench_detection_setup = self.get_quench_detection_setup()

        for axis in quench_detection_setup:
            quench_detection_status[axis] = 'QNCH {}, {}'.format(quench_detection_setpoint[axis],
                                                                 quench_detection_setup[axis]['current_step_limit'])

        self.tell(quench_detection_status)

    def set_quench_current_step_limit(self, current_step_limit_setpoint):
        quench_current_step_limit = {'x': '', 'y': '', 'z': ''}

        if not isinstance(current_step_limit_setpoint, dict):
            current_step_limit_setpoint = float_to_xyz_dict(current_step_limit_setpoint)

        quench_detection_setup = self.get_quench_detection_setup()

        for axis in quench_detection_setup:
            quench_current_step_limit[axis] = 'QNCH {}, {}'.format(quench_detection_setup[axis]['status'],
                                                                   current_step_limit_setpoint[axis])

        self.tell(quench_current_step_limit)

    def set_coil_constant(self, coil_constant_setpoint):
        coil_constant = {'x': '', 'y': '', 'z': ''}

        if not isinstance(coil_constant_setpoint, dict):
            coil_constant_setpoint = float_to_xyz_dict(coil_constant_setpoint)

        field_setup = self.get_field_setup()

        for axis in field_setup:
            coil_constant[axis] = 'FLDS 0, {}'.format(coil_constant_setpoint[axis])

        self.tell(coil_constant)

    def set_current_ramp_rate(self, current_ramp_rate_setpoint):
        current_ramp_rate = {'x': '', 'y': '', 'z': ''}

        if not isinstance(current_ramp_rate_setpoint, dict):
            current_ramp_rate_setpoint = float_to_xyz_dict(current_ramp_rate_setpoint)

        for axis in current_ramp_rate:
            current_ramp_rate[axis] = 'RATE {}'.format(current_ramp_rate_setpoint[axis])

        self.tell(current_ramp_rate)

    def set_field(self, field_setpoint):
        field = {'x': '', 'y': '', 'z': ''}

        if not isinstance(field_setpoint, dict):
            field_setpoint = float_to_xyz_dict(field_setpoint)

        for axis in field:
            field = 'SETF {}'.format(field_setpoint[axis])

        self.tell(field)

    def clear_errors(self, error_clear_dict):
        error_clear = {'x': None, 'y': None, 'z': None}

        for axis in error_clear_dict:
            if error_clear_dict[axis]:
                error_clear[axis] = 'ERRCL'

        self.tell(error_clear)
        self.log.info("ERROR CLEARED ON {}".format(error_clear_dict))
