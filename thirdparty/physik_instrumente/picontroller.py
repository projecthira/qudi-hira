# -*- coding: utf-8 -*-

"""
This file contains the PI Piezo hardware module for Qudi
through offical python moudle "PIPython" created by PI.

Copyright (c) 2019 diamond2nv@GitHub with GPLv3 License.

#1.

Physik Instrumente (PI) General Command Set 2 (GCS 2),
"for all controllers".

PIPython is a collection of Python modules to access a PI
device and process GCS data.
It can be used with Python 3.4+ (3.6.5) on Windows, Linux and
OS X and without the GCS DLL also on any other platform.

This module file is tested with PIPython Version: 1.3.9.40

PIPython Installation:
---------------------
Zip of PIPython for "python start.py install" should be in
the CD with new PI controller device.

PIPython Copyright (c) General Software License Agreement
of Physik Instrumente (PI) GmbH & Co. KG. See more at
<https://www.physikinstrumente.com/en/products/motion-control-software/programming/>

You can connect via these interfaces with the according methods.

    USB: EnumerateUSB(mask='')
    TCPIP: EnumerateTCPIPDevices(mask='')

    RS-232: ConnectRS232(comport, baudrate)
    USB: ConnectUSB(serialnum)
    TCP/IP: ConnectTCPIP(ipaddress, ipport=50000)
    TCP/IP: ConnectTCPIPByDescription(description)
    NI GPIB: ConnectNIgpib(board, device)
    PCI board: Connect(board)

Unknown PI devices:
------------------

When you call GCSDevice with the controller name the
according GCS DLL is chosen automatically. For unknown
devices you can specify a dedicated GCS v2 DLL instead:

from pipython import GCSDevice
pidevice = GCSDevice(gcsdll='PI_GCS2_DLL.dll')


#2.

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

Qudi Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

# import numpy as np
# import ctypes
import time

from collections import OrderedDict

# PI Stage
try:
    from pipython import GCSDevice
    from pipython import GCSError, gcserror
    # from pipython import pitools, datarectools
except ModuleNotFoundError as err:
    raise
# To install PIPython package, ref: https://github.com/Ulm-IQO/qudi/issues/503

pidevice = GCSDevice()

from core.module import Base
from core.configoption import ConfigOption

# from interface.confocal_scanner_interface import ConfocalScannerInterface
# TODO：Trigger-Gate Confocal Scanner （Need PI Controller Set TTL Sync Output
# to NI Card or Time Tagger or PYNQ Z2...)

from interface.motor_interface import MotorInterface


class PiezoStagePI_PyGCS2(Base, MotorInterface):
    """ This is the hardware module for the PI GCSdevice in Qudi,
        driven by PI offical python moudle "PIPython",
        that can support almost all PI Piezo Stage Controller,
        such as: E-516, E-727...

    !!!!!! PI GCS V2 DEVICES ONLY!!!!!!

    See PIPython for details, should be in the CD with new PI controller device.

    unstable: diamond2nv@GitHub

    This is intended as Confocal PI Piezo Scanner Hardware module
    that can be connected to confocal_scanner_motor_interfuse logic.

    If communication speed like MOV() for motor scanner is an issue,
    you can disable error checking:
    # pidevice.errcheck = False

    Example config for copy-paste:

    piezo_stage_nanos:
        module.Class: 'motor.piezo_stage_pi_py_gcs2.PiezoStagePI_PyGCS2'
        pi_controller_mask: 'E-727'
        pi_piezo_stage_mask: 'P-563'

        first_axis_label: 'x'
        second_axis_label: 'y'
        third_axis_label: 'z'

        first_axis_ID: '1'
        second_axis_ID: '2'
        third_axis_ID: '3'

        first_min: 0e-6 # in m
        first_max: 300e-6 # in m
        second_min: 0e-6 # in m
        second_max: 300e-6 # in m
        third_min: 0e-6 # in m
        third_max: 300e-6 # in m

        first_axis_step: 1e-9 # in m
        second_axis_step: 1e-9 # in m
        third_axis_step: 1e-9 # in m


    """

    _modtype = 'PiezoStagePI_PyGCS2'
    _modclass = 'hardware'

    # the flag for connected to controller: such as E-727
    _has_connect_piezo_controller = False
    # Need to communicate with piezo controller to confirm enable or not.
    _has_is_moving = False
    _has_move_abs = False
    _has_move_rel = False
    _has_abort = False
    _has_get_pos = False
    _has_calibrate = False
    _has_get_velocity = False
    _has_set_velocity = False

    # default servo on for xyz
    _default_servo_state = [True, True, True]

    # whether each axis range is smaller than its PI GCS range
    _has_diff_constrains = False

    unit_factor = 1e6  # This factor converts the values given in m to um.
    ### !!!!! Attention the units can be changed by setunit

    # config options, like other motor hardware
    _pi_controller_mask = ConfigOption('pi_controller_mask', 'E-727', missing='warn')
    _pi_piezo_stage_mask = ConfigOption('pi_piezo_stage_mask', 'P-563', missing='warn')

    _first_axis_label = ConfigOption('first_axis_label', 'x', missing='warn')
    _second_axis_label = ConfigOption('second_axis_label', 'y', missing='warn')
    _third_axis_label = ConfigOption('third_axis_label', 'z', missing='warn')
    # _fourth_axis_label = ConfigOption('fourth_axis_label', 'a', missing='warn')
    _first_axis_ID = ConfigOption('first_axis_ID', '1', missing='warn')
    _second_axis_ID = ConfigOption('second_axis_ID', '2', missing='warn')
    _third_axis_ID = ConfigOption('third_axis_ID', '3', missing='warn')
    # _fourth_axis_ID = ConfigOption('fourth_axis_ID', '4', missing='warn')

    _min_first = ConfigOption('first_min', 0e-6, missing='warn')
    _max_first = ConfigOption('first_max', 100e-6, missing='warn')
    _min_second = ConfigOption('second_min', 0e-6, missing='warn')
    _max_second = ConfigOption('second_max', 100e-6, missing='warn')
    _min_third = ConfigOption('third_min', 0e-6, missing='warn')
    _max_third = ConfigOption('third_max', 100e-6, missing='warn')
    # _min_fourth = ConfigOption('fourth_min', 0e-6, missing='warn')
    # _max_fourth = ConfigOption('fourth_max', 0e-6, missing='warn')

    # FIXME:
    # _objectlens_axis_lable = ConfigOption('objectlens_axis_lable', 'z', missing='warn')
    # canbe changed by set range
    # min_softlim_4_objectlens_axis = ConfigOption('min_softlim_range_4_objectlens_axis', 0e-6, missing='warn')
    # max_softlim_4_objectlens_axis = ConfigOption('max_softlim_range_4_objectlens_axis', 300e-6, missing='warn')

    step_first_axis = ConfigOption('first_axis_step', 1e-9, missing='warn')
    step_second_axis = ConfigOption('second_axis_step', 1e-9, missing='warn')
    step_third_axis = ConfigOption('third_axis_step', 1e-9, missing='warn')
    # step_fourth_axis = ConfigOption('fourth_axis_step', 1e-9, missing='warn')

    # _vel_min_first = ConfigOption('vel_first_min', 1e-9, missing='warn')
    # _vel_max_first = ConfigOption('vel_first_max', 1e-3, missing='warn')
    # _vel_min_second = ConfigOption('vel_second_min', 1e-9, missing='warn')
    # _vel_max_second = ConfigOption('vel_second_max', 1e-3, missing='warn')
    # _vel_min_third = ConfigOption('vel_third_min', 1e-9, missing='warn')
    # _vel_max_third = ConfigOption('vel_third_max', 1e-3, missing='warn')
    # _vel_min_fourth = ConfigOption('vel_fourth_min', 1e-5, missing='warn')
    # _vel_max_fourth = ConfigOption('vel_fourth_max', 5e-2, missing='warn')

    _vel_step_first = ConfigOption('vel_first_axis_step', 2e-6, missing='warn')
    _vel_step_second = ConfigOption('vel_second_axis_step', 2e-6, missing='warn')
    _vel_step_third = ConfigOption('vel_third_axis_step', 2e-6, missing='warn')

    # _vel_step_fourth = ConfigOption('vel_fourth_axis_step', 2e-6, missing='warn')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # Open connection with PI Controller through PIPython module.
    def on_activate(self):
        """ Initialise and activate the hardware module.

            @return: error code (0:OK, -1:error)
        """
        try:
            self._configured_constraints = self.get_constraints()
            # FIXME: use this logic instead of PI GCS error to threshold commond move_abs()
            pidevice.errcheck = True

            # FIXME This will trigger a GUI, shoud be taken by Qudi GUI.
            # pidevice.InterfaceSetupDlg('pidevice_token')
            # pidevice = GCSDevice('E-727')
            # pidevice.ConnectTCPIP('192.168.178.42')
            try:
                devices = pidevice.EnumerateUSB(mask=self._pi_controller_mask)
                self.log.warning("PI ConnectUSB Devices found:" + str(devices))
                if len(devices) is not 0:
                    pidevice.ConnectUSB(devices[0])
                    self._has_connect_piezo_controller = True
                else:
                    try:
                        devices = pidevice.EnumerateTCPIPDevices(mask=self._pi_controller_mask)
                        self.log.warning("PI ConnectTCPIP Devices found:" + str(devices))
                        if len(devices) is not 0:
                            pidevice.ConnectTCPIPByDescription(devices[0])
                            self._has_connect_piezo_controller = True
                        else:
                            self.log.error("NOT Found the PI Devices: {} by either USB or TCPIP: ".format(
                                self._pi_controller_mask))
                            raise ValueError("NOT Found the PI Devices.")
                    except:
                        pass
            except:
                pass

            if self._has_connect_piezo_controller:
                device_name = pidevice.qIDN()
                self._set_servo_state(True)
                self.log.warning('Activate Motor and Set servo on for PI Controller = {}'.format(device_name.strip()))
            else:
                raise ("Not Connect PI Controller = {} !".format(self._pi_controller_mask))

        except GCSError as exc:
            self.log.error("PI GCSError: " + str(GCSError(exc)))
            return -1
            # raise GCSError(exc)
        except IndexError:
            self.log.error("Not Found PI Controller = {} !".format(self._pi_controller_mask))
            return -1
        except Exception as e:
            self.log.error("Hardware Not Activated: PI Devices!")
            return -1

        if self._has_connect_piezo_controller:
            try:
                self._has_move_abs = pidevice.HasMOV()
                self._has_get_pos = pidevice.HasqPOS()
                # above is important to logic interfuse motor scanner

                # Hardware module xyz range self-auto-check.
                self._has_diff_constrains = self._has_diff_constrains_check()

                # Safe range init set by PI GCS for one axis with object lens.
                self._set_safe_range4objectlens_axis()

                if self._has_move_abs and self._has_get_pos:
                    try:
                        self._has_move_rel = pidevice.HasMVR()
                        self._has_abort = pidevice.HasStopAll()
                        self._has_is_moving = pidevice.HasIsMoving()
                        self._has_calibrate = pidevice.HasATZ()
                        self._has_get_velocity = pidevice.HasqVEL()
                        self._has_set_velocity = pidevice.HasVEL()
                        # above is not as important as MOV() and qPOS() in motor-scanner-interfuse
                    except GCSError as exc:
                        self.log.warning("PI GCSError: " + str(GCSError(exc)))
                        pass
                    finally:
                        pidevice.errcheck = False
                        # TODO: If communication speed like MOV() for motor scanner is an issue,
                        # can disable error checking.
                        self.log.debug("PI PZT is ready to go.")
                        return 0
                else:
                    self.log.error("PI Device has no MOV() or qPOS() func !")
                    return -1

            except:
                self.log.error("PI GCSError: " + str(GCSError(exc)))
                return -1

    def on_deactivate(self):
        """ Deinitialise and deactivate the hardware module.

            @return: error code (0:OK, -1:error)
        """
        # TODO add def shutdown(self) to set Votage=0 V for safety.
        # self._set_servo_state(False)
        # If not shutdown, keep servo on to stay on target.
        try:
            pidevice.errcheck = True
            pidevice.CloseConnection()
            self.log.warning("PI Device has been closed connection !")
            return 0
        except GCSError as exc:
            self.log.error("PI GCSError: " + str(GCSError(exc)))
            return -1

    def get_constraints(self):
        """ Retrieve the hardware constrains from the motor device.

        Provides all the constraints for the xyz stage  and rot stage (like total
        movement, velocity, ...)
        Each constraint is a tuple of the form
            (min_value, max_value, stepsize)

            @return dict constraints : dict with constraints for the device
        """
        # TODO get constraints auto by gcs

        constraints = OrderedDict()

        axis0 = {'label': self._first_axis_label,
                 'ID': self._first_axis_ID,
                 'unit': 'm',
                 'ramp': None,
                 'pos_min': self._min_first,
                 'pos_max': self._max_first,
                 'pos_step': self.step_first_axis,
                 'vel_min': None,
                 'vel_max': None,
                 'vel_step': None,
                 'acc_min': None,
                 'acc_max': None,
                 'acc_step': None}

        axis1 = {'label': self._second_axis_label,
                 'ID': self._second_axis_ID,
                 'unit': 'm',
                 'ramp': None,
                 'pos_min': self._min_second,
                 'pos_max': self._max_second,
                 'pos_step': self.step_second_axis,
                 'vel_min': None,
                 'vel_max': None,
                 'vel_step': None,
                 'acc_min': None,
                 'acc_max': None,
                 'acc_step': None}

        axis2 = {'label': self._third_axis_label,
                 'ID': self._third_axis_ID,
                 'unit': 'm',
                 'ramp': None,
                 'pos_min': self._min_third,
                 'pos_max': self._max_third,
                 'pos_step': self.step_third_axis,
                 'vel_min': None,
                 'vel_max': None,
                 'vel_step': None,
                 'acc_min': None,
                 'acc_max': None,
                 'acc_step': None}

        # assign the parameter container for x to a name which will identify it
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1
        constraints[axis2['label']] = axis2
        # constraints[axis3['label']] = axis3

        return constraints

    def move_rel(self, param_dict):
        """ Move stage relatively, positive or negative value.And if step is
        too small, PI GCS will ignore.#TODO:check this in PI GCS.
            @param dict param_dict : dictionary, which passes all the relevant
                                     parameters, which should be changed. Usage:
                                     {'axis_label': <the-abs-pos-value>}.
                                     'axis_label' must correspond to a label given
                                     to one of the axis.
                                     The values for the axes are in meter,
                                     the value for the rotation is in degrees.

            @return dict param_dict : dictionary with the current magnet position
        """
        pos = {}

        # get origin pos()
        try:
            self.on_target()
            pos = self.get_pos([param_dict.keys()])
        except GCSError as exc:
            self.log.warning("PI GCSError: " + str(GCSError(exc)))
            raise

        if self._has_move_rel:
            # if config range is smaller than PI GCS range
            if self._has_diff_constrains:
                # if target is not in the config range
                if self._move_rel_range_check(pos, param_dict) is False:
                    self.log.warning('''Cannot make the movement of the axis, 
                    out config range! Command ignore.''')
                    try:
                        # self.abort()
                        self.on_target()
                        pos = self.get_pos([param_dict.keys()])
                    except GCSError as exc:
                        self.log.debug("PI GCSError: " + str(GCSError(exc)))
                        pass
                    except:
                        self.log.warning("PI GCS move_rel / MVR failed !")
                        pass
                    finally:
                        return pos

            # move rel
            try:
                # self.log.debug("Send MVR to hardware PI before conver: " + str(param_dict))
                new_param_dict = self._axis_dict_send(param_dict)
                # self.log.debug("Send MVR to hardware PI actually: :" + str(new_param_dict))
                pidevice.MVR(new_param_dict)
                # Send str upper + um: 1 2 3

                try:
                    self.on_target()
                    pos = self.get_pos([param_dict.keys()])
                except:
                    pass
            except GCSError as exc:
                self.log.error("PI GCSError(MVR): " + str(GCSError(exc)))
            except:
                self.log.error("PI GCS move_rel / MVR failed !")
            finally:
                return pos
        else:
            self.log.warning('PI GCS MVR Function not yet implemented')

        return pos

    def move_abs(self, param_dict):
        """ Move the stage to an absolute position

        @param dict param_dict : dictionary, which passes all the absolute
                                 parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
                                 The values for the axes are in meter,
                                 the value for the rotation is in degrees.

        @return dict param_dict : dictionary with the current axis position
        """
        # pidevice.MOV or pidevice.MVT is better ?
        if self._has_move_abs:
            # if config range is smaller than PI GCS range
            if self._has_diff_constrains:
                # if target is not in the config range
                if self._move_abs_range_check(param_dict) is False:
                    self.log.warning('''Cannot make the movement of the axis, 
                    out config range! Command ignore.''')
                    try:
                        # self.abort()
                        self.on_target()
                        pos = self.get_pos([param_dict.keys()])
                        return pos
                    except GCSError as exc:
                        self.log.debug("PI GCSError: " + str(GCSError(exc)))
                        raise
                    except (KeyboardInterrupt, SystemExit):
                        # user wants to quit
                        self.log.warning("User wants to quit: keyboard interrupt or system exit!")
                        pass
                    except Exception:
                        self.log.error("PI move_abs / MOV failed !")
                        # FIXME:
                        raise

            # move abs: most used in scan, must be very fast to run python.
            try:
                # self.log.debug("Send MOV to hardware PI before conver: " + str(param_dict))
                new_param_dict = self._axis_dict_send(param_dict)
                # self.log.debug("Send MOV to hardware PI actually: " + str(new_param_dict))
                pidevice.MOV(new_param_dict)
                # Send str upper + um: 1 2 3
                return param_dict
            except GCSError as exc:
                self.log.debug("PI GCSError(MOV): " + str(GCSError(exc)))
                pass
                # FIXME: if move abs failed, return get position ?
                # but when xy is ok and z is error, still goto xy ?
                return param_dict
            except (KeyboardInterrupt, SystemExit):
                # user wants to quit
                self.log.warning("User wants to quit: keyboard interrupt or system exit!")
                # pass
                self.abort()
                pos = self.get_pos([param_dict.keys()])
                return pos
            except Exception:
                self.log.error("PI move_abs / MOV failed !")
                raise

        else:
            self.log.warning('PI GCS MOV Function not yet implemented')
            return param_dict

    def abort(self):
        """ Stop movement of the stage

        @return int: error code (0:OK, -1:error)
        """
        # Not pidevice.SystemAbort(): will cause halt or reboot.
        if self._has_abort:
            if self._has_is_moving:
                if pidevice.IsMoving:
                    try:
                        pidevice.StopAll()
                        # pidevice.errcheck = True
                        self.log.debug("PI Device has aborted and stoped all move! ")
                        return 0
                    except GCSError as exc:
                        self.log.error("PI GCSError(StopAll): " + str(GCSError(exc)))
                        return -1
                    except (KeyboardInterrupt, SystemExit):
                        # user wants to quit
                        self.log.warning("User wants to quit: keyboard interrupt or system exit!")
                        pidevice.StopAll()
                    except Exception:
                        self.log.error("Hardware PI cannot abort move !")
                        return -1
                else:
                    # if not moving, PI stage is stoped already.
                    self.log.warning("PI Device has aborted and stoped all move! ")
                    return 0
            else:
                try:
                    pidevice.StopAll()
                    # pidevice.errcheck = True
                    self.log.debug("PI Device has aborted and stoped all move! ")
                    return 0
                except GCSError as exc:
                    self.log.error("PI GCSError: " + str(GCSError(exc)))
                    # raise GCSError(exc)
                    # FIXME
                    return -1
                except (KeyboardInterrupt, SystemExit):
                    # user wants to quit
                    self.log.warning("User wants to quit: keyboard interrupt or system exit!")
                    pidevice.StopAll()
                except Exception:
                    self.log.error("Hardware PI cannot abort move !")
                    return -1
        else:
            self.log.warning('PI System Abort/StopAll Function not yet implemented')
            return 0

    def get_pos(self, param_list=None):
        """ Get the current position of the stage axis

        @param list param_list : optional, if a specific position of an axis
                                 is desired, then the labels of the needed
                                 axis should be passed in the param_list.
                                 If nothing is passed, then the positions of
                                 all axes are returned.

        @return dict param_dict : with keys being the axis labels and item the current
                                  position.
        """

        param_dict = {}
        if self._has_get_pos:
            new_param_list = self._axis_label_conver2pipy(param_list)
            try:
                param_dict_get = pidevice.qPOS(new_param_list)
                # self.log.debug("Hardware get before conver :" + str(param_dict))

                # axis dict get conversion
                param_dict = self._axis_dict_get(param_dict_get)
                # self.log.debug("Hardware get :" + str(param_dict))
                return param_dict
            except GCSError as exc:
                self.log.debug("PI GCSError(qPOS): " + str(GCSError(exc)))
                try:
                    self.on_target()
                    # try wait for on target, then get positions.
                    param_dict_get = pidevice.qPOS(new_param_list)
                    param_dict = self._axis_dict_get(param_dict_get)
                    return param_dict
                except (KeyboardInterrupt, SystemExit):
                    # user wants to quit
                    self.log.warning("User wants to quit: keyboard interrupt or system exit!")
                    return param_dict
                except Exception:
                    raise
            except:
                self.log.error("Hardware get_pos failed !")
                raise
        else:
            self.log.warning('PI qPOS() Function not yet implemented')
            return param_dict

    def on_target(self, param_list=None):
        """ Stage will move all axes to targets
        and waits until the motion has finished.
        Maybe useful in scan line began.

        @param list param_list : optional, if a specific status of an axis
                                 is desired, then the labels of the needed
                                 axis should be passed in the param_list.
                                 If nothing is passed, then from each axis the
                                 status is asked.

        @return int: error code (0:OK, -1:error)
        """
        if param_list is None:
            for i in range(10):
                # if xyz not all on target:
                if not all(list(pidevice.qONT().values())):
                    time.sleep(0.1)
                    i += 1
                    if i >= 9:
                        return -1
                        # over time
                else:
                    # break and return OK
                    return 0

        else:
            self.log.warning('PI qONT(param_list) not yet implemented, use qONT() only, for now.')
            time.sleep(0.1)
            return 0

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list : optional, if a specific status of an axis
                                 is desired, then the labels of the needed
                                 axis should be passed in the param_list.
                                 If nothing is passed, then from each axis the
                                 status is asked.

        @return dict : with the axis label as key and the status number as item.
            The meaning of the return value is:
            Bit 0: Ready
            Bit 1: On target
            Bit 2: Reference drive active
            Bit 3: Joystick ON --- pidevice.qJON #TODO
            Bit 4: Macro running
            Bit 5: Motor OFF
            Bit 6: Brake ON
            Bit 7: Drive current active
        """
        # TODO
        self.log.info('Not yet implemented for this hardware')

    def calibrate(self, param_list=None):
        """ Calibrate the stage. PI GCS ATZ() will move axes to their whole range, careful !
        NOT recommend to do ATZ by this function, use PI Software instead.

        @param dict param_list : param_list: optional, if a specific calibration
                                 of an axis is desired, then the labels of the
                                 needed axis should be passed in the param_list.
                                 If nothing is passed, then all connected axis
                                 will be calibrated.

        After calibration the stage moves to home position which will be the
        zero point for the passed axis.

        @return dict pos : dictionary with the current position of the axis
        """

        param_dict = {}

        if self._has_calibrate:
            try:
                self.abort()
                pidevice.errcheck = True
                pidevice.ATZ(axes=[1, 2])
                # PI Piezo Auto To Zero Calibration, just do it after power shutdown.
                # PI GCS ATZ() will move axes to their whole range, Careful !
                # TODO: NOT recommend to do ATZ by this function, use PI Software instead.
                time.sleep(10.0)
                # has ATZ(), also should has qATZ()
                if pidevice.qATZ(axes=[1]) and pidevice.qATZ(axes=[2]):
                    param_dict = self.get_pos([param_dict.keys()])
                    return param_dict
                else:
                    raise ValueError("PI Auto To Zero Function not succeed !")
            except GCSError as exc:
                self.log.error("PI GCSError(ATZ or qATZ): " + str(GCSError(exc)))
                # raise GCSError(exc)
                raise
            except (KeyboardInterrupt, SystemExit):
                # user wants to quit
                self.log.warning("User wants to quit: keyboard interrupt or system exit!")
                raise
            except Exception:
                raise

        else:
            self.log.warning('PI Auto To Zero Function not yet implemented')
            return param_dict

    def get_velocity(self, param_list=None):
        """ Get the current velocity for all connected axes in m/s.

            @param list param_list : optional, if a specific velocity of an axis
                                     is desired, then the labels of the needed
                                     axis should be passed as the param_list.
                                     If nothing is passed, then from each axis the
                                     velocity is asked.

            @return dict : with the axis label as key and the velocity as item.
        """
        # TODO
        # param_dict = {}
        # pidevice.qVEL(param_dict)
        self.log.warning('PI get velocity function not yet implemented for this stage')

    def set_velocity(self, param_dict):
        """ Write new value for velocity in m/s.

        @param dict param_dict : dictionary, which passes all the relevant
                                 parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.

        @return dict param_dict2 : dictionary with the updated axis velocity
        """
        # TODO
        # pidevice.VCO axis is "on"
        # pidevice.VEL(param_dict)
        self.log.warning('PI set velocity function not yet implemented for this hardware')

    ########################## internal methods ##################################

    def _set_servo_state(self, to_state=None):
        """ Set the servo state (internal method)

            @param bool to_state : desired state of the servos,
                                   default servo state is True
        """
        servo_state = self._default_servo_state

        axis_list = ['1', '2', '3']

        if to_state is True or False:
            servo_state = [to_state, to_state, to_state]
        else:
            servo_state = self._default_servo_state
            # default servo on
            self.log.warning("""PI set servo state value None! 
            Shoud be True or False. Set to default servo state.""")

        try:
            pidevice.SVO(axis_list, servo_state)
        except:
            self.log.error("PI XYZ axis servo on failed!")

    def _axis_dict_send(self, param_dict):
        """ Set the capitalization axis label to GCS command format.
        #TODO: Maybe not necessary for PIPython module

        @param dict param_dict : dictionary, which passes all the relevant
                                 parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """

        new_dict = {1: 0.0, 2: 0.0, 3: 0.0}
        for i, j in param_dict.items():
            if i is 'x':
                new_dict[1] = j * self.unit_factor
            elif i is 'y':
                new_dict[2] = j * self.unit_factor
            elif i is 'z':
                new_dict[3] = j * self.unit_factor
            elif i is 'a':
                # TODO: fourth axis
                pass
                # new_dict[4] = j * self.unit_factor
            else:
                # self.log.debug("PI send axis label to conver :" + str(i))
                raise ("PI send axis label no found ! Can't conver label.")
            # new_dict[i.upper()] = j * self.unit_factor
            # str upper: X Y Z A
            # unit conversion from communication: m to um
        return new_dict

    def _axis_dict_get(self, param_dict):
        """ Set the capitalization axis label to str lower().

        @param dict param_dict : dictionary, which passes all the relevant
                                 parameters, which should be changed. Usage:
                                 {'axis_label': <the-velocity-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
        """
        new_dict = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'a': 0.0}
        for i, j in param_dict.items():
            if i is '1':
                new_dict['x'] = j / self.unit_factor
            elif i is '2':
                new_dict['y'] = j / self.unit_factor
            elif i is '3':
                new_dict['z'] = j / self.unit_factor
            elif i is '4':
                # TODO: fourth axis
                new_dict['a'] = j / self.unit_factor
            else:
                # self.log.debug("PI get axis label" + str(i))
                raise ("PI get axis label no found ! Can't conver label.")
            # new_dict[i.upper()] = j / self.unit_factor

            # str lower: x y z a
            # unit conversion from communication: um to m

        return new_dict

    def _axis_label_conver2pipy(self, param_list=None):
        """Set the capitalization axis label to GCS command format.
        @param list param_list : optional, if a specific position of an axis
                                 is desired, then the labels of the needed
                                 axis should be passed in the param_list.
                                 If nothing is passed, then the lables of
                                 all axes are returned.
                                 ['1','2','3']
        """
        conver_dict = {'x': '1', 'y': '2', 'z': '3'}
        new_param_list = list()
        if param_list is not None:
            for i in param_list:
                new_param_list.append(conver_dict[i])
        if len(new_param_list) is 0:
            return ['1', '2', '3']
        else:
            return new_param_list

    # FIXME: maybe not needed for PI GCS, though it will check again.
    # But when config constraints smaller than PI GCS range
    # check, it will became important. Condition like axis
    # with object lens.
    def _move_abs_range_check(self, param_dict):
        """Check the send move_abs within the config range,
        NOT needed for PI GCS, add this will increase spending time.
        @param dict param_dict : dictionary, which passes all the absolute
                                 parameters, which should be changed. Usage:
                                 {'axis_label': <the-abs-pos-value>}.
                                 'axis_label' must correspond to a label given
                                 to one of the axis.
                                 The values for the axes are in meter,
                                 the value for the rotation is in degrees.

        @return bool : True or False. False mean target out of config.
        """
        # TODO: if range is smaller than PI GCS range.
        # if self._has_diff_constrains:

        # constraints = self._configured_constraints

        return True

    def _move_rel_range_check(self, position_dict, param_dict):
        """Check the send move_rel within the config range,
        NOT needed for PI GCS, add this will increase spending time.
        if step is too small, PI GCS will ignore.#TODO:check this in PI GCS.
            @param dict position_dict : dictionary with the current stage position

            @param dict param_dict : dictionary, which passes all the relevant
                                     parameters, which should be changed. Usage:
                                     {'axis_label': <the-abs-pos-value>}.
                                     'axis_label' must correspond to a label given
                                     to one of the axis.

            @return bool: True or False. False mean target out of config.
        """
        # TODO: if range is smaller than PI GCS range.
        # if self._has_diff_constrains:

        # constraints = self._configured_constraints

        return True

    def _has_diff_constrains_check(self):
        """#whether each axis range is smaller than its PI GCS range.
        bool dict flage:_has_diff_constrains will be True.
        To enable hardware-module pre check than PI GCS
        for the axis move to target value.
                             set enable?
                             range pzt hardware?
                             is 'P-563' ?
                             if larger, auto-reset?
        @return True or False
        """
        # TODO
        # constraints = self._configured_constraints
        return False

    def _set_safe_range4objectlens_axis(self, axis_lable=None):
        """Set safely PI GCS solft range limitation to PZT axis with object lens
        usually z axis.And then, _has_diff_constrains=False,needed for xy scan,
        can run move-abs hardware module faster.
        @axis_lable :   get from config,now it is only one
                        axis with all object lens,usually is z.
                        question PZT controller:

        @return int: error code (0:OK, -1:error)
        """
        # TODO: needed for using command inerface in stand alone Jupyter(Qudi).
        # FIXME: Well, set safe range for z, and then, _has_diff_constrains=False,
        # needed for xy scan, running move-abs hardware module faster
        # self._has_diff_constrains_check()
        # range config now?
        # range safe config now?
        # --->the smallest one----intersection---AND: math logic
        return 0
