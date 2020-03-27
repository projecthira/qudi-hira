# -*- coding: utf-8 -*-
__author__ = "Dinesh Pinto"
__email__ = "d.pinto@fkf.mpg.de"
"""
This file contains the Nanonis LabView controller module for Qudi
using the official LabView VI files from SPECS. 

Requires 64-bit LabView with backend configured to output to Nanonis

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
import os
from core.configoption import ConfigOption
import win32com.client


class NanonisCoarseMotion(Base):
    """Provides software backend to the Nanonis via LabView.
    """
    _vi_base_folder_path = ConfigOption('vi_base_folder_path', missing='error')
    _vi_file_motor_frequency_amplitude_get = ConfigOption('vi_file_motor_frequency_amplitude_get',  missing='error')
    _vi_file_motor_frequency_amplitude_set = ConfigOption('vi_file_motor_frequency_amplitude_set',  missing='error')
    _vi_file_motor_start_move = ConfigOption('vi_file_motor_start_move',  missing='error')
    _vi_file_motor_step_counter_get = ConfigOption('vi_file_motor_step_counter_get',  missing='error')
    _vi_file_motor_stop_move = ConfigOption('vi_file_motor_stop_move',  missing='error')

    # Create paths to all VI files
    _vi_path_motor_frequency_amplitude_get = os.path.join(_vi_base_folder_path, _vi_file_motor_frequency_amplitude_get)
    _vi_path_motor_frequency_amplitude_set = os.path.join(_vi_base_folder_path, _vi_file_motor_frequency_amplitude_set)
    _vi_path_motor_start_move = os.path.join(_vi_base_folder_path, _vi_file_motor_start_move)
    _vi_path_motor_step_counter_get = os.path.join(_vi_base_folder_path, _vi_file_motor_step_counter_get)
    _vi_path_motor_stop_move = os.path.join(_vi_base_folder_path, _vi_file_motor_stop_move)

    #_host = ConfigOption('host', default='localhost', missing='error')

    _host = 'localhost'
    #_port = ConfigOption('port', default=3353, missing='error')
    _port = 3364

    def on_activate(self):
        try:
            # Dispatches a signal to open 64-bit LabView
            self.labview = win32com.client.Dispatch("Labview.Application")
            # Load all the required VIs for piezo coarse motion
            self.motor_freq_amp_get = self.labview.GetVIReference(self._vi_path_motor_frequency_amplitude_get)
            self.motor_freq_amp_set = self.labview.GetVIReference(self._vi_path_motor_frequency_amplitude_set)
            self.motor_start_move = self.labview.GetVIReference(self._vi_path_motor_start_move)
            self.motor_step_counter_get = self.labview.GetVIReference(self._vi_path_motor_step_counter_get)
            self.motor_stop_move = self.labview.GetVIReference(self._vi_path_motor_stop_move)
            return 0
        except Exception as exc:
            self.log.error("Error during LabView connection : {}".format(exc))
            return 1

    def on_deactivate(self):
        self.labview.Quit()
        return 0

    def _get_amplitude(self, axis=None):
        if axis is not None:
            self.motor_freq_amp_get.setControlValue("Axis (Default)", axis)
        self.motor_freq_amp_get.Call()
        amplitude = self.motor_freq_amp_get.getControlValue("Amplitude (V)")
        return amplitude

    def _get_frequency(self, axis=None):
        if axis is not None:
            self.motor_freq_amp_get.setControlValue("Axis (Default)", axis)
        self.motor_freq_amp_get.Call()
        frequency = self.motor_freq_amp_get.getControlValue("Frequency (Hz)")
        return frequency

    def _set_amplitude(self, amplitude, axis=None):
        if axis is not None:
            self.motor_freq_amp_get.setControlValue("Axis (Default)", axis)
        self.motor_freq_amp_get.setControlValue("Amplitude (V)", amplitude)
        self.motor_freq_amp_get.Call()
        return 0

    def _set_frequency(self, frequency, axis=None):
        if axis is not None:
            self.motor_freq_amp_get.setControlValue("Axis (Default)", axis)
        self.motor_freq_amp_get.setControlValue("Frequency (Hz)", frequency)
        self.motor_freq_amp_get.Call()
        return 0
