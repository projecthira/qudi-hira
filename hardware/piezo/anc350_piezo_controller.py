# -*- coding: utf-8 -*-
"""
This file contains the Qudi hardware module to control Attocube ANC350 devices.
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

from core.module import Base
from core.configoption import ConfigOption
import ctypes


class ANC350:
    def __init__(self, dll_location, controller_number):
        self.controller_number = controller_number
        self._dll = ctypes.CDLL(dll_location)
        self.handle = ctypes.c_int(0)
        self._dll.PositionerConnect(self.controller_number, ctypes.byref(self.handle))

    def acInEnable(self, axis, state):
        """
        Activates/deactivates AC input of addressed axis; only applicable for dither axes
        """
        self._dll.PositionerAcInEnable(self.handle, axis, ctypes.c_bool(state))

    def getDeviceInfo(self):
        devinfo = PositionerInfo()  # create PositionerInfo Struct
        self._dll.PositionerGetDeviceInfo(0, devinfo)

    def amplitude(self, axis, amp):
        """
        set the amplitude setpoint in mV
        """
        self._dll.PositionerAmplitude(self.handle, axis, amp)

    def amplitudeControl(self, axis, mode):
        """
        selects the type of amplitude control. The amplitude is controlled by the Positioner to
        hold the value constant determined by the selected type of amplitude control.
        mode takes values 0: speed, 1: amplitude, 2: step size
        """
        self._dll.PositionerAmplitudeControl(self.handle, axis, mode)

    def bandwidthLimitEnable(self, axis, state):
        """
        activates/deactivates the bandwidth limiter of the addressed axis. only applicable for scanner axes
        """
        self._dll.PositionerBandwidthLimitEnable(self.handle, axis, ctypes.c_bool(state))

    def capacitanceMeasure(self, axis):
        """
        determines the capacitance of the piezo addressed by axis
        """
        self.status = self._dll.Int32(0)
        self._dll.PositionerCapMeasure(self.handle, axis, ctypes.byref(self.status))
        return self.status.value

    def clearStopDetection(self, axis):
        """
        when .setStopDetectionSticky() is enabled, this clears the stop detection status
        """
        self._dll.PositionerClearStopDetection(self.handle, axis)

    def close(self):
        """
        closes connection to ANC350 device
        """
        self._dll.PositionerClose(self.handle)

    def dcInEnable(self, axis, state):
        """
        Activates/deactivates DC input of addressed axis; only applicable for scanner/dither axes
        """
        self._dll.PositionerDcInEnable(self.handle, axis, ctypes.c_bool(state))

    def dcLevel(self, axis, dclev):
        """
        sets the dc level of selected axis. dclevel in mV
        """
        self._dll.PositionerDCLevel(self.handle, axis, dclev)

    def dutyCycleEnable(self, state):
        """
        controls duty cycle mode
        """
        self._dll.PositionerDutyCycleEnable(self.handle, ctypes.c_bool(state))

    def dutyCycleOffTime(self, value):
        """
        sets duty cycle off time
        """
        self._dll.PositionerDutyCycleOffTime(self.handle, value)

    def dutyCyclePeriod(self, value):
        """
        sets duty cycle period
        """
        self._dll.PositionerDutyCyclePeriod(self.handle, value)

    def externalStepBkwInput(self, axis, input_trigger):
        """
        configures external step trigger input for selected axis. a trigger on this
        input results in a backwards single step. input_trigger: 0 disabled, 1-6 input trigger
        """
        self._dll.PositionerExternalStepBkwInput(self.handle, axis, input_trigger)

    def externalStepFwdInput(self, axis, input_trigger):
        """
        configures external step trigger input for selected axis. a trigger on this
        input results in a forward single step. input_trigger: 0 disabled, 1-6 input trigger
        """
        self._dll.PositionerExternalStepFwdInput(self.handle, axis, input_trigger)

    def externalStepInputEdge(self, axis, edge):
        """
        configures edge sensitivity of external step trigger input for selected axis. edge: 0 rising, 1 falling
        """
        self._dll.PositionerExternalStepInputEdge(self.handle, axis, edge)

    def frequency(self, axis, freq):
        """
        sets the frequency of selected axis. frequency in Hz
        """
        self._dll.PositionerFrequency(self.handle, axis, freq)

    def getAcInEnable(self, axis):
        """
        determines status of ac input of addressed axis. only applicable for dither axes
        """
        self.status = ctypes.c_bool(None)
        self._dll.PositionerGetAcInEnable(self.handle, axis, ctypes.byref(self.status))
        return self.status.value

    def getAmplitude(self, axis):
        """
        determines the actual amplitude. In case of standstill of the actor this is
        the amplitude setpoint. In case of movement the amplitude set by amplitude control is determined.
        """
        self.status = self._dll.Int32(0)
        self._dll.PositionerGetAmplitude(self.handle, axis, ctypes.byref(self.status))
        return self.status.value

    def getBandwidthLimitEnable(self, axis):
        """
        determines status of bandwidth limiter of addressed axis. only applicable for scanner axes
        """
        self.status = ctypes.c_bool(None)
        self._dll.PositionerGetBandwidthLimitEnable(self.handle, axis, ctypes.byref(self.status))
        return self.status.value

    def getDcInEnable(self, axis):
        """
        determines status of dc input of addressed axis. only applicable for scanner/dither axes
        """
        self.status = ctypes.c_bool(None)
        self._dll.PositionerGetDcInEnable(self.handle, axis, ctypes.byref(self.status))
        return self.status.value

    def getDcLevel(self, axis):
        """
        determines the status actual DC level in mV
        """
        self.dclev = self._dll.Int32(0)
        self._dll.PositionerGetDcLevel(self.handle, axis, ctypes.byref(self.dclev))
        return self.dclev.value

    def getFrequency(self, axis):
        """
        determines the frequency in Hz
        """
        self.freq = self._dll.Int32(0)
        self._dll.PositionerGetFrequency(self.handle, axis, ctypes.byref(self.freq))
        return self.freq.value

    def getIntEnable(self, axis):
        """
        determines status of internal signal generation of addressed axis. only applicable for scanner/dither axes
        """
        self.status = ctypes.c_bool(None)
        self._dll.PositionerGetIntEnable(self.handle, axis, ctypes.byref(self.status))
        return self.status.value

    def getPosition(self, axis):
        """
        determines actual position of addressed axis
        """
        self.pos = self._dll.Int32(0)
        self._dll.PositionerGetPosition(self.handle, axis, ctypes.byref(self.pos))
        return self.pos.value

    def getReference(self, axis):
        """
        determines distance of reference mark to origin
        """
        self.pos = self._dll.Int32(0)
        self.validity = ctypes.c_bool(None)
        self._dll.PositionerGetReference(self.handle, axis, ctypes.byref(self.pos), ctypes.byref(self.validity))
        return self.pos.value, self.validity.value

    def getReferenceRotCount(self, axis):
        """
        determines actual position of addressed axis
        """
        self.rotcount = self._dll.Int32(0)
        self._dll.PositionerGetReferenceRotCount(self.handle, axis, ctypes.byref(self.rotcount))
        return self.rotcount.value

    def getRotCount(self, axis):
        """
        determines actual number of rotations in case of rotary actuator
        """
        self.rotcount = self._dll.Int32(0)
        self._dll.PositionerGetRotCount(self.handle, axis, ctypes.byref(self.rotcount))
        return self.rotcount.value

    def getSpeed(self, axis):
        """
        determines the actual speed. In case of standstill of this actor this is
        the calculated speed resulting	from amplitude setpoint, frequency, and motor parameters.
        In case of movement this is measured speed.
        """
        self.spd = self._dll.Int32(0)
        self._dll.PositionerGetSpeed(self.handle, axis, ctypes.byref(self.spd))
        return self.spd.value

    def getStatus(self, axis):
        """
        determines the status of the selected axis. result: bit0 (moving), bit1 (stop detected),
        bit2 (sensor error), bit3 (sensor disconnected)
        """
        self.status = self._dll.Int32(0)
        self._dll.PositionerGetStatus(self.handle, axis, ctypes.byref(self.status))
        return self.status.value

    def getStepwidth(self, axis):
        """
        determines the step width. In case of standstill of the motor this is the calculated
        step width	resulting from amplitude setpoint, frequency, and motor parameters.
        In case of movement this is measured step width
        """
        self.stepwdth = self._dll.Int32(0)
        self._dll.PositionerGetStepwidth(self.handle, axis, ctypes.byref(self.stepwdth))
        return self.stepwdth.value

    def intEnable(self, axis, state):
        """
        Activates/deactivates internal signal generation of addressed axis; only applicable for scanner/dither axes
        """
        self._dll.PositionerIntEnable(self.handle, axis, ctypes.c_bool(state))

    def load(self, axis, filename):
        """
        loads a parameter file for actor configuration.	note: this requires a pointer to a char datatype.
        having no parameter file to test, I have no way of telling whether this will work, especially with
        the manual being as erroneous as it is. as such, use at your own (debugging) risk!
        """
        self._dll.PositionerLoad(self.handle, axis, ctypes.byref(ctypes.char(filename)))

    def moveAbsolute(self, axis, position, rotcount=0):
        """
        starts approach to absolute target position. previous movement will be stopped. rotcount optional
        argument position units are in 'unit of actor multiplied by 1000' (generally nanometres)
        """
        self._dll.PositionerMoveAbsolute(self.handle, axis, position, rotcount)

    def moveAbsoluteSync(self, bitmask_of_axes):
        """
        starts the synchronous approach to absolute target position for selected axis. previous movement will be
        stopped. target position for each axis defined by .setTargetPos() takes a *bitmask* of axes!
        """
        self._dll.PositionerMoveAbsoluteSync(self.handle, bitmask_of_axes)

    def moveContinuous(self, axis, direction):
        """
        starts continuously positioning with set parameters for ampl and speed and amp control respectively.
        direction can be 0 (forward) or 1 (backward)
        """
        self._dll.PositionerMoveContinuous(self.handle, axis, direction)

    def moveReference(self, axis):
        """
        starts approach to reference position. previous movement will be stopped.
        """
        self._dll.PositionerMoveReference(self.handle, axis)

    def moveRelative(self, axis, position, rotcount=0):
        """
        starts approach to relative target position. previous movement will be stopped. rotcount optional argument.
        position units are in 'unit of actor multiplied by 1000' (generally nanometres)
        """
        self._dll.PositionerMoveRelative(self.handle, axis, position, rotcount)

    def moveSingleStep(self, axis, direction):
        """
        starts a one-step positioning. Previous movement will be stopped. direction can be 0 (forward) or 1 (backward)
        """
        self._dll.PositionerMoveSingleStep(self.handle, axis, direction)

    def quadratureAxis(self, quadratureno, axis):
        """
        selects the axis for use with this trigger in/out pair. quadratureno: number of addressed quadrature unit (0-2)
        """
        self._dll.PositionerQuadratureAxis(self.handle, quadratureno, axis)

    def quadratureInputPeriod(self, quadratureno, period):
        """
        selects the stepsize the controller executes when detecting a step on its input AB-signal.
        quadratureno: number of addressed quadrature unit (0-2). period: stepsize in unit of actor * 1000
        """
        self._dll.PositionerQuadratureInputPeriod(self.handle, quadratureno, period)

    def quadratureOutputPeriod(self, quadratureno, period):
        """
        selects the position difference which causes a step on the output AB-signal.
        quadratureno: number of addressed quadrature unit (0-2). period: period in unit of actor * 1000
        """
        self._dll.PositionerQuadratureOutputPeriod(self.handle, quadratureno, period)

    def resetPosition(self, axis):
        """
        sets the origin to the actual position
        """
        self._dll.PositionerResetPosition(self.handle, axis)

    def sensorPowerGroupA(self, state):
        """
        switches power of sensor group A. Sensor group A contains either the sensors of axis 1-3 or
        1-2 dependent on hardware of controller
        """
        self._dll.PositionerSensorPowerGroupA(self.handle, ctypes.c_bool(state))

    def sensorPowerGroupB(self, state):
        """
        switches power of sensor group B. Sensor group B contains either the sensors of axis 4-6 or 3
        dependent on hardware of controller
        """
        self._dll.PositionerSensorPowerGroupB(self.handle, ctypes.c_bool(state))

    def setHardwareId(self, hwid):
        """
        sets the hardware ID for the device (used to differentiate multiple devices)
        """
        self._dll.PositionerSetHardwareId(self.handle, hwid)

    def setOutput(self, axis, state):
        """
        activates/deactivates the addressed axis
        """
        self._dll.PositionerSetOutput(self.handle, axis, ctypes.c_bool(state))

    def setStopDetectionSticky(self, axis, state):
        """
        when enabled, an active stop detection status remains active until cleared manually by .clearStopDetection()
        """
        self._dll.PositionerSetStopDetectionSticky(self.handle, axis, state)

    def setTargetGround(self, axis, state):
        """
        when enabled, actor voltage set to zero after closed-loop positioning finished
        """
        self._dll.PositionerSetTargetGround(self.handle, axis, ctypes.c_bool(state))

    def setTargetPos(self, axis, pos, rotcount=0):
        """
        sets target position for use with .moveAbsoluteSync()
        """
        self._dll.PositionerSetTargetPos(self.handle, axis, pos, rotcount)

    def singleCircleMode(self, axis, state):
        """
        switches single circle mode. In case of activated single circle mode the number of rotations are
        ignored and the shortest way to target position is used. Only relevant for rotary actors.
        """
        self._dll.PositionerSingleCircleMode(self.handle, axis, ctypes.c_bool(state))

    def staticAmplitude(self, amp):
        """
        sets output voltage for resistive sensors
        """
        self._dll.PositionerStaticAmplitude(self.handle, amp)

    def stepCount(self, axis, stps):
        """
        configures number of successive step scaused by external trigger or manual step request. steps = 1 to 65535
        """
        self._dll.PositionerStepCount(self.handle, axis, stps)

    def stopApproach(self, axis):
        """
        stops approaching target/relative/reference position. DC level of affected axis after stopping
        depends on setting by .setTargetGround()
        """
        self._dll.PositionerStopApproach(self.handle, axis)

    def stopDetection(self, axis, state):
        """
        switches stop detection on/off
        """
        self._dll.PositionerStopDetection(self.handle, axis, ctypes.c_bool(state))

    def stopMoving(self, axis):
        """
        stops any positioning, DC level of affected axis is set to zero after stopping.
        """
        self._dll.PositionerStopMoving(self.handle, axis)

    def trigger(self, triggerno, lowlevel, highlevel):
        """
        sets the trigger thresholds for the external trigger. triggerno is 0-5, lowlevel/highlevel
        in units of actor * 1000
        """
        self._dll.PositionerTrigger(self.handle, triggerno, lowlevel, highlevel)

    def triggerAxis(self, triggerno, axis):
        """
        selects the corresponding axis for the addressed trigger. triggerno is 0-5
        """
        self._dll.PositionerTriggerAxis(self.handle, triggerno, axis)

    def triggerEpsilon(self, triggerno, epsilon):
        """
        sets the hysteresis of the external trigger. epsilon in units of actor * 1000
        """
        self._dll.PositionerTriggerEpsilon(self.handle, triggerno, epsilon)

    def triggerModeIn(self, mode):
        """
        selects the mode of the input trigger signals. state: 0 disabled - inputs trigger nothing,
        1 quadrature - three pairs of trigger in signals are used to accept AB-signals for relative positioning,
        2 coarse - trigger in signals are used to generate coarse steps
        """
        self._dll.PositionerTriggerModeIn(self.handle, mode)

    def triggerModeOut(self, mode):
        """
        selects the mode of the output trigger signals. state: 0 disabled - inputs trigger nothing,
        1 position - the trigger outputs reacts to the defined position ranges with the selected polarity,
        2 quadrature - three pairs of trigger out signals are used to signal relative movement as AB-signals,
        3 IcHaus - the trigger out signals are used to output the internal position signal of num-sensors
        """
        self._dll.PositionerTriggerModeOut(self.handle, mode)

    def triggerPolarity(self, triggerno, polarity):
        """
        sets the polarity of the external trigger, triggerno: 0-5, polarity: 0 low active, 1 high active
        """
        self._dll.PositionerTriggerPolarity(self.handle, triggerno, polarity)

    def updateAbsolute(self, axis, position):
        """
        updates target position for a *running* approach. function has lower performance impact on running
        approach compared to .moveAbsolute(). position units are in 'unit of actor multiplied by 1000'
        (generally nanometres)
        """
        self._dll.PositionerUpdateAbsolute(self.handle, axis, position)


class ANCController(Base):
    _modclass = 'attocube_anc350'
    _modtype = 'hardware'

    _dll_location = ConfigOption('dll_location', missing='error')
    _sample_controller_number = ConfigOption("sample_controller_number", 0, missing='error')
    _tip_controller_number = ConfigOption("tip_controller_number", 1, missing='error')
    tip = None
    sample = None

    def on_activate(self):
        self.tip = ANC350(self._dll_location, self._tip_controller_number)
        self.sample = ANC350(self._dll_location, self._sample_controller_number)

    def on_deactivate(self):
        self.tip.close()
        self.sample.close()


# structure for PositionerInfo to handle positionerCheck return data
class PositionerInfo(ctypes.Structure):
    _fields_ = [("id", ctypes.c_int16), ("locked", ctypes.c_bool)]
