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


class PowermeterLogic(GenericLogic):
    """ Logic module agreggating multiple hardware switches.
    """

    pm = Connector(interface='ProcessInterface')
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

    @staticmethod
    def calibrated_value(power):
        """
        Calculate power at objective from power at beamsplitter.
        Calibration extracted from fit up to 100 mW of laser power (20210610_OpticalAlignment.xlsx).

        eg.
            f(x) =  a*x + b
            where,
            a = 1.1773
            b = 0.0786
        @return: calibrated power value
        """
        power_mW = power * 1000
        a = 1.1773
        b = 0
        return a * power_mW + b

    @QtCore.Slot(bool)
    def get_power(self, state):
        """ Switched external driving on or off. """
        self.power = self._pm.get_process_value()
        self.calibrated_power_mW = self.calibrated_value(self.power)

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
