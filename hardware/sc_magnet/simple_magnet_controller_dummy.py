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

from core.module import Base
from interface.sc_magnet_interface import SCMagnetInterface
import random


class SimpleMagnetDummy(Base, SCMagnetInterface):
    """ This is the Interface class to define the controls for the devices
        controlling the magnetic field.
    """

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        self.log.warning('simplemagnetdummy>activation')

    def on_deactivate(self):
        self.log.warning('simplemagnetdummy>deactivation')

    def ask(self, query_string):
        pass

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

    def get_limits(self):
        pass

    def get_current(self):
        return {"x": random.uniform(0.1, 10), "y": random.uniform(0.1, 10), "z": random.uniform(0.1, 10)}

    def get_current_setpoint(self):
        return {"x": random.uniform(0.1, 10), "y": random.uniform(0.1, 10), "z": random.uniform(0.1, 10)}

    def get_voltage(self):
        return {"x": random.uniform(0.1, 5), "y": random.uniform(0.1, 5), "z": random.uniform(0.1, 5)}

    def get_quench_detection_setup(self):
        pass

    def get_field_setup(self):
        pass

    def get_ramping_state(self):
        pass

    def get_current_ramp_rate(self):
        lower = 0.0001
        upper = 99.999
        return {"x": random.uniform(lower, upper), "y": random.uniform(lower, upper), "z": random.uniform(lower, upper)}

    def get_operational_errors(self):
        pass

    def get_quench_state(self):
        quench_bit = {'x': bool(random.getrandbits(1)), 'y': bool(random.getrandbits(1)), 'z': bool(random.getrandbits(1))}
        return quench_bit

    def set_current_limit(self, current_limit_setpoint):
        pass

    def set_voltage_limit(self, voltage_limit_setpoint):
        pass

    def set_current_rate_limit(self, current_rate_limit_setpoint):
        pass

    def set_quench_detection_status(self, quench_detection_setpoint):
        pass

    def set_quench_current_step_limit(self, current_step_limit_setpoint):
        pass

    def set_coil_constant(self, coil_constant_setpoint):
        pass

    def set_current_ramp_rate(self, current_ramp_rate_setpoint):
        pass

    def set_field(self, field_setpoint):
        pass
