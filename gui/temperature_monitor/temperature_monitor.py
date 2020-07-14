# -*- coding: utf-8 -*-
"""
This file contains a gui for the temperature monitor logic.
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

Copyright (c) 2020 Dinesh Pinto. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/projecthira/qudi-hira/>
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


class MainGUIWindow(QtWidgets.QMainWindow):
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
        self._mw = MainGUIWindow()

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
                if name == 'baseplate':
                    curve.setPen(palette.c1)
                    plot1.addItem(curve)
                elif name == 'tip':
                    curve.setPen(palette.c2)
                    plot1.addItem(curve)
                elif name == 'sample':
                    curve.setPen(palette.c3)
                    plot1.addItem(curve)
                self.curves[name] = curve
                i += 1

        self.plot1 = plot1
        self._mw.record_temperature_Action.triggered.connect(self.save_clicked)

        # self.updateViews()
        # self.plot1.vb.sigResized.connect(self.updateViews)
        self._tm_logic.sigSavingStatusChanged.connect(self.update_saving_Action)
        self._tm_logic.sigUpdate.connect(self.updateGui)

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._tm_logic.sigSavingStatusChanged.disconnect()
        self._mw.record_temperature_Action.triggered.disconnect()
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
            self.curves['baseplate'].show()
            self._mw.baseplateTemperature.setText('{0:6.3f} K'.format(self._tm_logic.data['baseplate'][-1]))
            self.curves['baseplate'].setData(x=self._tm_logic.data['time'], y=self._tm_logic.data['baseplate'])
        else:
            self.curves['baseplate'].hide()
            self._mw.baseplateTemperature.setText('-')

        if self._mw.tipcheckBox.isChecked():
            self.curves['tip'].show()
            self._mw.tipTemperature.setText('{0:6.3f} K'.format(self._tm_logic.data['tip'][-1]))
            self.curves['tip'].setData(x=self._tm_logic.data['time'], y=self._tm_logic.data['tip'])
        else:
            self.curves['tip'].hide()
            self._mw.tipTemperature.setText('-')

        if self._mw.samplecheckBox.isChecked():
            self.curves['sample'].show()
            self._mw.sampleTemperature.setText('{0:6.3f} K'.format(self._tm_logic.data['sample'][-1]))
            self.curves['sample'].setData(x=self._tm_logic.data['time'], y=self._tm_logic.data['sample'])
        else:
            self.curves['sample'].hide()
            self._mw.sampleTemperature.setText('-')

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        if self._tm_logic.get_saving_state():
            self._mw.record_temperature_Action.setText('Start Saving Data')
            self._tm_logic.save_data()
        else:
            self._mw.record_temperature_Action.setText('Save')
            self._tm_logic.start_saving()
        return self._tm_logic.get_saving_state()

    def update_saving_Action(self, start):
        """Function to ensure that the GUI-save_action displays the current status

        @param bool start: True if the measurment saving is started
        @return bool start: see above
        """
        if start:
            self._mw.record_temperature_Action.setText('Save')
        else:
            self._mw.record_temperature_Action.setText('Start Saving Data')
        return start