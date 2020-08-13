# -*- coding: utf-8 -*-

"""
This file contains the Qudi counter gui.

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
from qtpy import QtCore
from qtpy import QtWidgets
from qtpy import uic

from core.module import Connector
from gui.colordefs import QudiPalettePale as palette
from gui.guibase import GUIBase


class AutocorrelationMainWindow(QtWidgets.QMainWindow):

    """ Create the Main Window based on the *.ui file. """

    def __init__(self, **kwargs):
        # Get the path to the *.ui file
        this_dir = os.path.dirname(__file__)
        ui_file = os.path.join(this_dir, 'ui_autocorrelation.ui')

        # Load it
        super().__init__(**kwargs)
        uic.loadUi(ui_file, self)
        self.show()


class AutocorrelationGui(GUIBase):

    """ to add: save as figure as well (Jan Kurzhals)
    """
    autocorrelation1 = Connector(interface='AutocorrelationLogic')

    sigStartCounter = QtCore.Signal()
    sigStopCounter = QtCore.Signal()
    sigResumeCounter = QtCore.Signal()

    sigResumeActionChanged = QtCore.Signal(bool)
    sigStopActionChanged = QtCore.Signal(bool)
    sigStartActionChanged = QtCore.Signal(bool)
    sigSaveMeasurement = QtCore.Signal(str)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

    def on_activate(self):
        """ Definition and initialisation of the GUI.
        """

        #####################
        # get connectors
        self._correlation_logic = self.autocorrelation1()
        #####################
        # Configuring the dock widgets
        # Use the inherited class 'CounterMainWindow' to create the GUI window
        self._mw = AutocorrelationMainWindow()
        # Setup dock widgets
        self._mw.centralwidget.hide()
        self._mw.setDockNestingEnabled(True)
        # Plot labels.
        self._pw = self._mw.autocorrelation_trace_PlotWidget
        self._pw.setLabel('left', 'Counts', units='')
        self._pw.setLabel('bottom', 'Delay', units='s')
        self.curves = []
        self.curves.append(
                    pg.PlotDataItem(
                        pen=pg.mkPen(palette.c1, style=QtCore.Qt.DotLine),
                        symbol='s',
                        symbolPen=palette.c1,
                        symbolBrush=palette.c1,
                        symbolSize=5))

        self._pw.addItem(self.curves[0])
        # setting the x axis length correctly
        xmin, xmax = self.get_x_range()
        self._pw.setXRange(xmin, xmax)

        #####################
        # Setting default parameters for
        # SpinBoxes
        self._mw.count_length_SpinBox.setValue(self._correlation_logic.get_count_length())
        self._mw.count_binwidth_SpinBox.setValue(self._correlation_logic.get_bin_width())
        self._mw.count_refreshtime_SpinBox.setValue(self._correlation_logic.get_refresh_time())
        # Actions
        self._mw.start_counter_Action.setEnabled(True)
        self._mw.resume_counter_Action.setEnabled(False)
        self._mw.stop_counter_Action.setEnabled(False)

        # Add save file tag input box
        self._mw.save_tag_LineEdit = QtWidgets.QLineEdit(self._mw)
        self._mw.save_tag_LineEdit.setMaximumWidth(500)
        self._mw.save_tag_LineEdit.setMinimumWidth(200)
        self._mw.save_tag_LineEdit.setToolTip('Enter a nametag which will be\n'
                                              'added to the filename.')
        self._mw.save_ToolBar.addWidget(self._mw.save_tag_LineEdit)

        #####################
        # Connecting user interaction of
        # Action
        self._mw.start_counter_Action.triggered.connect(self.start_clicked)
        self._mw.stop_counter_Action.triggered.connect(self.stop_clicked)
        self._mw.resume_counter_Action.triggered.connect(self.resume_clicked)

        self._mw.restore_default_view_Action_2.triggered.connect(self.restore_default_view)
        self._mw.action_Save.triggered.connect(self.save_data)

        # SpinBoxes
        self._mw.count_length_SpinBox.valueChanged.connect(self.count_length_changed)
        self._mw.count_binwidth_SpinBox.valueChanged.connect(self.count_bin_width_changed)
        self._mw.count_refreshtime_SpinBox.valueChanged.connect(self.count_refreshtime_changed)

        #####################
        # connect signals from logic to gui
        self._correlation_logic.sigCorrelationStatusChanged.connect(self.update_correlation_status_Action)
        self._correlation_logic.sigCorrelationUpdated.connect(self.updateData)
        self._correlation_logic.sigCountLengthChanged.connect(self.update_count_length_SpinBox)
        self._correlation_logic.sigCountingBinWidthChanged.connect(self.update_count_bin_width_SpinBox)
        self._correlation_logic.sigCountingRefreshTimeChanged.connect(self.update_refresh_time_SpinBox)

        #####################
        # connect signals from gui to gui and logic:
        # logic:
        self.sigStartCounter.connect(self._correlation_logic.start_correlation)
        self.sigStopCounter.connect(self._correlation_logic.stop_correlation)
        self.sigResumeCounter.connect(self._correlation_logic.continue_correlation)
        self.sigSaveMeasurement.connect(self._correlation_logic.save_data, QtCore.Qt.QueuedConnection)
        # gui:
        self.sigResumeActionChanged.connect(self.change_resume_state)
        self.sigStopActionChanged.connect(self.change_stop_state)
        self.sigStartActionChanged.connect(self.change_start_state)

        return 0

    def show(self):
        """Make window visible and put it above all other windows.
        """
        QtWidgets.QMainWindow.show(self._mw)
        self._mw.activateWindow()
        self._mw.raise_()
        return

    def on_deactivate(self):
        # FIXME: !
        """ Deactivate the module
        """
        # disconnect signals from main window
        self._mw.start_counter_Action.triggered.disconnect()
        self._mw.count_length_SpinBox.valueChanged.disconnect()
        self._mw.count_binwidth_SpinBox.valueChanged.disconnect()
        self._mw.restore_default_view_Action_2.triggered.disconnect()
        # disconnect signals from gui
        self.sigStartCounter.disconnect()
        self.sigStopCounter.disconnect()
        self.sigResumeCounter.disconnect()
        self.sigResumeActionChanged.disconnect()
        self.sigStopActionChanged.disconnect()
        self.sigStartActionChanged.disconnect()
        self.sigSaveMeasurement.disconnect()
        # disconnect signals from logic
        self._correlation_logic.sigCorrelationStatusChanged.disconnect()
        self._correlation_logic.sigCorrelationDataNext.disconnect()
        self._correlation_logic.sigCorrelationUpdated.disconnect()
        self._correlation_logic.sigCountLengthChanged.disconnect()
        self._correlation_logic.sigCountingBinWidthChanged.disconnect()
        self._correlation_logic.sigCountingRefreshTimeChanged.disconnect()

        self._mw.close()
        return

    def updateData(self):
        """ The function that grabs the data and sends it to the plot.
        """
        if self._correlation_logic.module_state() == 'locked':
            # x_vals = (
            #     np.arange(-1 * ((self._correlation_logic.get_count_length() / 2) * self._correlation_logic.get_bin_width() / (1e12)),
            #              (self._correlation_logic.get_count_length()/2)*self._correlation_logic.get_bin_width()/(1e12),
            #               self._correlation_logic.get_bin_width()/(1e12))
            # )
            self.curves[0].setData(y=self._correlation_logic.rawdata, x=self._correlation_logic.delay/1e12)

        return

    def start_clicked(self):
        if self._correlation_logic.module_state() == 'locked':
            self.sigResumeActionChanged.emit(False)
            self.sigStopActionChanged.emit(False)
            self.sigStopCounter.emit()
        else:
            self.sigResumeActionChanged.emit(False)
            self.sigStopActionChanged.emit(True)
            self.sigStartActionChanged.emit(False)
            self.sigStartCounter.emit()
        return self._correlation_logic.module_state()

    def stop_clicked(self):

        self.sigStartActionChanged.emit(True)
        self.sigResumeActionChanged.emit(True)
        self.sigStopActionChanged.emit(False)
        self.sigStopCounter.emit()

        return

    def resume_clicked(self):

        self.sigStartActionChanged.emit(False)
        self.sigResumeActionChanged.emit(False)
        self.sigStopActionChanged.emit(True)
        self.sigResumeCounter.emit()

        return

    def get_x_range(self):
        xlim = (self._correlation_logic.get_count_length() / 2) * self._correlation_logic.get_bin_width() / 1e12
        return (-1 * xlim, xlim)

    def count_length_changed(self):
        """ Handling the change of the count_length and sending it to the measurement.
        """
        self._correlation_logic.set_count_length(self._mw.count_length_SpinBox.value())
        xmin, xmax = self.get_x_range()
        self._pw.setXRange(xmin, xmax)
        return self._mw.count_length_SpinBox.value()

    def count_bin_width_changed(self):
        self._correlation_logic.set_bin_width(self._mw.count_binwidth_SpinBox.value())
        xmin, xmax = self.get_x_range()
        self._pw.setXRange(xmin, xmax)
        return self._mw.count_binwidth_SpinBox.value()

    def count_refreshtime_changed(self):

        self._correlation_logic.set_refresh_time(self._mw.count_refreshtime_SpinBox.value())

        return self._mw.count_refreshtime_SpinBox.value()

    def change_resume_state(self, tag):

        if tag == False:
            self._mw.resume_counter_Action.setEnabled(False)
        else:
            self._mw.resume_counter_Action.setEnabled(True)
        return

    def change_stop_state(self, tag):

        if tag == False:
            self._mw.stop_counter_Action.setEnabled(False)
        else:
            self._mw.stop_counter_Action.setEnabled(True)
        return

    def change_start_state(self, tag):

        if tag == False:
            self._mw.start_counter_Action.setEnabled(False)
        else:
            self._mw.start_counter_Action.setEnabled(True)
        return

    def restore_default_view(self):
        """ Restore the arrangement of DockWidgets to the default
        """
        # Show any hidden dock widgets
        self._mw.counter_trace_DockWidget.show()
        # self._mw.slow_counter_control_DockWidget.show()
        self._mw.autocorrelation_parameters_DockWidget.show()

        # re-dock any floating dock widgets
        self._mw.counter_trace_DockWidget.setFloating(False)
        self._mw.autocorrelation_parameters_DockWidget.setFloating(False)

        # Arrange docks widgets
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(1),
                               self._mw.counter_trace_DockWidget
                               )
        self._mw.addDockWidget(QtCore.Qt.DockWidgetArea(8),
                               self._mw.autocorrelation_parameters_DockWidget
                               )

        # Set the toolbar to its initial top area
        self._mw.addToolBar(QtCore.Qt.TopToolBarArea,
                            self._mw.counting_control_ToolBar)
        return 0

    def update_count_bin_width_SpinBox(self, count_freq):
        """Function to ensure that the GUI displays the current value of the logic

        @param float count_freq: adjusted count frequency in Hz
        @return float count_freq: see above
        """
        self._mw.count_binwidth_SpinBox.blockSignals(True)
        self._mw.count_binwidth_SpinBox.setValue(count_freq)
        xmin, xmax = self.get_x_range()
        self._pw.setXRange(xmin, xmax)
        self._mw.count_binwidth_SpinBox.blockSignals(False)
        return count_freq

    def update_refresh_time_SpinBox(self, refresh_time):
        self._mw.count_refreshtime_SpinBox.blockSignals(True)
        self._mw.count_refreshtime_SpinBox.setValue(refresh_time)
        self._mw.count_refreshtime_SpinBox.blockSignals(False)
        return refresh_time

    def update_count_length_SpinBox(self, count_length):
        """Function to ensure that the GUI displays the current value of the logic

        @param int count_length: adjusted count length in bins
        @return int count_length: see above
        """
        self._mw.count_length_SpinBox.blockSignals(True)
        self._mw.count_length_SpinBox.setValue(count_length)
        xmin, xmax = self.get_x_range()
        self._pw.setXRange(xmin, xmax)
        self._mw.count_length_SpinBox.blockSignals(False)
        return count_length

    def update_correlation_status_Action(self, running):
        """Function to ensure that the GUI-save_action displays the current status

        @param bool running: True if the counting is started
        @return bool running: see above
        """
        if running:
            #self._mw.start_counter_Action.setText('Stop counter')
            self.sigResumeActionChanged.emit(False)
            self.sigStopActionChanged.emit(True)
            self.sigStartActionChanged.emit(False)
        else:
            #self._mw.start_counter_Action.setText('Start counter')
            self.sigResumeActionChanged.emit(True)
            self.sigStartActionChanged.emit(True)
            self.sigStopActionChanged.emit(False)
        return running

    def save_data(self):
        """ Save the sum plot, the scan marix plot and the scan data """
        filetag = self._mw.save_tag_LineEdit.text()

        self.sigSaveMeasurement.emit(filetag)
        return
