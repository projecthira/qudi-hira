# -*- coding: utf-8 -*-

"""
This file contains the header files control ANC350 devices.

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

#
#  ANC350lib is a Python implementation of the C++ header provided
#     with the attocube ANC350 closed-loop positioner system.
#


import ctypes

#
# List of error types
#
NCB_Ok = 0  # No error
NCB_Error = -1  # Unknown / other error
NCB_Timeout = 1  # Timeout during data retrieval
NCB_NotConnected = 2  # No contact with the positioner via USB
NCB_DriverError = 3  # Error in the driver response
NCB_BootIgnored = 4  # Ignored boot, equipment was already running
NCB_FileNotFound = 5  # Boot image not found
NCB_InvalidParam = 6  # Transferred parameter is invalid
NCB_DeviceLocked = 7  # A connection attempt failed because the device is already in use
NCB_NotSpecifiedParam = 8  # Transferred parameter is out of specification


# checks the errors returned from the dll
def checkError(code, func, args):
    if code == NCB_Ok:
        return
    elif code == NCB_BootIgnored:
        print("Warning: boot ignored in", func.__name__, "with parameters:", args)
        return
    elif code == NCB_Error:
        raise Exception("Error: unspecific in" + str(func.__name__) + "with parameters:" + str(args))
    elif code == NCB_Timeout:
        raise Exception("Error: comm. timeout in" + str(func.__name__) + "with parameters:" + str(args))
    elif code == NCB_NotConnected:
        raise Exception("Error: not connected")
    elif code == NCB_DriverError:
        raise Exception("Error: driver error")
    elif code == NCB_FileNotFound:
        raise Exception("Error: file not found")
    elif code == NCB_InvalidParam:
        raise Exception("Error: invalid parameter")
    elif code == NCB_DeviceLocked:
        raise Exception("Error: device locked")
    elif code == NCB_NotSpecifiedParam:
        raise Exception("Error: unspec. parameter in" + str(func.__name__) + "with parameters:" + str(args))
    else:
        raise Exception("Error: unknown in" + str(func.__name__) + "with parameters:" + str(args))
    return code


# import dll
anc350v2 = ctypes.WinDLL("C:/qudi_quest-master/hardware/piezo/anc350v2.dll")
# anc350v2 = ctypes.windll.anc350v2

# creates alias for c_int as "Int32" (I really don't know why)
Int32 = ctypes.c_int32


# structure for PositionerInfo to handle positionerCheck return data
class PositionerInfo(ctypes.Structure):
    _fields_ = [("id", ctypes.c_int16), ("locked", ctypes.c_bool)]


# aliases for the strangely-named functions from the dll
positionerAcInEnable = getattr(anc350v2, "PositionerAcInEnable")
positionerAmplitude = getattr(anc350v2, "PositionerStaticAmplitude")
positionerAmplitudeControl = getattr(anc350v2, "PositionerAmplitudeControl")
positionerBandwidthLimitEnable = getattr(anc350v2, "PositionerBandwidthLimitEnable")
positionerCapMeasure = getattr(anc350v2, "PositionerCapMeasure")
positionerCheck = getattr(anc350v2, "PositionerCheck")
positionerClearStopDetection = getattr(anc350v2, "PositionerClearStopDetection")
positionerClose = getattr(anc350v2, "PositionerClose")
positionerConnect = getattr(anc350v2, "PositionerConnect")
positionerGetDeviceInfo = getattr(anc350v2, "PositionerGetDeviceInfo")
positionerDcInEnable = getattr(anc350v2, "PositionerDcInEnable")
positionerDCLevel = getattr(anc350v2, "PositionerDCLevel")
positionerDutyCycleEnable = getattr(anc350v2, "PositionerDutyCycleEnable")
positionerDutyCycleOffTime = getattr(anc350v2, "PositionerDutyCycleOffTime")
positionerDutyCyclePeriod = getattr(anc350v2, "PositionerDutyCyclePeriod")
positionerExternalStepBkwInput = getattr(anc350v2, "PositionerExternalStepBkwInput")
positionerExternalStepFwdInput = getattr(anc350v2, "PositionerExternalStepFwdInput")
positionerExternalStepInputEdge = getattr(anc350v2, "PositionerExternalStepInputEdge")
positionerFrequency = getattr(anc350v2, "PositionerFrequency")
positionerGetAcInEnable = getattr(anc350v2, "PositionerGetAcInEnable")
positionerGetAmplitude = getattr(anc350v2, "PositionerGetAmplitude")
positionerGetBandwidthLimitEnable = getattr(anc350v2, "PositionerGetBandwidthLimitEnable")
positionerGetDcInEnable = getattr(anc350v2, "PositionerGetDcInEnable")
positionerGetDcLevel = getattr(anc350v2, "PositionerGetDcLevel")
positionerGetFrequency = getattr(anc350v2, "PositionerGetFrequency")
positionerGetIntEnable = getattr(anc350v2, "PositionerGetIntEnable")
positionerGetPosition = getattr(anc350v2, "PositionerGetPosition")
positionerGetReference = getattr(anc350v2, "PositionerGetReference")
positionerGetReferenceRotCount = getattr(anc350v2, "PositionerGetReferenceRotCount")
positionerGetRotCount = getattr(anc350v2, "PositionerGetRotCount")
positionerGetSpeed = getattr(anc350v2, "PositionerGetSpeed")
positionerGetStatus = getattr(anc350v2, "PositionerGetStatus")
positionerGetStepwidth = getattr(anc350v2, "PositionerGetStepwidth")
positionerIntEnable = getattr(anc350v2, "PositionerIntEnable")
positionerLoad = getattr(anc350v2, "PositionerLoad")
positionerMoveAbsolute = getattr(anc350v2, "PositionerMoveAbsolute")
positionerMoveAbsoluteSync = getattr(anc350v2, "PositionerMoveAbsoluteSync")
positionerMoveContinuous = getattr(anc350v2, "PositionerMoveContinuous")
positionerMoveReference = getattr(anc350v2, "PositionerMoveReference")
positionerMoveRelative = getattr(anc350v2, "PositionerMoveRelative")
positionerMoveSingleStep = getattr(anc350v2, "PositionerMoveSingleStep")
positionerQuadratureAxis = getattr(anc350v2, "PositionerQuadratureAxis")
positionerQuadratureInputPeriod = getattr(anc350v2, "PositionerQuadratureInputPeriod")
positionerQuadratureOutputPeriod = getattr(anc350v2, "PositionerQuadratureOutputPeriod")
positionerResetPosition = getattr(anc350v2, "PositionerResetPosition")
positionerSensorPowerGroupA = getattr(anc350v2, "PositionerSensorPowerGroupA")
positionerSensorPowerGroupB = getattr(anc350v2, "PositionerSensorPowerGroupB")
positionerSetHardwareId = getattr(anc350v2, "PositionerSetHardwareId")
positionerSetOutput = getattr(anc350v2, "PositionerSetOutput")
positionerSetStopDetectionSticky = getattr(anc350v2, "PositionerSetStopDetectionSticky")
positionerSetTargetGround = getattr(anc350v2, "PositionerSetTargetGround")
positionerSetTargetPos = getattr(anc350v2, "PositionerSetTargetPos")
positionerSingleCircleMode = getattr(anc350v2, "PositionerSingleCircleMode")
positionerStaticAmplitude = getattr(anc350v2, "PositionerStaticAmplitude")
positionerStepCount = getattr(anc350v2, "PositionerStepCount")
positionerStopApproach = getattr(anc350v2, "PositionerStopApproach")
positionerStopDetection = getattr(anc350v2, "PositionerStopDetection")
positionerStopMoving = getattr(anc350v2, "PositionerStopMoving")
positionerTrigger = getattr(anc350v2, "PositionerTrigger")
positionerTriggerAxis = getattr(anc350v2, "PositionerTriggerAxis")
positionerTriggerEpsilon = getattr(anc350v2, "PositionerTriggerEpsilon")
positionerTriggerModeIn = getattr(anc350v2, "PositionerTriggerModeIn")
positionerTriggerModeOut = getattr(anc350v2, "PositionerTriggerModeOut")
positionerTriggerPolarity = getattr(anc350v2, "PositionerTriggerPolarity")
positionerUpdateAbsolute = getattr(anc350v2, "PositionerUpdateAbsolute")

# set error checking & handling
positionerAcInEnable.errcheck = checkError
positionerAmplitude.errcheck = checkError
positionerAmplitudeControl.errcheck = checkError
positionerBandwidthLimitEnable.errcheck = checkError
positionerCapMeasure.errcheck = checkError
positionerClearStopDetection.errcheck = checkError
positionerClose.errcheck = checkError
positionerConnect.errcheck = checkError
positionerDcInEnable.errcheck = checkError
positionerDCLevel.errcheck = checkError
positionerDutyCycleEnable.errcheck = checkError
positionerDutyCycleOffTime.errcheck = checkError
positionerDutyCyclePeriod.errcheck = checkError
positionerExternalStepBkwInput.errcheck = checkError
positionerExternalStepFwdInput.errcheck = checkError
positionerExternalStepInputEdge.errcheck = checkError
positionerFrequency.errcheck = checkError
positionerGetAcInEnable.errcheck = checkError
positionerGetAmplitude.errcheck = checkError
positionerGetBandwidthLimitEnable.errcheck = checkError
positionerGetDcInEnable.errcheck = checkError
positionerGetDcLevel.errcheck = checkError
positionerGetFrequency.errcheck = checkError
positionerGetIntEnable.errcheck = checkError
positionerGetPosition.errcheck = checkError
positionerGetReference.errcheck = checkError
positionerGetReferenceRotCount.errcheck = checkError
positionerGetRotCount.errcheck = checkError
positionerGetSpeed.errcheck = checkError
positionerGetStatus.errcheck = checkError
positionerGetStepwidth.errcheck = checkError
positionerIntEnable.errcheck = checkError
positionerLoad.errcheck = checkError
positionerMoveAbsolute.errcheck = checkError
positionerMoveAbsoluteSync.errcheck = checkError
positionerMoveContinuous.errcheck = checkError
positionerMoveReference.errcheck = checkError
positionerMoveRelative.errcheck = checkError
positionerMoveSingleStep.errcheck = checkError
positionerQuadratureAxis.errcheck = checkError
positionerQuadratureInputPeriod.errcheck = checkError
positionerQuadratureOutputPeriod.errcheck = checkError
positionerResetPosition.errcheck = checkError
positionerSensorPowerGroupA.errcheck = checkError
positionerSensorPowerGroupB.errcheck = checkError
positionerSetHardwareId.errcheck = checkError
positionerSetOutput.errcheck = checkError
positionerSetStopDetectionSticky.errcheck = checkError
positionerSetTargetGround.errcheck = checkError
positionerSetTargetPos.errcheck = checkError
positionerSingleCircleMode.errcheck = checkError
positionerStaticAmplitude.errcheck = checkError
positionerStepCount.errcheck = checkError
positionerStopApproach.errcheck = checkError
positionerStopDetection.errcheck = checkError
positionerStopMoving.errcheck = checkError
positionerTrigger.errcheck = checkError
positionerTriggerAxis.errcheck = checkError
positionerTriggerEpsilon.errcheck = checkError
positionerTriggerModeIn.errcheck = checkError
positionerTriggerModeOut.errcheck = checkError
positionerTriggerPolarity.errcheck = checkError
positionerUpdateAbsolute.errcheck = checkError
# positionerCheck.errcheck = checkError
# positionerCheck returns number of attached devices; gives "comms error" if this is applied, despite working fine

# set argtypes
positionerAcInEnable.argtypes = [Int32, Int32, ctypes.c_bool]
positionerAmplitude.argtypes = [Int32, Int32, Int32]
positionerAmplitudeControl.argtypes = [Int32, Int32, Int32]
positionerBandwidthLimitEnable.argtypes = [Int32, Int32, ctypes.c_bool]
positionerCapMeasure.argtypes = [Int32, Int32, ctypes.POINTER(Int32)]
positionerCheck.argtypes = [ctypes.POINTER(PositionerInfo)]
positionerClearStopDetection.argtypes = [Int32, Int32]
positionerClose.argtypes = [Int32]
positionerConnect.argtypes = [Int32, ctypes.POINTER(Int32)]
positionerDcInEnable.argtypes = [Int32, Int32, ctypes.c_bool]
positionerDCLevel.argtypes = [Int32, Int32, Int32]
positionerDutyCycleEnable.argtypes = [Int32, ctypes.c_bool]
positionerDutyCycleOffTime.argtypes = [Int32, Int32]
positionerDutyCyclePeriod.argtypes = [Int32, Int32]
positionerExternalStepBkwInput.argtypes = [Int32, Int32, Int32]
positionerExternalStepFwdInput.argtypes = [Int32, Int32, Int32]
positionerExternalStepInputEdge.argtypes = [Int32, Int32, Int32]
positionerFrequency.argtypes = [Int32, Int32, Int32]
positionerGetAcInEnable.argtypes = [Int32, Int32, ctypes.POINTER(ctypes.c_bool)]
positionerGetAmplitude.argtypes = [Int32, Int32, ctypes.POINTER(Int32)]
positionerGetBandwidthLimitEnable.argtypes = [Int32, Int32, ctypes.POINTER(ctypes.c_bool)]
positionerGetDcInEnable.argtypes = [Int32, Int32, ctypes.POINTER(ctypes.c_bool)]
positionerGetDcLevel.argtypes = [Int32, Int32, ctypes.POINTER(Int32)]
positionerGetFrequency.argtypes = [Int32, Int32, ctypes.POINTER(Int32)]
positionerGetIntEnable.argtypes = [Int32, Int32, ctypes.POINTER(ctypes.c_bool)]
positionerGetPosition.argtypes = [Int32, Int32, ctypes.POINTER(Int32)]
positionerGetReference.argtypes = [Int32, Int32, ctypes.POINTER(Int32), ctypes.POINTER(ctypes.c_bool)]
positionerGetReferenceRotCount.argtypes = [Int32, Int32, ctypes.POINTER(Int32)]
positionerGetRotCount.argtypes = [Int32, Int32, ctypes.POINTER(Int32)]
positionerGetSpeed.argtypes = [Int32, Int32, ctypes.POINTER(Int32)]
positionerGetStatus.argtypes = [Int32, Int32, ctypes.POINTER(Int32)]
positionerGetStepwidth.argtypes = [Int32, Int32, ctypes.POINTER(Int32)]
positionerIntEnable.argtypes = [Int32, Int32, ctypes.c_bool]
positionerLoad.argtypes = [Int32, Int32, ctypes.POINTER(ctypes.c_char)]
positionerMoveAbsolute.argtypes = [Int32, Int32, Int32, Int32]
positionerMoveAbsoluteSync.argtypes = [Int32, Int32]
positionerMoveContinuous.argtypes = [Int32, Int32, Int32]
positionerMoveReference.argtypes = [Int32, Int32]
positionerMoveRelative.argtypes = [Int32, Int32, Int32, Int32]
positionerMoveSingleStep.argtypes = [Int32, Int32, Int32]
positionerQuadratureAxis.argtypes = [Int32, Int32, Int32]
positionerQuadratureInputPeriod.argtypes = [Int32, Int32, Int32]
positionerQuadratureOutputPeriod.argtypes = [Int32, Int32, Int32]
positionerResetPosition.argtypes = [Int32, Int32]
positionerSensorPowerGroupA.argtypes = [Int32, ctypes.c_bool]
positionerSensorPowerGroupB.argtypes = [Int32, ctypes.c_bool]
positionerSetHardwareId.argtypes = [Int32, Int32]
positionerSetOutput.argtypes = [Int32, Int32, ctypes.c_bool]
positionerSetStopDetectionSticky.argtypes = [Int32, Int32, ctypes.c_bool]
positionerSetTargetGround.argtypes = [Int32, Int32, ctypes.c_bool]
positionerSetTargetPos.argtypes = [Int32, Int32, Int32, Int32]
positionerSingleCircleMode.argtypes = [Int32, Int32, ctypes.c_bool]
positionerStaticAmplitude.argtypes = [Int32, Int32]
positionerStepCount.argtypes = [Int32, Int32, Int32]
positionerStopApproach.argtypes = [Int32, Int32]
positionerStopDetection.argtypes = [Int32, Int32, ctypes.c_bool]
positionerStopMoving.argtypes = [Int32, Int32]
positionerTrigger.argtypes = [Int32, Int32, Int32, Int32]
positionerTriggerAxis.argtypes = [Int32, Int32, Int32]
positionerTriggerEpsilon.argtypes = [Int32, Int32, Int32]
positionerTriggerModeIn.argtypes = [Int32, Int32]
positionerTriggerModeOut.argtypes = [Int32, Int32]
positionerTriggerPolarity.argtypes = [Int32, Int32, Int32]
positionerUpdateAbsolute.argtypes = [Int32, Int32, Int32]
