# -*- coding: utf-8 -*-

"""
This file contains the Qudi Interface file to control magnet devices.
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

from core.interface import abstract_interface_method
from core.meta import InterfaceMetaclass


class SCMagnetInterface(metaclass=InterfaceMetaclass):
    """ This is the Interface class to define the controls for the devices
        controlling the magnetic field.
    """

    @abstract_interface_method
    def ask(self, query_string):
        pass

    @abstract_interface_method
    def tell(self, param_dict=None):
        """ Send a command to the magnet.

        @param dict param_dict: dictionary, which passes all the relevant
                                parameters, which should be changed. Usage:
                                 {'axis_label': <the command string>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return int: error code (0:OK, -1:error)
        """
        pass

    @abstract_interface_method
    def get_limits(self):
        pass

    @abstract_interface_method
    def get_current(self):
        pass

    @abstract_interface_method
    def get_voltage(self):
        pass

    @abstract_interface_method
    def get_current_setpoint(self):
        pass

    @abstract_interface_method
    def get_quench_detection_setup(self):
        pass

    @abstract_interface_method
    def get_field_setup(self):
        pass

    @abstract_interface_method
    def get_ramping_state(self):
        pass

    @abstract_interface_method
    def get_current_ramp_rate(self):
        pass

    @abstract_interface_method
    def get_quench_state(self):
        pass

    @abstract_interface_method
    def set_current_limit(self, current_limit_setpoint):
        pass

    @abstract_interface_method
    def set_voltage_limit(self, voltage_limit_setpoint):
        pass

    @abstract_interface_method
    def set_current_rate_limit(self, current_rate_limit_setpoint):
        pass

    @abstract_interface_method
    def set_quench_detection_status(self, quench_detection_setpoint):
        pass

    @abstract_interface_method
    def set_quench_current_step_limit(self, current_step_limit_setpoint):
        pass

    @abstract_interface_method
    def set_coil_constant(self, coil_constant_setpoint):
        pass

    @abstract_interface_method
    def set_current_ramp_rate(self, current_ramp_rate_setpoint):
        pass

    @abstract_interface_method
    def set_field(self, field_setpoint):
        pass
