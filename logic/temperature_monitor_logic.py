# -*- coding: utf-8 -*-
"""
This file contains the Qudi temperature monitor logic to readout and save temperature.
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

import time
from collections import OrderedDict

import matplotlib.pyplot as plt
import numpy as np
from qtpy import QtCore

from core.configoption import ConfigOption
from core.connector import Connector
from core.statusvariable import StatusVar
from core.util.mutex import Mutex
from logic.generic_logic import GenericLogic


class TemperatureMonitorLogic(GenericLogic):
    """ Logic module agreggating multiple hardware switches.
    """

    # waiting time between queries im milliseconds
    tm = Connector(interface='ProcessInterface')
    savelogic = Connector(interface='SaveLogic')

    queryInterval = ConfigOption('query_interval', 1000)
    queryIntervalLowerLim = ConfigOption('query_interval_lower_lim', 100)
    queryIntervalUpperLim = ConfigOption('query_interval_upper_lim', 60000)

    sigUpdate = QtCore.Signal()
    sigSavingStatusChanged = QtCore.Signal(bool)

    _saving = StatusVar('saving', False)

    def __init__(self, config, **kwargs):
        """ Create TemperatureMonitorLogic object with connectors.

        @param dict config: module configuration
        @param dict kwargs: optional parameters
        """
        super().__init__(config=config, **kwargs)

        # locking for thread safety
        self.threadlock = Mutex()

        self.log.debug('The following configuration was found.')

        # checking for the right configuration
        for key in config.keys():
            self.log.debug('{0}: {1}'.format(key, config[key]))

        self._saving = False
        self.header_string = None
        return

    def on_activate(self):
        """ Prepare logic module for work.
        """
        self._tm = self.tm()
        self._save_logic = self.savelogic()

        self.stopRequest = False
        self.data = {}
        self._data_to_save = []
        self._saving = False

        self.queryTimer = QtCore.QTimer()
        self.queryTimer.setInterval(self.queryInterval)
        self.queryTimer.setSingleShot(True)
        self.queryTimer.timeout.connect(self.check_temperature_loop, QtCore.Qt.QueuedConnection)

        # get laser capabilities
        self.tm_unit = self._tm.get_process_unit()

        self.init_data_logging()
        self.start_query_loop()

    def on_deactivate(self):
        """ Deactivate module.
        """
        self.stop_query_loop()
        if self._saving:
            self.stop_saving()
        self.clear_buffer()

    @QtCore.Slot(int)
    def change_qtimer_interval(self, interval):
        """ Change query interval time. """
        if self.queryIntervalLowerLim <= interval <= self.queryIntervalUpperLim:
            self.queryTimer.setInterval(interval)
            self.queryInterval = interval
            self.log.info(f"Query interval changed to {self.queryInterval}")
        else:
            self.log.warn(f"Query interval limits are {self.queryIntervalLowerLim} to {self.queryIntervalUpperLim}. "
                          f"Query interval is {self.queryInterval}")

    def get_saving_state(self):
        """ Returns if the data is saved in the moment.

        @return bool: saving state
        """
        return self._saving

    def get_channels(self):
        """ Shortcut for hardware get_counter_channels.

            @return list(str): return list of active counter channel names
        """
        return self._tm.get_channels()

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
            for channel in self.get_channels():
                self.data[channel].append(self._tm.get_process_value(channel=channel))

            self.data['time'].append(time.time())
        except:
            qi = 3000
            self.log.exception("Exception in TM status loop, throttling refresh rate.")

        # save the data if necessary
        if self._saving:
            newdata = np.empty((len(self.get_channels()) + 1), )
            newdata[0] = time.time() - self._saving_start_time
            for i, channel in enumerate(self.get_channels()):
                newdata[i + 1] = self.data[channel][-1]
            self._save_logic.write_data([newdata], header=self.header_string, filepath=self.filepath,
                                        filename=self.filename)
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
        self.queryTimer.stop()

    def init_data_logging(self):
        """
        Initialize data logging into a continuously expanding dictionary.
        Note that this can potentially cause problems with extremely long measurements on systems with less memory.
        """
        self.data['time'] = []
        for ch in self.get_channels():
            self.data[ch] = []

    def clear_buffer(self):
        """ Flush all data currently stored in memory. """
        if self.data:
            # Only clear data if it is not empty
            self.data.clear()
        self.init_data_logging()

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
        self.save_data_header()
        self.sigSavingStatusChanged.emit(self._saving)
        return self._saving

    def stop_saving(self):
        """
        Stop the saving of the file, and set the QtSignal accordingly.

        @return bool: saving state
        """
        if not self._data_to_save:
            # Check if list is empty
            self.log.warn("No data to save!")
        else:
            # Only save figure if list is not empty to prevent IndexError
            fig = self.draw_figure(data=np.array(self._data_to_save))
            self._save_logic.save_figure(plotfig=fig, filepath=self.filepath, filename=self.filename)

        self._saving = False
        self.sigSavingStatusChanged.emit(self._saving)
        self.header = None
        self._data_to_save.clear()
        return self._saving

    def draw_figure(self, data):
        """ Draw figure to save with data file.

        @param: nparray data: a numpy array containing counts vs time for all detectors

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        time_data = data[:, 0]

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qudihira_style)

        # Create figure
        fig, ax = plt.subplots(nrows=len(self.get_channels()), ncols=1, sharex=True)

        if len(self.get_channels()) == 1:
            ax = [ax]

        for i, channel in enumerate(self.get_channels()):
            ax[i].plot(time_data, data[:, i + 1], '.-')
            ax[i].set_xlabel('Time (s)')
            ax[i].set_ylabel(channel.title() + ' T (K)')

        plt.tight_layout()

        return fig

    def save_data_header(self, to_file=True, postfix=''):
        """ Save the counter trace data and writes it to a file.

        @param bool to_file: indicate, whether data have to be saved to file
        @param str postfix: an additional tag, which will be added to the filename upon save
        @param bool save_figure: select whether png and pdf should be saved

        @return dict parameters: Dictionary which contains the saving parameters
        """
        # write the parameters:
        parameters = OrderedDict()
        parameters['Start counting time'] = time.strftime('%d.%m.%Y %Hh:%Mmin:%Ss',
                                                          time.localtime(self._saving_start_time))

        if to_file:
            # If there is a postfix then add separating underscore
            if postfix == '':
                filelabel = 'temperature'
            else:
                filelabel = 'temperature_' + postfix

            # prepare the data in a dict or in an OrderedDict:
            self.header_string = 'Time (s)'

            for i, channel in enumerate(self.get_channels()):
                self.header_string += ',{}_temp (K)'.format(channel)

            header_array = self.header_string.split(",")
            self.filepath = self._save_logic.get_path_for_module(module_name='Temperature')
            self.filename = self._save_logic.create_file_and_header(header_array, filepath=self.filepath,
                                                                    parameters=parameters,
                                                                    filelabel=filelabel, delimiter='\t')

        return [], parameters
