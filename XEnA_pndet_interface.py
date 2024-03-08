# -*- coding: utf-8 -*-
"""
Created on Mon Oct 16 10:07:25 2023

@author: prrta


Before usage one should make sure that the appropriate xia_usb drivers are installed
Additionally, install the xia_microdxp_api_v2_2023.xia_microdxp_api_v2_2023 library
(pip install xia_microdxp_api-2-py3-none-any.whl)
    Ask your PNDetector contact for advice if you do not have this wheel
"""

import time

class PNDet():
    def __init__(self):
        import xia_microdxp_api_v2_2023.xia_microdxp_api_v2_2023 as dpp_api

        # when multiple detectors will be used it is best to read this info from an external library or such
        self._type = 'PNDetector'
        self._uname = "XiaDet0"
        
        dpp_api.init_xia_systems()  # Initialize XIA Systems only for microDXP
        print("")
        print(f"Connecting {self._uname} from {self._type}...")
        print(f"Number of active DPPs {dpp_api.number_of_detectors()}")
        print(f"XIA DPP version {dpp_api.xia_get_version_info()}")

        try:
            self._device = dpp_api.XiaMicroDXP(0)  # Create an instance with channel 0
            print(f"Connected to dpp {self._uname}, serial nr {self._device.simple_get_serial_number()}")
            self._connected = True
        except Exception as err:
            self._connected = False
            raise err

    def __del__(self):
        import xia_microdxp_api_v2_2023.xia_microdxp_api_v2_2023 as dpp_api

        ID = self._device.simple_get_serial_number()
        dpp_api.deinit_xia_systems()
        print(f"Connection to _device {ID} closed.")

    @property 
    def connected(self):
        return self._connected
    
    @connected.setter 
    def connected(self, value:bool):
        if isinstance(value, bool):
            self._connected = value
        else:
            raise TypeError(f"{value} is not a bool")

    @property 
    def name(self):
        return self._uname

    @property 
    def gain(self):
        return self._device.get_gain()

    @property
    def type(self):
        return self._type
    
    @property
    def nchan(self):
        return self._device.get_mca_length()
    
    @nchan.setter
    def nchan(self, value:int):
        valid_values = [256, 512, 1024, 2048, 4096, 8192]
        if value in valid_values and isinstance(value, int):
            self._device.set_number_mca_channels(value)
        else:
            raise TypeError(f"Select an integer value from {valid_values}")
            
    @property
    def peakingtime(self):
        return self._device.simple_get_all_setting()['selected_peaking_time']
    
    @peakingtime.setter 
    def peakingtime(self, value:float):
        valid_values = [0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0, 1.2, 1.6, 2.0,
            2.4, 3.2, 4.0, 4.8, 6.4, 8.0, 9.6, 12.8, 16.0, 19.2, 24.0]
        if value in valid_values and isinstance(value, float):
            self._device.simple_set_peaking_time(value)
        else:
            raise TypeError(f": Select a float value from {valid_values}")

    def start(self):
        self._device.start_run()
        
    def stop(self):
        self._device.stop_run()
        
    def clear(self):
        self.data = {}
    
    def readout(self):
        temp = self._device.get_statistics()
        self.data = {'spe_cts' : self._device.get_mca(self.nchan),
                     'nchannels' : self.nchan,
                     'gain_eV' : self.gain,
                     'peakingtime_us' : self.peakingtime,
                     'realtime_s' : temp['runtime_s'],
                     'events_cts' : temp['events'],
                     'icr_cps' : temp['icr_cps'],
                     'ocr_cps' : temp['ocr_cps']}
        del(temp) #shouldn't be needed in python, but maybe doesn't harm either
        
    def acq(self, realtime:float):
        if realtime <= 0:
            raise ValueError(f"Argument realtime should be strictly positive: {realtime} s.")
        else:
            self.start()
            time.sleep(realtime)
            self.stop()
            self.readout()
        


# print(f"number of active dpps {dpp_api.number_of_detectors()}")
# print(f"version {dpp_api.xia_get_version_info()}")
# x = 
# print(f"dpp board temp {x.simple_get_temperature()}")

# print('\nSettings')
# print(f"{x.simple_get_all_setting()}")

# print("\nAcquire a spectrum; realtime = 2.0 sec; peaking-time = 1.0")
# spectrum = x.simple_get_spectrum(2.0, 1.0)
# spectrum_statistic = x.get_statistics()

# print(f"Spectrum {spectrum[0:20]}")
# print(f"Statistics {spectrum_statistic}")

# print('\nADC trace')
# adc_trace_length = x.get_adc_trace_length()
# adc = x.get_adc_trace(adc_trace_length)
# print(f'{adc[0:20]}')



