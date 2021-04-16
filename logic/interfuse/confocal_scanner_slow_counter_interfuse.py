# -*- coding: utf-8 -*-
__author__ = "Dinesh Pinto"
__email__ = "d.pinto@fkf.mpg.de"
"""
Interfuse to perform confocal scans when using different hardware to perform scanning and photon counting. 
An example will be scanning with a PI controller (over ConfocalScannerInterface) and counting photons with a 
TimeTagger (over SlowCounterInterface).

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
from core.connector import Connector
from core.configoption import ConfigOption

from interface.confocal_scanner_interface import ConfocalScannerInterface


class SlowCounterScannerInterfuse(Base, ConfocalScannerInterface):
    """ This is the interfuse class between ConfocalScannerInterface and SlowCounterInterface.
    """
    # connectors
    confocalscanner1 = Connector(interface='ConfocalScannerInterface')
    counter1 = Connector(interface='SlowCounterInterface')
    _clock_frequency = ConfigOption('clock_frequency', 100, missing='warn')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # Internal parameters
        self._line_length = None
        self._voltage_range = [-10., 10.]

        self._num_points = 500

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        self._scanner_hw = self.confocalscanner1()
        self._slowcounter_hw = self.counter1()

        self._current_position = [0., 0., 0., 0.][0:len(self._scanner_hw.get_scanner_axes())]
        self._position_range = self.get_position_range()

    def on_deactivate(self):
        self.reset_hardware()

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs can access it.

        @return int: error code (0:OK, -1:error)
        """
        return self._scanner_hw.reset_hardware()

    def get_position_range(self):
        """ Returns the physical range of the scanner.
        This is a direct pass-through to the scanner HW.

        @return float [4][2]: array of 4 ranges with an array containing lower and upper limit
        """
        return self._scanner_hw.get_position_range()

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.
        This is a direct pass-through to the scanner HW

        @param float [4][2] myrange: array of 4 ranges with an array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        return self._scanner_hw.set_position_range(myrange=myrange)

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card.
        This is a direct pass-through to the scanner HW

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        return self._scanner_hw.set_voltage_range(myrange=myrange)

    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.
        This is a direct pass-through to the scanner HW

        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock

        @return int: error code (0:OK, -1:error)
        """
        self._clock_frequency = float(clock_frequency)

        # return self._scanner_hw.set_up_scanner_clock(clock_frequency=clock_frequency, clock_channel=clock_channel)
        return self._slowcounter_hw.set_up_clock(clock_frequency=clock_frequency)

    def set_up_scanner(self, counter_channel=None, photon_source=None, clock_channel=None, scanner_ao_channels=None):
        """ Configures the actual scanner with a given clock.

        TODO this is not technically required, because the spectrometer scanner does not need clock synchronisation.

        @param string counter_channel: if defined, this is the physical channel of the counter
        @param string photon_source: if defined, this is the physical channel where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for the counter
        @param string scanner_ao_channels: if defined, this specifies the analoque output channels

        @return int: error code (0:OK, -1:error)
        """
        return self._slowcounter_hw.set_up_counter()

    def get_scanner_axes(self):
        """ Pass through scanner axes. """
        return self._scanner_hw.get_scanner_axes()

    def scanner_set_position(self, x=None, y=None, z=None, a=None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).
        This is a direct pass-through to the scanner HW

        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """
        self._current_position = [x, y, z, a][0:len(self.get_scanner_axes())]

        return self._scanner_hw.scanner_set_position(x=x, y=y)

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """

        return self._current_position[0:len(self._scanner_hw.get_scanner_axes())]

    def get_scanner_count_channels(self):
        return ['1']

    def set_up_line(self, length=100):
        """ Set the line length
        Nothing else to do here, because the line will be scanned using multiple scanner_set_position calls.

        @param int length: length of the line in pixel

        @return int: error code (0:OK, -1:error)
        """
        self._line_length = length
        return 0

    def scan_line(self, line_path=None, pixel_clock=False):
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the voltage points
        @param bool pixel_clock: whether we need to output a pixel clock for this line

        @return float[]: the photon counts per second
        """

        if not isinstance(line_path, (frozenset, list, set, tuple, np.ndarray)):
            self.log.error('Given voltage list is no array type.')
            return np.array([-1.])

        self.set_up_line(np.shape(line_path)[1])

        line_counts = np.zeros((self._line_length, 1))

        for i in range(self._line_length):
            coords = line_path[:, i]
            self.scanner_set_position(x=coords[0], y=coords[1])
            # record spectral data
            line_counts[i] = self._slowcounter_hw.get_counter()

        self._current_position = line_path[:, -1]

        return line_counts

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        # self._scanner_hw.close_scanner()
        self.log.debug("Lying to ConfocalLogic : close_scanner")
        return 0

    def close_scanner_clock(self, power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        # self._scanner_hw.close_scanner_clock()
        self.log.debug("Lying to ConfocalLogic : close_scanner_clock")
        return 0
