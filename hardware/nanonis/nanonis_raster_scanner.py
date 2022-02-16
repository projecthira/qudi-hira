import csv
from core.configoption import ConfigOption
from core.module import Base
from interface.motor_interface import MotorInterface


class NanonisRasterScanner(Base, MotorInterface):
    _sync_filepath = ConfigOption('sync_filepath', missing='error')

    def on_activate(self):
        self.syncfile = self._sync_filepath

    def on_deactivate(self):
        pass

    def get_syncfile_rows(self):
        rows = []
        with open(self.syncfile) as f:
            csv_reader = csv.reader(f, delimiter=',')
            for idx, row in enumerate(csv_reader):
                rows.append(list(map(int, row)))
        return rows

    def get_total_syncfile_rows_and_cols(self):
        return self.get_syncfile_rows()[0]

    def get_current_syncfile_row_and_col(self):
        rows = self.get_syncfile_rows()
        if len(rows) == 1:
            raise ValueError("Insufficient data")
        else:
            return rows[-1]

    def get_constraints(self):
        pass

    def move_rel(self,  param_dict):
        pass

    def move_abs(self, param_dict):
        pass

    def abort(self):
        pass

    def get_pos(self, param_list=None):
        """ Gets current position of the stage arms

        @param list param_list: optional, if a specific position of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                position is asked.

        @return dict: with keys being the axis labels and item the current
                      position.
        """
        if param_list == ["total"]:
            total_rows, total_cols = self.get_total_syncfile_rows_and_cols()
            return {"row": total_rows, "col": total_cols}
        elif param_list == ["current"]:
            row, col = self.get_current_syncfile_row_and_col()
            return {"row": row, "col": col}

    def get_status(self, param_list=None):
        """ Get the status of the position

        @param list param_list: optional, if a specific status of an axis
                                is desired, then the labels of the needed
                                axis should be passed in the param_list.
                                If nothing is passed, then from each axis the
                                status is asked.

        @return dict: with the axis label as key and the status number as item.
        """
        rows = self.get_syncfile_rows()
        if len(rows) == 1:
            return {"nanonis_running": True}
        else:
            return {"nanonis_running": False}

    def calibrate(self, param_list=None):
        pass

    def get_velocity(self, param_list=None):
        pass

    def set_velocity(self, param_dict):
        pass
