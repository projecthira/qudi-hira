import numpy as np

from core.module import Base
from interface.autocorrelation_interface import AutocorrelationConstraints
from interface.autocorrelation_interface import AutocorrelationInterface


class AutocorrelationDummy(Base, AutocorrelationInterface):
    """
        Dummy for Autocorrelation
    """

    _modclass = 'autocorrelationinterface'
    _modtype = 'hardware'

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._count_length = int(10)
        self._bin_width = 1  # bin width in ps

    def on_deactivate(self):
        """ Deactivate the FPGA.
        """

    def get_constraints(self):
        """ Get hardware limits of NI device.

        @return SlowCounterConstraints: constraints class for slow counter

        FIXME: ask hardware for limits when module is loaded
            """
        constraints = AutocorrelationConstraints()
        constraints.max_channels = 2
        constraints.min_channels = 2
        constraints.min_count_length = 1
        constraints.min_bin_width = 100

        return constraints

    def set_up_correlation(self, bin_width, count_length):
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

        return 0

    def stop_measure(self):
        """ Stop the fast counter. """

        return 0

    def pause_measure(self):
        """ Pauses the current measurement.

        Fast counter must be initially in the run state to make it pause.
        """

        return 0

    def continue_measure(self):
        """ Continues the current measurement.

        If fast counter is in pause state, then fast counter will be continued.
        """

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
        return (2 * self._count_length + 1)

    def get_data_trace(self):
        """

        @return numpy.array: onedimensional array of dtype = int64.
                             Size of array is determined by 2*count_length+1
        """

        correlation_data = np.random.randint(0, 100, self._count_length, dtype='int32')
        return correlation_data

    def get_normalized_data_trace(self):
        """

        @return numpy.array: onedimensional array of dtype = int64 normalized
                             according to
                             https://www.physi.uni-heidelberg.de/~schmiedm/seminar/QIPC2002/SinglePhotonSource/SolidStateSingPhotSource_PRL85(2000).pdf
                             Size of array is determined by 2*count_length+1
        """
        return np.array(self.correlation.getDataNormalized(), dtype='int32')

    def close_correlation(self):
        """ Closes the counter and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        return 0