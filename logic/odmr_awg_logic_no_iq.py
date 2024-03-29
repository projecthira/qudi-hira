# -*- coding: utf-8 -*-

"""
ODMR logic for pulsed measurements without an IQ mixer.

This file contains the Qudi Logic module base class.

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

Copyright (c) Dinesh Pinto. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import time
from collections import OrderedDict
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from qtpy import QtCore

from core.module import Connector
from core.statusvariable import StatusVar
from core.util.mutex import Mutex
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge
from logic.generic_logic import GenericLogic


class AwgODMRLogicNoIQ(GenericLogic):
    """This is the Logic class for ODMR."""
    _modclass = 'odmrlogic'
    _modtype = 'logic'

    # declare connectors
    odmrcounter = Connector(interface='ODMRCounterInterface')
    fitlogic = Connector(interface='FitLogic')
    microwave1 = Connector(interface='MicrowaveInterface')
    pulsegenerator = Connector(interface='PulserInterface')
    savelogic = Connector(interface='SaveLogic')
    taskrunner = Connector(interface='TaskRunner')
    laserlogic = Connector(interface='LaserLogic')

    # config option
    mw_scanmode = MicrowaveMode.SWEEP

    clock_frequency = StatusVar('clock_frequency', 200)
    cw_mw_frequency = StatusVar('cw_mw_frequency', 2870e6)
    cw_mw_power = StatusVar('cw_mw_power', -20)
    sweep_mw_power = StatusVar('sweep_mw_power', -20)
    mw_start = StatusVar('mw_start', 2800e6)
    mw_stop = StatusVar('mw_stop', 2950e6)
    mw_step = StatusVar('mw_step', 2e6)
    run_time = StatusVar('run_time', 60)

    pi_pulse_length = StatusVar('pi_pulse_length', 100e-9)
    delay_length = StatusVar('delay_length', 1e-6)
    laser_readout_length = StatusVar('laser_length', 350e-9)
    single_sweep_time = StatusVar('single_sweep_time', 1)
    freq_rep = StatusVar('freq_repetition', 100)

    number_of_lines = StatusVar('number_of_lines', 50)
    fc = StatusVar('fits', None)
    lines_to_average = StatusVar('lines_to_average', 0)
    _oversampling = StatusVar('oversampling', default=10)
    _lock_in_active = StatusVar('lock_in_active', default=False)

    freq_list = []

    # Set up all the constants of the system, these are chosen after optimizing for
    # performance and accuracy
    # Sample set to default - 1.25 GSa/sec
    sample_rate = 1.25e9
    # Synchronize analog and digital channels
    digital_sync_length = 9e-9
    # Null pulse to settle instruments
    null_pulse_length = 30e-9
    # MW trigger length, detected at POS edge
    mw_trig_length = 30e-9
    # Max samples supported by AWG
    max_samples = 130e6

    # Internal signals
    sigNextLine = QtCore.Signal()

    # Update signals, e.g. for GUI module
    sigParameterUpdated = QtCore.Signal(dict)
    sigOutputStateUpdated = QtCore.Signal(str, bool)
    sigOdmrPlotsUpdated = QtCore.Signal(np.ndarray, np.ndarray, np.ndarray)
    sigOdmrFitUpdated = QtCore.Signal(np.ndarray, np.ndarray, dict, str)
    sigOdmrElapsedTimeUpdated = QtCore.Signal(float, int)

    def __init__(self, config, **kwargs):
        super().__init__(config=config, **kwargs)
        self.threadlock = Mutex()

    def on_activate(self):
        """
        Initialisation performed during activation of the module.
        """
        # Get connectors
        self._mw_device = self.microwave1()
        self._awg_device = self.pulsegenerator()
        self._fit_logic = self.fitlogic()
        self._odmr_counter = self.odmrcounter()
        self._save_logic = self.savelogic()
        self._taskrunner = self.taskrunner()
        self._laser_logic = self.laserlogic()

        # self._awg_device.reset()

        # Get hardware constraints
        mw_limits = self.get_hw_constraints()

        # Set/recall microwave source parameters
        self.cw_mw_frequency = mw_limits.frequency_in_range(self.cw_mw_frequency)
        self.cw_mw_power = mw_limits.power_in_range(self.cw_mw_power)
        self.sweep_mw_power = mw_limits.power_in_range(self.sweep_mw_power)

        self.mw_start = mw_limits.frequency_in_range(self.mw_start)
        self.mw_stop = mw_limits.frequency_in_range(self.mw_stop)
        self.mw_step = mw_limits.list_step_in_range(self.mw_step)

        self.total_pulse_length = 0

        # Set the trigger polarity (RISING/FALLING) of the mw-source input trigger
        self.mw_trigger_pol = TriggerEdge.RISING
        self.set_trigger(self.mw_trigger_pol)

        # Elapsed measurement time and number of sweeps
        self.elapsed_time = 0.0
        self.elapsed_sweeps = 0

        # Set flags
        # for stopping a measurement
        self._stopRequested = False
        # for clearing the ODMR data during a measurement
        self._clearOdmrData = False

        # Initalize the ODMR data arrays (mean signal and sweep matrix)
        self._initialize_odmr_plots()
        # Raw data array
        self.odmr_raw_data = np.zeros(
            [self.number_of_lines,
             len(self._odmr_counter.get_odmr_channels()),
             self.odmr_plot_x.size]
        )

        # Switch off microwave and set CW frequency and power
        self.cw_mode_off()
        self._awg_device.pulser_off()
        self.mw_off()

        # Connect signals
        self.sigNextLine.connect(self._scan_odmr_line, QtCore.Qt.QueuedConnection)
        return

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        # Stop measurement if it is still running
        if self.module_state() == 'locked':
            self.stop_odmr_scan()
        timeout = 30.0
        start_time = time.time()
        while self.module_state() == 'locked':
            time.sleep(0.5)
            timeout -= (time.time() - start_time)
            if timeout <= 0.0:
                self.log.error('Failed to properly deactivate odmr logic. Odmr scan is still '
                               'running but can not be stopped after 30 sec.')
                break
        # Switch off microwave source for sure (also if CW mode is active or module is still locked)
        self.log.info('Deactivated ODMRAWGLogic')
        self._mw_device.off()
        # Disconnect signals
        self.sigNextLine.disconnect()

    @staticmethod
    def dbm_to_vpeak_converter(power_dbm):
        power_mw = 1e-3 * 10 ** (power_dbm / 10)
        v_eff = np.sqrt(power_mw * 50)
        v_peak = np.sqrt(2) * v_eff
        return v_peak

    @staticmethod
    def vpeak_to_dbm_converter(v_peak):
        return 10 * np.log10(v_peak ** 2 * 10)

    @fc.constructor
    def sv_set_fits(self, val):
        fc = self.fitlogic().make_fit_container('ODMR sum', '1d')
        fc.set_units(['Hz', 'c/s'])
        if isinstance(val, dict) and len(val) > 0:
            fc.load_from_dict(val)
        else:
            d1 = OrderedDict()
            d1['Lorentzian dip'] = {
                'fit_function': 'lorentzian',
                'estimator': 'dip'
            }
            d1['Two Lorentzian dips'] = {
                'fit_function': 'lorentziandouble',
                'estimator': 'dip'
            }
            d1['N14'] = {
                'fit_function': 'lorentziantriple',
                'estimator': 'N14'
            }
            d1['N15'] = {
                'fit_function': 'lorentziandouble',
                'estimator': 'N15'
            }
            d1['Two Gaussian dips'] = {
                'fit_function': 'gaussiandouble',
                'estimator': 'dip'
            }
            default_fits = OrderedDict()
            default_fits['1d'] = d1
            fc.load_from_dict(default_fits)
        return fc

    @fc.representer
    def sv_get_fits(self, val):
        """ save configured fits """
        if len(val.fit_list) > 0:
            return val.save_to_dict()
        else:
            return None

    def change_sample_rate(self, resolution: str) -> float:
        if resolution == "low":
            self.sample_rate = 0.3125e9
        elif resolution == "med":
            self.sample_rate = 0.625e9
        elif resolution == "high":
            self.sample_rate = 1.25e9
        else:
            self.log.error("Incorrect resolution: use 'low', 'med' or 'high'")

        self.log.info(f"Sample rate set to {self.sample_rate / 1e9} GSa/s")
        return self.sample_rate

    def _initialize_odmr_plots(self):
        """ Initializing the ODMR plots (line and matrix). """
        self.odmr_plot_x = np.arange(self.mw_start, self.mw_stop + self.mw_step, self.mw_step)
        self.odmr_plot_y = np.zeros([len(self.get_odmr_channels()), self.odmr_plot_x.size])
        self.odmr_fit_x = np.arange(self.mw_start, self.mw_stop + self.mw_step, self.mw_step)
        self.odmr_fit_y = np.zeros(self.odmr_fit_x.size)
        self.odmr_plot_xy = np.zeros(
            [self.number_of_lines, len(self.get_odmr_channels()), self.odmr_plot_x.size])
        self.sigOdmrPlotsUpdated.emit(self.odmr_plot_x, self.odmr_plot_y, self.odmr_plot_xy)
        current_fit = self.fc.current_fit
        self.sigOdmrFitUpdated.emit(self.odmr_fit_x, self.odmr_fit_y, {}, current_fit)
        return

    def set_average_length(self, lines_to_average):
        """
        Sets the number of lines to average for the sum of the data

        @param int lines_to_average: desired number of lines to average (0 means all)

        @return int: actually set lines to average
        """
        self.lines_to_average = int(lines_to_average)

        if self.lines_to_average <= 0:
            self.odmr_plot_y = np.mean(
                self.odmr_raw_data[:max(1, self.elapsed_sweeps), :, :],
                axis=0,
                dtype=np.float64
            )
        else:
            self.odmr_plot_y = np.mean(
                self.odmr_raw_data[:max(1, min(self.lines_to_average, self.elapsed_sweeps)), :, :],
                axis=0,
                dtype=np.float64
            )

        self.sigOdmrPlotsUpdated.emit(self.odmr_plot_x, self.odmr_plot_y, self.odmr_plot_xy)
        self.sigParameterUpdated.emit({'average_length': self.lines_to_average})
        return self.lines_to_average

    def set_clock_frequency(self, clock_frequency):
        """
        Sets the frequency of the counter clock

        @param int clock_frequency: desired frequency of the clock

        @return int: actually set clock frequency
        """
        # checks if scanner is still running
        if self.module_state() != 'locked' and isinstance(clock_frequency, (int, float)):
            self.clock_frequency = int(clock_frequency)
        else:
            self.log.warning('set_clock_frequency failed. Logic is either locked or input value is '
                             'no integer or float.')

        update_dict = {'clock_frequency': self.clock_frequency}
        self.sigParameterUpdated.emit(update_dict)
        return self.clock_frequency

    @property
    def oversampling(self):
        return self._oversampling

    @oversampling.setter
    def oversampling(self, oversampling):
        """
        Sets the frequency of the counter clock

        @param int oversampling: desired oversampling per frequency step
        """
        # checks if scanner is still running
        if self.module_state() != 'locked' and isinstance(oversampling, (int, float)):
            self._oversampling = int(oversampling)
            self._odmr_counter.oversampling = self._oversampling
        else:
            self.log.warning('setter of oversampling failed. Logic is either locked or input value is '
                             'no integer or float.')

        update_dict = {'oversampling': self._oversampling}
        self.sigParameterUpdated.emit(update_dict)

    def set_oversampling(self, oversampling):
        self.oversampling = oversampling
        return self.oversampling

    @property
    def lock_in(self):
        return self._lock_in_active

    @lock_in.setter
    def lock_in(self, active):
        """
        Sets the frequency of the counter clock

        @param bool active: specify if signal should be detected with lock in
        """
        # checks if scanner is still running
        if self.module_state() != 'locked' and isinstance(active, bool):
            self._lock_in_active = active
            self._odmr_counter.lock_in_active = self._lock_in_active
        else:
            self.log.warning('setter of lock in failed. Logic is either locked or input value is no boolean.')

        update_dict = {'lock_in': self._lock_in_active}
        self.sigParameterUpdated.emit(update_dict)

    def set_lock_in(self, active):
        self.lock_in = active
        return self.lock_in

    def set_matrix_line_number(self, number_of_lines):
        """
        Sets the number of lines in the ODMR matrix

        @param int number_of_lines: desired number of matrix lines

        @return int: actually set number of matrix lines
        """
        if isinstance(number_of_lines, int):
            self.number_of_lines = number_of_lines
        else:
            self.log.warning('set_matrix_line_number failed. '
                             'Input parameter number_of_lines is no integer.')

        update_dict = {'number_of_lines': self.number_of_lines}
        self.sigParameterUpdated.emit(update_dict)
        return self.number_of_lines

    def set_runtime(self, runtime):
        """
        Sets the runtime for ODMR measurement

        @param float runtime: desired runtime in seconds

        @return float: actually set runtime in seconds
        """
        if isinstance(runtime, (int, float)):
            self.run_time = runtime
        else:
            self.log.warning('set_runtime failed. Input parameter runtime is no integer or float.')

        update_dict = {'run_time': self.run_time}
        self.sigParameterUpdated.emit(update_dict)
        return self.run_time

    def set_pulse_parameters(self, laser_readout_length, delay_length, pi_pulse_length, freq_repetition):
        if self.module_state() != 'locked':
            self.laser_readout_length = laser_readout_length
            self.delay_length = delay_length
            self.pi_pulse_length = pi_pulse_length
            self.freq_rep = freq_repetition
        else:
            self.log.warning('set_pulse_parameters failed. Logic is locked.')

        param_dict = {'laser_readout_length': self.laser_readout_length, 'delay_length': self.delay_length,
                      'pi_pulse_length': self.pi_pulse_length, 'freq_repetition': self.freq_rep}
        self.sigParameterUpdated.emit(param_dict)

        return self.laser_readout_length, self.delay_length, self.pi_pulse_length

    def set_sweep_parameters(self, start, stop, step, power, single_sweep_time):
        """ Set the desired frequency parameters for list and sweep mode

        @param float start: start frequency to set in Hz
        @param float stop: stop frequency to set in Hz
        @param float step: step frequency to set in Hz
        @param float power: mw power to set in dBm

        @return float, float, float, float: current start_freq, current stop_freq,
                                            current freq_step, current power
        """
        limits = self.get_hw_constraints()

        # How long will a sweep be
        self.single_sweep_time = single_sweep_time

        if self.module_state() != 'locked':
            if isinstance(start, (int, float)) and isinstance(stop, (int, float)) and isinstance(step, (int, float)):
                self.mw_start = limits.frequency_in_range(start)
                self.mw_stop = limits.frequency_in_range(stop)
                self.mw_step = limits.list_step_in_range(step)
                if self.mw_stop <= self.mw_start:
                    self.mw_stop = self.mw_start + self.mw_step
                if self.mw_stop - self.mw_start > 8e8:
                    self.mw_stop = self.mw_start + np.floor(8e8 / self.mw_step) * self.mw_step
                self.cw_mw_frequency = (self.mw_stop + self.mw_start) / 2
            if isinstance(power, (int, float)):
                self.sweep_mw_power = limits.power_in_range(power)
        else:
            self.log.warning('set_sweep_parameters failed. Logic is locked.')

        param_dict = {'cw_mw_frequency': self.cw_mw_frequency, 'mw_start': self.mw_start,
                      'mw_stop': self.mw_stop, 'mw_step': self.mw_step, 'sweep_mw_power': self.sweep_mw_power,
                      'single_sweep_time': self.single_sweep_time}
        self.sigParameterUpdated.emit(param_dict)
        return self.mw_start, self.mw_stop, self.mw_step, self.sweep_mw_power, self.cw_mw_frequency

    def list_to_waveform_cw(self):
        analog_samples = {'a_ch0': []}
        digital_samples = {'d_ch0': [], 'd_ch1': [], 'd_ch2': [], 'd_ch5': []}

        # Length of a single frequency (single pulse * frequency repetition rate)
        single_freq_pulse_length = (self.laser_readout_length + self.null_pulse_length) * self.freq_rep

        total_pulse_length = self.mw_trig_length + 2 * self.null_pulse_length + single_freq_pulse_length
        total_pulse_samples = int(np.floor(total_pulse_length * self.sample_rate))
        self.total_pulse_length = total_pulse_length

        if total_pulse_length < 2.0e-3:
            self.log.error(f"Repetition too low, pulses may not work correctly")
            return False, False

        if total_pulse_samples > self.max_samples:
            self.log.error(f"Too many samples {total_pulse_samples} > {self.max_samples}")
            return False, False

        # Set up all the pulse lengths
        mw_trig_pulse_sample = int(np.floor(self.mw_trig_length * self.sample_rate))
        laser_readout_pulse_sample = int(np.floor(self.laser_readout_length * self.sample_rate))
        null_pulse_sample = int(np.floor(self.null_pulse_length * self.sample_rate))

        # Set up empty sequences for channels (switch uses np.ones as channel HIGH is off and LOW is on)
        mw_trig_samples = np.zeros(total_pulse_samples)
        laser_samples = np.zeros(total_pulse_samples)
        readout_samples = np.zeros(total_pulse_samples)
        switch_samples = np.zeros(total_pulse_samples)

        mw_trig_samples[0:mw_trig_pulse_sample] = 1
        # Null pulses are added to take into account the settling time of the instruments
        current_freq_idx = mw_trig_pulse_sample + 2 * null_pulse_sample

        for _ in range(self.freq_rep):
            laser_start = current_freq_idx
            laser_stop = laser_start + laser_readout_pulse_sample

            laser_samples[laser_start:laser_stop] = np.ones(laser_stop - laser_start)
            readout_samples[laser_start:laser_stop] = np.ones(laser_stop - laser_start)

            current_freq_idx += laser_readout_pulse_sample + null_pulse_sample

        # Digital and analog channels are mapped to the sequences
        digital_samples['d_ch0'] = laser_samples
        digital_samples['d_ch1'] = readout_samples
        digital_samples['d_ch2'] = switch_samples
        digital_samples['d_ch5'] = mw_trig_samples
        analog_samples['a_ch0'] = np.zeros(total_pulse_samples)

        self.log.info(f"Finished generating cwODMR analog and digital arrays")
        return analog_samples, digital_samples

    def list_to_waveform_pulsed(self):
        # Laser, Readout, Switch and MW trigger channels
        analog_samples = {'a_ch0': []}
        digital_samples = {'d_ch0': [], 'd_ch1': [], 'd_ch2': [], 'd_ch5': []}

        if self.pi_pulse_length < 50.0e-9:
            self.log.error(f"Pi pulse too short: {self.pi_pulse_length * 1e9} ns < 50.0 ns")
            return False, False

        # Change pi pulse length according to hardware spec
        if 50.0e-9 < self.pi_pulse_length < 60.0e-9:
            pi_pulse_length = self.pi_pulse_length - 40.0e-9
        else:
            pi_pulse_length = self.pi_pulse_length - 50.0e-9

        self.log.warning(f"pi_pulse_length changed from {self.pi_pulse_length * 1e9} ns to "
                         f"{pi_pulse_length * 1e9} ns to match hardware.")

        # Length of a single frequency (single pulse * frequency repetition rate)
        single_freq_pulse_length = (self.laser_readout_length + self.delay_length + pi_pulse_length +
                                    self.null_pulse_length) * self.freq_rep

        total_pulse_length = self.mw_trig_length + 2 * self.null_pulse_length + single_freq_pulse_length
        total_pulse_samples = int(np.floor(total_pulse_length * self.sample_rate))
        self.total_pulse_length = total_pulse_length

        if total_pulse_length < 2.0e-3:
            self.log.error(f"Repetition too low, pulses may not work correctly")
            return False, False

        if total_pulse_samples > self.max_samples:
            self.log.error(f"Too many samples {total_pulse_samples} > {self.max_samples}")
            return False, False

        # Set up all the pulse lengths
        mw_trig_pulse_sample = int(np.floor(self.mw_trig_length * self.sample_rate))
        delay_pulse_sample = int(np.floor(self.delay_length * self.sample_rate))
        switch_pulse_sample = int(np.floor(pi_pulse_length * self.sample_rate))
        null_pulse_sample = int(np.floor(self.null_pulse_length * self.sample_rate))
        laser_readout_pulse_sample = int(np.floor(self.laser_readout_length * self.sample_rate))

        # Set up empty sequences for channels (switch uses np.ones as channel HIGH is off and LOW is on)
        mw_trig_samples = np.zeros(total_pulse_samples, dtype=bool)
        laser_samples = np.zeros(total_pulse_samples, dtype=bool)
        readout_samples = np.zeros(total_pulse_samples, dtype=bool)
        switch_samples = np.zeros(total_pulse_samples, dtype=bool)

        mw_trig_samples[0:mw_trig_pulse_sample] = np.ones(mw_trig_pulse_sample, dtype=bool)

        current_freq_idx = mw_trig_pulse_sample + 2 * null_pulse_sample

        for _ in range(self.freq_rep):
            # Null pulses are added to take into account the settling time of the instruments
            single_freq_start = current_freq_idx

            laser_start = single_freq_start
            laser_stop = laser_start + laser_readout_pulse_sample

            switch_start = single_freq_start + delay_pulse_sample
            switch_stop = switch_start + switch_pulse_sample

            laser_samples[laser_start:laser_stop] = np.ones(laser_stop - laser_start, dtype=bool)
            readout_samples[laser_start:laser_stop] = np.ones(laser_stop - laser_start, dtype=bool)
            switch_samples[switch_start:switch_stop] = np.ones(switch_stop - switch_start, dtype=bool)

            current_freq_idx += laser_readout_pulse_sample + delay_pulse_sample + switch_pulse_sample + \
                                null_pulse_sample

        # Digital and analog channels are mapped to the sequences
        digital_samples['d_ch0'] = laser_samples
        digital_samples['d_ch1'] = readout_samples
        digital_samples['d_ch2'] = switch_samples
        digital_samples['d_ch5'] = mw_trig_samples
        analog_samples['a_ch0'] = np.zeros(total_pulse_samples)

        self.log.info(f"Finished generating pulsedODMR analog and digital arrays")
        return analog_samples, digital_samples

    def sweep_list(self):
        freq_range_size = np.abs(self.mw_stop - self.mw_start)

        # adjust the end frequency in order to have an integer multiple of step size
        # The master module (i.e. GUI) will be notified about the changed end frequency
        num_steps = int(freq_range_size / self.mw_step)
        end_freq = self.mw_start + num_steps * self.mw_step
        self.freq_list = np.linspace(self.mw_start, end_freq, num_steps + 1)
        return 0

    def write_test_waveform(self):
        self.sweep_list()

        analog_samples, digital_samples = self.list_to_waveform_cw()
        num_of_samples, waveform_names = \
            self._awg_device.write_waveform(
                name='noiqODMR',
                analog_samples=analog_samples,
                digital_samples=digital_samples,
                is_first_chunk=True,
                is_last_chunk=True,
                total_number_of_samples=len(digital_samples['d_ch0'])
            )
        self._awg_device.load_waveform(load_dict=waveform_names)
        self._awg_device.set_reps(100)
        return num_of_samples, waveform_names

    def cw_mode_on(self):
        self._cw_mode_on = True
        self.log.info("CW mode switched on")

    def cw_mode_off(self):
        self._cw_mode_on = False
        self.log.info("CW mode switched off")

    def set_cw_parameters(self, freq, power):
        pass

    def _awg_on(self):
        self.sweep_list()

        # Load Trigger pulses onto AWG
        if self._cw_mode_on:
            analog_samples, digital_samples = self.list_to_waveform_cw()
        else:
            analog_samples, digital_samples = self.list_to_waveform_pulsed()

        if not analog_samples and not digital_samples:
            mode = "sweep"
            is_running = False
            self.sigOutputStateUpdated.emit(mode, is_running)
            return mode, is_running

        num_of_samples, waveform_names = self._awg_device.write_waveform(
            name='noiqODMR',
            analog_samples=analog_samples,
            digital_samples=digital_samples,
            is_first_chunk=True,
            is_last_chunk=True,
            total_number_of_samples=len(analog_samples['a_ch0'])
        )
        self._awg_device.load_waveform(load_dict=waveform_names)

        # Following lines update the corrected parameters to the GUI
        param_dict = {'mw_start': self.mw_start, 'mw_stop': self.mw_stop,
                      'mw_step': self.mw_step, 'sweep_mw_power': self.sweep_mw_power}
        self.sigParameterUpdated.emit(param_dict)

    def _mw_on(self):
        # LOAD MW PARAMETERS
        limits = self.get_hw_constraints()
        param_dict = {}

        if self.mw_scanmode == MicrowaveMode.LIST:
            if np.abs(self.mw_stop - self.mw_start) / self.mw_step >= limits.list_maxentries:
                self.log.warning('Number of frequency steps too large for microwave device. '
                                 'Lowering resolution to fit the maximum length.')
                self.mw_step = np.abs(self.mw_stop - self.mw_start) / (limits.list_maxentries - 1)
                self.sigParameterUpdated.emit({'mw_step': self.mw_step})

            # adjust the end frequency in order to have an integer multiple of step size
            # The master module (i.e. GUI) will be notified about the changed end frequency
            num_steps = int(np.rint((self.mw_stop - self.mw_start) / self.mw_step))
            end_freq = self.mw_start + num_steps * self.mw_step
            freq_list = np.linspace(self.mw_start, end_freq, num_steps + 1)
            freq_list, self.sweep_mw_power, mode = self._mw_device.set_list(freq_list,
                                                                            self.sweep_mw_power)
            self.mw_start = freq_list[0]
            self.mw_stop = freq_list[-1]
            self.mw_step = (self.mw_stop - self.mw_start) / (len(freq_list) - 1)

            param_dict = {'mw_start': self.mw_start, 'mw_stop': self.mw_stop,
                          'mw_step': self.mw_step, 'sweep_mw_power': self.sweep_mw_power}

        elif self.mw_scanmode == MicrowaveMode.SWEEP:
            if np.abs(self.mw_stop - self.mw_start) / self.mw_step >= limits.sweep_maxentries:
                self.log.warning('Number of frequency steps too large for microwave device. '
                                 'Lowering resolution to fit the maximum length.')
                self.mw_step = np.abs(self.mw_stop - self.mw_start) / (limits.list_maxentries - 1)
                self.sigParameterUpdated.emit({'mw_step': self.mw_step})

            sweep_return = self._mw_device.set_sweep(
                self.mw_start, self.mw_stop, self.mw_step, self.sweep_mw_power)
            self.mw_start, self.mw_stop, self.mw_step, self.sweep_mw_power, mode = sweep_return

            param_dict = {'mw_start': self.mw_start, 'mw_stop': self.mw_stop,
                          'mw_step': self.mw_step, 'sweep_mw_power': self.sweep_mw_power}

        else:
            self.log.error('Scanmode not supported. Please select SWEEP or LIST.')

        self.set_trigger(self.mw_trigger_pol)
        self.sigParameterUpdated.emit(param_dict)
        return mode

    def mw_sweep_on(self, continue_scan=False):
        """
        Switching on the mw source in list/sweep mode.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running

        When using the AWG the sweep mode is redundant, so we leave only the list options.
        """
        # LOAD AWG PARAMETERS
        if not continue_scan:
            self._awg_on()

        num, status = self._awg_device.get_status()
        if num == 0:
            is_running = 1
        else:
            self.log.error("AWG is not ready")

        mode = self._mw_on()
        if mode != 'list' and mode != 'sweep':
            self.log.error('Switching to list/sweep microwave output mode failed.')
        elif self.mw_scanmode == MicrowaveMode.SWEEP:
            err_code = self._mw_device.sweep_on()
            if err_code < 0:
                self.log.error('Activation of microwave output failed.')
        else:
            err_code = self._mw_device.list_on()
            if err_code < 0:
                self.log.error('Activation of microwave output failed.')

        self.sigOutputStateUpdated.emit(mode, is_running)

        return mode, is_running

    def set_trigger(self, trigger_pol):
        """
        Set trigger polarity of external microwave trigger (for list and sweep mode).

        @param object trigger_pol: one of [TriggerEdge.RISING, TriggerEdge.FALLING]
        @param float frequency: trigger frequency during ODMR scan

        @return object: actually set trigger polarity returned from hardware
        """
        self.mw_trigger_pol, triggertime = self._mw_device.set_ext_trigger(trigger_pol, 0)
        self.log.info("MW polarity set to {}".format(self.mw_trigger_pol))

        update_dict = {'trigger_pol': self.mw_trigger_pol}
        self.sigParameterUpdated.emit(update_dict)
        return self.mw_trigger_pol

    def reset_sweep(self):
        """
        Resets the AWG, starting the sweep from the beginning.
        """
        self._awg_device.pulser_off()
        time.sleep(0.1)
        self._awg_device.pulser_on()
        return

    def mw_off(self):
        """ Switching off the MW source.

        @return str, bool: active mode ['cw', 'list', 'sweep'], is_running
        """
        error_code_pulsar = self._awg_device.pulser_off()
        if error_code_pulsar < 0:
            self.log.error('Switching off pulsar source failed.')

        error_code_mw = self._mw_device.off()
        if error_code_mw < 0:
            self.log.error('Switching off microwave source failed.')

        mode, is_running = self._mw_device.get_status()
        self.sigOutputStateUpdated.emit(mode, is_running)
        return mode, is_running

    def _start_odmr_counter(self):
        """
        Starting the ODMR counter and set up the clock for it.

        @return int: error code (0:OK, -1:error)
        """
        self._odmr_counter.set_up_odmr()
        return 0

    def _stop_odmr_counter(self):
        """
        Stopping the ODMR counter.

        @return int: error code (0:OK, -1:error)
        """
        ret_val1 = self._odmr_counter.close_odmr()
        if ret_val1 != 0:
            self.log.error('ODMR counter could not be stopped!')
        ret_val2 = self._odmr_counter.close_odmr_clock()
        if ret_val2 != 0:
            self.log.error('ODMR clock could not be stopped!')

        # Check with a bitwise or:
        return ret_val1 | ret_val2

    def start_odmr_scan(self):
        """ Starting an ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self.log.error('Can not start ODMR scan. Logic is already locked.')
                return -1

            self._laser_logic.set_external_state(True)

            self.module_state.lock()
            self._clearOdmrData = False
            self.stopRequested = False
            self.fc.clear_result()

            self.elapsed_sweeps = 0
            self.elapsed_time = 0.0
            self._startTime = time.time()
            self.sigOdmrElapsedTimeUpdated.emit(self.elapsed_time, self.elapsed_sweeps)

            mode, is_running = self.mw_sweep_on()

            if not is_running:
                self._stop_odmr_counter()
                self.module_state.unlock()
                return -1

            # Defining the frequency list, making sure the end frequency is a multiple of freq step
            # Calculate the average factor - number of sweeps in a single acquisition based on a single sweep time
            self.average_factor = int(self.single_sweep_time / (self.total_pulse_length * len(self.freq_list)))
            # Just to make sure we're not averaging on a very low number (or zero...)
            if self.average_factor < 1:
                self.average_factor = 1
            self._awg_device.set_reps(self.average_factor * len(self.freq_list))

            sweep_bin_num = self.average_factor * len(self.freq_list) * self.freq_rep
            self._odmr_counter.set_odmr_length(length=sweep_bin_num)

            odmr_status = self._start_odmr_counter()

            if odmr_status < 0:
                mode, is_running = self._mw_device.get_status()
                self.sigOutputStateUpdated.emit(mode, is_running)
                self.module_state.unlock()
                return -1

            self._initialize_odmr_plots()
            # initialize raw_data array
            estimated_number_of_lines = self.run_time / (
                    sweep_bin_num * self.total_pulse_length * self.odmr_plot_x.size)
            estimated_number_of_lines = int(1.5 * estimated_number_of_lines)  # Safety
            if estimated_number_of_lines < self.number_of_lines:
                estimated_number_of_lines = self.number_of_lines
            self.log.debug('Estimated number of raw data lines: {0:d}'
                           ''.format(estimated_number_of_lines))
            self.odmr_raw_data = np.zeros(
                [estimated_number_of_lines,
                 len(self._odmr_counter.get_odmr_channels()),
                 self.odmr_plot_x.size]
            )
            self.sigNextLine.emit()
            return 0

    def continue_odmr_scan(self):
        """ Continue ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self.log.error('Can not start ODMR scan. Logic is already locked.')
                return -1

            self.module_state.lock()
            self.stopRequested = False
            self.fc.clear_result()

            self._startTime = time.time() - self.elapsed_time
            self.sigOdmrElapsedTimeUpdated.emit(self.elapsed_time, self.elapsed_sweeps)

            self._laser_logic.set_external_state(True)
            odmr_status = self._start_odmr_counter()

            if odmr_status < 0:
                mode, is_running = self._mw_device.get_status()
                self.sigOutputStateUpdated.emit(mode, is_running)
                self.module_state.unlock()
                return -1

            mode, is_running = self.mw_sweep_on(continue_scan=True)
            if not is_running:
                self._stop_odmr_counter()
                self.module_state.unlock()
                return -1

            self.sigNextLine.emit()
            return 0

    def stop_odmr_scan(self):
        """ Stop the ODMR scan.

        @return int: error code (0:OK, -1:error)
        """
        with self.threadlock:
            if self.module_state() == 'locked':
                self.stopRequested = True
        self._laser_logic.set_external_state(False)
        return 0

    def clear_odmr_data(self):
        """¨Set the option to clear the curret ODMR data.

        The clear operation has to be performed within the method
        _scan_odmr_line. This method just sets the flag for that. """
        with self.threadlock:
            if self.module_state() == 'locked':
                self._clearOdmrData = True
        return

    def _scan_odmr_line(self):
        """ Scans one line in ODMR

        (from mw_start to mw_stop in steps of mw_step)
        """
        with self.threadlock:
            # If the odmr measurement is not running do nothing
            if self.module_state() != 'locked':
                return

            # Stop measurement if stop has been requested
            if self.stopRequested:
                self.stopRequested = False
                self.mw_off()
                self._awg_device.pulser_off()
                self._stop_odmr_counter()
                self._laser_logic.set_external_state(False)
                self.module_state.unlock()
                return

            # reset position so every line starts from the same frequency
            self._odmr_counter.clear_odmr()
            self._mw_device.reset_sweeppos()

            self._awg_device.pulser_on()
            # Acquire count data
            time.sleep(self.single_sweep_time + 0.05)

            err, new_counts = self._odmr_counter.count_odmr(pulsed=False)

            if err:
                self.stopRequested = True
                self.sigNextLine.emit()
                return

            # self._awg_device.pulser_off()
            # self._mw_device.simple_off()

            # Reshaping the array into (average_factor, num_of_freq, freq_rep)
            new_counts = np.reshape(new_counts, newshape=(self.average_factor, len(self.freq_list), self.freq_rep))
            # Get the mean across freq_rep
            new_counts = np.mean(new_counts, axis=2)
            # Get the mean across average_factor
            new_counts = np.mean(new_counts, axis=0)

            # Add new count data to raw_data array and append if array is too small
            if self._clearOdmrData:
                self.odmr_raw_data[:, :, :] = 0
                self._clearOdmrData = False
            if self.elapsed_sweeps == (self.odmr_raw_data.shape[0] - 1):
                expanded_array = np.zeros(self.odmr_raw_data.shape)
                self.odmr_raw_data = np.concatenate((self.odmr_raw_data, expanded_array), axis=0)
                self.log.warning('raw data array in ODMRLogic was not big enough for the entire '
                                 'measurement. Array will be expanded.\nOld array shape was '
                                 '({0:d}, {1:d}), new shape is ({2:d}, {3:d}).'
                                 ''.format(self.odmr_raw_data.shape[0] - self.number_of_lines,
                                           self.odmr_raw_data.shape[1],
                                           self.odmr_raw_data.shape[0],
                                           self.odmr_raw_data.shape[1]))

            # shift data in the array "up" and add new data at the "bottom"
            self.odmr_raw_data = np.roll(self.odmr_raw_data, 1, axis=0)

            self.odmr_raw_data[0] = new_counts

            # Add new count data to mean signal
            if self._clearOdmrData:
                self.odmr_plot_y[:, :] = 0

            if self.lines_to_average <= 0:
                self.odmr_plot_y = np.mean(
                    self.odmr_raw_data[:max(1, self.elapsed_sweeps), :, :],
                    axis=0,
                    dtype=np.float64
                )
            else:
                self.odmr_plot_y = np.mean(
                    self.odmr_raw_data[:max(1, min(self.lines_to_average, self.elapsed_sweeps)), :, :],
                    axis=0,
                    dtype=np.float64
                )

            # Set plot slice of matrix
            self.odmr_plot_xy = self.odmr_raw_data[:self.number_of_lines, :, :]

            # Update elapsed time/sweeps
            self.elapsed_sweeps += 1
            self.elapsed_time = time.time() - self._startTime
            if self.elapsed_time >= self.run_time:
                self.stopRequested = True
            # Fire update signals
            self.sigOdmrElapsedTimeUpdated.emit(self.elapsed_time, self.elapsed_sweeps)
            self.sigOdmrPlotsUpdated.emit(self.odmr_plot_x, self.odmr_plot_y, self.odmr_plot_xy)
            self.sigNextLine.emit()
            return

    def get_odmr_channels(self):
        return self._odmr_counter.get_odmr_channels()

    def get_awg_constraints(self):
        return self._awg_device.get_limits()

    def get_awg_power_constraints_in_dbm(self):
        constraints = self.get_awg_constraints()
        constraints.max_power = self.vpeak_to_dbm_converter(constraints.max_power)
        constraints.min_power = self.vpeak_to_dbm_converter(constraints.min_power)
        return constraints

    def get_hw_constraints(self):
        """ Return the names of all ocnfigured fit functions.
        @return object: Hardware constraints object
        """
        constraints = self._mw_device.get_limits()
        return constraints

    def get_fit_functions(self):
        """ Return the hardware constraints/limits
        @return list(str): list of fit function names
        """
        return list(self.fc.fit_list)

    def do_fit(self, fit_function=None, x_data=None, y_data=None, channel_index=0):
        """
        Execute the currently configured fit on the measurement data. Optionally on passed data
        """
        if (x_data is None) or (y_data is None):
            x_data = self.odmr_plot_x
            y_data = self.odmr_plot_y[channel_index]

        if fit_function is not None and isinstance(fit_function, str):
            if fit_function in self.get_fit_functions():
                self.fc.set_current_fit(fit_function)
            else:
                self.fc.set_current_fit('No Fit')
                if fit_function != 'No Fit':
                    self.log.warning('Fit function "{0}" not available in ODMRLogic fit container.'
                                     ''.format(fit_function))

        self.odmr_fit_x, self.odmr_fit_y, result = self.fc.do_fit(x_data, y_data)

        if result is None:
            result_str_dict = {}
        else:
            result_str_dict = result.result_str_dict
        self.sigOdmrFitUpdated.emit(
            self.odmr_fit_x, self.odmr_fit_y, result_str_dict, self.fc.current_fit)
        return

    def save_odmr_data(self, tag=None, colorscale_range=None, percentile_range=None):
        """ Saves the current ODMR data to a file."""
        timestamp = datetime.now()

        if tag is None:
            tag = ''
        for nch, channel in enumerate(self.get_odmr_channels()):
            # two paths to save the raw data and the odmr scan data.
            filepath = self._save_logic.get_path_for_module(module_name='pulsedODMR')
            filepath2 = self._save_logic.get_path_for_module(module_name='pulsedODMR')

            if len(tag) > 0:
                filelabel = '{0}_ODMR_data_ch{1}'.format(tag, nch)
                filelabel2 = '{0}_ODMR_data_ch{1}_raw'.format(tag, nch)
            else:
                filelabel = 'ODMR_data_ch{0}'.format(nch)
                filelabel2 = 'ODMR_data_ch{0}_raw'.format(nch)

            # prepare the data in a dict or in an OrderedDict:
            data = OrderedDict()
            data2 = OrderedDict()
            data['frequency (Hz)'] = self.odmr_plot_x
            data['count data (counts/s)'] = self.odmr_plot_y[nch]
            data2['count data (counts/s)'] = self.odmr_raw_data[:self.elapsed_sweeps, nch, :]

            parameters = OrderedDict()
            parameters['Microwave CW Power (dBm)'] = self.cw_mw_power
            parameters['Microwave Sweep Power (dBm)'] = self.sweep_mw_power
            parameters['Run Time (s)'] = self.run_time
            parameters['Number of frequency sweeps (#)'] = self.elapsed_sweeps
            parameters['Start Frequency (Hz)'] = self.mw_start
            parameters['Stop Frequency (Hz)'] = self.mw_stop
            parameters['Step size (Hz)'] = self.mw_step
            parameters['Clock Frequency (Hz)'] = self.clock_frequency
            parameters['Channel'] = '{0}: {1}'.format(nch, channel)
            parameters['Laser readout length(s)'] = self.laser_readout_length
            parameters['Delay Length (s)'] = self.delay_length
            parameters['Pi pulse length (s)'] = self.pi_pulse_length
            parameters['Frequency repetition'] = self.freq_rep
            parameters['Single sweep time (s)'] = self.single_sweep_time

            if self.fc.current_fit != 'No Fit':
                parameters['Fit function'] = self.fc.current_fit

            # add all fit parameter to the saved data:
            for name, param in self.fc.current_fit_param.items():
                parameters[name] = str(param)

            fig = self.draw_figure(
                nch,
                cbar_range=colorscale_range,
                percentile_range=percentile_range)

            self._save_logic.save_data(data,
                                       filepath=filepath,
                                       parameters=parameters,
                                       filelabel=filelabel,
                                       fmt='%.6e',
                                       delimiter='\t',
                                       timestamp=timestamp,
                                       plotfig=fig)

            self._save_logic.save_data(data2,
                                       filepath=filepath2,
                                       parameters=parameters,
                                       filelabel=filelabel2,
                                       fmt='%.6e',
                                       delimiter='\t',
                                       timestamp=timestamp)

            self.log.info('ODMR data saved to:\n{0}'.format(filepath))
        return

    def draw_figure(self, channel_number, cbar_range=None, percentile_range=None):
        """ Draw the summary figure to save with the data.

        @param: list cbar_range: (optional) [color_scale_min, color_scale_max].
                                 If not supplied then a default of data_min to data_max
                                 will be used.

        @param: list percentile_range: (optional) Percentile range of the chosen cbar_range.

        @return: fig fig: a matplotlib figure object to be saved to file.
        """
        freq_data = self.odmr_plot_x
        count_data = self.odmr_plot_y[channel_number]
        fit_freq_vals = self.odmr_fit_x
        fit_count_vals = self.odmr_fit_y
        matrix_data = self.odmr_plot_xy[:, channel_number]

        # If no colorbar range was given, take full range of data
        if cbar_range is None:
            cbar_range = np.array([np.min(matrix_data), np.max(matrix_data)])
        else:
            cbar_range = np.array(cbar_range)

        prefix = ['', 'k', 'M', 'G', 'T']
        prefix_index = 0

        # Rescale counts data with SI prefix
        while np.max(count_data) > 1000:
            count_data = count_data / 1000
            fit_count_vals = fit_count_vals / 1000
            prefix_index = prefix_index + 1

        counts_prefix = prefix[prefix_index]

        # Rescale frequency data with SI prefix
        prefix_index = 0

        while np.max(freq_data) > 1000:
            freq_data = freq_data / 1000
            fit_freq_vals = fit_freq_vals / 1000
            prefix_index = prefix_index + 1

        mw_prefix = prefix[prefix_index]

        # Rescale matrix counts data with SI prefix
        prefix_index = 0

        while np.max(matrix_data) > 1000:
            matrix_data = matrix_data / 1000
            cbar_range = cbar_range / 1000
            prefix_index = prefix_index + 1

        cbar_prefix = prefix[prefix_index]

        # Use qudi style
        plt.style.use(self._save_logic.mpl_qd_style)

        # Create figure
        fig, (ax_mean, ax_matrix) = plt.subplots(nrows=2, ncols=1)

        ax_mean.plot(freq_data, count_data, linestyle=':', linewidth=0.5)

        # Do not include fit curve if there is no fit calculated.
        if max(fit_count_vals) > 0:
            ax_mean.plot(fit_freq_vals, fit_count_vals, marker='None')

        ax_mean.set_ylabel('Fluorescence (' + counts_prefix + 'c/s)')
        ax_mean.set_xlim(np.min(freq_data), np.max(freq_data))

        matrixplot = ax_matrix.imshow(
            matrix_data,
            cmap=plt.get_cmap('inferno'),  # reference the right place in qd
            origin='lower',
            vmin=cbar_range[0],
            vmax=cbar_range[1],
            extent=[np.min(freq_data),
                    np.max(freq_data),
                    0,
                    self.number_of_lines
                    ],
            aspect='auto',
            interpolation='nearest')

        ax_matrix.set_xlabel('Frequency (' + mw_prefix + 'Hz)')
        ax_matrix.set_ylabel('Scan #')

        # Adjust subplots to make room for colorbar
        fig.subplots_adjust(right=0.8)

        # Add colorbar axis to figure
        cbar_ax = fig.add_axes([0.85, 0.15, 0.02, 0.7])

        # Draw colorbar
        cbar = fig.colorbar(matrixplot, cax=cbar_ax)
        cbar.set_label('Fluorescence (' + cbar_prefix + 'c/s)')

        # remove ticks from colorbar for cleaner image
        cbar.ax.tick_params(which=u'both', length=0)

        # If we have percentile information, draw that to the figure
        if percentile_range is not None:
            cbar.ax.annotate(str(percentile_range[0]),
                             xy=(-0.3, 0.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate(str(percentile_range[1]),
                             xy=(-0.3, 1.0),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )
            cbar.ax.annotate('(percentile)',
                             xy=(-0.3, 0.5),
                             xycoords='axes fraction',
                             horizontalalignment='right',
                             verticalalignment='center',
                             rotation=90
                             )

        return fig

    def perform_odmr_measurement(self, freq_start, freq_step, freq_stop, power, runtime,
                                 fit_function='No Fit', save_after_meas=True, name_tag=''):
        """ An independant method, which can be called by a task with the proper input values
            to perform an odmr measurement.

        @return
        """
        timeout = 30
        start_time = time.time()
        while self.module_state() != 'idle':
            time.sleep(0.5)
            timeout -= (time.time() - start_time)
            if timeout <= 0:
                self.log.error('perform_odmr_measurement failed. Logic module was still locked '
                               'and 30 sec timeout has been reached.')
                return {}

        # set all relevant parameter:
        self.set_power(power)
        self.set_sweep_frequencies(freq_start, freq_stop, freq_step)
        self.set_runtime(runtime)

        # start the scan
        self.start_odmr_scan()

        # wait until the scan has started
        while self.module_state() != 'locked':
            time.sleep(1)
        # wait until the scan has finished
        while self.module_state() == 'locked':
            time.sleep(1)

        # Perform fit if requested
        if fit_function != 'No Fit':
            self.do_fit(fit_function)
            fit_params = self.fc.current_fit_param
        else:
            fit_params = None

        # Save data if requested
        if save_after_meas:
            self.save_odmr_data(tag=name_tag)

        return self.odmr_plot_x, self.odmr_plot_y, fit_params
