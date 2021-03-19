# -*- coding: utf-8 -*-
"""
This file contains a gui for the pressure monitor logic.
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
import time

import pyqtgraph as pg
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic

from core.connector import Connector
from gui.guibase import GUIBase


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
        ui_file = os.path.join(this_dir, 'ui_sc_magnet.ui')

        # Load it
        super().__init__()
        uic.loadUi(ui_file, self)
        self.show()


class SCMagnetGUI(GUIBase):
    """ FIXME: Please document
    """
    mclogic = Connector(interface='SCMagnetLogic')
    sigQueryIntervalChanged = QtCore.Signal(int)
    sigMagnetCurrentSetpointChanged = QtCore.Signal(dict)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

    def on_activate(self):
        """ Definition and initialisation of the GUI plus staring the measurement.
        """
        self._mc_logic = self.mclogic()

        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = MainGUIWindow()

        # Setup dock widgets
        self._mw.setDockNestingEnabled(True)
        self._mw.actionReset_View.triggered.connect(self.restoreDefaultView)

        self._mw.actionRecord_Magnet.triggered.connect(self.save_clicked)
        self._mw.actionClear_Buffer.triggered.connect(self.clear_buffer_clicked)
        self._mw.actionSendCommand.triggered.connect(self.send_commands)
        self._mw.magnet_z_clear_errors_pushButton.clicked.connect(self.magnet_z_clear_errors_clicked)

        # self.updateViews()
        # self.plot1.vb.sigResized.connect(self.updateViews)
        self._mc_logic.sigSavingStatusChanged.connect(self.update_saving_Action)
        self._mc_logic.sigUpdate.connect(self.updateGui)

        self.sigQueryIntervalChanged.connect(self._mc_logic.change_qtimer_interval)
        self._mw.queryIntervalSpinBox.valueChanged.connect(self.update_query_interval)

        self._mw.queryIntervalSpinBox.setValue(self._mc_logic.queryInterval)

        # Required to autostart loop on launch
        self.update_query_interval()

        quench_setup = self._mc_logic.get_quench_detection_setup()
        self._mw.magnet_x_quench_setup_label.setText('Quench detection: {} \n ({:.2f} A/s)'
                                                     .format(bool(quench_setup["x"]["status"]),
                                                             quench_setup["x"]["current_step_limit"]))
        self._mw.magnet_y_quench_setup_label.setText('Quench detection: {} \n ({:.2f} A/s)'
                                                     .format(bool(quench_setup["y"]["status"]),
                                                             quench_setup["y"]["current_step_limit"]))
        self._mw.magnet_z_quench_setup_label.setText('Quench detection: {} \n ({:.2f} A/s)'
                                                     .format(bool(quench_setup["z"]["status"]),
                                                             quench_setup["z"]["current_step_limit"]))

        self._mw.magnet_x_quenchbit.setStyleSheet('color: gray')
        self._mw.magnet_y_quenchbit.setStyleSheet('color: gray')
        self._mw.magnet_z_quenchbit.setStyleSheet('color: gray')

    def on_deactivate(self):
        """ Deactivate the module properly.
        """
        self._mc_logic.sigSavingStatusChanged.disconnect()
        self._mc_logic.sigUpdate.disconnect()
        self._mw.actionRecord_Magnet.triggered.disconnect()
        self._mw.actionClear_Buffer.triggered.disconnect()
        self._mw.actionSendCommand.triggered.disconnect()
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
    def magnet_z_clear_errors_clicked(self):
        self._mc_logic.clear_errors({"x": False, "y": False, "z": True})

    @QtCore.Slot()
    def update_query_interval(self):
        self.sigQueryIntervalChanged.emit(self._mw.queryIntervalSpinBox.value())

    @QtCore.Slot()
    def updateGui(self):
        """ Update labels, the plot and button states with new data. """

        self._mw.magnet_x_current.setText('Output I = {:.4f} A'.format(self._mc_logic.data['current_x'][-1]))
        self._mw.magnet_y_current.setText('Output I = {:.4f} A'.format(self._mc_logic.data['current_y'][-1]))
        self._mw.magnet_z_current.setText('Output I = {:.4f} A'.format(self._mc_logic.data['current_z'][-1]))

        self._mw.magnet_x_voltage.setText('Output V = {:.4f} V'.format(self._mc_logic.data['voltage_x'][-1]))
        self._mw.magnet_y_voltage.setText('Output V = {:.4f} V'.format(self._mc_logic.data['voltage_y'][-1]))
        self._mw.magnet_z_voltage.setText('Output V = {:.4f} V'.format(self._mc_logic.data['voltage_z'][-1]))

        self._mw.magnet_x_ramp_rate.setText('Ramp Rate = {:.4f} A/s'.format(self._mc_logic.data['ramp_rate_x'][-1]))
        self._mw.magnet_y_ramp_rate.setText('Ramp Rate = {:.4f} A/s'.format(self._mc_logic.data['ramp_rate_y'][-1]))
        self._mw.magnet_z_ramp_rate.setText('Ramp Rate = {:.4f} A/s'.format(self._mc_logic.data['ramp_rate_z'][-1]))

        self._mw.magnet_x_setpoint_current.setText(
            'Set I = {:.4f} A'.format(self._mc_logic.data['current_setpoint_x'][-1]))
        self._mw.magnet_y_setpoint_current.setText(
            'Set I = {:.4f} A'.format(self._mc_logic.data['current_setpoint_y'][-1]))
        self._mw.magnet_z_setpoint_current.setText(
            'Set I = {:.4f} A'.format(self._mc_logic.data['current_setpoint_z'][-1]))

        self._mw.magnet_x_voltage_limit.setText('Limit V = {:.4f} V'.format(self._mc_logic.data['voltage_limit_x'][-1]))
        self._mw.magnet_y_voltage_limit.setText('Limit V = {:.4f} V'.format(self._mc_logic.data['voltage_limit_y'][-1]))
        self._mw.magnet_z_voltage_limit.setText('Limit V = {:.4f} V'.format(self._mc_logic.data['voltage_limit_z'][-1]))

        if self._mc_logic.data['quench_state_x'][-1]:
            self._mw.magnet_x_quenchbit.setText('QUENCH!')
            self._mw.magnet_x_quenchbit.setStyleSheet('color: red')
        else:
            self._mw.magnet_x_quenchbit.setText('Not quenched')

        if self._mc_logic.data['quench_state_y'][-1]:
            self._mw.magnet_y_quenchbit.setText('QUENCH!')
            self._mw.magnet_y_quenchbit.setStyleSheet('color: red')
        else:
            self._mw.magnet_y_quenchbit.setText('Not quenched')

        if self._mc_logic.data['quench_state_z'][-1]:
            self._mw.magnet_z_quenchbit.setText('QUENCH!')
            self._mw.magnet_z_quenchbit.setStyleSheet('color: red')
        else:
            self._mw.magnet_z_quenchbit.setText('Not quenched')

        if self._mc_logic.data["ramping_state_x"][-1]:
            self._mw.magnet_x_ramping_label.setStyleSheet('color: yellow')
        else:
            self._mw.magnet_x_ramping_label.setStyleSheet('color: gray')

        if self._mc_logic.data["ramping_state_y"][-1]:
            self._mw.magnet_y_ramping_label.setStyleSheet('color: yellow')
        else:
            self._mw.magnet_y_ramping_label.setStyleSheet('color: gray')

        if self._mc_logic.data["ramping_state_z"][-1]:
            self._mw.magnet_z_ramping_label.setStyleSheet('color: yellow')
        else:
            self._mw.magnet_z_ramping_label.setStyleSheet('color: gray')

    def save_clicked(self):
        """ Handling the save button to save the data into a file.
        """
        if self._mc_logic.get_saving_state():
            self._mw.actionRecord_Magnet.setText('Stop Stream Saving')
            self._mc_logic.stop_saving()
        else:
            self._mw.actionRecord_Magnet.setText('Start Stream Saving')
            self._mc_logic.start_saving()
        return self._mc_logic.get_saving_state()

    def clear_buffer_clicked(self):
        self._mc_logic.clear_buffer()
        return

    def update_saving_Action(self, start):
        """Function to ensure that the GUI-save_action displays the current status

        @param bool start: True if the measurment saving is started
        @return bool start: see above
        """
        if start:
            self._mw.actionRecord_Magnet.setText('Stop Stream Saving')
        else:
            self._mw.actionRecord_Magnet.setText('Start Stream Saving')
        return start

    @QtCore.Slot()
    def send_commands(self):
        voltage_limit_dict = {"x": self._mw.magnet_x_voltage_limit_doubleSpinBox.value(),
                              "y": self._mw.magnet_y_voltage_limit_doubleSpinBox.value(),
                              "z": self._mw.magnet_z_voltage_limit_doubleSpinBox.value()}

        ramp_rate_dict = {"x": self._mw.magnet_x_ramp_rate_doubleSpinBox.value(),
                          "y": self._mw.magnet_y_ramp_rate_doubleSpinBox.value(),
                          "z": self._mw.magnet_z_ramp_rate_doubleSpinBox.value()}

        current_setpoint_dict = {"x": self._mw.magnet_x_current_doubleSpinBox.value(),
                                 "y": self._mw.magnet_y_current_doubleSpinBox.value(),
                                 "z": self._mw.magnet_z_current_doubleSpinBox.value()}

        self._mc_logic.change_parameters(voltage_limit_dict, ramp_rate_dict, current_setpoint_dict)




