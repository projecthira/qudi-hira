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
from core.configoption import ConfigOption
import win32com.client
import subprocess


def _get_lv_axis(axis):
    if axis == "X" or axis == "x":
        return 1
    elif axis == "Y" or axis == "y":
        return 2
    elif axis == "Z" or axis == "z":
        return 3
    else:
        # All axes are referenced
        return 0


def _get_lv_direction(direction):
    if direction == "x+" or direction == "X+":
        return 0
    elif direction == "x-" or direction == "X-":
        return 1
    elif direction == "y+" or direction == "Y+":
        return 2
    elif direction == "y-" or direction == "Y-":
        return 3
    elif direction == "z+" or direction == "Z+":
        return 4
    elif direction == "z-" or direction == "Z-":
        return 5
    else:
        raise ValueError("Invalid direction {} specified.".format(direction))


class NanonisCoarseMotion(Base):
    """Provides software interface to the Nanonis Coarse Motion via LabView.
    """
    _labview_executable = ConfigOption('labview_executable', missing='error')
    _labview_progint_path = ConfigOption('labview_progint_path', missing='error')
    _vi_casestruct_tcp_alpha = ConfigOption('vi_casestruct_tcp_alpha', default="test\\case_struct_tcp_alpha.vi",
                                            missing='warn')
    _vi_motor_frequency_amplitude_get = ConfigOption('vi_motor_frequency_amplitude_get',
                                                     default="Coarse motion\\Motor Frequency Amplitude Get.vi",
                                                     missing='warn')
    _vi_motor_frequency_amplitude_set = ConfigOption('vi_motor_frequency_amplitude_set',
                                                     default="Coarse motion\\Motor Frequency Amplitude Set.vi",
                                                     missing='warn')
    _vi_motor_start_move = ConfigOption('vi_motor_start_move', default="Coarse motion\\Motor Start Move.vi",
                                        missing='warn')
    _vi_motor_step_counter_get = ConfigOption('vi_motor_step_counter_get',
                                              default="Coarse motion\\Motor Step Counter Get.vi", missing='warn')
    _vi_motor_stop_move = ConfigOption('vi_motor_stop_move', default="Coarse motion\\Motor Stop Move.vi",
                                       missing='warn')
    _sample_group = ConfigOption('sample_group', default=0, missing='warn')
    _tip_group = ConfigOption('tip_group', default=1, missing='warn')

    def on_activate(self):
        """ Initialise and activate the hardware module.

            @return: error code (0:OK, -1:error)
        """
        # Combine paths together (this needs to be done with self., otherwise the ConfigOption does not reveal itself)
        self._vi_path_casestruct_tcp_alpha = os.path.join(self._labview_progint_path, self._vi_casestruct_tcp_alpha)
        self._vi_path_motor_frequency_amplitude_get = os.path.join(self._labview_progint_path,
                                                                   self._vi_motor_frequency_amplitude_get)
        self._vi_path_motor_frequency_amplitude_set = os.path.join(self._labview_progint_path,
                                                                   self._vi_motor_frequency_amplitude_set)
        self._vi_path_motor_start_move = os.path.join(self._labview_progint_path, self._vi_motor_start_move)
        self._vi_path_motor_step_counter_get = os.path.join(self._labview_progint_path, self._vi_motor_step_counter_get)
        self._vi_path_motor_stop_move = os.path.join(self._labview_progint_path, self._vi_motor_stop_move)

        try:
            # Dispatches a signal to open 64-bit LabView
            # dynamic dispatch is required to ensure late-binding of application, otherwise the code will not be
            # able to read all available LabView container functions
            self.labview = win32com.client.dynamic.Dispatch("Labview.Application")
            # Load all the required VIs for piezo coarse motion
            self.labview._FlagAsMethod("GetVIReference")
            self.motor_freq_amp_get = self.labview.GetVIReference(self._vi_path_motor_frequency_amplitude_get)
            self.motor_freq_amp_set = self.labview.GetVIReference(self._vi_path_motor_frequency_amplitude_set)
            self.motor_start_move = self.labview.GetVIReference(self._vi_path_motor_start_move)
            self.motor_step_counter_get = self.labview.GetVIReference(self._vi_path_motor_step_counter_get)
            self.motor_stop_move = self.labview.GetVIReference(self._vi_path_motor_stop_move)
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

    def open_front_panels(self):
        """ Open all LabView front panels used.

        @return: 0
        """
        try:
            self.motor_freq_amp_set.OpenFrontPanel()
        except TypeError:
            pass
        try:
            self.motor_start_move.OpenFrontPanel()
        except TypeError:
            pass
        try:
            self.motor_step_counter_get.OpenFrontPanel()
        except TypeError:
            pass
        try:
            self.motor_stop_move.OpenFrontPanel()
        except TypeError:
            pass
        try:
            self.openappref.OpenFrontPanel()
        except TypeError:
            pass
        return 0

    def get_amplitude(self, axis=None):
        """ Get driving amplitude of piezo motion from LabView.

        :param axis: string either "x", "y" or "z". If None then the Axis (Default) is called.
        :return: float of piezo driving amplitude
        """
        lv_axis = _get_lv_axis(axis)
        self.motor_freq_amp_get.setControlValue("Axis (Default)", lv_axis)
        try:
            self.motor_freq_amp_get.Run()
        except TypeError:
            pass
        amplitude = self.motor_freq_amp_get.getControlValue("Amplitude (V)")
        return amplitude

    def get_frequency(self, axis=None):
        """ Get driving frequency of piezo motion from LabView.

        :param axis: string either "x", "y" or "z". If None then the Axis (Default) is called.
        :return: float of piezo driving frequency
        """
        lv_axis = _get_lv_axis(axis)
        self.motor_freq_amp_get.setControlValue("Axis (Default)", lv_axis)
        try:
            self.motor_freq_amp_get.Run()
        except TypeError:
            pass
        frequency = self.motor_freq_amp_get.getControlValue("Frequency (Hz)")
        return frequency

    def set_amplitude_and_frequency(self, amplitude, frequency, axis=None):
        """Set driving amplitude and frequency of piezo motion from LabView.
        These are done together to as the LabView interface has no memory.

        :param frequency: float Piezo driving frequency in Hertz (Hz)
        :param amplitude: float Piezo driving amplitude in Volts (V)
        :param axis: string either "x", "y" or "z". If None then the Axis (All) is called
        :return: 0 if successful
        """
        lv_axis = _get_lv_axis(axis)
        self.motor_freq_amp_set.setControlValue("Axis (All)", lv_axis)
        self.motor_freq_amp_set.setControlValue("Amplitude (V) (NaN=no change)", str(amplitude))
        self.motor_freq_amp_set.setControlValue("Frequency (Hz) (NaN=no change)", str(frequency))

        try:
            self.motor_freq_amp_set.Run()
        except TypeError:
            pass
        return 0

    def move_rel(self, group, direction, steps):
        """Move piezos a specific number of steps in a given direction.

        :param group: Piezo group as assigned in Nanonis
        :param direction: Direction of movement "X+", "X-" etc.
        :param steps: Number of steps to take in that direction
        :return: 0 if successful
        """
        if group == "tip" or group == self._tip_group:
            self.motor_start_move.setControlValue("Group", self._tip_group)
        elif group == "sample" or group == self._sample_group:
            self.motor_start_move.setControlValue("Group", self._sample_group)
        else:
            self.log.warn("Group parameter {} is not 'tip' or 'sample'.".format(group))
            self.motor_start_move.setControlValue("Group", group)

        lv_direction = _get_lv_direction(direction)
        self.motor_start_move.setControlValue("Direction", lv_direction)
        self.motor_start_move.setControlValue("Number of steps", steps)
        try:
            self.motor_start_move.Run()
        except TypeError:
            pass
        return 0

    def get_step_counters(self):
        """Get current step count.

        :return: dict of {x, y, z} step counts
        """
        x_steps = self.motor_step_counter_get.getControlValue("Step Counter X")
        y_steps = self.motor_step_counter_get.getControlValue("Step Counter Y")
        z_steps = self.motor_step_counter_get.getControlValue("Step Counter Z")
        return {"x_steps": x_steps, "y_steps": y_steps, "z_steps": z_steps}

    def reset_step_counters(self):
        """Reset all step counters, if not already reset.

        :return: 0 if successful
        """
        if not self.motor_step_counter_get.getControlValue("Reset X (F)"):
            self.motor_step_counter_get.setControlValue("Reset X (F)", True)
        if not self.motor_step_counter_get.getControlValue("Reset Y (F)"):
            self.motor_step_counter_get.setControlValue("Reset Y (F)", True)
        if not self.motor_step_counter_get.getControlValue("Reset Z (F)"):
            self.motor_step_counter_get.setControlValue("Reset Z (F)", True)
        try:
            self.motor_step_counter_get.Run()
        except TypeError:
            pass

        self.motor_step_counter_get.setControlValue("Reset Z (F)", False)
        self.motor_step_counter_get.setControlValue("Reset Z (F)", False)
        self.motor_step_counter_get.setControlValue("Reset Z (F)", False)
        return 0

    def stop(self):
        """Stop all motion of piezos.

        :return: 0 if successful
        """
        try:
            self.motor_stop_move.Run()
        except TypeError:
            pass
        return 0
