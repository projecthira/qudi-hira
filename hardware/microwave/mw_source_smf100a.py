# -*- coding: utf-8 -*-
"""
This file contains the Qudi hardware file to control R&S SMF100A devices.

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

import visa
from core.module import Base
from core.configoption import ConfigOption
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode


class MicrowaveSMF(Base, MicrowaveInterface):
    """ Hardware control class to controls R&S SMF100A devices.  """

    _modclass = 'MicrowaveSMF'
    _modtype = 'hardware'
    _smf_visa_address = ConfigOption('smf_visa_address', missing='error')
    _smf_timeout = ConfigOption('smf_timeout', 100, missing='warn')

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

    def on_deactivate(self):
        """ Deinitialization performed during deactivation of the module."""
        self.inst.close()
        self.rm.close()
        return

    def rf_on(self):
        """
        Switches on cw microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        self.inst.write(':OUTP:STAT 1')
        return 0

    def cw_on(self):
        current_mode, is_running = self.get_status()
        if is_running:
            if current_mode == 'cw':
                return 0
            else:
                self.off()

        if current_mode != 'cw':
            self.inst.write(':FREQ:MODE CW')

        self.inst.write(':OUTP:STAT 1')
        return 0

    def off(self):
        """
        Switches off cw microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        self.inst.write(':OUTP:STAT 0')
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
        self.freq = float(self.inst.query('SOUR:FREQ:CW?'))
        return self.freq

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
            self.set_frequency(freq)
        if power is not None:
            self.set_power(power)
        if useinterleave is not None:
            self.log.warning("No interleave available at the moment!")

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

        # This needs to be done due to stupid design of the list mode (sweep is better)
        self.cw_on()
        self._command_wait(':LIST:LEARN')
        self._command_wait(':FREQ:MODE LIST')
        dummy, is_running = self.get_status()
        while not is_running:
            time.sleep(0.2)
            dummy, is_running = self.get_status()
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

    """
    The following methods are not connected by the interface, so they are only being utilized by other methods in the class.
    """

    def set_power(self, power):
        self.inst.write(':SOUR:POW:POW {}'.format(power))
        return

    def set_frequency(self, frequency):
        self.inst.write(':SOUR:FREQ:CW {}'.format(frequency))
        return
