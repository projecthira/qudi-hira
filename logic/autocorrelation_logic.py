# -*- coding: utf-8 -*-
"""
This file contains the Qudi autocorrealtion logic class.

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

import datetime
import time
from collections import OrderedDict

import matplotlib.pyplot as plt
import numpy as np
from qtpy import QtCore

from core.module import Connector
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic


class AutocorrelationLogic(GenericLogic):
    """
    This is the Logic class for confocal scanning.
    """
    autocorrelator = Connector(interface='AutocorrelationInterface')
    savelogic = Connector(interface='SaveLogic')

    sigCorrelationStatusChanged = QtCore.Signal(bool)
    sigCorrelationDataNext = QtCore.Signal()
    sigCorrelationUpdated = QtCore.Signal()
    sigCountLengthChanged = QtCore.Signal(int)
    sigCountingBinWidthChanged = QtCore.Signal(int)
    sigCountingRefreshTimeChanged = QtCore.Signal(int)
    sigSavingStatusChanged = QtCore.Signal(bool)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        self.threadlock = Mutex()

        self.log.info('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.info('{0}: {1}'.format(key, config[key]))

        # locking for thread safety
        self.threadlock = Mutex()

        self._count_length = 50
        self._bin_width = 500
        self._refresh_time = 1000  # in ms
        self._saving = False

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._correlation_device = self.autocorrelator()
        self._save_logic = self.savelogic()

        # Recall saved app-parameters
        if 'count_length' in self._statusVariables:
            self._count_length = self._statusVariables['count_length']
        if 'bin_width' in self._statusVariables:
            self._bin_width = self._statusVariables['bin_width']
        if 'saving' in self._statusVariables:
            self._saving = self._statusVariables['saving']

        self.rawdata = np.zeros([self._correlation_device.get_count_length()])
        self.delay = np.zeros([self._correlation_device.get_count_length()])

        self._data_to_save = []

        self.sigCorrelationDataNext.connect(self.correlation_loop_body, QtCore.Qt.QueuedConnection)

        self._saving_start_time = time.time()

        self.stopRequested = False
        self.continueRequested = False

    def on_deactivate(self):
        """ Reverse steps of activation

        @return int: error code (0:OK, -1:error)
        """
        # Save parameters to disk
        self._statusVariables['count_length'] = self._count_length
        self._statusVariables['bin_width'] = self._bin_width
        self._statusVariables['saving'] = self._saving

        # Stop measurement
        if self.module_state() == 'locked':
            self._stop_correlation_wait()
        return 0

    def get_hardware_constraints(self):
        """
        Retrieve the hardware constrains from the counter device.

        @return AutocorrelationConstraints: object with constraints for the autocorrelator
        """
        return self._correlation_device.get_constraints()

    def set_count_length(self, count_length=300):
        if self.module_state() == 'locked':
            restart = True
        else:
            restart = False

        if count_length > 0:
            self._stop_correlation_wait()
            self._count_length = int(count_length)
            # if the counter was running, restart it
            if restart:
                self.start_correlation()
        else:
            self.log.warning('count_length has to be larger than 0! Command ignored!')
        self.sigCountLengthChanged.emit(self._count_length)
        return self._count_length

    def _get_hardware_constraints(self):
        return self._correlation_device.get_constraints()

    def set_bin_width(self, bin_width=1000):
        """ Sets the frequency with which the data is acquired.

        @param float frequency: the desired frequency of counting in Hz

        @return float: the actual frequency of counting in Hz

        This makes sure, the counter is stopped first and restarted afterwards.
        """

        constraints = self._get_hardware_constraints()

        if self.module_state() == 'locked':
            restart = True
        else:
            restart = False

        if constraints.min_bin_width <= bin_width:
            self._stop_correlation_wait()
            self._bin_width = bin_width
            # if the counter was running, restart it
            if restart:
                self.start_correlation()
        else:
            self.log.warning('bin_width too small! Command ignored!')
        self.sigCountingBinWidthChanged.emit(self._bin_width)
        return self._bin_width

    def set_refresh_time(self, refresh_time=500):

        if self.module_state() == 'locked':
            restart = True
        else:
            restart = False

        if restart:
            self.start_correlation()
        self._refresh_time = refresh_time
        self.sigCountingRefreshTimeChanged.emit(self._refresh_time)
        return self._refresh_time

    def get_count_length(self):
        """ Returns the currently set length of the counting array.

        @return int: count_length
        """
        return self._count_length

    def get_bin_width(self):
        """ Returns the currently set width of the bins in picoseconds.

        @return int: bin_width
        """
        return self._bin_width

    def get_refresh_time(self):
        return self._refresh_time

    def start_correlation(self):
        # self._correlation_device.start_measure()

        with self.threadlock:
            # Lock module
            if self.module_state() != 'locked':
                self.module_state.lock()

            # configure correlation device
            correlation_status = self._correlation_device.set_up_correlation(self._bin_width, self._count_length)

            if correlation_status < 0:
                self.module_state.unlock()
                self.sigCorrelationStatusChanged.emit(False)
                return -1

            self.rawdata = np.zeros((self.get_count_length(),))
            self.sigCorrelationStatusChanged.emit(True)
            self.sigCorrelationDataNext.emit()
            return

    def stop_correlation(self):
        """ Set a flag to request stopping counting.
        """
        if self.module_state() == 'locked':
            with self.threadlock:
                self.stopRequested = True
        return

    def continue_correlation(self):
        if self.module_state() != 'locked':
            self._correlation_device.continue_measure()
            with self.threadlock:
                self.module_state.lock()
                self.sigCorrelationDataNext.emit()
        return

    def correlation_loop_body(self):
        if self.module_state() == 'locked':
            with self.threadlock:
                if self.stopRequested:
                    self._correlation_device.close_correlation()
                    self.stopRequested = False
                    self.module_state.unlock()
                    self.sigCorrelationUpdated.emit()
                    return
                time.sleep(self._refresh_time / 1000)  # sleep in seconds
                # self.delay = np.arange(-1 * ((self.get_count_length() / 2) * self.get_bin_width() / 1e12),
                #                            (self.get_count_length() / 2) * self.get_bin_width() / 1e12,
                #                            self.get_bin_width() / 1e12)
                self.delay = self._correlation_device.get_bin_times()
                self.rawdata = self._correlation_device.get_data_trace()
                self.rawdata_norm = self._correlation_device.get_normalized_data_trace()

                if self.rawdata[0] < 0:
                    self.log.error('The correlation went wrong, killing the correlator.')
                    self.stopRequested = True

            # call this again from event loop
            self.sigCorrelationUpdated.emit()
            self.sigCorrelationDataNext.emit()
        return

    def get_saving_state(self):
        """ Returns if the data is saved in the moment.

        @return bool: saving state
        """
        return self._saving

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

        # If the counter is not running, then it should start running so there is data to save
        if self.module_state() != 'locked':
            self.start_correlation()

        self.sigSavingStatusChanged.emit(self._saving)
        return self._saving

    def save_data(self, tag=None):
        """ Save the Autocorrelation trace data and writes it to a file (without figure).

            Figure still needs to be implemented!
        """
        timestamp = datetime.datetime.now()

        if tag is None:
            tag = ''
        filepath = self._save_logic.get_path_for_module(module_name='Autocorrelation')

        if len(tag) > 0:
            filelabel = '{0}_autocorrelation'.format(tag)
        else:
            filelabel = 'autocorrelation'

        # write the parameters:
        parameters = OrderedDict()
        # parameters['Start counting time'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss',
        #                                                   time.localtime(self._saving_start_time))
        # parameters['Stop counting time'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss',
        #                                                  time.localtime(self._saving_stop_time))
        parameters['Count length'] = self._count_length
        parameters['Bin width'] = self._bin_width

        data = OrderedDict()
        data['Time (ps)'] = np.array(self.delay)
        data['g2(t)'] = np.array(self.rawdata)
        data['g2(t) norm'] = np.array(self.rawdata_norm)

        fig = self.draw_figure(data=data)
        self._save_logic.save_data(data, filepath=filepath, parameters=parameters, filelabel=filelabel,
                                   timestamp=timestamp, plotfig=fig, delimiter='\t')
        self.log.info('Autocorrealtion Trace saved to:\n{0}'.format(filepath))

        self.sigSavingStatusChanged.emit(self._saving)

        return self._data_to_save, parameters

    def draw_figure(self, data):
        """ Draw figure to save with data file.

        @param: nparray data: a numpy array containing counts vs delaytime between two detectors

        @return: fig fig: a matplotlib figure object to be saved to file.
        """

        count_data = data['g2(t)']
        time_data = data['Time (ps)']

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qudihira_style)

        # Create figure
        fig, ax = plt.subplots()
        ax.plot(time_data, count_data, 'o', linewidth=0.5)
        ax.set_xlabel('Time (ps)')
        ax.set_ylabel('Counts')
        return fig

    def _stop_correlation_wait(self, timeout=5.0):
        """
        Stops the correlator and waits until it actually has stopped.

        @param timeout: float, the max. time in seconds how long the method should wait for the
                        process to stop.

        @return: error code
        """
        self.stop_correlation()
        start_time = time.time()
        while self.module_state() == 'locked':
            time.sleep(0.1)
            if time.time() - start_time >= timeout:
                self.log.error('Stopping the counter timed out after {0}s'.format(timeout))
                return -1
        return 0
