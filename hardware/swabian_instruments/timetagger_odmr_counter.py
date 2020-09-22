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
    _cw_channel_trigger = ConfigOption('cw_timetagger_channel_trigger', missing='error')
    _pulsed_channel_trigger = ConfigOption('pulsed_timetagger_channel_trigger', missing='error')
    sweep_length = 100

    def on_activate(self):
        """ Start up TimeTagger interface
        """
        self._tagger = tt.createTimeTagger()

        # Configuring if we are working with one APD or two
        if self._channel_apd_1 is None:
            self._mode = 1
        else:
            self._mode = 2

    def on_deactivate(self):
        """ Shut down the TimeTagger.
        """
        self._tagger.reset()
        return 0

    def set_up_odmr(self, counter_channel=None, photon_source=None,
                    clock_channel=None, odmr_trigger_channel=None):
        """
        Setting up the counters in the time tagger, depending on the mode set to it.
        """

        """
        This is the is the original implementation, that was changed due to difficulty using the combiner channel. It is
        a more elegant solution if these issues are resolved.         
        """

        # Default trigger levels are 0.5V. The channel with the splitter needs a higher trigger to avoid ghost counts.
        # self._tagger.setTriggerLevel(self._channel_apd_0, 1.0)
        # self._tagger.setTriggerLevel(self._channel_apd_1, 1.0)
        # self._tagger.setTriggerLevel(self._channel_trigger, 1.0)

        # Combine channel internally for both continuous and pulsed measurements
        self.trigger_combined = tt.Combiner(tagger=self._tagger,
                                    channels=[self._cw_channel_trigger, self._pulsed_channel_trigger])
        self._channel_trigger = self.trigger_combined.getChannel()

        if self._mode == 1:
            self._channel_clicks = self._channel_apd_0
        if self._mode == 2:
            self.combined = tt.Combiner(tagger=self._tagger,
                                        channels=[self._channel_apd_0, self._channel_apd_1])
            self._channel_clicks = self.combined.getChannel()

        self.triggered_counter = tt.CountBetweenMarkers(tagger=self._tagger,
                                                        click_channel=self._channel_clicks,
                                                        begin_channel=self._channel_trigger,
                                                        n_values=self.sweep_length)
        self.log.info('set up counter with {0} channels and sweep length {1}'.format(self._mode, self.sweep_length))
        return 0

    def get_counter_channels(self):
        return self._channel_clicks

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

    def count_odmr(self, length=100, pulsed=False):
        """ Obtains the counts from the count between markers method of the Time Tagger. Each bin belongs to a different
        frequency in the sweep.
        Returns the counts per second for each bin.
        The length argument is required by the interface, but not used here because it was already defined when the
        counter was initialized.
        """

        t0 = time.time()
        t = 0
        while (not self.triggered_counter.ready()) and (t < 5):
            time.sleep(0.1)
            t = time.time()-t0

        if t >= 5:
            self.log.error('ODMR measurement timed out after {:03.2f} seconds'.format(t))
            err = True
            count_rates = []
        else:
            err = False
            count_array = self.triggered_counter.getData()
            bin_widths = self.triggered_counter.getBinWidths()
            count_rates = np.divide(count_array, (bin_widths * 10 ** -12))

            # The count array intentionally discards the last bin because it isn't terminated by a pulse (at the end of
            # the average_factor number of repetitions. To allow for later reshaping of the array we add another cell
            # with zero. This should have very little effect on the counts.
            if pulsed:
                count_rates = np.append(count_rates, [0])

        return err, count_rates

    def clear_odmr(self):
        """Clear the current measurement in the Time Tagger"""
        self.triggered_counter.clear()
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
        """
        Set length of ODMR in pixels. It should be called before set_up_odmr to ensure array is created correctly.

        @param length: Length of ODMR in pixels
        @return: int: error code (0:OK, -1:error)
        """
        self.sweep_length = length
        return 0

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
