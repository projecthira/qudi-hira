# -*- coding: utf-8 -*-

"""
This file contains the Qudi hardware file to control Vaunix Microwave Device.

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

Parts of this file were developed from a PI3diamond module which is
Copyright (C) 2009 Helmut Rathgen <helmut.rathgen@gmail.com>

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import ctypes
import os

from core.module import Base
from core.util.modules import get_main_dir
from interface.microwave_interface import MicrowaveInterface
from interface.microwave_interface import MicrowaveLimits
from interface.microwave_interface import MicrowaveMode
from interface.microwave_interface import TriggerEdge


class MicrowaveVaunix(Base, MicrowaveInterface):
    """ Hardware control file for Vaunix Microwave Devices.
        Tested for the model LMS-203.
    """
    _modclass = 'MicrowaveVaunix'
    _modtype = 'hardware'
    _devID = ctypes.c_uint()

    _double3d = ctypes.c_double * 3  # This is creating a 3D double array object
    _double1d = ctypes.c_double * 1  # This is creating a 1D double object
    _bool1d = ctypes.c_bool * 1  # This is creating a 1D bool object

    # Status returns for DevStatus
    INVALID_DEVID = 0x80000000  # MSB is set if the device ID is invalid
    DEV_CONNECTED = 0x00000001  # LSB is set if a device is connected
    DEV_OPENED = 0x00000002  # set if the device is opened
    SWP_ACTIVE = 0x00000004  # set if the device is sweeping
    SWP_UP = 0x00000008  # set if the device is sweeping up in frequency
    SWP_REPEAT = 0x00000010  # set if the device is in continuous sweep mode
    SWP_BIDIRECTIONAL = 0x00000020  # set if the device is in bidirectional sweep mode
    PLL_LOCKED = 0x00000040  # set if the PLL lock status is TRUE (both PLL's are locked)
    FAST_PULSE_OPTION = 0x00000080  # set if the fast pulse mode option is installed

    def on_activate(self):
        """ Initialisation performed during activation of the module.
        """
        path_dll = os.path.join(get_main_dir(),
                                'thirdparty',
                                'vaunix',
                                'vnx_fmsynth.dll'
                                )
        self._vaunixdll = ctypes.windll.LoadLibrary(path_dll)

        self._vaunixdll.fnLMS_GetNumDevices()
        self._vaunixdll.fnLMS_SetTestMode(ctypes.c_bool(False))

        active_devices = (ctypes.c_uint * 64)()
        numofdevs = self._vaunixdll.fnLMS_GetDevInfo(active_devices)

        if numofdevs == 1:
            self._devID = active_devices[0]
            err = self._vaunixdll.fnLMS_InitDevice(self._devID)
            if err:
                self.log.error('Error occurred during initialization: {}'.format(err))
                return -1
            return 0

        elif numofdevs > 1:
            self.log.warning(
                'There is more than 1 Vaunix device connected, currently only one connection is supported.')
            return -1

        else:
            self.log.warning('No Vaunix devices found.')
            return -1

    def on_deactivate(self):
        """ Deinitialisation performed during deactivation of the module.
        """
        self._vaunixdll.fnLMS_CloseDevice(self._devID)
        return 0

    def off(self):
        """
        Switches off any microwave output.
        Must return AFTER the device is actually stopped.

        @return int: error code (0:OK, -1:error)
        """
        lvstatus = self._vaunixdll.fnLMS_SetRFOn(self._devID, ctypes.c_bool(False))
        if lvstatus == 0:
            return 0
        else:
            return -1

    def get_status(self):
        """
        Gets the current status of the MW source, i.e. the mode (cw, list or sweep) and
        the output state (stopped, running)

        @return str, bool: mode ['cw', 'list', 'sweep'], is_running [True, False]
        """

        dev_status = self._vaunixdll.fnLMS_GetDeviceStatus(self._devID)

        if dev_status & self.SWP_ACTIVE:
            sweep_active = True
        else:
            sweep_active = False

        if dev_status & self.SWP_REPEAT:
            sweep_repeat = True
        else:
            sweep_repeat = False

        if not sweep_active:
            mode = 'cw'
        elif sweep_active and sweep_repeat:
            mode = 'sweep'
        elif sweep_active and not sweep_repeat:
            mode = 'asweep'
        else:
            self.log.error('Unable to get device status!')
            return -1

        is_running = bool(self._vaunixdll.fnLMS_GetRF_On(self._devID))
        return mode, is_running

    def get_power(self):
        """
        Gets the microwave output power for the currently active mode.

        @return float: the output power in dBm
        """

        return int(self._vaunixdll.fnLMS_GetAbsPowerLevel(self._devID)) * 0.25

    def get_frequency(self):
        """
        Gets the frequency of the microwave output.
        Returns single float value if the device is in cw mode.
        Returns list like [start, stop, step] if the device is in sweep mode.
        Returns list of frequencies if the device is in list mode.

        @return [float, list]: frequency(s) currently set for this device in Hz
        """
        mode, is_running = self.get_status()

        if 'cw' in mode:
            return_val = float(self._vaunixdll.fnLMS_GetFrequency(self._devID)) * 10
        elif 'sweep' in mode or 'asweep' in mode:
            start = float(self._vaunixdll.fnLMS_GetStartFrequency(self._devID)) * 10
            stop = float(self._vaunixdll.fnLMS_GetEndFrequency(self._devID)) * 10

            step = 0.1e6  # arbitrary
            return_val = [start, stop, step]

        return return_val

    def cw_on(self):
        """
        Switches on cw microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        mode, is_running = self.get_status()

        if mode != 'cw':
            self.set_cw()
        elif is_running:
            return 0

        lvstatus = self._vaunixdll.fnLMS_SetRFOn(self._devID, ctypes.c_bool(True))
        if lvstatus == 0:
            return 0
        else:
            return -1

    def set_cw(self, frequency=None, power=None):
        """
        Configures the device for cw-mode and optionally sets frequency and/or power

        @param float frequency: frequency to set in Hz
        @param float power: power to set in dBm

        @return tuple(float, float, str): with the relation
            current frequency in Hz,
            current power in dBm,
            current mode
        """

        mode, is_running = self.get_status()
        if is_running:
            self.off()

        # Activate CW mode
        if mode != 'cw':
            self._vaunixdll.fnLMS_StartSweep(self._devID, ctypes.c_bool(False))

        # Set CW frequency
        if frequency is not None:
            frequency_on10 = ctypes.c_int(int(round(frequency / 10)))
            self._vaunixdll.fnLMS_SetFrequency(self._devID, frequency_on10)

        # Set CW power
        if power is not None:
            int_power_level = ctypes.c_int(int(round(power / 0.25)))
            self._vaunixdll.fnLMS_SetPowerLevel(self._devID, int_power_level)

        # Return actually set values
        mode, dummy = self.get_status()
        actual_freq = self.get_frequency()
        actual_power = self.get_power()

        return actual_freq, actual_power, mode

    def list_on(self):
        """
        Switches on the list mode microwave output.
        Must return AFTER the device is actually running.

        @return int: error code (0:OK, -1:error)
        """
        self.log.warning('List mode is not available for Vaunix microwave generators!')
        return -1

    def set_list(self, frequency=None, power=None):
        """
        Configures the device for list-mode and optionally sets frequencies and/or power

        @param list frequency: list of frequencies in Hz
        @param float power: MW power of the frequency list in dBm

        @return list, float, str: current frequencies in Hz, current power in dBm, current mode
        """
        self.log.warning('List mode is not available for Vaunix microwave generators!')
        return self.get_frequency(), self.get_power(), 'sweep'

    def reset_listpos(self):
        """
        Reset of MW list mode position to start (first frequency step)

        @return int: error code (0:OK, -1:error)
        """
        self.log.warning('List mode is not available for Vaunix microwave generators!')
        return -1

    def sweep_on(self):
        """ Switches on the sweep mode.

        @return int: error code (0:OK, -1:error)
        """
        self.log.warning('Sweep mode is not implemented yet!')
        return -1

    def set_sweep(self, start=None, stop=None, step=None, power=None):
        """
        Configures the device for sweep-mode and optionally sets frequency start/stop/step
        and/or power

        @return float, float, float, float, str: current start frequency in Hz,
                                                 current stop frequency in Hz,
                                                 current frequency step in Hz,
                                                 current power in dBm,
                                                 current mode
        """
        self.log.warning('Sweep mode is not implemented yet!')
        return start, stop, step, power, 'sweep'

    def reset_sweeppos(self):
        """
        Reset of MW sweep mode position to start (start frequency)

        @return int: error code (0:OK, -1:error)
        """
        self.log.warning('Sweep mode is not implemented yet!')
        return -1

    def set_ext_trigger(self, pol=TriggerEdge.RISING):
        """ Set the external trigger for this device with proper polarization.

        @param TriggerEdge pol: polarisation of the trigger (basically rising edge or falling edge)

        @return object: current trigger polarity [TriggerEdge.RISING, TriggerEdge.FALLING]
        """
        self.log.warning('Sweep mode is not implemented yet!')
        return pol

    def trigger(self):
        """ Trigger the next element in the list or sweep mode programmatically.

        @return int: error code (0:OK, -1:error)

        Ensure that the Frequency was set AFTER the function returns, or give
        the function at least a save waiting time corresponding to the
        frequency switching speed.
        """
        self.log.warning('Trigger not available for Vaunix microwave generator.')
        return -1

    def get_limits(self):
        """ Return the device-specific limits in a nested dictionary.

          @return MicrowaveLimits: Microwave limits object
        """
        # Right now, this is for Vaunix Lab Brick LMS-203 only.
        limits = MicrowaveLimits()
        limits.supported_modes = (MicrowaveMode.CW, MicrowaveMode.SWEEP, MicrowaveMode.ASWEEP)

        limits.min_frequency = 10e9  # unit: Hz
        limits.max_frequency = 20e9  # unit: Hz

        limits.min_power = -30  # unit: dBm
        limits.max_power = 10  # unit: dBm
        return limits
