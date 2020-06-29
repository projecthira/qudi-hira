import numpy as np
from logic.pulsed.pulse_objects import PulseBlock, PulseBlockEnsemble, PulseSequence
from logic.pulsed.pulse_objects import PredefinedGeneratorBase

"""
General Pulse Creation Procedure:
=================================
- Create at first each PulseBlockElement object
- add all PulseBlockElement object to a list and combine them to a
  PulseBlock object.
- Create all needed PulseBlock object with that idea, that means
  PulseBlockElement objects which are grouped to PulseBlock objects.
- Create from the PulseBlock objects a PulseBlockEnsemble object.
- If needed and if possible, combine the created PulseBlockEnsemble objects
  to the highest instance together in a PulseSequence object.
"""


class BasicPredefinedGenerator(PredefinedGeneratorBase):
    """

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def generate_simple_sin(self, name='simple_sin', length=1000e-9, amp=0.25,
                            freq=5e7, phase=0, num_of_points=50):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # Create the readout PulseBlockEnsemble
        # Get necessary PulseBlockElements

        iq_element = self._get_iq_mix_element(length=length, increment=0, amp=amp, freq=freq, phase=phase)

        # Create PulseBlock and append PulseBlockElements
        signal_block = PulseBlock(name=name)
        signal_block.append(iq_element)
        created_blocks.append(signal_block)
        # Create PulseBlockEnsemble and append block to it
        signal_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        signal_ensemble.append((signal_block.name, 0))

        if self.sync_channel:
            # Create the last readout PulseBlockEnsemble including a sync trigger
            # Get necessary PulseBlockElements
            sync_element = self._get_sync_element()
            # Create PulseBlock and append PulseBlockElements
            sync_block = PulseBlock(name=name)
            sync_block.append(iq_element)
            sync_block.append(sync_element)
            created_blocks.append(sync_block)
            # Create PulseBlockEnsemble and append block to it
            sync_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
            sync_ensemble.append((sync_block.name, 0))
            created_ensembles.append(sync_ensemble)

        # add metadata to invoke settings later on
        signal_ensemble.measurement_information['alternating'] = False
        signal_ensemble.measurement_information['laser_ignore_list'] = list()
        signal_ensemble.measurement_information['units'] = ('s', '')
        signal_ensemble.measurement_information['number_of_lasers'] = num_of_points
        signal_ensemble.measurement_information['counting_length'] = 0

        # Append PulseSequence to created_sequences list
        created_ensembles.append(signal_ensemble)

        return created_blocks, created_ensembles, created_sequences

    def generate_pulsedodmr_iq(self, name='pulsedODMR_iq', freq_start=50e6, freq_step=1e6,
                               measure_time=500e-9, num_of_points=10):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # Create frequency array
        freq_array = freq_start + np.arange(num_of_points) * freq_step

        # create the elements
        # TODO delete this
        waiting_element = self._get_idle_element(length=1e-03,
                                                 increment=0)
        start_element = self._get_trigger_element(20e-9, 0, 'd_ch0')
        waiting_element = self._get_idle_element(length=measure_time,
                                                 increment=0)
        end_element = self._get_trigger_element(20e-9, 0, 'd_ch1')

        # Create block and append to created_blocks list
        pulsedodmr_block = PulseBlock(name=name)
        for mw_freq in freq_array:
            mw_element = self._get_iq_mix_element(length=self.rabi_period / 2,
                                                  increment=0,
                                                  amp=self.iq_amplitude,
                                                  freq=mw_freq,
                                                  phase=0)
            pulsedodmr_block.append(mw_element)
            pulsedodmr_block.append(start_element)
            pulsedodmr_block.append(waiting_element)
            pulsedodmr_block.append(end_element)

        created_blocks.append(pulsedodmr_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((pulsedodmr_block.name, 0))

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append((sync_block.name, 0))

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = freq_array
        block_ensemble.measurement_information['units'] = ('Hz', '')
        block_ensemble.measurement_information['labels'] = ('Frequency', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_pulsed_demo(self, name='pulsed_demo', freq_start=50e6, freq_step=1e6,
                             num_of_points=10):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # Create frequency array
        freq_array = freq_start + np.arange(num_of_points) * freq_step

        # create the elements
        waiting_element = self._get_idle_element(length=200e-9,
                                                 increment=0)
        laser_element = self._get_laser_gate_element(length=self.laser_length,
                                                     increment=0)
        delay_element = self._get_delay_gate_element()

        start_element = self._get_trigger_element(10e-9, 0, 'd_ch0')
        click_element = self._get_trigger_element(100e-9, 0, 'd_ch1')

        # Create block and append to created_blocks list
        pulsedodmr_block = PulseBlock(name=name)
        for mw_freq in freq_array:
            mw_element = self._get_iq_mix_element(length=self.rabi_period / 2,
                                                  increment=0,
                                                  amp=self.microwave_amplitude,
                                                  freq=mw_freq,
                                                  phase=0)
            pulsedodmr_block.append(mw_element)
            # pulsedodmr_block.append(laser_element)
            # pulsedodmr_block.append(delay_element)
            pulsedodmr_block.append(start_element)
            pulsedodmr_block.append(waiting_element)
            pulsedodmr_block.append(click_element)
            pulsedodmr_block.append(waiting_element)
            pulsedodmr_block.append(click_element)
            pulsedodmr_block.append(waiting_element)
            pulsedodmr_block.append(click_element)
            pulsedodmr_block.append(start_element)
            pulsedodmr_block.append(waiting_element)
        created_blocks.append(pulsedodmr_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((pulsedodmr_block.name, 0))

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append((sync_block.name, 0))

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = freq_array
        block_ensemble.measurement_information['units'] = ('Hz', '')
        block_ensemble.measurement_information['labels'] = ('Frequency', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = num_of_points
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences

    def generate_trig_click(self, name='trig_click(', num_clicks=3, num_reps=10, wait_time=100e-9):
        """

        """
        created_blocks = list()
        created_ensembles = list()
        created_sequences = list()

        # create the elements
        waiting_element = self._get_idle_element(length=wait_time,
                                                 increment=0)
        start_element = self._get_trigger_element(10e-9, 0, 'd_ch0')
        click_element = self._get_trigger_element(10e-9, 0, 'd_ch1')

        # Create block and append to created_blocks list
        pulsedodmr_block = PulseBlock(name=name)
        trig = 0
        while trig < num_reps:
            pulsedodmr_block.append(start_element)
            pulsedodmr_block.append(waiting_element)
            count = 0
            while count < num_clicks:
                pulsedodmr_block.append(click_element)
                pulsedodmr_block.append(waiting_element)
                count += 1
            trig += 1

        created_blocks.append(pulsedodmr_block)

        # Create block ensemble
        block_ensemble = PulseBlockEnsemble(name=name, rotating_frame=False)
        block_ensemble.append((pulsedodmr_block.name, 0))

        # Create and append sync trigger block if needed
        if self.sync_channel:
            sync_block = PulseBlock(name='sync_trigger')
            sync_block.append(self._get_sync_element())
            created_blocks.append(sync_block)
            block_ensemble.append((sync_block.name, 0))

        # add metadata to invoke settings later on
        block_ensemble.measurement_information['alternating'] = False
        block_ensemble.measurement_information['laser_ignore_list'] = list()
        block_ensemble.measurement_information['controlled_variable'] = np.arange(num_reps)
        block_ensemble.measurement_information['units'] = ('Hz', '')
        block_ensemble.measurement_information['labels'] = ('Frequency', 'Signal')
        block_ensemble.measurement_information['number_of_lasers'] = num_reps
        block_ensemble.measurement_information['counting_length'] = self._get_ensemble_count_length(
            ensemble=block_ensemble, created_blocks=created_blocks)

        # append ensemble to created ensembles
        created_ensembles.append(block_ensemble)
        return created_blocks, created_ensembles, created_sequences
