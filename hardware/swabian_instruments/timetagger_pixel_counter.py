import TimeTagger as tt
import numpy as np

from core.module import Base
from core.configoption import ConfigOption
from interface.slow_counter_interface import SlowCounterConstraints
from interface.slow_counter_interface import CountingMode
from interface.slow_counter_interface import SlowCounterInterface


class TimeTaggerPixelCounter(Base, SlowCounterInterface):
    _channel_apd_0 = ConfigOption('timetagger_channel_apd_0', missing='error')
    _channel_apd_1 = ConfigOption('timetagger_channel_apd_1', missing='error')
    _pixel_trigger = ConfigOption('pixel_trigger', missing='error')

    _tagger = None
    _clicks_combined = None
    pixel_counter = None

    def on_activate(self):
        """ Start up TimeTagger interface
        """
        self._tagger = tt.createTimeTagger()

    def on_deactivate(self):
        """ Shut down the TimeTagger.
        """
        self._tagger.reset()
        return 0

    def set_up_counter(
            self,
            counter_buffer=None,
            counter_channels=None,
            sources=None,
            clock_channel=None
    ):

        self._clicks_combined = tt.Combiner(
            tagger=self._tagger,
            channels=[self._channel_apd_0, self._channel_apd_1]
        )
        _click_channel = self._clicks_combined.getChannel()

        self.pixel_counter = tt.CountBetweenMarkers(
            tagger=self._tagger,
            click_channel=_click_channel,
            begin_channel=self._pixel_trigger,
            n_values=counter_buffer
        )
        self.log.info('set up counter with {} pixels'.format(counter_buffer))
        return 0

    def get_counter_channels(self):
        return [self._channel_apd_0, self._channel_apd_1]

    def get_constraints(self):
        """ Get hardware limits the device
        """
        constraints = SlowCounterConstraints()
        constraints.max_detectors = 2
        constraints.min_count_frequency = 1e-3
        constraints.max_count_frequency = 10e9
        constraints.counting_mode = [CountingMode.CONTINUOUS]
        return constraints

    def get_counter(self, samples=None):
        count_array = self.pixel_counter.getData()
        bin_widths = self.pixel_counter.getBinWidths()
        # Bin widths are in ps, convert to s
        count_rates = np.divide(count_array, (bin_widths * 10 ** -12))
        return count_rates

    def close_counter(self):
        """Clear the current measurement data in the Time Tagger"""
        if self.pixel_counter:
            self.pixel_counter.clear()
        return 0

    def reset_tagger(self):
        self._tagger.reset()
        return 0

    def set_up_clock(self, clock_frequency=None, clock_channel=None):
        # Clock is given by Nanonis trigger
        pass

    def close_clock(self):
        pass
