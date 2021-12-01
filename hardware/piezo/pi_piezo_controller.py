# -*- coding: utf-8 -*-
"""
This file contains the PI Piezo hardware module for Qudi through official python module "PIPython" created by PI.
author: Dinesh Pinto
email: d.pinto@fkf.mpg.d

* Requires PIPython: https://github.com/git-anonymous/PIPython
* pip install --upgrade git+https://github.com/git-anonymous/PIPython.git

Qudi is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Qudi is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Qudi. If not, see <https://www.gnu.org/licenses/>.

Copyright (c) 2020 Dinesh Pinto. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at
<https://github.com/projecthira/qudi-hira/>
"""

from core.module import Base
from core.configoption import ConfigOption
from interface.confocal_scanner_interface import ConfocalScannerInterface
import numpy as np
import time
try:
    from pipython import GCSDevice, pitools, GCSError, gcserror
except ModuleNotFoundError as err:
    raise


class PIPiezoController(Base, ConfocalScannerInterface):
    _modtype = 'PIPiezoController'
    _modclass = 'hardware'

    _ipaddress = ConfigOption("ipaddress", default='192.168.0.8', missing="error")
    _ipport = ConfigOption("ipport", default=50000, missing="warn")
    _stages = ConfigOption("stages", default=['S-330.8SH', 'S-330.8SH'], missing="error")
    _scanner_position_ranges = ConfigOption('scanner_position_ranges', missing='error')
    _x_scanner = ConfigOption("x_scanner", default='1', missing="warn")
    _y_scanner = ConfigOption("y_scanner", default='2', missing="warn")
    _z_scanner = ConfigOption("z_scanner", default=None)
    _controllername = ConfigOption("controllername", missing="error")
    fine_scanning_mode = ConfigOption("fine_scanning_mode", default=False, missing="warn")
    _refmodes = None
    pidevice = None

    def on_activate(self):
        """ Initialise and activate the hardware module.

            @return: error code (0:OK, -1:error)
        """
        self.sleeper = 0.02
        try:
            self.pidevice = GCSDevice(self._controllername)
            self.pidevice.ConnectTCPIP(self._ipaddress, self._ipport)
            device_name = self.pidevice.qIDN().strip()
            self.log.info('PI controller {} connected'.format(device_name))
            pitools.startup(self.pidevice, stages=self._stages)
            self._current_position = [0., 0., 0., 0.][0:len(self.get_scanner_axes())]
            return 0
        except GCSError as error:
            self.log.error(error)
            return -1

    def on_deactivate(self):
        """ Deinitialise and deactivate the hardware module.

            @return: error code (0:OK, -1:error)
        """
        # self._set_servo_state(False)
        # If not shutdown, keep servo on to stay on target.
        try:
            self.pidevice.CloseConnection()
            self.log.info("PI Device has been closed connection !")
            return 0
        except GCSError as error:
            self.log.error(error)
            return -1

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """
        try:
            self.pidevice.close()
            self.log.info("PI Device has been reset")
            return 0
        except GCSError as error:
            self.log.error(error)
            return -1

    def get_position_range(self):
        """ Returns the physical range of the scanner.

        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit. The unit of the scan range is
                              meters.
        """
        return self._scanner_position_ranges

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.

        @param float [4][2] myrange: array of 4 ranges with an array containing
                                     lower and upper limit. The unit of the
                                     scan range is meters.

        @return int: error code (0:OK, -1:error)
        """
        if myrange is None:
            # myrange = [[0., 1.e-3], [0., 1.e-3], [0., 1e-4], [0., 1.]]
            myrange = self._scanner_position_ranges

        if not isinstance(myrange, (frozenset, list, set, tuple, np.ndarray,)):
            self.log.error('Given range is no array type.')
            return -1

        if len(myrange) != 4:
            self.log.error(
                'Given range should have dimension 4, but has {0:d} instead.'
                ''.format(len(myrange)))
            return -1

        for pos in myrange:
            if len(pos) != 2:
                self.log.error(
                    'Given range limit {1:d} should have dimension 2, but has {0:d} instead.'
                    ''.format(len(pos), pos))
                return -1
            if pos[0] > pos[1]:
                self.log.error(
                    'Given range limit {0:d} has the wrong order.'.format(pos))
                return -1

        self._scanner_position_ranges = myrange
        return 0

    def set_voltage_range(self, myrange=None):
        """ Sets the voltage range of the NI Card.

        @param float [2] myrange: array containing lower and upper limit

        @return int: error code (0:OK, -1:error)
        """
        return 0

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
        return ['x', 'y', 'z']

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

    def set_fine_scanning_mode(self, mode):
        """
        Switch between fine and coarse scanning
        @param mode: bool, values can be True (fine) and False (coarse)
        @return:
        """
        self.fine_scanning_mode = mode
        return 0

    def scanner_set_position(self, x=None, y=None, z=None, a=None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).

        @param float x: position in x-direction (m)
        @param float y: position in y-direction (m)

        @return int: error code (0:OK, -1:error)
        """
        if self.module_state() == 'locked':
            self.log.error('Another scan_line is already running, close this one first.')
            return -1

        if x is not None:
            if not (self._scanner_position_ranges[0][0] <= x <= self._scanner_position_ranges[0][1]):
                self.log.error('You want to set x out of range: {0:f}.'.format(x))
                return -1
            self._current_position[0] = np.float(x)
        else:
            x = self._current_position[0]

        if y is not None:
            if not (self._scanner_position_ranges[1][0] <= y <= self._scanner_position_ranges[1][1]):
                self.log.error('You want to set y out of range: {0:f}.'.format(y))
                return -1
            self._current_position[1] = np.float(y)
        else:
            y = self._current_position[1]

        if z is not None:
            if not (self._scanner_position_ranges[2][0] <= z <= self._scanner_position_ranges[2][1]):
                self.log.error('You want to set z out of range: {0:f}.'.format(z))
                return -1
            self._current_position[2] = np.float(z)
        else:
            z = self._current_position[2]

        if a is not None:
            if not (self._scanner_position_ranges[3][0] <= a <= self._scanner_position_ranges[3][1]):
                self.log.error('You want to set a out of range: {0:f}.'.format(a))
                return -1
            self._current_position[3] = np.float(a)

        try:
            if self._z_scanner is None:
                axes = [self._x_scanner, self._y_scanner]
                # Axes will start moving to the new positions if ALL given targets are within the allowed ranges and
                # ALL axes can move. All axes start moving simultaneously.
                # Servo must be enabled for all commanded axes prior to using this command.

                # Transform x and y position
                # x_pos = (x / 4) * 1e9
                # y_pos = (y / 4) * 1e9
                self.pidevice.MOV(axes=axes, values=[x * 1e6, y * 1e6])
            else:
                axes = [self._x_scanner, self._y_scanner, self._z_scanner]
                # Axes will start moving to the new positions if ALL given targets are within the allowed ranges and
                # ALL axes can move. All axes start moving simultaneously.
                # Servo must be enabled for all commanded axes prior to using this command.
                self.pidevice.MOV(axes=axes, values=[x * 1.e6, y * 1.e6, z * 1.e6])
        except Exception as exc:
            self.log.error(f"Exception when moving: {exc}")
            return -1

        # Takes longer but does more error checking
        # pitools.waitontarget(self.pidevice, axes=axes)

        if self.fine_scanning_mode:
            # Check if axes have reached the target.
            while not all(list(self.pidevice.qONT(axes).values())):
                # Can go as low as 1 ms
                time.sleep(self.sleeper)
        else:
            #
            time.sleep(self.sleeper)
        return 0

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[n]: current position in (x, y, z, a).
        """
        position = self.pidevice.qPOS()
        if self._z_scanner is None:
            return [position['1'] * 4 * 1e-3, position['2'] * 4 * 1e-3, 0., 0.]
        else:
            self.log.error(position)
            return [position['1'] * 1e-6, position['2'] * 1e-6, position['3'] * 1e-6, 0.]

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
        self.pidevice.HLT()
        return 0

    def close_scanner_clock(self, power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass
