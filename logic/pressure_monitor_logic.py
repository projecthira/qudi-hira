# -*- coding: utf-8 -*-
__author__ = "Dinesh Pinto"
__email__ = "d.pinto@fkf.mpg.de"
"""
Temperature Monitor logic.

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
from collections import OrderedDict

from core.connector import Connector
from core.statusvariable import StatusVar
from core.configoption import ConfigOption
from logic.generic_logic import GenericLogic


class PressureMonitorLogic(GenericLogic):
    """ Logic module agreggating multiple hardware switches.
    """

    # waiting time between queries im milliseconds
    pm = Connector(interface='ProcessInterface')
    savelogic = Connector(interface='SaveLogic')

    queryInterval = ConfigOption('query_interval', 5000)

    sigUpdate = QtCore.Signal()
    sigSavingStatusChanged = QtCore.Signal(bool)
    _saving = StatusVar('saving', False)

    def on_activate(self):
        """ Prepare module for work.
        """
        self._pm = self.pm()
        self._save_logic = self.savelogic()

        self.stopRequest = False
        self.bufferLength = 100
        self.data = {}

        # delay timer for querying
        self.queryTimer = QtCore.QTimer()
        self.queryTimer.setInterval(self.queryInterval)
        self.queryTimer.setSingleShot(True)
        self.queryTimer.timeout.connect(self.check_pressure_loop, QtCore.Qt.QueuedConnection)

        self.pm_unit = self._pm.get_process_unit()

        self.init_data_logging()
        self.start_query_loop()
        self._data_to_save = []

    def on_deactivate(self):
        """ Deactivate module.
        """
        self.stop_query_loop()
        for i in range(5):
            time.sleep(self.queryInterval / 1000)
            QtCore.QCoreApplication.processEvents()

    def get_saving_state(self):
        """ Returns if the data is saved in the moment.

        @return bool: saving state
        """
        return self._saving

    @QtCore.Slot()
    def check_pressure_loop(self):
        """ Get pressures from monitor. """
        if self.stopRequest:
            if self.module_state.can('stop'):
                self.module_state.stop()
            self.stopRequest = False
            return
        qi = self.queryInterval
        try:
            self.main_pressure = self._pm.get_process_value(channel="main_gauge")
            self.prep_pressure = self._pm.get_process_value(channel="prep_gauge")
            self.back_pressure = self._pm.get_process_value(channel="back_gauge")

            for k in self.data:
                self.data[k] = np.roll(self.data[k], -1)

            if isinstance(self.main_pressure, float):
                self.data['main_pressure'][-1] = self.main_pressure
            else:
                self.data['main_pressure'][-1] = -1
            if isinstance(self.prep_pressure, float):
                self.data['prep_pressure'][-1] = self.prep_pressure
            else:
                self.data['prep_pressure'][-1] = -1
            if isinstance(self.back_pressure, float):
                self.data['back_pressure'][-1] = self.back_pressure
            else:
                self.data['back_pressure'][-1] = -1

            self.data['time'][-1] = time.time()
        except:
            qi = 3000
            self.log.exception("Exception in PM status loop, throttling refresh rate.")

        # save the data if necessary
        if self._saving:
            newdata = np.empty((4, ))
            newdata[0] = time.time() - self._saving_start_time
            newdata[1] = self.data['main_pressure'][-1]
            newdata[2] = self.data['prep_pressure'][-1]
            newdata[3] = self.data['back_pressure'][-1]

            self._data_to_save.append(newdata)

        self.queryTimer.start(qi)
        self.sigUpdate.emit()

    @QtCore.Slot()
    def start_query_loop(self):
        """ Start the readout loop. """
        self.module_state.run()
        self.queryTimer.start(self.queryInterval)

    @QtCore.Slot()
    def stop_query_loop(self):
        """ Stop the readout loop. """
        self.stopRequest = True
        for i in range(10):
            if not self.stopRequest:
                return
            QtCore.QCoreApplication.processEvents()
            time.sleep(self.queryInterval / 1000)

    def init_data_logging(self):
        """ Zero all log buffers. """
        self.data['main_pressure'] = np.zeros(self.bufferLength)
        self.data['prep_pressure'] = np.zeros(self.bufferLength)
        self.data['back_pressure'] = np.zeros(self.bufferLength)
        self.data['time'] = np.ones(self.bufferLength) * time.time()

    def start_saving(self, resume=False):
        """
        Sets up start-time and initializes data array, if not resuming, and changes saving state.
        If the counter is not running it will be started in order to have data to save.

        @return bool: saving state
        """
        if not resume:
            self._data_to_save = []
            self._saving_start_time = time.time()

        self._saving = True

        self.sigSavingStatusChanged.emit(self._saving)
        return self._saving

    def save_data(self, to_file=True, postfix='', save_figure=True):
        """ Save the counter trace data and writes it to a file.

        @param bool to_file: indicate, whether data have to be saved to file
        @param str postfix: an additional tag, which will be added to the filename upon save
        @param bool save_figure: select whether png and pdf should be saved

        @return dict parameters: Dictionary which contains the saving parameters
        """
        # stop saving thus saving state has to be set to False
        self._saving = False
        self._saving_stop_time = time.time()

        # write the parameters:
        parameters = OrderedDict()
        parameters['Start counting time'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_start_time))
        parameters['Stop counting time'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss', time.localtime(self._saving_stop_time))

        if to_file:
            # If there is a postfix then add separating underscore
            if postfix == '':
                filelabel = 'pressure_'
            else:
                filelabel = 'pressure_' + postfix

            # prepare the data in a dict or in an OrderedDict:
            header = 'Time (s)' + ",main_pressure (mbar)" + ",prep_pressure (mbar)" + ",back_pressure (mbar)"

            data = {header: self._data_to_save}
            filepath = self._save_logic.get_path_for_module(module_name='Pressure')

            self._save_logic.save_data(data, filepath=filepath, parameters=parameters,
                                       filelabel=filelabel, plotfig=None, delimiter='\t')
            self.log.info('Pressure data saved to:\n{0}'.format(filepath))

        self.sigSavingStatusChanged.emit(self._saving)
        return self._data_to_save, parameters