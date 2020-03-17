# -*- coding: utf-8 -*-
"""
Interfuse to do confocal scans where two different insturments perform the roles of scanning and photon counting.
The confocal_scanner_interface is intended for the case where one instrument performs both roles - e.g. the NI card.
This is originally intended to be able to use the NI card for the physical scanning, while the Time Tagger will function
as the slow counter.
This is based on the confocal_scanner_spectrometer_interfuse that is built-in to qudi-0.9.
Written by Dan Yudilevich, January 2019.

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

import time
import numpy as np

from core.module import Base
from core.connector import Connector
from core.configoption import ConfigOption
from interface.confocal_scanner_interface import ConfocalScannerInterface


class SlowCounterScannerInterfuse(Base, ConfocalScannerInterface):

    """This is the Interface class to define the controls for the simple
    microwave hardware.
    """
    _modclass = 'confocalscannerinterface'
    _modtype = 'hardware'

    # connectors
    confocalscanner1 = Connector(interface='ConfocalScannerInterface')
    counter1 = Connector(interface='SlowCounterInterface')

    # config options
    _clock_frequency = ConfigOption('clock_frequency', 100, missing='warn')

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)

        # Internal parameters
        self._line_length = None
        self._scanner_counter_daq_task = None
        self._voltage_range = [-10., 10.]

        self._position_range = [[0., 100.], [0., 100.], [0., 100.], [0., 1.]]
        self._current_position = [0., 0., 0., 0.]

        self._num_points = 500

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """

        self._scanner_hw = self.confocalscanner1()
        self._slowcounter_hw = self.counter1()


    def on_deactivate(self):
        self.reset_hardware()

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs can access it.

        @return int: error code (0:OK, -1:error)
        """
        self.log.warning('Scanning Device will be reset.')
        return 0

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
        if myrange is None:
            myrange = [[0,1],[0,1],[0,1],[0,1]]

        self._scanner_hw.set_position_range(myrange=myrange)

        return 0

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card.
        This is a direct pass-through to the scanner HW

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        if myrange is None:
            myrange = [-10.,10.]

        self._scanner_hw.set_voltage_range(myrange=myrange)
        return 0

    def set_up_scanner_clock(self, clock_frequency = None, clock_channel = None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.
        This is a direct pass-through to the scanner HW

        @param float clock_frequency: if defined, this sets the frequency of the clock
        @param string clock_channel: if defined, this is the physical channel of the clock

        @return int: error code (0:OK, -1:error)
        """

        #return self._scanner_hw.set_up_scanner_clock(clock_frequency=clock_frequency, clock_channel=clock_channel)
        return 0

    def set_up_scanner(self, counter_channel = None, photon_source = None, clock_channel = None, scanner_ao_channels = None):
        """ Configures the actual scanner with a given clock.

        TODO this is not technically required, because the spectrometer scanner does not need clock synchronisation.

        @param string counter_channel: if defined, this is the physical channel of the counter
        @param string photon_source: if defined, this is the physical channel where the photons are to count from
        @param string clock_channel: if defined, this specifies the clock for the counter
        @param string scanner_ao_channels: if defined, this specifies the analoque output channels

        @return int: error code (0:OK, -1:error)
        """
        self.log.warning('ConfocalScannerInterfaceDummy>set_up_scanner')
        return 0

    def get_scanner_axes(self):
        """ Pass through scanner axes. """
        return self._scanner_hw.get_scanner_axes()

    def scanner_set_position(self, x = None, y = None, z = None, a = None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).
        This is a direct pass-through to the scanner HW

        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """

        self._scanner_hw.scanner_set_position(x=x, y=y, z=z, a=a)
        return 0

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[]: current position in (x, y, z, a).
        """

        return self._scanner_hw.get_scanner_position()

    def get_scanner_count_channels(self):
        return [1]


    def set_up_line(self, length=100):
        """ Set the line length
        Nothing else to do here, because the line will be scanned using multiple scanner_set_position calls.

        @param int length: length of the line in pixel

        @return int: error code (0:OK, -1:error)
        """
        self._line_length = length
        return 0

    def scan_line(self, line_path=None, pixel_clock=False): #Taken as is from the nix file
        """ Scans a line and return the counts on that line.

        @param float[c][m] line_path: array of c-tuples defining the voltage points
            (m = samples per line)
        @param bool pixel_clock: whether we need to output a pixel clock for this line

        @return float[m][n]: m (samples per line) n-channel photon counts per second

        The input array looks for a xy scan of 5x5 points at the position z=-2
        like the following:
            [ [1, 2, 3, 4, 5], [1, 1, 1, 1, 1], [-2, -2, -2, -2] ]
        n is the number of scanner axes, which can vary. Typical values are 2 for galvo scanners,
        3 for xyz scanners and 4 for xyz scanners with a special function on the a axis.
        """

        if len(self._scanner_counter_channels) > 0 and len(self._scanner_counter_daq_tasks) < 1:
            self.log.error('Configured counter is not running, cannot scan a line.')
            return np.array([[-1.]])

        if len(self._scanner_ai_channels) > 0 and self._scanner_analog_daq_task is None:
            self.log.error('Configured analog input is not running, cannot scan a line.')
            return -1

        if not isinstance(line_path, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.log.error('Given line_path list is not array type.')
            return np.array([[-1.]])
        try:
            # set task timing to use a sampling clock:
            # specify how the Data of the selected task is collected, i.e. set it
            # now to be sampled by a hardware (clock) signal.
            daq.DAQmxSetSampTimingType(self._scanner_ao_task, daq.DAQmx_Val_SampClk)
            self._set_up_line(np.shape(line_path)[1])
            line_volts = self._scanner_position_to_volt(line_path)
            # write the positions to the analog output
            written_voltages = self._write_scanner_ao(
                voltages=line_volts,
                length=self._line_length,
                start=False)

            # start the timed analog output task
            daq.DAQmxStartTask(self._scanner_ao_task)

            for i, task in enumerate(self._scanner_counter_daq_tasks):
                daq.DAQmxStopTask(task)

            daq.DAQmxStopTask(self._scanner_clock_daq_task)

            if pixel_clock and self._pixel_clock_channel is not None:
                daq.DAQmxConnectTerms(
                    self._scanner_clock_channel + 'InternalOutput',
                    self._pixel_clock_channel,
                    daq.DAQmx_Val_DoNotInvertPolarity)

            # start the scanner counting task that acquires counts synchroneously
            for i, task in enumerate(self._scanner_counter_daq_tasks):
                daq.DAQmxStartTask(task)

            if len(self._scanner_ai_channels) > 0:
                daq.DAQmxStartTask(self._scanner_analog_daq_task)

            daq.DAQmxStartTask(self._scanner_clock_daq_task)

            for i, task in enumerate(self._scanner_counter_daq_tasks):
                # wait for the scanner counter to finish
                daq.DAQmxWaitUntilTaskDone(
                    # define task
                    task,
                    # Maximum timeout for the counter times the positions. Unit is seconds.
                    self._RWTimeout * 2 * self._line_length)

            # wait for the scanner clock to finish
            daq.DAQmxWaitUntilTaskDone(
                # define task
                self._scanner_clock_daq_task,
                # maximal timeout for the counter times the positions
                self._RWTimeout * 2 * self._line_length)

            # count data will be written here
            self._scan_data = np.empty(
                (len(self.get_scanner_count_channels()), 2 * self._line_length),
                dtype=np.uint32)

            # number of samples which were read will be stored here
            n_read_samples = daq.int32()
            for i, task in enumerate(self._scanner_counter_daq_tasks):
                # actually read the counted photons
                daq.DAQmxReadCounterU32(
                    # read from this task
                    task,
                    # read number of double the # number of samples
                    2 * self._line_length,
                    # maximal timeout for the read# process
                    self._RWTimeout,
                    # write into this array
                    self._scan_data[i],
                    # length of array to write into
                    2 * self._line_length,
                    # number of samples which were actually read
                    daq.byref(n_read_samples),
                    # Reserved for future use. Pass NULL(here None) to this parameter.
                    None)

                # stop the counter task
                daq.DAQmxStopTask(task)

            # Analog channels
            if len(self._scanner_ai_channels) > 0:
                self._analog_data = np.full(
                    (len(self._scanner_ai_channels), self._line_length + 1),
                    222,
                    dtype=np.float64)

                analog_read_samples = daq.int32()

                daq.DAQmxReadAnalogF64(
                    self._scanner_analog_daq_task,
                    self._line_length + 1,
                    self._RWTimeout,
                    daq.DAQmx_Val_GroupByChannel,
                    self._analog_data,
                    len(self._scanner_ai_channels) * (self._line_length + 1),
                    daq.byref(analog_read_samples),
                    None
                )

                daq.DAQmxStopTask(self._scanner_analog_daq_task)

            # stop the clock task
            daq.DAQmxStopTask(self._scanner_clock_daq_task)

            # stop the analog output task
            self._stop_analog_output()

            if pixel_clock and self._pixel_clock_channel is not None:
                daq.DAQmxDisconnectTerms(
                    self._scanner_clock_channel + 'InternalOutput',
                    self._pixel_clock_channel)

            # create a new array for the final data (this time of the length
            # number of samples):
            self._real_data = np.empty(
                (len(self._scanner_counter_channels), self._line_length),
                dtype=np.uint32)

            # add up adjoint pixels to also get the counts from the low time of
            # the clock:
            self._real_data = self._scan_data[:, ::2]
            self._real_data += self._scan_data[:, 1::2]

            all_data = np.full(
                (len(self.get_scanner_count_channels()), self._line_length), 2, dtype=np.float64)
            all_data[0:len(self._real_data)] = np.array(
                self._real_data * self._scanner_clock_frequency, np.float64)

            if len(self._scanner_ai_channels) > 0:
                all_data[len(self._scanner_counter_channels):] = self._analog_data[:, :-1]

            # update the scanner position instance variable
            self._current_position = np.array(line_path[:, -1])
        except:
            self.log.exception('Error while scanning line.')
            return np.array([[-1.]])
        # return values is a rate of counts/s
        return all_data.transpose()


    def scan_line(self, line_path=None, pixel_clock=False):
        # The old version similar to what appeared in the nix file
        """ Scans a line and returns the counts on that line.

        @param float[][4] line_path: array of 4-part tuples defining the voltage points
        @param bool pixel_clock: whether we need to output a pixel clock for this line

        @return float[]: the photon counts per second
        """

        #if self.module_state() == 'locked':
        #    self.log.error('A scan_line is already running, close this one first.')
        #    return -1
        #
        #self.module_state.lock()

        if not isinstance( line_path, (frozenset, list, set, tuple, np.ndarray, ) ):
            self.log.error('Given voltage list is no array type.')
            return np.array([-1.])

        self.set_up_line(np.shape(line_path)[1])

        count_data = np.zeros(self._line_length)

        for i in xrange(self._line_length):
            coords = line_path[:, i]
            self.scanner_set_position(x=coords[0], y=coords[1], z=coords[2], a=coords[3])
            print(coords)
            print(i)

            # record spectral data
            count_data = self._slowcounter_hw.get_counter()
            time.sleep(0.2)

        return count_data

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """

        #self._scanner_hw.close_scanner()

        return 0

    def close_scanner_clock(self):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        #self._scanner_hw.close_scanner_clock()
        return 0
