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
import pyqtgraph as pg
import time

from core.connector import Connector
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic


class TimeAxisItem(pg.AxisItem):
    """ pyqtgraph AxisItem that shows a HH:MM:SS timestamp on ticks.
        X-Axis must be formatted as (floating point) Unix time.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enableAutoSIPrefix(False)

    def tickStrings(self, values, scale, spacing):
        """ Hours:Minutes:Seconds string from float unix timestamp. """
        return [time.strftime("%H:%M:%S", time.localtime(value)) for value in values]


class LaserWindow(QtWidgets.QMainWindow):
    """ Create the Main Window based on the *.ui file. """

    def __init__(self):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_temperature_monitor.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class TemperatureMonitorGUI(GUIBase):
    """ FIXME: Please document
    """

    ## declare connectors
    tmlogic = Connector(interface='TemperatureMonitorLogic')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """
        self._tm_logic = self.tmlogic()

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = LaserWindow()

        # Setup dock widgets
        self._mw.setDockNestingEnabled(True)
        self._mw.actionReset_View.triggered.connect(self.restoreDefaultView)

        # set up plot
        self._mw.plotWidget = pg.PlotWidget(
            axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self._mw.pwContainer.layout().addWidget(self._mw.plotWidget)

        plot1 = self._mw.plotWidget.getPlotItem()
        plot1.setLabel('left', 'Temperature', units='K', color=palette.c1.name())
        plot1.setLabel('bottom', 'Time', units=None)

        self.curves = {}
        i = 0
        for name in self._tm_logic.data:
            if name != 'time':
                curve = pg.PlotDataItem()
                if name == 'baseplate_temp':
                    curve.setPen(palette.c1)
                    plot1.addItem(curve)
                elif name == 'tip_temp':
                    curve.setPen(palette.c2)
                    plot1.addItem(curve)
                elif name == 'sample_temp':
                    curve.setPen(palette.c3)
                    plot1.addItem(curve)
                self.curves[name] = curve
                i += 1

        self.plot1 = plot1
        self._tm_logic.sigUpdate.connect(self.updateGui)

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
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.plotDockWidget.show()

        # re-dock any floating dock widgets
        self._mw.plotDockWidget.setFloating(False)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.plotDockWidget)

    @QtCore.Slot()
    def updateGui(self):
        """ Update labels, the plot and button states with new data. """
        if self._mw.baseplatecheckBox.isChecked():
            self.curves['baseplate_temp'].show()
            self._mw.baseplateTemperature.setText('{0:6.3f} K'.format(self._tm_logic.baseplate_temp))
            self.curves['baseplate_temp'].setData(x=self._tm_logic.data['time'],
                                                  y=self._tm_logic.data['baseplate_temp'])
        else:
            self.curves['baseplate_temp'].hide()
            self._mw.baseplateTemperature.setText('-')

        if self._mw.samplecheckBox.isChecked():
            self.curves['sample_temp'].show()
            self._mw.sampleTemperature.setText('{0:6.3f} K'.format(self._tm_logic.sample_temp))
            self.curves['sample_temp'].setData(x=self._tm_logic.data['time'], y=self._tm_logic.data['sample_temp'])
        else:
            self.curves['sample_temp'].hide()
            self._mw.sampleTemperature.setText('-')

        if self._mw.tipcheckBox.isChecked():
            self.curves['tip_temp'].show()
            self._mw.tipTemperature.setText('{0:6.3f} K'.format(self._tm_logic.tip_temp))
            self.curves['tip_temp'].setData(x=self._tm_logic.data['time'], y=self._tm_logic.data['tip_temp'])
        else:
            self.curves['tip_temp'].hide()
            self._mw.tipTemperature.setText('-')
