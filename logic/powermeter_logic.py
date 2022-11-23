# -*- coding: utf-8 -*-
__author__ = "Dinesh Pinto"
__email__ = "d.pinto@fkf.mpg.de"
"""
Powermeter Logic.

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

import time
import numpy as np
from qtpy import QtCore

from core.connector import Connector
from logic.generic_logic import GenericLogic
from core.configoption import ConfigOption


class PowermeterLogic(GenericLogic):
    """ Logic module agreggating multiple hardware switches.
    """

    pm = Connector(interface='ProcessInterface')
    calibration_param_uhv = ConfigOption("calibration_param_uhv", default=1, missing="warn")
    calibration_param_rt = ConfigOption("calibration_param_rt", default=1, missing="warn")

    sigUpdate = QtCore.Signal()

    def on_activate(self):
        """ Prepare logic module for work.
        """
        self._pm = self.pm()
        self.stopRequest = False
        self.bufferLength = 100
        self.data = {}

        self.pm_unit = self._pm.get_process_unit()

        self.init_data_logging()

    def on_deactivate(self):
        """ Deactivate module.
        """
        for i in range(5):
            QtCore.QCoreApplication.processEvents()

    @QtCore.Slot(bool)
    def get_power(self, state):
        """ Switched external driving on or off. """
        self.power = self._pm.get_process_value()
        self.calibrated_power_uhv = self.calibration_param_uhv * self.power
        self.calibrated_power_rt = self.calibration_param_rt * self.power

        for k in self.data:
            self.data[k] = np.roll(self.data[k], -1)

        if isinstance(self.power, float):
            self.data['power'][-1] = self.power
            self.data['time'][-1] = time.time()
        else:
            self.log.warn("Powermeter did not return a number")
            pass
        self.sigUpdate.emit()

    def init_data_logging(self):
        """ Zero all log buffers. """
        self.data['power'] = np.zeros(self.bufferLength)
        self.data['time'] = np.ones(self.bufferLength) * time.time()
