# -*- coding: utf-8 -*-
__author__ = "Dinesh Pinto"
__email__ = "d.pinto@fkf.mpg.de"
"""
This file contains a gui for the temperature monitor logic.

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

import os
import time

from core.connector import Connector
from gui.guibase import GUIBase
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic


class MainGUIWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_pressure_monitor.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class PressureMonitorGUI(GUIBase):
    """ FIXME: Please document
    """

    ## declare connectors
    pmlogic = Connector(interface='PressureMonitorLogic')

    sigPower = QtCore.Signal(float)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """
        self._pm_logic = self.pmlogic()

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = MainGUIWindow()

        # Setup dock widgets
        self._mw.setDockNestingEnabled(True)
        self._mw.actionReset_View.triggered.connect(self.restoreDefaultView)

        self._pm_logic.sigUpdate.connect(self.updateGui)

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._mw.close()

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()

    def restoreDefaultView(self):
        pass

    @QtCore.Slot()
    def updateGui(self):
        """ Update labels, the plot and button states with new data. """
        if self._mw.maincheckBox.isChecked():
            self._mw.mainPressure.setText('{} mbar'.format(self._pm_logic.main_pressure))
        else:
            self._mw.mainPressure.setText('-')

        if self._mw.prepcheckBox.isChecked():
            self._mw.prepPressure.setText('{} mbar'.format(self._pm_logic.prep_pressure))
        else:
            self._mw.prepPressure.setText('-')

        if self._mw.backcheckBox.isChecked():
            self._mw.backPressure.setText('{} mbar'.format(self._pm_logic.back_pressure))
        else:
            self._mw.backPressure.setText('-')
