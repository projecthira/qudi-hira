# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware module to use TimeTagger for autocorrelation measurements.

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

import numpy as np

from core.module import Base
from core.configoption import ConfigOption

from interface.autocorrelation_interface import AutocorrelationConstraints
from interface.autocorrelation_interface import AutocorrelationInterface


class TimeTaggerAutocorrelationDummy(Base, AutocorrelationInterface):
    """ UNSTABLE
    Using the TimeTagger for autocorrelation measurement.

    Example config for copy-paste:

    timetagger_slowcounter:
        module.Class: 'timetagger_autocorrelation.TimeTaggerAutocorrelation'
        timetagger_channel_apd_0: 0
        timetagger_channel_apd_1: 1
    """

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._count_length = 1000
        self._bin_width = 1000  # bin width in ps
        self.correlation = None
        self.statusvar = 0

    def on_deactivate(self):
        """ Deactivate the FPGA.
        """
        return 0

    def get_constraints(self):
        """ Get hardware limits of TimeTagger autocorrelation device.

        @return AutocorrelationConstraints: constraints class for autocorrelation
        """
        constraints = AutocorrelationConstraints()
        constraints.max_channels = 2
        constraints.min_channels = 2
        constraints.min_count_length = 1
        constraints.min_bin_width = 0

        return constraints

    def set_up_correlation(self, count_length=None, bin_width=None):
        """ Configuration of the fast counter.

        @param float bin_width: Length of a single time bin in the time trace
                                  histogram in picoseconds.
        @param float count_length: Total number of bins.

        @return tuple(bin_width, count_length):
                    bin_width: float the actual set binwidth in picoseconds
                    count_length: actual number of bins
        """
        self._bin_width = bin_width
        self._count_length = count_length

        self.statusvar = 1
        return 0

    def _reset_hardware(self):
        return 0

    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as
            return value.

        0 = unconfigured
        1 = idle
        2 = running
        3 = paused
        -1 = error state
        """
        return self.statusvar

    def start_measure(self):
        """ Start the fast counter. """
        if self.module_state() != 'locked':
            self.lock()
            self.statusvar = 2
        return 0

    def stop_measure(self):
        """ Stop the fast counter. """
        if self.module_state() == 'locked':
            self.module_state.unlock()
        self.statusvar = 1
        return 0

    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        if self.module_state() == 'locked':
            self.statusvar = 3
        return 0

    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """
        if self.module_state() == 'locked':
            self.statusvar = 2
        return 0

    def get_bin_width(self):
        """ Returns the width of a single timebin in the timetrace in picoseconds.

        @return float: current length of a single bin in seconds (seconds/bin)
        """
        return self._bin_width

    def get_count_length(self):
        """ Returns the number of time bins.

        @return float: number of bins
        """
        return int(2 * self._count_length + 1)

    def get_data_trace(self):
        """

        @return numpy.array: onedimensional array of dtype = int64.
                             Size of array is determined by 2*count_length+1
        """
        return np.random.randint(low=0, high=10, size=self.get_count_length(), dtype=np.int64)

    def get_normalized_data_trace(self):
        """

        @return numpy.array: onedimensional array of dtype = int64 normalized
                             according to
                             https://www.physi.uni-heidelberg.de/~schmiedm/seminar/QIPC2002/SinglePhotonSource/SolidStateSingPhotSource_PRL85(2000).pdf
                             Size of array is determined by 2*count_length+1
        """
        return np.random.randint(low=0, high=10, size=self.get_count_length(), dtype=np.int64)

    def get_bin_times(self):
        return np.arange(-self._count_length * self._bin_width, (self._count_length + 1) * self._bin_width, self._bin_width)

    def close_correlation(self):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return 0
