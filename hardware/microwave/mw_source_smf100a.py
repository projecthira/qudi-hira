# -*- coding: utf-8 -*-
__author__ = "Dinesh Pinto"
__email__ = "d.pinto@fkf.mpg.de"
"""
This file contains the Qudi hardware file to control R&S SMF100a devices.
author: Dinesh Pinto
email: d.pinto@fkf.mpg.de

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

import visa
import time
import numpy as np
from core.module import Base
from core.configoption import ConfigOption
from interface.microwave_interface import MicrowaveInterface, MicrowaveMode, MicrowaveLimits, TriggerEdge


class MicrowaveSMF(Base, MicrowaveInterface):
    """ Hardware control class to controls R&S SMF100a devices.

    Example config for copy-paste:

    mw_smf100a:
        module.Class: 'microwave.mw_source_smf100a.MicrowaveSMF'
        smf_visa_address: 'TCPIP0::192.168.0.6::inst0::INSTR'
        smf_timeout: 100
     """

    _modclass = 'MicrowaveSMF'
    _modtype = 'hardware'
    _smf_visa_address = ConfigOption('smf_visa_address', missing='error')
    _smf_timeout = ConfigOption('smf_timeout', 5000, missing='warn')

    def on_activate(self):
        """ Initialization performed during activation of the module. """

        try:
            # trying to load the visa connection to the module
            self.rm = visa.ResourceManager()
            self.inst = self.rm.open_resource(
                resource_name=self._smf_visa_address,
                timeout=self._smf_timeout)
            self.log.info('MW SMF100A initialised and connected to hardware.')
            self.model = self.inst.query('*IDN?').split(',')[1]
        except:
            self.log.error('SMF100A could not connect to LAN address {}. Check NI-MAX settings to see if device '
                           'is connected correctly.'.format(self._smf_visa_address))

        self._command_wait('*CLS')
        # TODO: This appears to cause unnecessary timeouts, removed for now
        # self._command_wait('*RST')
        self.inst.write('*RST')
        self._command_wait('POW:ALC OFF')

    def on_deactivate(self):
        """ Deinitialization performed during deactivation of the module."""
        self.inst.close()
        self.rm.close()
        return

    def off(self):
        """
        Switches off cw microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        mode, is_running = self.get_status()
        if not is_running:
            return 0

        if mode != 'cw':
            self.inst.write("SYST:DISP:UPD ON")
            self._command_wait(':FREQ:MODE CW')

        self.inst.write(':OUTP:STAT 0')
        self.inst.write('*WAI')

        while int(float(self.inst.query('OUTP:STAT?'))) != 0:
            time.sleep(0.2)

        return 0

    def get_status(self):
        """
        Gets the current status of the MW source, i.e. the mode (cw, list or
        sweep) and the output state (stopped, running)

        @return str, bool: mode ['cw', 'sweep'], is_running [True, False]
        """
        mode = self.inst.query(':SOUR:FREQ:MODE?').strip('\n').lower()
        is_running = bool(int(float(self.inst.query(':OUTP:STAT?'))))
        if mode == 'swe':
            mode = 'sweep'
        return mode, is_running

    def get_power(self):
        """ Gets the microwave output power.

        @return float: the power set at the device in dBm
        """
        self.power = float(self.inst.query(':SOUR:POW:POW?'))
        return self.power

    def get_frequency(self):
        """ Gets the frequency of the microwave output.

        @return float: frequency (in Hz), which is currently set for this device
        """
        mode, is_running = self.get_status()

        if mode == "cw":
            freq = float(self.inst.query('SOUR:FREQ:CW?'))
        elif mode == "list":
            frequency_str = self.inst.query(':LIST:FREQ?').split(',', 1)[1]
            freq = np.array([float(freq) for freq in frequency_str.split(',')])
        elif mode == "sweep":
            start = float(self.inst.query(':FREQ:STAR?'))
            stop = float(self.inst.query(':FREQ:STOP?'))
            step = float(self.inst.query(':SWE:STEP?'))
            freq = [start, stop, step]
        else:
            self.log.warning("Undefined mode {} for MW device".format(mode))
            freq = None

        return freq

    def cw_on(self):
        current_mode, is_running = self.get_status()
        if is_running:
            if current_mode == 'cw':
                return 0
            else:
                self.off()

        if current_mode != 'cw':
            self._command_wait(':FREQ:MODE CW')

        self.inst.write(':OUTP:STAT 1')
        self.inst.write('*WAI')

        _, is_running = self.get_status()
        while not is_running:
            time.sleep(0.2)
            _, is_running = self.get_status()

        return 0

    def set_cw(self, freq=None, power=None, useinterleave=None):
        """
        Configures the device for cw-mode and optionally sets frequency and/or power

        @param float freq: frequency to set in Hz
        @param float power: power to set in dBm

        @return tuple(float, float, str): with the relation
            current frequency in Hz,
            current power in dBm,
            current mode
        """
        mode, is_running = self.get_status()
        if is_running:
            self.off()

        if mode != 'cw':
            self._command_wait(':FREQ:MODE CW')
        if freq is not None:
            self._command_wait(':SOUR:FREQ:CW {}'.format(freq))
        if power is not None:
            self._command_wait(':SOUR:POW:POW {}'.format(power))
        if useinterleave is not None:
            self.log.warning("No interleave available at the moment!")

        mode, _ = self.get_status()
        actual_freq = self.get_frequency()
        actual_power = self.get_power()
        return actual_freq, actual_power, mode

    def set_list(self, frequency=None, power=None):

        mode, is_running = self.get_status()
        if is_running:
            self.off()

        # Cant change list parameters if in list mode
        if mode != 'cw':
            self.set_cw()

        self.inst.write(':LIST:SEL "QUDI"')
        self.inst.write('*WAI')

        # Set list frequencies
        if frequency is not None:
            s = ' {0:f},'.format(frequency[0])
            for f in frequency[:-1]:
                s += ' {0:f},'.format(f)
            s += ' {0:f}'.format(frequency[-1])
            self.inst.write(':LIST:FREQ' + s)
            self.inst.write('*WAI')
            self.inst.write(':LIST:MODE STEP')
            self.inst.write('*WAI')

        # Set list power
        if power is not None:
            self.inst.write(':LIST:POW {0:f}'.format(power))
            self.inst.write('*WAI')

        self._command_wait(':LIST:TRIG:SOUR EXT')
        self._command_wait(':LIST:LEARN')
        self._command_wait(':FREQ:MODE LIST')

        mode, _ = self.get_status()
        actual_freq = self.get_frequency()
        actual_power = self.get_power()
        return actual_freq, actual_power, mode

    def list_on(self):
        """
        Switches on the list mode microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        current_mode, is_running = self.get_status()
        if is_running:
            if current_mode == 'list':
                return 0
            else:
                self.off()

        self.cw_on()
        self._command_wait(':FREQ:MODE LIST')
        self.inst.write(':LIST:TRIG:EXEC')

        _, is_running = self.get_status()
        return 0

    def reset_listpos(self):
        """
        Reset of MW list mode position to start (first frequency step)

        @return int: error code (0:OK, -1:error)
        """
        self._command_wait(':LIST:RES')
        return 0

    def set_sweep(self, start=None, stop=None, step=None, power=None, dwell=100):
        """
        Configures the device for sweep-mode and optionally sets frequency start/stop/step
        and/or power

        @return float, float, float, float, str: current start frequency in Hz,
                                                 current stop frequency in Hz,
                                                 current frequency step in Hz,
                                                 current power in dBm,
                                                 current mode
        """
        mode, is_running = self.get_status()
        if is_running:
            self.off()

        if mode != 'sweep':
            self._command_wait(':FREQ:MODE SWE')

        if (start is not None) and (stop is not None) and (step is not None):
            self.inst.write(':SWE:SPAC LIN')
            self.inst.write('*WAI')
            self.inst.write(':FREQ:STAR {0:f}'.format(start))
            self.inst.write(':FREQ:STOP {0:f}'.format(stop))
            self.inst.write(':SWE:STEP {0:f}'.format(step))
            self.inst.write(':SWE:DWeLl {0:f}'.format(dwell))
            self.inst.write('*WAI')

        if power is not None:
            self.inst.write(':POW {0:f}'.format(power))
            self.inst.write('*WAI')

        self._command_wait(':TRIG:FSW:SOUR SING')
        self._command_wait(':SWE:FREQ:MODE AUTO')

        actual_power = self.get_power()
        actual_start, actual_stop, actual_step = self.get_frequency()
        mode, _ = self.get_status()
        return actual_start, actual_stop, actual_step, actual_power, mode

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        current_mode, is_running = self.get_status()
        if is_running:
            if current_mode == 'sweep':
                return 0
            else:
                self.off()

        if current_mode != 'sweep':
            self._command_wait(':FREQ:MODE SWEEP')

        if float(self.inst.query(":SWE:DWeLl?")) < 2.0:
            self.inst.write("SYST:DISP:UPD OFF")

        self._command_wait(':SWE:FREQ:EXEC')
        self.inst.write(':OUTP:STAT 1')

        _, is_running = self.get_status()
        while not is_running:
            time.sleep(0.2)
            _, is_running = self.get_status()
        return 0

    def reset_sweeppos(self):
        """
        Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """
        self._command_wait(':SWE:RES')
        return 0

    def get_limits(self):
        """ Return the device-specific limits in a nested dictionary.

          @return MicrowaveLimits: Microwave limits object
        """
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.LIST)

        limits.min_frequency = 1e9
        limits.max_frequency = 22e9

        limits.min_power = -30
        limits.max_power = 30

        return limits

    def set_ext_trigger(self, pol, timing):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or falling edge)
        @param float timing: estimated time between triggers

        @return object, float: current trigger polarity [TriggerEdge.RISING, TriggerEdge.FALLING],
            trigger timing
        """
        mode, is_running = self.get_status()
        if is_running:
            self.off()

        self.log.warning("Parameter 'timing' in set_ext_trigger will be ignored.")

        if pol == TriggerEdge.RISING:
            edge = 'POS'
        elif pol == TriggerEdge.FALLING:
            edge = 'NEG'
        else:
            self.log.warning('No valid trigger polarity passed to microwave hardware module.')
            edge = None

        if edge is not None:
            self._command_wait('INP:TRIG:SLOP {0}'.format(edge))

        polarity = self.inst.query(':TRIG:SLOP?')
        if 'NEG' in polarity:
            return TriggerEdge.FALLING, timing
        else:
            return TriggerEdge.RISING, timing

    def _command_wait(self, command_str):
        """
        Writes the command in command_str via GPIB and waits until the device has finished
        processing it.

        @param command_str: The command to be written
        """
        self.inst.write(command_str)
        self.inst.write('*WAI')
        while int(float(self.inst.query('*OPC?'))) != 1:
            time.sleep(0.1)
        return
