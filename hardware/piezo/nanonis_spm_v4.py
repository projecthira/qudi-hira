# -*- coding: utf-8 -*-
__author__ = "Dinesh Pinto"
__email__ = "d.pinto@fkf.mpg.de"
"""
This file contains the Nanonis SPM hardware module for Qudi
through official LabView VI files from SPECS. 

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
from core.util.modules import get_main_dir

import socket


class NanonisSPMv4(Base):
    """Provides software backend to the Nanonis via Python.
    """

    #_host = ConfigOption('host', default='localhost', missing='error')
    _vi_base_path = ConfigOption('vi_base_path',
                                 default=os.path.join(get_main_dir(), 'thirdparty', 'Nanonis Prog Interface'),
                                 missing='error')
    _host = 'localhost'
    #_port = ConfigOption('port', default=3353, missing='error')
    _port = 3364

    def on_activate(self):
        try:
            self.inst = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.inst.connect((self._host, self._port))
            return 0
        except Exception as exc:
            self.log.error("Error during connection to Nanonis {}".format(exc))
            return 1

    def on_deactivate(self):
        self.inst.shutdown(2)
        self.inst.close()
        return 0

    def _communicate(self, command):
        full_command = os.path.join(self._vi_base_path, command)
        self.inst.send(full_command.encode())
        reply = self.inst.recv(1024).decode()
        return reply

    def get_scan_properties(self):
        subfolder_path = 'Scan'
        fname = 'Scan GetProperties.vi'
        responce = self._communicate(os.path.join(subfolder_path, fname))
        print(responce)
