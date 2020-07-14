# -*- coding: utf-8 -*-
"""
This file contains the Nanonis LabView controller module for Qudi using the official LabView VI files from SPECS.
author: Dinesh Pinto
email: d.pinto@fkf.mpg.de

* Requires 64-bit LabView with server configured to output to Nanonis

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

Copyright (c) 2020 Dinesh Pinto. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/projecthira/qudi-hira/>
"""
import os
from core.module import Base
from interface.confocal_scanner_interface import ConfocalScannerInterface
from core.configoption import ConfigOption
import subprocess
import numpy as np
import time
import pythoncom
import win32com.client


def _limit_precision(number):
    """ Limit to 10 decimal places of precision to synchronize Python and Nanonis values. Otherwise LabView returns an
    overly precise value. Eg. 5e-9 becomes 4.999999999e-9

    @param number: Number queried from LabView interface
    @return: float: Floating point number as in Nanonis
    """
    return float("{0:.10f}".format(number))


class NanonisFineScanner(Base, ConfocalScannerInterface):
    """Provides software interface to the Nanonis Fine Scanner via LabView.
    """
    _labview_executable = ConfigOption('labview_executable', missing='error')
    _labview_progint_path = ConfigOption('labview_progint_path',  missing='error')
    _vi_casestruct_tcp_alpha = ConfigOption('vi_casestruct_tcp_alpha', default="test\\case_struct_tcp_alpha.vi", missing='warn')
    _vi_folme_speed_set = ConfigOption('vi_folme_speed_set', default="Scan\\Follow Me\\FolMe Speed Set.vi", missing='warn')
    _vi_folme_speed_get = ConfigOption('vi_folme_speed_get', default="Scan\\Follow Me\\FolMe Speed Get.vi", missing='warn')
    _vi_xy_pos_set_fast = ConfigOption('vi_xy_pos_set_fast', default="Scan\\Follow Me\\XY-Pos Set - Fast.vi", missing='warn')
    _vi_folme_stop_movement = ConfigOption('vi_folme_stop_movement', default="Scan\\Follow Me\\FolMe Stop Movement.vi", missing='warn')
    _vi_xy_pos_get = ConfigOption('vi_xy_pos_get', default="Scan\\XY-Pos Get.vi", missing='warn')
    _scanner_position_ranges = ConfigOption('scanner_position_ranges', missing='error')

    # _host = ConfigOption('host', default='localhost', missing='error')
    # _port = ConfigOption('port', default=3353, missing='error')

    def on_activate(self):
        """ Initialise and activate the hardware module.

            @return: error code (0:OK, -1:error)
        """
        # Combine paths together (this needs to be done with self., otherwise the ConfigOption does not reveal itself)
        self._vi_path_casestruct_tcp_alpha = os.path.join(self._labview_progint_path, self._vi_casestruct_tcp_alpha)
        self._vi_path_folme_speed_set = os.path.join(self._labview_progint_path, self._vi_folme_speed_set)
        self._vi_path_folme_speed_get = os.path.join(self._labview_progint_path, self._vi_folme_speed_get)
        self._vi_path_xy_pos_set_fast = os.path.join(self._labview_progint_path, self._vi_xy_pos_set_fast)
        self._vi_path_xy_pos_get = os.path.join(self._labview_progint_path, self._vi_xy_pos_get)
        self._vi_path_folme_stop_movement = os.path.join(self._labview_progint_path, self._vi_folme_stop_movement)

        self.run_casestruct_tcp_alpha()

        return 0
        try:
            # Dispatches a signal to open 64-bit LabView
            # dynamic dispatch is required to ensure late-binding of application, otherwise the code will not be
            # able to read all available LabView container functions
            self.labview = win32com.client.dynamic.Dispatch("Labview.Application")
            # Load all the required VIs for scanner motion
            self.labview._FlagAsMethod("GetVIReference")
            self.scanner_speed_set = self.labview.GetVIReference(self._vi_path_folme_speed_set)
            self.scanner_speed_get = self.labview.GetVIReference(self._vi_path_folme_speed_get)
            self.scanner_xy_pos_set = self.labview.GetVIReference(self._vi_path_xy_pos_set_fast)
            self.scanner_xy_pos_get = self.labview.GetVIReference(self._vi_path_xy_pos_get)
            self.scanner_stop = self.labview.GetVIReference(self._vi_path_folme_stop_movement)
            self.run_casestruct_tcp_alpha()
            # self.open_front_panels()
            self.log.info("Finished loading all required LabView VIs.")
            return 0
        except Exception as exc:
            self.log.error("Error during LabView connection : {}".format(exc))
            return -1

    def on_deactivate(self):
        """ Deinitialise and deactivate the hardware module.

            @return: error code (0:OK, -1:error)
        """
        return 0

        try:
            self.log.info("LabView Save Dialog should be dealt with.")
            self.labview.Quit()
        except TypeError:
            pass
        return 0

    def get_id_from_logic(self, labview_id_logic):
        pythoncom.CoInitialize()

        # Get instance from the id
        self.labview_logic = win32com.client.dynamic.Dispatch(
            pythoncom.CoGetInterfaceAndReleaseStream(labview_id_logic, pythoncom.IID_IDispatch)
        )
        # Load all the required VIs for scanner motion
        self.labview_logic._FlagAsMethod("GetVIReference")
        self.scanner_speed_set_logic = self.labview_logic.GetVIReference(self._vi_path_folme_speed_set)
        self.scanner_speed_get_logic = self.labview_logic.GetVIReference(self._vi_path_folme_speed_get)
        self.scanner_xy_pos_set_logic = self.labview_logic.GetVIReference(self._vi_path_xy_pos_set_fast)
        self.scanner_xy_pos_get_logic = self.labview_logic.GetVIReference(self._vi_path_xy_pos_get)
        self.scanner_stop_logic = self.labview_logic.GetVIReference(self._vi_path_folme_stop_movement)

    def get_id_from_gui(self, labview_id_gui):
        pythoncom.CoInitialize()

        # Get instance from the id
        self.labview_gui = win32com.client.dynamic.Dispatch(
            pythoncom.CoGetInterfaceAndReleaseStream(labview_id_gui, pythoncom.IID_IDispatch)
        )
        # Load all the required VIs for scanner motion
        self.labview_gui._FlagAsMethod("GetVIReference")
        self.scanner_speed_set_gui = self.labview_gui.GetVIReference(self._vi_path_folme_speed_set)
        self.scanner_speed_get_gui = self.labview_gui.GetVIReference(self._vi_path_folme_speed_get)
        self.scanner_xy_pos_set_gui = self.labview_gui.GetVIReference(self._vi_path_xy_pos_set_fast)
        self.scanner_xy_pos_get_gui = self.labview_gui.GetVIReference(self._vi_path_xy_pos_get)
        self.scanner_stop_gui = self.labview_gui.GetVIReference(self._vi_path_folme_stop_movement)

    # def activate_from_logic(self, labview_id):
    #     # Get instance from the id
    #     self.labview = win32com.client.dynamic.Dispatch(
    #         pythoncom.CoGetInterfaceAndReleaseStream(labview_id, pythoncom.IID_IDispatch)
    #     )
    #
    #     # Load all the required VIs for scanner motion
    #     self.labview._FlagAsMethod("GetVIReference")
    #     self.scanner_speed_set = self.labview.GetVIReference(self._vi_path_folme_speed_set)
    #     self.scanner_speed_get = self.labview.GetVIReference(self._vi_path_folme_speed_get)
    #     self.scanner_xy_pos_set = self.labview.GetVIReference(self._vi_path_xy_pos_set_fast)
    #     self.scanner_xy_pos_get = self.labview.GetVIReference(self._vi_path_xy_pos_get)
    #     self.scanner_stop = self.labview.GetVIReference(self._vi_path_folme_stop_movement)
    #
    #     self.run_casestruct_tcp_alpha()
    #     # self.open_front_panels()
    #     self.log.info("Finished loading all required LabView VIs.")
    #     print("getting scan speed from HW")
    #     self.get_scan_speed()

    def deactivate_from_logic(self):
        try:
            self.log.info("LabView Save Dialog should be dealt with.")
            self.labview.Quit()
        except TypeError:
            pass
        return 0

    def run_casestruct_tcp_alpha(self):
        """ Runs a non-blocking command shell prompt in a subprocess to call casestruct_tcp_alpha.vi, which is
        required for setting up the Nanonis server communication.

        :return: 0 if successful
        """
        self.process = subprocess.Popen([self._labview_executable, self._vi_path_casestruct_tcp_alpha])
        self.log.info("Launching LabView in a subprocess PID = {}.".format(self.process.pid))
        return 0

    def reset_hardware(self):
        """ Resets the hardware, so the connection is lost and other programs
            can access it.

        @return int: error code (0:OK, -1:error)
        """
        self.log.warn("reset_hardware not implemented.")
        pass

    def get_position_range(self):
        """ Returns the physical range of the scanner.

        @return float [4][2]: array of 4 ranges with an array containing lower
                              and upper limit. The unit of the scan range is
                              meters.
        """
        return [[0., 1.e-6], [0., 1.e-6], [0., 1.e-6], [0., 1.]]

    def set_position_range(self, myrange=None):
        """ Sets the physical range of the scanner.

        @param float [4][2] myrange: array of 4 ranges with an array containing
                                     lower and upper limit. The unit of the
                                     scan range is meters.

        @return int: error code (0:OK, -1:error)
        """
        if myrange is None:
            myrange = [[0., 1.e-6], [0., 1.e-6], [0., 1.e-6], [0., 1.]]

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
        self.log.warn("set_voltage_range is not implemented")
        return self._scanner_position_ranges

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

    def set_up_scanner(self,
                       counter_channels=None,
                       sources=None,
                       clock_channel=None,
                       scanner_ao_channels=None,
                       scan_speed=None):
        """ Configures the actual scanner with a given clock.

        @param str counter_channels: if defined, these are the physical conting devices
        @param str sources: if defined, these are the physical channels where
                                  the photons are to count from
        @param str clock_channel: if defined, this specifies the clock for the
                                  counter
        @param str scanner_ao_channels: if defined, this specifies the analoque
                                        output channels

        @param scan_speed: speed at which the scanner moves from point to point
        @return int: error code (0:OK, -1:error)
        """
        if scan_speed is not None:
            self.set_scan_speed(scan_speed)
        self.scanner_xy_pos_set.setControlValue("Wait end-of-motion (T=True)", True)
        self.scanner_xy_pos_get.setControlValue("Wait for newest data (F=False)", True)
        return 0

    def set_up_scanner_clock(self, clock_frequency=None, clock_channel=None):
        """ Configures the hardware clock of the NiDAQ card to give the timing.

        @param float clock_frequency: if defined, this sets the frequency of the
                                      clock
        @param str clock_channel: if defined, this is the physical channel of
                                  the clock

        @return int: error code (0:OK, -1:error)
        """
        pass

    def set_scan_speed(self, scan_speed):
        """ Set Nanonis Follow Me speed. Defines how quickly the scanner moves from point to point between measurements.

        @param scan_speed: scanner speed in m/s
        @return: int: error code (0:OK, -1:error)
        """
        self.scanner_speed_set.setControlValue("Speed (m/s)", scan_speed)
        self.scanner_speed_set.setControlValue("Speed Setting (Custom)", 1)
        try:
            self.scanner_speed_set.Run()
        except TypeError:
            pass
        return 0

    def get_scan_speed(self):
        """ Get Nanonis Follow Me speed. Defines how quickly the scanner moves from point to point between measurements.

        @return: float: scanner speed in m/s
        """
        try:
            self.scanner_speed_get.Run()
        except TypeError:
            pass
        speed = _limit_precision(self.scanner_speed_get.getControlValue("Speed (m/s)"))

        # 0 = Scan setting; 1 = Custom setting
        speed_setting = self.scanner_speed_get.getControlValue("Speed Setting")

        print(speed_setting)
        if speed_setting != 1:
            self.log.warn("Scanner speed is not set to custom. Run set_scan_speed")
        return speed

    def scanner_set_position(self, x=None, y=None, z=None, a=None):
        """Move stage to x, y, z, a (where a is the fourth voltage channel).

        @param float x: position in x-direction (m)
        @param float y: position in y-direction (m)

        @return int: error code (0:OK, -1:error)
        """
        print(x, y)
        time.sleep(1)
        try:
            self.scanner_xy_pos_set_logic.setControlValue("X (m)", x)
            self.scanner_xy_pos_set_logic.setControlValue("Y (m)", y)
            print("Set logic")
        except TypeError:
            pass
        except Exception:
            try:
                self.scanner_xy_pos_set_gui.setControlValue("X (m)", x)
                self.scanner_xy_pos_set_gui.setControlValue("Y (m)", y)
                print("Set GUI")
            except TypeError:
                pass


        try:
            self.scanner_xy_pos_set_logic.Run()
        except TypeError:
            pass
        except Exception:
            try:
                self.scanner_xy_pos_set_gui.Run()
            except TypeError:
                pass
        print("Im here")

        actual_pos = self.get_scanner_position()

        if x != actual_pos[0] or y != actual_pos[1]:
            self.log.warn("Scanners did not set position correctly. TARGET = {0},{1}, ACTUAL = {2},{3}".
                          format(x, y, actual_pos[0], actual_pos[1]))
        return 0

    def get_frequency_shift(self):
        # TODO Extract frequency shift data from "FolMe Tip Recorder Data Get.vi"
        pass

    def get_scanner_position(self):
        """ Get the current position of the scanner hardware.

        @return float[n]: current position in (x, y, z, a).
        """
        try:
            self.scanner_xy_pos_get_logic.Run()
        except TypeError:
            pass
        except Exception:
            try:
                self.scanner_xy_pos_get_gui.Run()
            except TypeError:
                pass
        # Limit to 10 decimal places of precision to synchronize Python and Nanonis values
        try:
            x = _limit_precision(self.scanner_xy_pos_get_logic.getControlValue("X (m)"))
            y = _limit_precision(self.scanner_xy_pos_get_logic.getControlValue("Y (m)"))
        except TypeError:
            pass
        except Exception:
            try:
                x = _limit_precision(self.scanner_xy_pos_get_gui.getControlValue("X (m)"))
                y = _limit_precision(self.scanner_xy_pos_get_gui.getControlValue("Y (m)"))
            except TypeError:
                pass
        return [x, y, 0., 0.]

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
        try:
            self.scanner_stop.Run()
        except TypeError:
            pass
        return 0

    def close_scanner_clock(self, power=0):
        """ Closes the clock and cleans up afterwards.

        @return int: error code (0:OK, -1:error)
        """
        pass

    def open_front_panels(self):
        """ Open all LabView front panels used.

        @return: 0
        """
        try:
            self.scanner_speed_set.OpenFrontPanel()
        except TypeError:
            pass
        try:
            self.scanner_xy_pos_set.OpenFrontPanel()
        except TypeError:
            pass
        try:
            self.scanner_speed_get.OpenFrontPanel()
        except TypeError:
            pass
        try:
            self.scanner_stop.OpenFrontPanel()
        except TypeError:
            pass
        try:
            self.scanner_xy_pos_get.OpenFrontPanel()
        except TypeError:
            pass
        return 0
