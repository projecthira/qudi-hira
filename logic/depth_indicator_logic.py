# -*- coding: utf-8 -*-
__author__ = "Dinesh Pinto"
__email__ = "d.pinto@fkf.mpg.de"
"""
Helium Depth Indicator logic.

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
from core.configoption import ConfigOption
from logic.generic_logic import GenericLogic


class DepthIndicatorLogic(GenericLogic):
    """ Logic module agreggating multiple hardware switches.
    """

    hdi = Connector(interface='ProcessInterface')

    sigUpdate = QtCore.Signal()

    def on_activate(self):
        """ Prepare logic module for work.
        """
        self._hdi = self.hdi()
        self.stopRequest = False
        self.bufferLength = 100
        self.data = {}

        self.hdi_unit = self._hdi.get_process_unit()

        self.init_data_logging()

    def on_deactivate(self):
        """ Deactivate module.
        """
        for i in range(5):
            QtCore.QCoreApplication.processEvents()

    @QtCore.Slot(bool)
    def measure_depth(self, state):
        """ Switched external driving on or off. """
        self.helium_depth = self._hdi.get_process_value()

        for k in self.data:
            self.data[k] = np.roll(self.data[k], -1)

        if isinstance(self.helium_depth, float):
            self.data['helium_depth'][-1] = self.helium_depth
            self.data['time'][-1] = time.time()
        else:
            self.log.warn("HDI did not return a number")
            pass
        self.sigUpdate.emit()

    def maximum_depth(self):
        return self._hdi.get_process_value_maximum()

    def init_data_logging(self):
        """ Zero all log buffers. """
        self.data['helium_depth'] = np.zeros(self.bufferLength)
        self.data['time'] = np.ones(self.bufferLength) * time.time()
