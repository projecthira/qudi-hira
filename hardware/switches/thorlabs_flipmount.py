from pylablib.devices import Thorlabs
from core.module import Base
from core.configoption import ConfigOption


class ThorlabsFlipMount(Base):
    """ This class is implements communication with the Radiant Dyes flip mirror driver using pyVISA

    Example config for copy-paste:

    flip_beamsplitter:
        serial: "37006263"
    """
    serial = ConfigOption("serial", missing="error")

    inst = None

    def on_activate(self):
        self.inst = Thorlabs.kinesis.MFF(self.serial)

    def on_deactivate(self):
        self.inst.close()

    def flip_into_path(self):
        self.inst.move_to_state(0)

    def flip_out_of_path(self):
        self.inst.move_to_state(1)
