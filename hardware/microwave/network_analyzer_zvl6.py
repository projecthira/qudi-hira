# -*- coding: utf-8 -*-
"""
This file contains the Qudi hardware module to read the Rohde & Schwarz ZVL6 Network Analyzer.
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
along with Qudi. If not, see <https://www.gnu.org/licenses/>.

Copyright (c) 2020 Dinesh Pinto. See the COPYRIGHT.txt file at the
top-level directory of this distribution and at
<https://github.com/projecthira/qudi-hira/>
"""

import time
from typing import Tuple
from core.module import Base
from core.configoption import ConfigOption

import numpy as np
from RsInstrument import RsInstrument


class NetworkAnalyzerZVL6(Base):
    _zvl_visa_address = ConfigOption('zvl_visa_address', missing='error')
    instr = None

    def on_activate(self):
        self.instr = RsInstrument(self._zvl_visa_address)
        self.log.info(f"Success! Connected to {self.instr.query_str('*IDN?')}")

    def on_deactivate(self):
        self.instr.close()

    @staticmethod
    def convert_str_to_float_list(string: str):
        return list(map(float, string.split(",")))

    def get_trace(self, points: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
        self.log.info("Measuring trace...")

        self.instr.write_str(f'SWE:POIN {points}')
        time.sleep(1.5)

        self.instr.write_str('CALC:FORM MLOG; :FORM ASCII; FORM:DEXP:SOUR FDAT')
        time.sleep(1.5)

        frequency = self.instr.query_str('TRAC:STIM? CH1DATA')
        power = self.instr.query_str('TRAC? CH1DATA')

        frequency = np.array(self.convert_str_to_float_list(frequency))
        power = np.array(self.convert_str_to_float_list(power))

        return frequency, power
