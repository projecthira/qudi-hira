import csv
import time

from typing import Tuple
import numpy as np
import visa
from RsInstrument import RsInstrument


def read_from_dat(filepath: str) -> Tuple[list,list]:
    output_frequency, output_power = [], []
    with open(filepath, 'r') as file:
        reader = csv.reader(file, delimiter=';')
        for idx, row in enumerate(reader):
            if idx >= 29:
                if "," in row[0] or "," in row[1]:
                    row[0] = row[0].replace(",", ".")
                    row[1] = row[1].replace(",", ".")
                    output_frequency.append(float(row[0]))
                    output_power.append(float(row[1]))

    return output_frequency, output_power


def read_from_csv(filepath: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    frequency, power, corrected_power = [], [], []
    with open(filepath, 'r') as file:
        reader = csv.reader(file)
        for idx, row in enumerate(reader):
            if idx == 0:
                continue
            frequency.append(float(row[0]))
            power.append(float(row[1]))
            corrected_power.append(float(row[2]))

    return np.array(frequency), np.array(power), np.array(corrected_power)


def write_to_csv(frequency: list, power: list, corrected_power: list, filepath: str):
    with open(filepath, "w", newline="") as file:
        header = ['Frequency', 'Power', "Corrected_Power"]
        writer = csv.DictWriter(file, fieldnames=header)

        writer.writeheader()
        for f, p, cp in zip(frequency, power, corrected_power):
            writer.writerow({'Frequency': f, 'Power': p, "Corrected_Power": cp})


def generate_f_p_strings(frequency, power) -> Tuple[str, str]:
    if not len(frequency) == len(power):
        raise ValueError()

    frequency_string = ""
    power_string = ""

    for idx, (f, p) in enumerate(zip(frequency, power)):
        if idx == len(frequency) - 1:
            frequency_string += f"{f}Hz"
            power_string += f"{p}dB"
        else:
            frequency_string += f"{f}Hz,"
            power_string += f"{p}dB,"

    return frequency_string, power_string


def get_corrected_power(power: np.ndarray):
    return -power - (np.max(-power) - 30)


# Save and load ZVL traces
def save_trace(frequency: list, power: list, filepath: str):
    with open(filepath, "w", newline="") as file:
        header = ['Frequency', 'Power']
        writer = csv.DictWriter(file, fieldnames=header)

        writer.writeheader()
        for f, p in zip(frequency, power):
            writer.writerow({'Frequency': f, 'Power': p})
    print(f"Trace saved to {filepath}")


def load_trace(filepath: str) -> Tuple[np.ndarray, np.ndarray]:
    frequency, power = [], []

    with open(filepath, 'r') as file:
        reader = csv.reader(file)
        for idx, row in enumerate(reader):
            if idx == 0:
                continue
            frequency.append(float(row[0]))
            power.append(float(row[1]))

    return np.array(frequency), np.array(power)


class RohdeSchwarzZVL:
    def __init__(self, address: str):
        self.instr = RsInstrument(address)
        print(f"Success! Connected to {self.instr.query_str('*IDN?')}")

    @staticmethod
    def convert_str_to_float_list(string: str):
        return list(map(float, string.split(",")))

    def get_trace(self, points: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
        print("Measuring trace...")

        self.instr.write_str(f'SWE:POIN {points}')
        time.sleep(1.5)

        self.instr.write_str('CALC:FORM MLOG; :FORM ASCII; FORM:DEXP:SOUR FDAT')
        time.sleep(1.5)

        frequency = self.instr.query_str('TRAC:STIM? CH1DATA')
        power = self.instr.query_str('TRAC? CH1DATA')

        frequency = np.array(self.convert_str_to_float_list(frequency))
        power = np.array(self.convert_str_to_float_list(power))

        return frequency, power


class MWSMF100A:
    def __init__(self, address: str):
        rm = visa.ResourceManager()
        self.inst = rm.open_resource(resource_name=address, timeout=10000)

    def create_user_correction_file(self, name: str):
        self.inst.write(f"CORR:CSET '/var/user/{name}'")
        self.inst.write(f"CORR:DEXC:SEL '/var/user/{name}'")
        return name

    def write_string_to_device(self, frequency_string: str, power_string: str):
        self.inst.write(f"CORR:CSET:DATA:FREQ {frequency_string}")
        self.inst.write(f"CORR:CSET:DATA:POW {power_string}")

    def check_number_of_points(self):
        return self.inst.query("CORR:CSET:DATA:FREQ:POIN?"), self.inst.query("CORR:CSET:DATA:POW:POIN?")

    def load_user_correction_and_turn_on(self, name: str):
        self.inst.write(f"SOUR:CORR:CSET '/var/user/{name}'")
        self.inst.write("SOUR:CORR ON")

    def disable_user_correction(self):
        self.inst.write("SOUR:CORR OFF")
