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
import matplotlib.pyplot as plt

from core.connector import Connector
from core.statusvariable import StatusVar
from core.configoption import ConfigOption
from logic.generic_logic import GenericLogic


class TemperatureMonitorLogic(GenericLogic):
    """ Logic module agreggating multiple hardware switches.
    """

    # waiting time between queries im milliseconds
    tm = Connector(interface='ProcessInterface')
    savelogic = Connector(interface='SaveLogic')

    queryInterval = ConfigOption('query_interval', 1000)

    sigUpdate = QtCore.Signal()
    sigSavingStatusChanged = QtCore.Signal(bool)
    _saving = StatusVar('saving', False)

    def on_activate(self):
        """ Prepare logic module for work.
        """
        self._tm = self.tm()
        self._save_logic = self.savelogic()


        self.stopRequest = False
        self.bufferLength = 100
        self.data = {}

        # delay timer for querying laser
        self.queryTimer = QtCore.QTimer()
        self.queryTimer.setInterval(self.queryInterval)
        self.queryTimer.setSingleShot(True)
        self.queryTimer.timeout.connect(self.check_temperature_loop, QtCore.Qt.QueuedConnection)

        # get laser capabilities
        self.tm_unit = self._tm.get_process_unit()

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
    def check_temperature_loop(self):
        """ Get temperatures from monitor. """
        if self.stopRequest:
            if self.module_state.can('stop'):
                self.module_state.stop()
            self.stopRequest = False
            return
        qi = self.queryInterval
        try:
            self.baseplate_temp = self._tm.get_process_value(channel="baseplate")
            self.tip_temp = self._tm.get_process_value(channel="tip")
            self.sample_temp = self._tm.get_process_value(channel="sample")

            for k in self.data:
                self.data[k] = np.roll(self.data[k], -1)

            self.data['baseplate_temp'][-1] = self.baseplate_temp
            self.data['tip_temp'][-1] = self.tip_temp
            self.data['sample_temp'][-1] = self.sample_temp
            self.data['time'][-1] = time.time()
        except:
            qi = 3000
            self.log.exception("Exception in TM status loop, throttling refresh rate.")

        # save the data if necessary
        if self._saving:
            newdata = np.empty((4, ))
            newdata[0] = time.time() - self._saving_start_time
            newdata[1] = self.data['baseplate_temp'][-1]
            newdata[2] = self.data['tip_temp'][-1]
            newdata[3] = self.data['sample_temp'][-1]

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
        self.data['baseplate_temp'] = np.zeros(self.bufferLength)
        self.data['tip_temp'] = np.zeros(self.bufferLength)
        self.data['sample_temp'] = np.zeros(self.bufferLength)
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

    def draw_figure(self, data):
        """ Draw figure to save with data file.

        @param: nparray data: a numpy array containing counts vs time for all detectors

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        time_data = data[:, 0]
        baseplate_temp = data[:, 1]
        tip_temp = data[:, 2]
        sample_temp = data[:, 3]

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, (ax1, ax2, ax3) = plt.subplots(nrows=3, ncols=1, sharex=True)
        ax1.plot(time_data, baseplate_temp, linestyle=':', linewidth=0.5)
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Baseplate T (K)')

        ax2.plot(time_data, tip_temp, linestyle=':', linewidth=0.5)
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Tip T (K)')

        ax3.plot(time_data, sample_temp, linestyle=':', linewidth=0.5)
        ax3.set_xlabel('Time (s)')
        ax3.set_ylabel('Sample T (K)')

        plt.tight_layout()

        return fig

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
                filelabel = 'temperature'
            else:
                filelabel = 'temperature_' + postfix

            # prepare the data in a dict or in an OrderedDict:
            header = 'Time (s)' + ",baseplate_temp (K)" + ",tip_temp (K)" + ",sample_temp (K)"

            data = {header: self._data_to_save}
            filepath = self._save_logic.get_path_for_module(module_name='Temperature')

            if save_figure:
                fig = self.draw_figure(data=np.array(self._data_to_save))
            else:
                fig = None
            self._save_logic.save_data(data, filepath=filepath, parameters=parameters,
                                       filelabel=filelabel, plotfig=fig, delimiter='\t')
            self.log.info('Temperature data saved to:\n{0}'.format(filepath))

        self.sigSavingStatusChanged.emit(self._saving)
        return self._data_to_save, parameters