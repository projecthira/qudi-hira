# -*- coding: utf-8 -*-

"""
Time Tagger slow counter file, adapted to be an ODMR counter

This file contains the Qudi hardware module to use TimeTagger as a counter.

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

import TimeTagger as tt
import time
import numpy as np

from core.module import Base
from core.configoption import ConfigOption
from interface.odmr_counter_interface import ODMRCounterInterface
from interface.slow_counter_interface import SlowCounterConstraints
from interface.slow_counter_interface import CountingMode


class TimeTaggerODMRCounter(Base, ODMRCounterInterface):
    """ Using the TimeTagger as a slow counter.

    # TODO: Write a proper config

    Example config for copy-paste:

    tt_odmr:
        module.Class: 'timetagger__odmr_counter.TimeTaggerODMRCounter'
        timetagger_channel_apd_0: 0
        timetagger_channel_apd_1: 1
        timetagger_channel_trigger: 6

    """

    _modtype = 'TTCounter'
    _modclass = 'hardware'

    _channel_apd_0 = ConfigOption('timetagger_channel_apd_0', missing='error')
    _channel_apd_1 = ConfigOption('timetagger_channel_apd_1', None, missing='warn')
    _channel_trigger = ConfigOption('timetagger_channel_trigger', missing='error')
    sweep_length = 100

    _channel_apd_0 = ConfigOption('timetagger_channel_apd_0', missing='error')
    _channel_apd_1 = ConfigOption('timetagger_channel_apd_1', None, missing='warn')
    _sum_channels = ConfigOption('timetagger_sum_channels', False)

    def on_activate(self):
        print('Time Tagger ODMR counter activated')
        """ Start up TimeTagger interface
        """
        self._tagger = tt.createTimeTagger()
        self._count_frequency = 0.5  # Hz

        # self._mode can take 3 values:
        # 0: single channel, no summing
        # 1: single channel, summed over apd_0 and apd_1
        # 2: dual channel for apd_0 and apd_1
        if self._sum_channels:
            self._mode = 1
            channel_combined = tt.Combiner(self._tagger, channels=[self._channel_apd_0, self._channel_apd_1])
            self._channel_apd = channel_combined.getChannel()
        elif self._channel_apd_1 is None:
            self._mode = 0
            self._channel_apd = self._channel_apd_0
        else:
            self._mode = 2

    def on_deactivate(self):
        """ Shut down the TimeTagger.
        """
        #self.reset_hardware()
        pass

    def set_up_odmr(self, counter_channel=None, photon_source=None,
                    clock_channel=None, odmr_trigger_channel=None):
        """
        Setting up the counters in the time tagger, depending on the mode set to it.
        """
        # currently, parameters passed to this function are ignored -- the channels used and clock frequency are
        # set at startup

        if self._mode == 1:
            self.counter = tt.Counter(
                self._tagger,
                channels=[self._channel_apd],
                binwidth=int((1 / self._count_frequency) * 1e12),
                n_values=100
            )
        elif self._mode == 2:
            self.counter0 = tt.Counter(
                self._tagger,
                channels=[self._channel_apd_0],
                binwidth=int((1 / self._count_frequency) * 1e12),
                n_values=100
            )

            self.counter1 = tt.Counter(
                self._tagger,
                channels=[self._channel_apd_1],
                binwidth=int((1 / self._count_frequency) * 1e12),
                n_values=100
            )
        else:
            self.counter = tt.Counter(
                self._tagger,
                channels=[self._channel_apd],
                binwidth=int((1 / self._count_frequency) * 1e12),
                n_values=100
            )

        self.log.info('set up counter with {0}'.format(self._count_frequency))
        return 0

    def get_counter_channels(self):
        if self._mode < 2:
            return [self._channel_apd]
        else:
            return [self._channel_apd_0, self._channel_apd_1]

    def get_constraints(self):
        """ Get hardware limits the device

        @return SlowCounterConstraints: constraints class for slow counter

        FIXME: ask hardware for limits when module is loaded
        """
        # TODO: See if someone needs this method, at the moment it is not being used.

        constraints = SlowCounterConstraints()
        constraints.max_detectors = 2
        constraints.min_count_frequency = 1e-3
        constraints.max_count_frequency = 10e9
        constraints.counting_mode = [CountingMode.CONTINUOUS]
        return constraints

    def count_odmr(self, length=100):
        """ Obtains the counts from the count between markers method of the Time Tagger. Each bin belongs to a different
        frequency in the sweep.
        Returns the counts per second for each bin.
        The length argument is required by the interface, but not used here because it was already defined when the
        counter was initialized.
        """

        t0 = time.time()
        t = 0

        if t >= 5:
            self.log.error('ODMR measurement timed out after {:03.2f} seconds'.format(t))
            err = True
            count_rates = []
        else:
            err = False

            time.sleep(2 / self._count_frequency)
            if self._mode < 2:
                count_rate = self.counter.getData() * self._count_frequency
            else:
                count_rate = self.counter0.getData() * self._count_frequency + \
                              self.counter1.getData() * self._count_frequency
            count_rates = np.append(count_rate, [0])

        return err, count_rates

    def clear_odmr(self):
        """Clear the current measurement in the Time Tagger"""
        self.counter0.clear()
        self.counter1.clear()
        return 0

    def get_counter(self, samples=None):
        """ Returns the current counts per second of the counter.

        @param int samples: if defined, number of samples to read in one go

        @return numpy.array(uint32): the photon counts per second
        """

        # TODO: Implement this using counter, which requires setting up a clock and and a Counter

        return 0

    # From here these are methods from the ODMR counter interface that need to be implemented for the Time Tagger

    def close_odmr(self):
        """ Close the odmr and clean up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        self._tagger.reset()
        return 0

    def set_odmr_length(self, length=100):
        self.sweep_length = length
        return

    # These are useless methods, but the interface requires them

    def get_odmr_channels(self):
        # This sets the channels in the droplist next to the ODMR plot, but I don't think it is useful.
        ch = [1]
        return ch

    def set_up_odmr_clock(self, clock_frequency=None, clock_channel=None):
        return 0

    def close_odmr_clock(self):
        return 0

    def oversampling(self):
        pass

    def lock_in_active(self):
        pass
