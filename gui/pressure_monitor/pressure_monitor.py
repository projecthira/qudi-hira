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
import pyqtgraph as pg

from gui.colordefs import QudiPalettePale as palette

from core.connector import Connector
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
    pmlogic = Connector(interface='PressureMonitorLogic')

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

        # set up plot
        self._mw.plotWidget = pg.PlotWidget(
            axisItems={'bottom': TimeAxisItem(orientation='bottom')})
        self._mw.pwContainer.layout().addWidget(self._mw.plotWidget)

        plot1 = self._mw.plotWidget.getPlotItem()
        plot1.setLabel('left', 'Pressure', units='mbar', color=palette.c1.name())
        plot1.setLabel('bottom', 'Time', units=None)

        plot2 = pg.ViewBox()
        plot1.scene().addItem(plot2)
        plot1.getAxis('right').linkToView(plot2)
        plot2.setXLink(plot1)

        self.curves = {}
        colorlist = (palette.c2, palette.c3, palette.c4, palette.c5, palette.c6)
        i = 0
        for name in self._pm_logic.data:
            if name != 'time':
                curve = pg.PlotDataItem()
                if name == 'main_pressure':
                    curve.setPen(palette.c1)
                    plot1.addItem(curve)
                elif name == 'prep_pressure':
                    curve.setPen(palette.c2)
                    plot1.addItem(curve)
                elif name == 'back_pressure':
                    curve.setPen(palette.c3)
                    plot1.addItem(curve)
                else:
                    curve.setPen(colorlist[(2 * i) % len(colorlist)])
                    plot2.addItem(curve)
                self.curves[name] = curve
                i += 1

        self.plot1 = plot1
        self.plot2 = plot2
        # self.updateViews()
        # self.plot1.vb.sigResized.connect(self.updateViews)
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
        # Show any hidden dock widgets
        self._mw.plotDockWidget.show()

        # re-dock any floating dock widgets
        self._mw.plotDockWidget.setFloating(False)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(2), self._mw.plotDockWidget)

    @QtCore.Slot()
    def updateGui(self):
        """ Update labels, the plot and button states with new data. """
        if self._mw.maincheckBox.isChecked():
            if not isinstance(self._pm_logic.main_pressure, float):
                self._mw.mainPressure.setText('{}'.format(self._pm_logic.main_pressure))
                self.curves['prep_pressure'].hide()
            else:
                self._mw.mainPressure.setText('{} mbar'.format(self._pm_logic.main_pressure))
                self.curves['main_pressure'].show()
                self.curves['main_pressure'].setData(x=self._pm_logic.data['time'],
                                                     y=self._pm_logic.data['main_pressure'])
        else:
            self.curves['main_pressure'].hide()
            self._mw.mainPressure.setText('-')

        if self._mw.prepcheckBox.isChecked():
            if not isinstance(self._pm_logic.prep_pressure, float):
                self._mw.prepPressure.setText('{}'.format(self._pm_logic.prep_pressure))
                self.curves['prep_pressure'].hide()
            else:
                self._mw.prepPressure.setText('{} mbar'.format(self._pm_logic.prep_pressure))
                self.curves['prep_pressure'].show()
                self.curves['prep_pressure'].setData(x=self._pm_logic.data['time'],
                                                     y=self._pm_logic.data['prep_pressure'])
        else:
            self._mw.prepPressure.setText('-')
            self.curves['prep_pressure'].hide()

        if self._mw.backcheckBox.isChecked():
            if not isinstance(self._pm_logic.back_pressure, float):
                self._mw.backPressure.setText('{}'.format(self._pm_logic.back_pressure))
                self.curves['back_pressure'].hide()

            else:
                self._mw.backPressure.setText('{} mbar'.format(self._pm_logic.back_pressure))
                self.curves['back_pressure'].show()
                self.curves['back_pressure'].setData(x=self._pm_logic.data['time'],
                                                     y=self._pm_logic.data['back_pressure'])
        else:
            self._mw.backPressure.setText('-')
            self.curves['back_pressure'].hide()

