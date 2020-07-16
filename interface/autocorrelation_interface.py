# -*- coding: utf-8 -*-

"""
This module contains the Qudi interface file for confocal scanner.

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

import abc

from core.meta import InterfaceMetaclass


class AutocorrelationInterface(metaclass=InterfaceMetaclass):
    """ This is the Interface class to define the controls for the simple
    microwave hardware.
    """

    _modtype = 'AutocorrelationInterface'
    _modclass = 'interface'

    def get_constraints(self):
        """ Retrieve the hardware constrains from the counter device.

        @return SlowCounterConstraints: object with constraints for the counter
        """
        pass

    @abc.abstractmethod
    def set_up_correlation(self, count_length=None, bin_width=None):
        """ Sets up device for autocorrelation measurement
        @param int count_length: number of bins for measurement
        @param int bin_width: length of used bins
        @return int: error code (0:OK, -1:error)
        """
        pass

    @abc.abstractmethod
    def get_status(self):
        """ Receives the current status of the Fast Counter and outputs it as
            return value.

        0 = unconfigured
        1 = idle
        2 = running
        3 = paused
      -1 = error state
        """
        pass

    @abc.abstractmethod
    def start_measure(self):
        """ Start the fast counter. """
        pass

    @abc.abstractmethod
    def stop_measure(self):
        """ Stop the fast counter. """
        pass

    @abc.abstractmethod
    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """
        pass

    @abc.abstractmethod
    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """
        pass

    @abc.abstractmethod
    def get_count_length(self):
        """ Returns number of configured bins for measurement.

        @return int count_length: number of bins for measurement
        """
        pass

    @abc.abstractmethod
    def get_bin_width(self):
        """ Returns the width of a single timebin in the timetrace in seconds.

        @return int: current length of a single bin in seconds
        """
        pass

    def get_data_trace(self):
        """ Polls the current timetrace data from the fast counter.

        Return value is a numpy array (dtype = int64).
        The binning, specified by calling configure() in forehand, must be
        taken care of in this hardware class. A possible overflow of the
        histogram bins must be caught here and taken care of.
        If the counter is NOT GATED it will return a 1D-numpy-array with
            returnarray[timebin_index]
        If the counter is GATED it will return a 2D-numpy-array with
            returnarray[gate_index, timebin_index]
        """
        pass


class AutocorrelationConstraints:

    def __init__(self):
        # maximum numer of possible channels for autocorrelation measurement
        self.max_channels = 2
        self.min_channels = 2

        self.min_count_length = 1
        self.min_bin_width = 100
