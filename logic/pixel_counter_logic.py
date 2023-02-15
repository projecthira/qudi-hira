import datetime
from collections import OrderedDict

import matplotlib.pyplot as plt
import numpy as np

from core.connector import Connector
from logic.generic_logic import GenericLogic


class PixelCounterLogic(GenericLogic):
    counter = Connector(interface='SlowCounterInterface')
    savelogic = Connector(interface='SaveLogic')

    _counting_device = None
    _save_logic = None
    pixels = None
    lines = None
    count_rates = None
    forward_counts = None
    backward_counts = None

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        # Connect to hardware and save logic
        self._counting_device = self.counter()
        self._save_logic = self.savelogic()

    def on_deactivate(self):
        """ De-initialisation performed during deactivation of the module.
        """
        pass

    def trigger_pixel_counter(self, pixels, lines=None):
        """ Trigger the pixel counter with a given number of pixels and lines.

        @param int pixels: number of pixels per line to count
        @param int lines: number of lines to count (default: number of pixels)
        """
        if not lines:
            # Use equal number of lines as pixels
            self.lines = pixels
        else:
            self.lines = lines

        self.pixels = pixels

        # Subtract 1 as last pixel doesn't have a closing trigger
        total_pixels = 2 * self.pixels * self.lines - 1

        # Set up data arrays
        self.count_rates = np.zeros(self.pixels * self.lines)
        self.forward_counts = np.zeros((self.pixels, self.lines))
        self.backward_counts = np.zeros((self.pixels, self.lines))

        # Set up counter
        self._counting_device.set_up_counter(counter_buffer=total_pixels)
        return 0

    def _get_cleaned_count_rate(self):
        """ Get the count rate from the pixel counter and clean it up. """

        # Get raw count rates
        count_rates = self.get_counter()

        # Add last data point to the end of the array to get an N*N array
        count_rates = np.append(count_rates, count_rates[-1])

        return count_rates

    def update_counts(self):
        """ Get the forward and backward counts from the pixel counter. """
        self.count_rates = self._get_cleaned_count_rate()

        # Since the data is collected from forward-backward scans
        # Split the data into N parts where each element contains 2 * pixels
        split_array = np.split(self.count_rates, 2 * self.pixels)

        # Extract forward scan array as every second element
        self.forward_counts = np.stack(split_array[::2])
        # Extract backward scan array as every shifted second element
        # Flip scan so that backward and forward scans represent the same data
        self.backward_counts = np.flip(np.stack(split_array[1::2]), axis=1)
        return self.forward_counts, self.backward_counts

    def draw_figure(self, data, parameters):
        plt.style.use(self._save_logic.mpl_qudihira_style)

        pixels = parameters["Pixels"]
        forward = data["Forward Counts (cps)"].reshape(pixels, pixels)
        backward = data["Backward Counts (cps)"].reshape(pixels, pixels)

        fig, (ax, ax1, ax2, ax3) = plt.subplots(ncols=4, sharey="row")

        img_forward = ax.imshow(forward, origin="lower", interpolation="hanning")
        ax.set_title("Forward")
        fig.colorbar(img_forward, ax=ax, shrink=0.4)

        img_backward = ax1.imshow(backward, origin="lower", interpolation="hanning")
        ax1.set_title("Backward")
        fig.colorbar(img_backward, ax=ax1, shrink=0.4)

        img_sum = ax2.imshow(forward + backward, origin="lower", interpolation="hanning")
        ax2.set_title("Sum")
        fig.colorbar(img_sum, ax=ax2, shrink=0.4)

        img_mean = ax3.imshow((forward + backward) / 2, origin="lower", interpolation="hanning")
        ax3.set_title("Mean")
        fig.colorbar(img_mean, ax=ax3, shrink=0.4)

        return fig

    def save_data(self, tag=None):
        timestamp = datetime.datetime.now()

        filepath = self._save_logic.get_path_for_module(module_name='PixelScanner')

        if tag:
            file_label = '{0}_pixelscanner'.format(tag)
        else:
            file_label = 'pixelscanner'

        # write the parameters:
        parameters = OrderedDict()
        parameters['Pixels'] = self.pixels
        parameters['Lines'] = self.lines

        data = OrderedDict()
        data['Count Rates (cps)'] = self.count_rates
        data['Forward Counts (cps)'] = self.forward_counts.flatten()
        data['Backward Counts (cps)'] = self.backward_counts.flatten()

        fig = self.draw_figure(data=data, parameters=parameters)

        self._save_logic.save_data(
            data,
            filepath=filepath,
            parameters=parameters,
            filelabel=file_label,
            timestamp=timestamp,
            plotfig=fig,
            delimiter='\t'
        )
