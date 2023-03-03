import TimeTagger as tt
import time
import numpy as np

from core.module import Base
from core.configoption import ConfigOption
from interface.slow_counter_interface import SlowCounterConstraints
from interface.slow_counter_interface import CountingMode


class TimeTaggerPixelCounter(Base):
    _channel_apd_0 = ConfigOption('timetagger_channel_apd_0', missing='error')
    _channel_apd_1 = ConfigOption('timetagger_channel_apd_1', missing='error')
    _pixel_trigger = ConfigOption('pixel_trigger', missing='error')

    _tagger = None
    _clicks_combined = None
    _click_channel = None
    triggered_counter = None
    pixels = 0

    def on_activate(self):
        """ Start up TimeTagger interface
        """
        self._tagger = tt.createTimeTagger()

    def on_deactivate(self):
        """ Shut down the TimeTagger.
        """
        self._tagger.reset()
        return 0

    def configure(self, pixels):
        self.pixels = pixels
        total_pixels = 2 * self.pixels ** 2 - 1

        self._clicks_combined = tt.Combiner(
            tagger=self._tagger,
            channels=[self._channel_apd_0, self._channel_apd_1]
        )
        self._click_channel = self._clicks_combined.getChannel()

        self.triggered_counter = tt.CountBetweenMarkers(
            tagger=self._tagger,
            click_channel=self._click_channel,
            begin_channel=self._pixel_trigger,
            n_values=total_pixels
        )
        self.log.info('set up counter with {} pixels'.format(total_pixels))
        return 0

    def get_counter_channels(self):
        return self._click_channel

    def get_constraints(self):
        """ Get hardware limits the device
        """
        constraints = SlowCounterConstraints()
        constraints.max_detectors = 2
        constraints.min_count_frequency = 1e-3
        constraints.max_count_frequency = 10e9
        constraints.counting_mode = [CountingMode.CONTINUOUS]
        return constraints

    def get_final_counts(self):
        t0 = time.time()
        t = 0
        while (not self.triggered_counter.ready()) and (t < 5):
            time.sleep(0.1)
            t = time.time() - t0

        if t >= 5:
            self.log.error('No data or incomplete data recorded, timing out...')
            err = True
            count_rates = []
        else:
            err = False
            count_array = self.triggered_counter.getData()
            bin_widths = self.triggered_counter.getBinWidths()
            count_rates = np.divide(count_array, (bin_widths * 10 ** -12))
        return err, count_rates

    def get_cleaned_count_rate(self):
        raw_counts = self.triggered_counter.getData()
        raw_bin_widths = self.triggered_counter.getBinWidths()

        # Since no trigger is received for the last point, set it to the previous data point
        counts = np.append(raw_counts, raw_counts[-1])
        bin_widths = np.append(raw_bin_widths, raw_bin_widths[-1])

        # Calculate counts per second
        count_rates = np.divide(counts, (bin_widths * 10 ** -12))
        return count_rates

    def get_forward_backward_counts(self, count_rates):
        # Since the data is collected from forward-backward scans
        # Split the data into N parts where each element contains 2 * pixels
        split_array = np.split(count_rates, 2 * self.pixels)
        # Extract forward scan array as every second element
        forward = np.stack(split_array[::2])
        # Extract backward scan array as every shifted second element
        # Flip scan so that backward and forward scans represent the same data
        backward = np.flip(np.stack(split_array[1::2]), axis=1)
        return forward, backward

    def clear_counter(self):
        """Clear the current measurement in the Time Tagger"""
        if self.triggered_counter:
            self.triggered_counter.clear()
        return 0

    def reset_tagger(self):
        self._tagger.reset()
        return 0
