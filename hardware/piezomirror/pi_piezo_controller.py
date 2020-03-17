# -*- coding: utf-8 -*-
"""
This file contains the PI Piezo hardware module for Qudi
through offical python moudle "PIPython" created by PI.

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

from core.module import Base
from core.configoption import ConfigOption
from interface.motor_interface import MotorInterface
from collections import OrderedDict

from interface.slow_counter_interface import SlowCounterInterface
from interface.slow_counter_interface import SlowCounterConstraints
from interface.slow_counter_interface import CountingMode
from interface.odmr_counter_interface import ODMRCounterInterface
from interface.confocal_scanner_interface import ConfocalScannerInterface
try:
    from pipython import GCSDevice, pitools, GCSError, gcserror
except ModuleNotFoundError as err:
    raise


class PIPiezoController(Base):
    _modtype = 'PIPiezoController'
    _modclass = 'hardware'

    _ipaddress = ConfigOption("ipaddress", default='192.168.0.8', missing="error")
    _ipport = ConfigOption("ipport", default=50000, missing="warn")
    #_stages = ConfigOption("stages", default=['S-330.8SH', 'S-330.8SH', 'NOSTAGE'], missing="warn")
    _stages = ['S-330.8SH', 'S-330.8SH', 'DEFAULT_STAGE-Z']
    _refmodes = ['FNL', 'FRF']
    _controllername = 'E-727'

    def on_activate(self):
        """ Initialise and activate the hardware module.

            @return: error code (0:OK, -1:error)
        """
        self.pidevice = GCSDevice(self._controllername)
        self.pidevice.ConnectTCPIP(self._ipaddress, self._ipport)
        device_name = self.pidevice.qIDN().strip()
        self.log.info('PI controller {} connected'.format(device_name))
        pitools.startup(self.pidevice, stages=self._stages)

    def on_deactivate(self):
        """ Deinitialise and deactivate the hardware module.

            @return: error code (0:OK, -1:error)
        """
        # TODO add def shutdown(self) to set Votage=0 V for safety.
        # self._set_servo_state(False)
        # If not shutdown, keep servo on to stay on target.
        self.pidevice.errcheck = True
        self.pidevice.CloseConnection()
        self.log.info("PI Device has been closed connection !")
        return 0

    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        Provides all the constraints for the xyz stage  and rot stage (like total
        movement, velocity, ...)
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)

            @return dict constraints : dict with constraints for the device
        """
        # TODO get constraints auto by gcs

        constraints = OrderedDict()
        rangemin = self.pidevice.qTMN()
        rangemax = self.pidevice.qTMX()
        curpos = self.pidevice.qPOS()

        axis0 = {'label': self._first_axis_label,
                 'ID': self._first_axis_ID,
                 'unit': 'm',
                 'ramp': None,
                 'pos_min': self._min_first,
                 'pos_max': self._max_first,
                 'pos_step': self.step_first_axis,
                 'vel_min': None,
                 'vel_max': None,
                 'vel_step': None,
                 'acc_min': None,
                 'acc_max': None,
                 'acc_step': None}

        axis1 = {'label': self._second_axis_label,
                 'ID': self._second_axis_ID,
                 'unit': 'm',
                 'ramp': None,
                 'pos_min': self._min_second,
                 'pos_max': self._max_second,
                 'pos_step': self.step_second_axis,
                 'vel_min': None,
                 'vel_max': None,
                 'vel_step': None,
                 'acc_min': None,
                 'acc_max': None,
                 'acc_step': None}

        axis2 = {'label': self._third_axis_label,
                 'ID': self._third_axis_ID,
                 'unit': 'm',
                 'ramp': None,
                 'pos_min': self._min_third,
                 'pos_max': self._max_third,
                 'pos_step': self.step_third_axis,
                 'vel_min': None,
                 'vel_max': None,
                 'vel_step': None,
                 'acc_min': None,
                 'acc_max': None,
                 'acc_step': None}

        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1
        constraints[axis2['label']] = axis2
        # constraints[axis3['label']] = axis3

        return constraints

    def _has_diff_constrains_check(self):
        """#whether each axis range is smaller than its PI GCS range.
        bool dict flage:_has_diff_constrains will be True.
        To enable hardware-module pre check than PI GCS
        for the axis move to target value.
                             set enable?
                             range pzt hardware?
                             is 'P-563' ?
                             if larger, auto-reset?
        @return True or False
        """
        # TODO
        # constraints = self._configured_constraints
        return False

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """
        pass

    def get_position_range(self):
        """ Returns the physical range of the scanner.

        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit
        """

        pass

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.

        @param float [4][2] myrange: array of 4 ranges with an array containing
                                     lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        pass

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card.

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        pass

    def get_scanner_axes(self):
        """ Find out how many axes the scanning device is using for confocal and their names.

        @return list(str): list of axis names

        Example:
          For 3D confocal microscopy in cartesian coordinates, ['x', 'y', 'z'] is a sensible value.
          For 2D, ['x', 'y'] would be typical.
          You could build a turntable microscope with ['r', 'phi', 'z'].
          Most callers of this function will only care about the number of axes, though.

          On error, return an empty list.
        """
        pass

    def get_scanner_count_channels(self):
        """ Returns the list of channels that are recorded while scanning an image.

        @return list(str): channel names

        Most methods calling this might just care about the number of channels.
        """
        pass

    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """
        pass

    def set_up_scanner(self,
                       counter_channels=None,
                       sources=None,
                       clock_channel=None,
                       scanner_ao_channels=None):
        """ Configures the actual scanner with a given clock.

        @param str counter_channels: if defined, these are the physical conting devices
        @param str sources: if defined, these are the physical channels where
                                  the photons are to count from
        @param str clock_channel: if defined, this specifies the clock for the
                                  counter
        @param str scanner_ao_channels: if defined, this specifies the analoque
                                        output channels

        @return int: error code (0:OK, -1:error)
        """
        pass

    def scanner_set_position(self, x=None, y=None, z=None, a=None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).

        @param float x: postion in x-direction (volts)
        @param float y: postion in y-direction (volts)
        @param float z: postion in z-direction (volts)
        @param float a: postion in a-direction (volts)

        @return int: error code (0:OK, -1:error)
        """
        pass

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[n]: current position in (x, y, z, a).
        """
        pass

    def scan_line(self, line_path=None, pixel_clock=False):
        """ Scans a line and returns the counts on that line.

        @param float[k][n] line_path: array k of n-part tuples defining the pixel positions
        @param bool pixel_clock: whether we need to output a pixel clock for this line

        @return float[k][m]: the photon counts per second for k pixels with m channels
        """
        pass

    def close_scanner(self):
        """ Closes the scanner and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass

    def close_scanner_clock(self, power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass

