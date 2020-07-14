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

        self.curves = {}
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
                self.curves[name] = curve
                i += 1

        self.plot1 = plot1

        self._mw.record_pressure_Action.triggered.connect(self.save_clicked)

        # self.updateViews()
        # self.plot1.vb.sigResized.connect(self.updateViews)
        self._pm_logic.sigSavingStatusChanged.connect(self.update_saving_Action)
        self._pm_logic.sigUpdate.connect(self.updateGui)

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._pm_logic.sigSavingStatusChanged.disconnect()
        self._mw.record_pressure_Action.triggered.disconnect()
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
        if self._pm_logic.get_saving_state():
            self._mw.record_pressure_Action.setText('Save')
        else:
            self._mw.record_pressure_Action.setText('Start Saving Data')

        if self._mw.maincheckBox.isChecked():
            pressure = self._pm_logic.data['main'][-1]
            if pressure == -1:
                self._mw.mainPressure.setText('{}'.format(self._pm_logic.pressure_state))
                self.curves['main'].hide()
            else:
                self._mw.mainPressure.setText('{} mbar'.format(pressure))
                self.curves['main'].show()
                self.curves['main'].setData(x=self._pm_logic.data['time'],
                                            y=self._pm_logic.data['main'])
        else:
            self.curves['main'].hide()
            self._mw.mainPressure.setText('-')

        if self._mw.prepcheckBox.isChecked():
            pressure = self._pm_logic.data['prep'][-1]
            if pressure == -1:
                self._mw.prepPressure.setText('{}'.format(self._pm_logic.pressure_state))
                self.curves['prep'].hide()
            else:
                self._mw.prepPressure.setText('{} mbar'.format(pressure))
                self.curves['prep'].show()
                self.curves['prep'].setData(x=self._pm_logic.data['time'],
                                            y=self._pm_logic.data['prep'])
        else:
            self.curves['main'].hide()
            self._mw.prepPressure.setText('-')

        if self._mw.backcheckBox.isChecked():
            pressure = self._pm_logic.data['back'][-1]
            if pressure == -1:
                self._mw.backPressure.setText('{}'.format(self._pm_logic.pressure_state))
                self.curves['back'].hide()
            else:
                self._mw.backPressure.setText('{} mbar'.format(pressure))
                self.curves['back'].show()
                self.curves['back'].setData(x=self._pm_logic.data['time'],
                                            y=self._pm_logic.data['back'])
        else:
            self.curves['back'].hide()
            self._mw.backPressure.setText('-')

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        if self._pm_logic.get_saving_state():
            self._mw.record_pressure_Action.setText('Start Saving Data')
            self._pm_logic.save_data()
        else:
            self._mw.record_pressure_Action.setText('Save')
            self._pm_logic.start_saving()
        return self._pm_logic.get_saving_state()

    def update_saving_Action(self, start):
        """Function to ensure that the GUI-save_action displays the current status

        @param bool start: True if the measurment saving is started
        @return bool start: see above
        """
        if start:
            self._mw.record_pressure_Action.setText('Save')
        else:
            self._mw.record_pressure_Action.setText('Start Saving Data')
        return start