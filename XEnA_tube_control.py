# -*- coding: utf-8 -*-
"""
Created on Mon May 31 08:49:47 2021

@author: prrta
"""

# Connection layout:
#  DAQ          tube
# AO GND ---- DB9 pin 9
# AO 0 ------ DB9 pin 3   # kV adj  0-10V  = 0-50kV
# AO 1 ------ DB9 pin 6   # mA adj  0-10V  = 0-2mA

# AI GND ---- J4 pin 1
# AI 0 ------ J4 pin 2    # kV mon
# AI 1 ------ J4 pin 3    # mA mon

# DO PF2.0 (Active Drive) ------ connector J4 pin 4 # Interlock  5V
#       nidaqmx.constants.DigitalDriveType.ACTIVE_DRIVE (= 12573)

import sys
# from PySide2.QtCore import Qt
# from PySide2.QtGui import QDoubleValidator
# from PySide2.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout,\
#     QCheckBox, QLabel, QLineEdit, QScrollArea
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout,\
    QCheckBox, QLabel, QLineEdit, QScrollArea


import time
import nidaqmx  # pip install nidaqmx
import threading
import numpy as np



class XEnA_tube_gui(QWidget):
    def __init__(self, parent=None):
        super(XEnA_tube_gui, self).__init__(parent)
    
        # create main layout for widgets
        layout_main = QVBoxLayout()
        layout_interlock = QHBoxLayout()
        layout_voltage = QHBoxLayout()
        layout_current = QHBoxLayout()
        layout_messages = QVBoxLayout()

        self.label_main = QLabel("XEnA Source Control")
        layout_main.addWidget(self.label_main)
        
        self.switch_interlock = QCheckBox("Interlock (on=photons, off=no photons)")
        layout_interlock.addWidget(self.switch_interlock)
        layout_main.addLayout(layout_interlock)
        
        self.label_kVmon = QLabel("Voltage [kV]:  monitor: ")
        layout_voltage.addWidget(self.label_kVmon)
        self.field_kVmon = QLineEdit("-----")
        self.field_kVmon.setMaximumWidth(40)
        self.field_kVmon.setValidator(QDoubleValidator(-1E6, 1E6,3))
        layout_voltage.addWidget(self.field_kVmon)
        self.field_kVmon.setEnabled(False)
        self.label_kVset = QLabel(" set: ")
        layout_voltage.addWidget(self.label_kVset)
        self.field_kVset = QLineEdit("-----")
        self.field_kVset.setMaximumWidth(40)
        self.field_kVset.setValidator(QDoubleValidator(-1E6, 1E6,3))
        layout_voltage.addWidget(self.field_kVset)
        layout_voltage.addStretch()
        layout_main.addLayout(layout_voltage)

        self.label_mAmon = QLabel("Current [mA]: monitor: ")
        layout_current.addWidget(self.label_mAmon)
        self.field_mAmon = QLineEdit("-----")
        self.field_mAmon.setMaximumWidth(40)
        self.field_mAmon.setValidator(QDoubleValidator(-1E6, 1E6,3))
        layout_current.addWidget(self.field_mAmon)
        self.field_mAmon.setEnabled(False)
        self.label_mAset = QLabel(" set: ")
        layout_current.addWidget(self.label_mAset)
        self.field_mAset = QLineEdit("-----")
        self.field_mAset.setMaximumWidth(40)
        self.field_mAset.setValidator(QDoubleValidator(-1E6, 1E6,3))
        layout_current.addWidget(self.field_mAset)
        layout_current.addStretch()
        layout_main.addLayout(layout_current)
        
        self.message_win = QLabel('Connecting...\n')
        self.message_win.setStyleSheet("QLabel { background-color : white; color : blackd; }");
        self.message_win.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.message_win.setCursor(Qt.IBeamCursor)
        self.message_win.setAlignment(Qt.AlignTop)
        self.scroll_win = QScrollArea()
        self.scroll_win.setWidget(self.message_win)
        self.scroll_win.setWidgetResizable(True)
        self.scroll_win.setMinimumHeight(180)
        layout_messages.addWidget(self.scroll_win)
        layout_main.addLayout(layout_messages)
        self.scroll_win.verticalScrollBar().rangeChanged.connect(lambda: self.scroll_win.verticalScrollBar().setValue(self.scroll_win.verticalScrollBar().maximum())) # Set scrollbar to max value when range changed

        
        # set dialog layout
        self.setLayout(layout_main)
        self.setWindowTitle("XEnA Source Control")
        
        
        # event handling
        self.switch_interlock.stateChanged.connect(self.toggle_interlock) # toggle interlock on or off
        self.field_kVset.returnPressed.connect(self.set_voltage)
        self.field_mAset.returnPressed.connect(self.set_current)

        # start additional thread for tube monitoring
        self.monitor = True
        self.thread = threading.Thread(target=self.tube_monitor)
        self.thread.start()

    def tube_monitor(self):
        voltage = np.zeros(10)
        current = np.zeros(10)
        time.sleep(7) #have to sleep a while here to give rest of GUI time to spawn
        try:
            with nidaqmx.Task() as task:
                task.ai_channels.add_ai_voltage_chan("Dev1/ai0") #kV monitor
                task.read()
            with nidaqmx.Task() as task:
                task.ai_channels.add_ai_voltage_chan("Dev1/ai1") #mA monitor
                task.read()
        except Exception as ex:
            self.add_message("----------------")
            self.add_message(str(ex))
            self.add_message("========")
            self.add_message("**ERROR: Could not connect to NI-DAQmx monitor input channels.")
            return

            
        while self.monitor == True:
            for i in range(10): #display an averaged value of 10 measurements within approx 1s.
                with nidaqmx.Task() as task:
                    task.ai_channels.add_ai_voltage_chan("Dev1/ai0") #kV monitor
                    voltage[i] = task.read()/10.*50.
                with nidaqmx.Task() as task:
                    task.ai_channels.add_ai_voltage_chan("Dev1/ai1") #mA monitor
                    current[i] = task.read()/10.*2.
                time.sleep(0.1)
            self.field_mAmon.setText("{:.3f}".format(np.average(current)))
            self.field_kVmon.setText("{:.3f}".format(np.average(voltage)))

    def toggle_interlock(self):
        if self.switch_interlock.isChecked() is True: # if interlock off, set voltage to 0. If on set voltage to 5
            state = True
        else:
            state = False
            self.field_kVset.setText("{:.3f}".format(0.))
            self.field_mAset.setText("{:.3f}".format(0.))
            self.ramp_voltage(0., "Dev1/ao0", "Dev1/ai0")
            self.ramp_voltage(0., "Dev1/ao1", "Dev1/ai1")

        try:            
            with nidaqmx.Task() as task:
                task.do_channels.add_do_chan("Dev1/port2/line0")
                task.write(state, auto_start=True)
        except Exception as ex:
            self.add_message("----------------")
            self.add_message(str(ex))
            self.add_message("========")
            self.add_message("**ERROR: Could not connect to digital output channel Dev1/port2/line0")
            return
    
    def set_voltage(self):
        value = float(self.field_kVset.text())
        # ramp up voltage certain timeframe (e.g. 50s for 0-10V; 0.2V/s)
        voltage = value/50.*10. #0V=0keV, 10V=50keV
        if voltage < 0.:
            voltage = 0.
            self.field_kVset.setText("{:.3f}".format(0.))
        if voltage > 10:
            voltage = 10.
            self.field_kVset.setText("{:.3f}".format(50.))

        if self.ramp_voltage(voltage, "Dev1/ao0", "Dev1/ai0") == True:
            self.add_message("Tube voltage set to "+self.field_kVset.text()+"kV")
            return True
        else:
            self.add_message("**ERROR: could not set tube voltage to "+self.field_kVset.text()+"kV")
            return False
    
    def set_current(self):
        value = float(self.field_mAset.text())
        # ramp up voltage certain timeframe (e.g. 50s for 0-10V; 0.2V/s)
        voltage = value/2.*10. #0V=0mA; 10V=2mA
        if voltage < 0.:
            voltage = 0.
            self.field_mAset.setText("{:.3f}".format(0.))
        if voltage > 10:
            voltage = 10.
            self.field_mAset.setText("{:.3f}".format(2.))
        
        if self.ramp_voltage(voltage, "Dev1/ao1", "Dev1/ai1") == True:
            self.add_message("Tube current set to "+self.field_mAset.text()+"mA")
            return True
        else:
            self.add_message("**ERROR: could not set tube current to "+self.field_mAset.text()+"mA")
            return False

    def ramp_voltage(self, setpoint, address_set, address_mon):
        try:
            with nidaqmx.Task() as task:
                task.ai_channels.add_ai_voltage_chan(address_mon)
                current_volt = task.read()
            
            if setpoint <= current_volt:
                incr = -0.2
            else:
                incr = 0.2
            n_incr = int(np.floor((current_volt - setpoint)/incr))
            set_voltage = (np.arange(n_incr)+1)*incr + current_volt
            
            for i in range(n_incr):
                with nidaqmx.Task() as task:
                    task.ao_channels.add_ao_voltage_chan(address_set)
                    task.write(set_voltage[i], auto_start=True)
                time.sleep(1)
               
            with nidaqmx.Task() as task:
                task.ao_channels.add_ao_voltage_chan(address_set)
                task.write(setpoint, auto_start=True)
            
            return True
        
        except Exception as ex:
            self.add_message("----------------")
            self.add_message(str(ex))
            self.add_message("========")
            return False

    def add_message(self, text):
        output = self.message_win.text()
        output += text+'\n'
        self.message_win.setText(output)

    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    xena_tube = XEnA_tube_gui()
    xena_tube.show()
    sys.exit(app.exec_())
