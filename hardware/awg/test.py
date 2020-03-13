# -*- coding: utf-8 -*-
"""
This file contains the Qudi hardware module for Spectrum AWG.

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

Copyright (c) the Qudi Developers. See the COPYRIGHT.txt file atgeneral cleanup the
top-level directory of this distribution and at <https://github.com/Ulm-IQO/qudi/>
"""

import numpy as np
import pickle
from hardware.awg import SpectrumAWG35 as SpectrumAWG35
from hardware.awg.pyspcm import *
from collections import OrderedDict
from interface.pulser_interface import PulserConstraints


class AWG663():
    """ A hardware module for the Spectrum AWG for generating
        waveforms and sequences thereof.
    """
    _modclass = 'awg663'
    _modtype = 'hardware'

    # config options
    _tmp_work_dir = 'C:\\Users\\qudiamond\\Desktop'
    awg_ip_address = "192.168.0.4"
    waveform_folder = os.path.join(os.getcwd(), 'hardware', 'awg', 'waveform')
    sequence_folder = os.path.join(os.getcwd(), 'hardware', 'awg', 'sequence')

    def __init__(self):
        #super().__init__(config=config, **kwargs)

        self.cards = [0, 1]
        self.hub = 0
        self.channel_setup = [
            {
                'name': 'mw',
                'ch': 0,
                'type': 'sin',
                'amp': 1.0,
                'phase': 0.0,
                'freq': 30e6,
                'freq2': 0.0
            },
            {
                'name': 'mwy',
                'ch': 1,
                'type': 'sin',
                'amp': 1.0,
                'phase': np.pi / 2.,
                'freq': 30e6,
                'freq2': 0.0
            },
            {
                'name': 'rf',
                'ch': 2,
                'type': 'DC',
                'amp': 1.0,
                'phase': 0.0,  # np.pi/2.,
                'freq': 0.0,  # 'rf_freq'
                'freq2': 0.0
            },
            {
                'name': 'mw3',
                'ch': 3,
                'type': 'DC',
                'amp': 1.0,
                'phase': 0.0,
                'freq': 0.0,
                'freq2': 0.0
            },
            {
                'name': 'laser',
                'ch': 4,
                'type': 'DC',
                'amp': 1.0,
                'phase': 0.0,
                'freq': 0.0,
                'freq2': 0.0
            },
            {
                'name': 'aom',
                'ch': 5,
                'type': 'DC',
                'amp': 1.0,
                'phase': 0.0,
                'freq': 0.0,
                'freq2': 0.0
            },
            {
                'name': 'trig',
                'ch': 6,
                'type': 'DC',
                'amp': 1.0,
                'phase': 0.0,
                'freq': 0.0,
                'freq2': 0.0
            },
            {
                'name': 'mw_gate',
                'ch': 7,
                'type': 'DC',
                'amp': 1.0,
                'phase': 0.0,
                'freq': 0.0,
                'freq2': 0.0
            }
        ]
        # [card, channel, binary channel for later use]
        self.channels = [[0, 0, 0b1], [0, 1, 0b10], [1, 0, 0b100], [1, 1, 0b1000]]
        self.loaded_assets = {}
        self.CurrentUpload = os.path.join(os.getcwd(),  'hardware', 'awg', 'CurrentUpload.pkl')
        self.typeloaded = None

    def on_activate(self):
        print('activate')
        self.instance = SpectrumAWG35.AWG(self.awg_ip_address, self.cards, self.hub, self.channel_setup)
        self.instance.init_all_channels()
        self.instance.cards[0].set_amplitude(0, 500)
        self.instance.cards[0].set_amplitude(1, 500)
        self.instance.cards[1].set_amplitude(0, 100)
        self.instance.cards[1].set_amplitude(1, 100)
        active_chan = self.get_constraints().activation_config['config1']
        self.loaded_assets = dict.fromkeys(active_chan)

    def on_deactivate(self):
        """ Method called when module is deactivated. If not overridden
            this method returns an error.
        """
        self.instance.reset()
        self.instance.stop()
        self.instance.close()
        del self.instance

    def get_constraints(self):
        """
        Retrieve the hardware constrains from the Pulsing device.
        @return constraints object: object with pulser constraints as attributes.
        """
        constraints = PulserConstraints()

        constraints.a_ch_amplitude.min = 80
        constraints.a_ch_amplitude.max = 2500
        constraints.a_ch_amplitude.step = 1
        constraints.a_ch_amplitude.default = 500

        constraints.waveform_length.step = 1
        constraints.waveform_length.default = 1

        activation_config = OrderedDict()
        activation_config['config1'] = {'a_ch0', 'a_ch1', 'd_ch0', 'd_ch1', 'd_ch2',
                                        'a_ch2', 'a_ch3', 'd_ch3', 'd_ch4',
                                        'd_ch5'}
        constraints.activation_config = activation_config
        return constraints

    def pulser_on(self):
        """ Switches the pulsing device on.
        @return int: error code (0:OK, -1:error)
        """
        ERR = self.instance.start()
        return ERR

    def pulser_off(self):
        """ Switches the pulsing device off.
        @return int: error code (0:OK, -1:error)
        """
        ERR = self.instance.stop()
        return ERR

    def prepare_ch(self, name, type=None, amp=None, phase=None, freq=None, freq2=None, reset_phase=True):
        chan = self.instance.ch(name, type, amp, phase, freq, freq2, reset_phase)
        return chan

    def load_waveform(self, load_dict):
        """ Loads a waveform to the specified channel of the pulsing device.

        @param dict|list load_dict: a dictionary with keys being one of the available channel
                                    index and values being the name of the already written
                                    waveform to load into the channel.
                                    Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                {1: rabi_ch2, 2: rabi_ch1}
                                    If just a list of waveform names if given, the channel
                                    association will be invoked from the channel
                                    suffix '_ch1', '_ch2' etc.

                                        {1: rabi_ch1, 2: rabi_ch2}
                                    or
                                        {1: rabi_ch2, 2: rabi_ch1}

                                    If just a list of waveform names if given,
                                    the channel association will be invoked from
                                    the channel suffix '_ch1', '_ch2' etc. A
                                    possible configuration can be e.g.

                                        ['rabi_ch1', 'rabi_ch2', 'rabi_ch3']

        @return dict: Dictionary containing the actually loaded waveforms per
                      channel.

        For devices that have a workspace (i.e. AWG) this will load the waveform
        from the device workspace into the channel. For a device without mass
        memory, this will make the waveform/pattern that has been previously
        written with self.write_waveform ready to play.

        Please note that the channel index used here is not to be confused with the number suffix
        in the generic channel descriptors (i.e. 'd_ch1', 'a_ch1'). The channel index used here is
        highly hardware specific and corresponds to a collection of digital and analog channels
        being associated to a SINGLE wavfeorm asset.
        """

        # create new dictionary with keys = num_of_ch and item = waveform

        max_chunk_size = self.instance.max_chunk_size
        empty_chunk_array_factor = self.instance.empty_chunk_array_factor

        if isinstance(load_dict, list):
            new_dict = dict()
            for waveform in load_dict:
                wave_name = waveform.rsplit('.pkl')[0]
                channel_num = int(wave_name.rsplit('_ch', 1)[1])
                if not '_a_ch' in waveform:
                    channel = channel_num + 4
                else:
                    channel = channel_num
                new_dict[channel] = wave_name
            load_dict = new_dict

        if not bool(dict):
            print('No data to sent to awg')
            return -1

        # load possible sequences
        path = self.waveform_folder
        wave_form_files = self.get_waveform_names()
        wave_form_list = [file.rsplit('.pkl')[0] for file in wave_form_files]
        # with open(path,'w') as json_file:
        #     wave_form_dict  = json.load(json_file)

        # dict_path = os.path.join('awg', 'WaveFormDict.pkl')
        # pkl_file = open(dict_path, 'rb')
        # wave_form_dict = pickle.load(pkl_file)
        # pkl_file.close()

        data_list = list()
        # this looks like 4 analog channels and 6 digital
        for i in range(4):
            data_list.append(np.zeros(int(max_chunk_size * empty_chunk_array_factor), np.int16))
        for i in range(6):
            data_list.append(np.zeros(int(max_chunk_size * empty_chunk_array_factor), np.bool))

        for ch, value in load_dict.items():
            if value in wave_form_list:
                wavefile = '{0}.pkl'.format(value)
                filepath = os.path.join(path, wavefile)
                data = self.my_load_dict(filepath)
                data_list[ch][0:len(data)] = data
                data_size = len(data)
                if '_a_ch' in value:
                    chan_name = 'a_ch{0}'.format(value.rsplit('a_ch')[1])
                    self.loaded_assets[chan_name] = value
                else:
                    chan_name = 'd_ch{0}'.format(value.rsplit('d_ch')[1])
                    self.loaded_assets[chan_name] = value
            else:
                print('waveform not found')
                data_size = 0

        # key_list = list()

        # for key in wave_form_dict.keys():
        # key_list.append(key.rsplit('_a',1)[0])

        # find the given sequence in the dictionary and load to the wanted channel
        # for chan, wave_name in load_dict.items():
        #     wave_form = wave_form_dict.get(wave_name)
        #     if wave_form is not None:
        #         # prepare_ch(name=)
        #         # self.instance.upload_wave_from_list(wave_form)
        #         data = np.asarray(wave_form*(2**15-1), dtype=np.int16)
        #         data_list[chan][0:len(wave_form)] = data
        #         # plt.plot(data)
        #         # plt.show()
        #         data_size = len(wave_form)
        #     else:
        #         self.log.error(wave_name + ' not in dictionary')n
        new_list = list()
        if data_size < len(data_list[0]):
            for row in data_list:
                new_row = row[0:data_size]
                new_list.append(new_row)
            data_list = new_list

        # this is done in the spectrumAWG file, now both QUEST_AWG and spectrumAWG have the same output, see pg 80 in manual
        count = 0
        while not data_size % 32 == 0:
            data_size += 1
            count += 1
        if not count == 1:
            extra = np.zeros(count, np.int16)
            new_list = list()
            for row in data_list:
                new_row = np.concatenate((row, extra), axis=0)
                new_list.append(new_row)
            data_list = new_list

        self.instance.set_memory_size(int(data_size))
        self.log.info('Waveform sent to AWG')

        if not data_size == 0:
            self.instance.upload(data_list, data_size, mem_offset=0)
            self.typeloaded = 'waveform'
            print('data sent to awg')
            # print(data_list[0][0:5])
        return load_dict

        # self.set_mode('continuous')
        # self.instance.upload_wave_from_list(load_dict)

    def load_sequence(self, sequence_name):
        """ Loads a sequence to the channels of the device in order to be ready for playback.
        For devices that have a workspace (i.e. AWG) this will load the sequence from the device
        workspace into the channels.
        For a device without mass memory this will make the waveform/pattern that has been
        previously written with self.write_waveform ready to play.

        @param dict|list sequence_name: a dictionary with keys being one of the available channel
                                        index and values being the name of the already written
                                        waveform to load into the channel.
                                        Examples:   {1: rabi_ch1, 2: rabi_ch2} or
                                                    {1: rabi_ch2, 2: rabi_ch1}
                                        If just a list of waveform names if given, the channel
                                        association will be invoked from the channel
                                        suffix '_ch1', '_ch2' etc.

        @return dict: Dictionary containing the actually loaded waveforms per channel.
        """

        # create new dictionary with keys = num_of_ch and item = waveform

        max_chunk_size = self.instance.max_chunk_size
        empty_chunk_array_factor = self.instance.empty_chunk_array_factor
        if isinstance(sequence_name, list):
            new_dict = dict()
            for waveform in sequence_name:
                channel = int(waveform.rsplit('_ch', 1)[1])
                new_dict[channel] = waveform
            load_dict = new_dict

        # load possible sequences
        path = self.SequenceFile
        wave_form_dict = self.my_load_dict(path)

        # with open(path,'w') as json_file:
        #     wave_form_dict  = json.load(json_file)
        # dict_path = os.path.join('awg', 'SequenceDict.pkl')
        # pkl_file = open(dict_path, 'rb')
        # wave_form_dict = pickle.load(pkl_file)
        # pkl_file.close()

        data_list = list()
        # this looks like 4 analog channels and 6 digital
        for i in range(4):
            data_list.append(np.zeros(int(max_chunk_size * empty_chunk_array_factor), np.int16))
        for i in range(6):
            data_list.append(np.zeros(int(max_chunk_size * empty_chunk_array_factor), np.bool))

        # key_list = list()

        # for key in wave_form_dict.keys():
        # key_list.append(key.rsplit('_a',1)[0])

        # find the given sequence in the dictionary and load to the wanted channel
        for chan, wave_name in load_dict.items():
            wave_form = wave_form_dict.get(wave_name)
            if wave_form is not None:
                # prepare_ch(name=)
                # self.instance.upload_wave_from_list(wave_form)
                data = np.asarray(wave_form * (2 ** 15 - 1), dtype=np.int16)
                data_list[chan][0:len(wave_form)] = data
                # plt.plot(data)
                # plt.show()
                data_size = len(wave_form)
            else:
                self.log.error(wave_name + ' not in dictionary')

        self.instance.upload(data_list, data_size, mem_offset=0)

        return load_dict

    def get_loaded_assets(self):
        """
        Retrieve the currently loaded asset names for each active channel of the device.
        The returned dictionary will have the channel numbers as keys.
        In case of loaded waveforms the dictionary values will be the waveform names.
        In case of a loaded sequence the values will be the sequence name appended by a suffix
        representing the track loaded to the respective channel (i.e. '<sequence_name>_1').

        @return (dict, str): Dictionary with keys being the channel number and values being the
                             respective asset loaded into the channel,
                             string describing the asset type ('waveform' or 'sequence')
        """

        return self.loaded_assets, self.typeloaded

    def clear_all(self):
        """ Clears all loaded waveforms from the pulse generators RAM/workspace.

        @return int: error code (0:OK, -1:error)
        """
        self.instance.awg.reset()

    def get_status(self):
        """ Retrieves the status of the pulsing hardware

        @return (int, dict): tuple with an integer value of the current status and a corresponding
                             dictionary containing status description for all the possible status
                             variables of the pulse generator hardware.
        """
        status_dic = {-1: 'no communication with device', 0: ' device is active and ready'}
        self.status_dic = status_dic
        num = 0
        return num, status_dic

    def get_sample_rate(self):
        """ Get the sample rate of the pulse generator hardware

        @return float: The current sample rate of the device (in Hz)

        Do not return a saved sample rate from an attribute, but instead retrieve the current
        sample rate directly from the device.
        """
        rate = self.instance.get_samplerate()
        return rate

    def set_sample_rate(self, sample_rate):
        """ Set the sample rate of the pulse generator hardware.

        @param float sample_rate: The sampling rate to be set (in Hz)

        @return float: the sample rate returned from the device (in Hz).

        Note: After setting the sampling rate of the device, use the actually set return value for
              further processing.
        """
        rate = self.instance.set_samplerate(sample_rate)
        return rate

    def get_analog_level(self, amplitude=None, offset=None):
        """ Retrieve the analog amplitude and offset of the provided channels.

        @param list amplitude: optional, if the amplitude value (in Volt peak to peak, i.e. the
                               full amplitude) of a specific channel is desired.
        @param list offset: optional, if the offset value (in Volt) of a specific channel is
                            desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel descriptor string
                               (i.e. 'a_ch1') and items being the values for those channels.
                               Amplitude is always denoted in Volt-peak-to-peak and Offset in volts.

        Note: Do not return a saved amplitude and/or offset value but instead retrieve the current
              amplitude and/or offset directly from the device.

        If nothing (or None) is passed then the levels of all channels will be returned. If no
        analog channels are present in the device, return just empty dicts.

        Example of a possible input:
            amplitude = ['a_ch1', 'a_ch4'], offset = None
        to obtain the amplitude of channel 1 and 4 and the offset of all channels
            {'a_ch1': -0.5, 'a_ch4': 2.0} {'a_ch1': 0.0, 'a_ch2': 0.0, 'a_ch3': 1.0, 'a_ch4': 0.0}

        ls
        for each channel
        Card[id].get_filter(ch_num)
        Card[id].get_amplitude(ch_num)

        """

        channels = self.get_constraints().activation_config['config1']
        a_ch = [ch for ch in channels if 'a' in ch]

        AllAmp = dict()
        if amplitude is not None:
            for chan in amplitude:
                channel = int(chan.rsplit('_ch', 1)[1])
                chInd = self.channels[channel]
                state = self.instance.cards[chInd[0]].get_amplitude(chInd[1])
                AllAmp[chan] = state
        else:
            for channel in range(4):
                chInd = self.channels[channel]
                state = self.instance.cards[chInd[0]].get_amplitude(chInd[1])
                chan = "a_ch{0}".format(channel)
                AllAmp[chan] = state

        AllOffset = dict()
        if offset is not None:
            for chan in offset:
                channel = int(chan.rsplit('_ch', 1)[1])
                chInd = self.channels[channel]
                state = self.instance.cards[chInd[0]].get_offset(chInd[1])
                AllOffset[chan] = state
        else:
            for ch in a_ch:
                ch_num = int(ch.rsplit('_ch')[1])
                chInd = self.channels[ch_num]
                state = self.instance.cards[chInd[0]].get_offset(chInd[1])
                AllOffset[ch] = state

        return AllAmp, AllOffset

    def set_analog_level(self, amplitude=None, offset=None):
        """ Set amplitude and/or offset value of the provided analog channel(s).

        @param dict amplitude: dictionary, with key being the channel descriptor string
                               (i.e. 'a_ch1', 'a_ch2') and items being the amplitude values
                               (in Volt peak to peak, i.e. the full amplitude) for the desired
                               channel.
        @param dict offset: dictionary, with key being the channel descriptor string
                            (i.e. 'a_ch1', 'a_ch2') and items being the offset values
                            (in absolute volt) for the desired channel.

        @return (dict, dict): tuple of two dicts with the actual set values for amplitude and
                              offset for ALL channels.

        If nothing is passed then the command will return the current amplitudes/offsets.

        Note: After setting the amplitude and/or offset values of the device, use the actual set
              return values for further processing.
        """

        if amplitude is not None:
            for chan in amplitude:
                channel = int(chan.rsplit('_ch', 1)[1])
                chInd = self.channels[channel]
                amp = amplitude[chan]
                state = self.instance.cards[chInd[0]].set_amplitude(chInd[1], amp)

        if offset is not None:
            for chan in offset:
                channel = int(chan.rsplit('_ch', 1)[1])
                chInd = self.channels[channel]
                off = offset[chan]
                state = self.instance.cards[chInd[0]].set_offset(chInd[1], off)

        AllAmp, AllOffset = self.get_analog_level()

        return AllAmp, AllOffset

    def get_digital_level(self, low=None, high=None):
        """ Retrieve the digital low and high level of the provided/all channels.

        @param list low: optional, if the low value (in Volt) of a specific channel is desired.
        @param list high: optional, if the high value (in Volt) of a specific channel is desired.

        @return: (dict, dict): tuple of two dicts, with keys being the channel descriptor strings
                               (i.e. 'd_ch1', 'd_ch2') and items being the values for those
                               channels. Both low and high value of a channel is denoted in volts.

        Note: Do not return a saved low and/or high value but instead retrieve
              the current low and/or high value directly from the device.

        If nothing (or None) is passed then the levels of all channels are being returned.
        If no digital channels are present, return just an empty dict.

        Example of a possible input:
            low = ['d_ch1', 'd_ch4']
        to obtain the low voltage values of digital channel 1 an 4. A possible answer might be
            {'d_ch1': -0.5, 'd_ch4': 2.0} {'d_ch1': 1.0, 'd_ch2': 1.0, 'd_ch3': 1.0, 'd_ch4': 4.0}
        Since no high request was performed, the high values for ALL channels are returned (here 4).
        """

        channels = self.get_constraints().activation_config['config1']
        d_ch = [ch for ch in channels if 'd' in ch]

        if low is None:
            low = []
        if high is None:
            high = []

        low_val = {}
        high_val = {}

        if (low == []) and (high == []):
            for ch in d_ch:
                low_val[ch] = 0
                high_val[ch] = 1

        for d_ch in low:
            low_val[d_ch] = 0

        for d_ch in low:
            high_val[d_ch] = 1

        return low_val, high_val

    def set_digital_level(self, low=None, high=None):
        """ Set low and/or high value of the provided digital channel.

        @param dict low: dictionary, with key being the channel descriptor string
                         (i.e. 'd_ch1', 'd_ch2') and items being the low values (in volt) for the
                         desired channel.
        @param dict high: dictionary, with key being the channel descriptor string
                          (i.e. 'd_ch1', 'd_ch2') and items being the high values (in volt) for the
                          desired channel.

        @return (dict, dict): tuple of two dicts where first dict denotes the current low value and
                              the second dict the high value for ALL digital channels.
                              Keys are the channel descriptor strings (i.e. 'd_ch1', 'd_ch2')

        If nothing is passed then the command will return the current voltage levels.

        Note: After setting the high and/or low values of the device, use the actual set return
              values for further processing.
        """
        pass

    def get_active_channels(self, ch=None):
        """ Get the active channels of the pulse generator hardware.

        @param list ch: optional, if specific analog or digital channels are needed to be asked
                        without obtaining all the channels.

        @return dict:  where keys denoting the channel string and items boolean expressions whether
                       channel are active or not.

        Example for an possible input (order is not important):
            ch = ['a_ch2', 'd_ch2', 'a_ch1', 'd_ch5', 'd_ch1']
        then the output might look like
            {'a_ch2': True, 'd_ch2': False, 'a_ch1': False, 'd_ch5': True, 'd_ch1': False}

        If no parameter (or None) is passed to this method all channel states will be returned.

        DONT KNOW HOW TO CHECK IF DIGITAL IS ENABLED, JUST ASSUME IT IS SINCE THIS IS PART OF THE CARD INITIALIZATION

        """

        all_state = dict()
        all_constraints = self.get_constraints()
        all_options = all_constraints.activation_config['config1']
            # ['a_ch0', 'a_ch1', 'a_ch2', 'a_ch3', 'd_ch0', 'd_ch1', 'd_ch2', 'd_ch3', 'd_ch4', 'd_ch5']
        count = 0
        #
        # index = 0
        # for card in self.instance.cards:
        #     active = card.get_selected_channels()
        #     state[index] = index & bin(active)
        #     index =+1

        for c in all_options:
            if c.startswith('a'):
                num = int(c.rsplit('ch')[1])
                ind = self.channels[num]
                card = self.instance.cards[ind[0]]
                # state = card.get_channel_output(ind[1])
                state = card.get_selected_channels()
                all_state[c] = bool(state)
            elif c.startswith('d'):
                all_state[c] = True

        # for c in self.instance.cards:
        #     for chan in range(2):
        #         state = c.get_channel_output(chan)
        #         all_state[all_options[count]] = state
        #         count +=1

        if ch is not None:
            for chan in all_options:
                if chan is not ch:
                    all_state.pop(chan, 'None')

        return all_state

    def set_active_channels(self, ch=None):
        """
        Set the active/inactive channels for the pulse generator hardware.
        The state of ALL available analog and digital channels will be returned
        (True: active, False: inactive).
        The actually set and returned channel activation must be part of the available
        activation_configs in the constraints.
        You can also activate/deactivate subsets of available channels but the resulting
        activation_config must still be valid according to the constraints.
        If the resulting set of active channels can not be found in the available
        activation_configs, the channel states must remain unchanged.

        @param dict ch: dictionary with keys being the analog or digital string generic names for
                        the channels (i.e. 'd_ch1', 'a_ch2') with items being a boolean value.
                        True: Activate channel, False: Deactivate channel

        @return dict: with the actual set values for ALL active analog and digital channels

        If nothing is passed then the command will simply return the unchanged current state.

        Note: After setting the active channels of the device, use the returned dict for further
              processing.

        Example for possible input:
            ch={'a_ch2': True, 'd_ch1': False, 'd_ch3': True, 'd_ch4': True}
        to activate analog channel 2 digital channel 3 and 4 and to deactivate
        digital channel 1. All other available channels will remain unchanged.


        THE ANALOG CHANNELS ARE DONE, THE DIGITAL IS NOT CLEAR
        """

        binary = 0b0

        status = self.get_active_channels()
        status.update(ch)

        if ch is not None:
            for chan, value in status.items():
                if chan.startswith('a'):
                    num = int(chan.rsplit('ch')[1])
                    if value:
                        binary = self.channels[num][2] | binary
        else:
            binary = 0b1111

        self.instance.set_selected_channels(binary)

        status = self.get_active_channels()

        return status

    def write_waveform(self, name, analog_samples, digital_samples, is_first_chunk, is_last_chunk,
                       total_number_of_samples):
        """
        Write a new waveform or append samples to an already existing waveform on the device memory.
        The flags is_first_chunk and is_last_chunk can be used as indicator if a new waveform should
        be created or if the write process to a waveform should be terminated.

        NOTE: All sample arrays in analog_samples and digital_samples must be of equal length!

        @param str name: the name of the waveform to be created/append to
        @param dict analog_samples: keys are the generic analog channel names (i.e. 'a_ch1') and
                                    values are 1D numpy arrays of type float32 containing the
                                    voltage samples.
        @param dict digital_samples: keys are the generic digital channel names (i.e. 'd_ch1') and
                                     values are 1D numpy arrays of type bool containing the marker
                                     states.
        @param bool is_first_chunk: Flag indicating if it is the first chunk to write.
                                    If True this method will create a new empty waveform.
                                    If False the samples are appended to the existing waveform.
        @param bool is_last_chunk:  Flag indicating if it is the last chunk to write.
                                    Some devices may need to know when to close the appending wfm.
        @param int total_number_of_samples: The number of sample points for the entire waveform
                                            (not only the currently written chunk)

        @return (int, list): Number of samples written (-1 indicates failed process) and list of
                             created waveform names
        """
        waveforms = list()

            #
            #     # & is_last_chunk:
            # self.log.error('sample is either first of last, not both')
            # return -1, waveforms

        if len(analog_samples) == 0:
            self.log.error('No analog samples passed to write_waveform method')
            return -1, waveforms

        activation_dict = self.get_active_channels()
        active_channels = {chnl for chnl in activation_dict if activation_dict[chnl]}
        active_analog = sorted(chnl for chnl in active_channels if chnl.startswith('a'))

        # Sanity check of channel numbers
        # First need to undersatnd how to enable / disable digital channel
        # if active_channels != set(analog_samples.keys()).union(set(digital_samples.keys())):
        #     self.log.error('Mismatch of channel activation and sample array dimensions for '
        #                    'waveform creation.\nChannel activation is: {0}\nSample arrays have: '
        #                    ''.format(active_channels,
        #                              set(analog_samples.keys()).union(set(digital_samples.keys()))))
        #     return -1, waveforms

        # file with all the waveforms saved

        # wave_dict = self.get_waveform_names()
        total_length = 0

        # data is converted from float64 to int16
        # if name not in wave_dict:
        for chan, value in analog_samples.items():
            full_name = '{0}_{1}'.format(name, chan)
            wavename = '{0}.pkl'.format(full_name)
            path = os.path.join(self.waveform_folder, wavename)
            if not value.dtype == 'float64':
                convert = np.zeros(len(value),dtype='float64')
                ch_amp = self.get_analog_level(amplitude=[chan])
                convert[0:len(value)]=value*ch_amp[0][chan]
                value = convert
            if is_first_chunk:
                full_signal = np.asarray(value * (2 ** 15 - 1), dtype=np.int16)
                print(value[0:5])
            else:
                old_part = self.my_load_dict(path)
                new_part = np.asarray(value * (2 ** 15 - 1), dtype=np.int16)
                full_signal = np.concatenate((old_part, new_part))
            self.my_save_dict(full_signal, path)
            waveforms.append(full_name)
            total_length = len(full_signal)

        for chan, value in digital_samples.items():
            # maybe need to convert to boolian
            full_name = '{0}_{1}'.format(name, chan)
            wavename = '{0}.pkl'.format(full_name)
            path = os.path.join(self.waveform_folder, wavename)
            self.my_save_dict(value, path)
            waveforms.append(full_name)
            total_length = len(full_signal)

        # with open(path,'r') as json_file:
        #     wave_dict = json.load(json_file)

        # for key, value in analog_samples.items():
        #     # key_name = name
        #     # key_name = name + '_' + key
        #     if key_name in wave_dict.keys():
        #         if is_first_chunk:
        #             # new_value = np.concate(value,wave_dict[key_name])
        #             new_value = np.asarray(value * (2 ** 15 - 1), dtype=np.int16)
        #             wave_dict[key_name] = new_value
        #             waveforms.append(key_name)
        #             total_length = len(new_value)
        #         elif is_last_chunk:
        #             value = np.asarray(value * (2 ** 15 - 1), dtype=np.int16)
        #             new_value = np.concatenate(wave_dict[key_name],value)
        #             wave_dict[key_name] = new_value
        #             waveforms.append(key_name)
        #             total_length = len(new_value)
        #         else:
        #             total_length = 0
        #             self.log.error('name exists, specify first or last chunk')
        #     else:
        #         wave_dict[key_name] = np.asarray(value * (2 ** 15 - 1), dtype=np.int16)
        #         waveforms.append(key_name)
        #         total_length = len(value)

        return total_length, waveforms

    def prepare_data_via_channel(self, channel, duration, sample_rate, start_position):

        data = self.instance.get_data_from_channel(self, channel, duration, sample_rate, start_position)
        return data

    def write_sequence(self, name, sequence_parameters):
        """
        Write a new sequence on the device memory.

        @param str name: the name of the waveform to be created/append to
        @param dict sequence_parameters: dictionary containing the parameters for a sequence

        @return: int, number of sequence steps written (-1 indicates failed process)

        In our AWG we will have a dictionary with sequences, this is saved locally (not on the AWG)
        sequence parameters are the waveforms and lengths? repetitions?
        The specific channel is set at uploading
        """

        sequencename = '{0}.pkl'.format(name)
        path = os.path.join(self.sequence_folder, sequencename)
        sequence_list = self.get_sequence_names()

        if name not in sequence_list:
            self.my_save_dict(sequence_parameters, path)

        count = len(sequence_parameters)
        # with open(path, 'w') as json_file:
        #     json.dump(sequence_dict, json_file)

        # output = open(path, 'wb')
        # pickle.dump(sequence_dict, output)
        # output.close()

        return count

    def get_waveform_names(self):
        """ Retrieve the names of all uploaded waveforms on the device.

        @return list: List of all uploaded waveform name strings in the device workspace.
        """
        # path = os.path.join(os.getcwd(), 'awg','WaveFormDict.pkl')
        # pkl_file = open(path, 'rb')
        # wave_dict = pickle.load(pkl_file)
        # pkl_file.close()
        #
        # names = wave_dict.keys()

        path = self.waveform_folder
        names = [f.rsplit('.pkl')[0] for f in os.listdir(path) if f.endswith(".pkl")]

        return names

    def get_sequence_names(self):
        """ Retrieve the names of all uploaded sequence on the device.

        @return list: List of all uploaded sequence name strings in the device workspace.
        """
        # path = os.path.join(os.getcwd(), 'awg','SequenceDict.pkl')
        # pkl_file = open(path, 'rb')
        # wave_dict = pickle.load(pkl_file)
        # pkl_file.close()
        #
        # names = wave_dict.keys()
        path = self.sequence_folder

        names = [f for f in os.listdir(path) if f.endswith(".pkl")]

        return names

    def delete_waveform(self, waveform_name):
        """ Delete the waveform with name "waveform_name" from the device memory.

        @param str waveform_name: The name of the waveform to be deleted
                                  Optionally a list of waveform names can be passed.

        @return list: a list of deleted waveform names.
        """

        path = os.path.join(os.getcwd(), 'awg', 'WaveFormDict.pkl')
        pkl_file = open(path, 'rb')
        wave_dict = pickle.load(pkl_file)
        pkl_file.close()

        names = list()
        for wave in waveform_name:
            if wave in wave_dict.keys():
                wave_dict.pop(wave, "None")
                names.append = wave
            else:
                print("waveform {0} not in list".format(wave))

        path = os.path.join(os.getcwd(), 'awg', 'WaveFormDict.pkl')
        output = open(path, 'wb')
        pickle.dump(wave_dict, output)
        output.close()

        return names

    def delete_sequence(self, sequence_name):
        """ Delete the sequence with name "sequence_name" from the device memory.

        @param str sequence_name: The name of the sequence to be deleted
                                  Optionally a list of sequence names can be passed.

        @return list: a list of deleted sequence names.
        """
        path = os.path.join(os.getcwd(), 'awg', 'SequenceDict.pkl')
        pkl_file = open(path, 'rb')
        wave_dict = pickle.load(pkl_file)
        pkl_file.close()

        names = list()
        for wave in sequence_name:
            if wave in wave_dict.keys():
                wave_dict.pop(wave, "None")
                names.append = wave
            else:
                print("waveform {0} not in list".format(wave))

        output = open(path, 'wb')
        pickle.dump(wave_dict, output)
        output.close()

        return names

    def get_interleave(self):
        """ Check whether Interleave is ON or OFF in AWG.

        @return bool: True: ON, False: OFF

        Will always return False for pulse generator hardware without interleave.
        """
        return False

    def set_interleave(self, state=False):
        """ Turns the interleave of an AWG on or off.

        @param bool state: The state the interleave should be set to
                           (True: ON, False: OFF)

        @return bool: actual interleave status (True: ON, False: OFF)

        Note: After setting the interleave of the device, retrieve the
              interleave again and use that information for further processing.

        Unused for pulse generator hardware other than an AWG.
        """

        return False

    def reset(self):
        """ Reset the device.

        @return int: error code (0:OK, -1:error)
        """
        err = self.instance.reset()
        return err

    def has_sequence_mode(self):
        """ Asks the pulse generator whether sequence mode exists.

        @return: bool, True for yes, False for no.
        """
        return True

    def my_load_dict(self, filename):
        # if file doesn't exist it create a file with this name

        with open(filename, 'rb+') as file:
            my_dictionary = pickle.load(file)

        return my_dictionary

    def my_save_dict(self, my_dictionary, filename):
        """ save dictionary to pkl file, will overwrite existing data"""

        with open(filename, 'wb+') as file:
            data = pickle.dump(my_dictionary, file)

        return data

    def set_reps(self, reps):
        self.instance.set_loops(reps)
