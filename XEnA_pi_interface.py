# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 09:48:43 2019

@author: prrta
"""

from pipython import GCSDevice, pitools
import json

STAGES = ('M-414.3PD',)  # connect stages to axes
REFMODE = ('FNL',)  # reference the connected stages

# CONTROLLERNAME = 'C-884.DB'  # 'C-884' will also work
# STAGES = ('M-111.1DG', 'M-111.1DG', 'NOSTAGE', 'NOSTAGE')
# REFMODE = ('FNL', 'FNL')

class Pidevice():
    """Connect to a PIPython device."""
    def __init__(self, stagedict):
        # We recommend to use GCSDevice as context manager with "with".
        # InterfaceSetupDlg() is an interactive dialog. There are other
        # methods to connect to an interface without user interaction.
        # _pidevice.InterfaceSetupDlg(key='sample')
        # _pidevice.ConnectRS232(comport=1, baudrate=115200)
        # _pidevice.ConnectUSB(serialnum='123456789')
        # _pidevice.ConnectTCPIP(ipaddress='192.168.178.42')

        self.device = GCSDevice(stagedict['controller'])
        if stagedict['uname'] == 'dummy':
            None
        else:
            self.device.ConnectUSB(serialnum=stagedict['usb'])
        self.device.CLR() #reset motor
        self.device.SVO(self.device.axes, values=True) # switches on servo
        
        # print('connected: {}'.format(self.device.qIDN().strip()))
        
        self.uname = stagedict['uname']
        self.usb = stagedict['usb']
        self.stage = stagedict['stage']
        self.controller = stagedict['controller']
        self.lastpos = stagedict['lastpos']

def XEnA_pi_init():
    pidevices = list('')
    # go through stagedict and initiate each stage
    stagedict = XEnA_read_dict('lib/stages.json')
    for stage in stagedict:
        pidevices.append(Pidevice(stage))
        # pidevices.append(Pidevice('C-863.11', None,'dummy'))

    # home motors
    for i in range(len(pidevices)):
        print(pidevices[i].uname+", ", end=" ")
        pidevices[i].device.FRF(pidevices[i].device.axes)  # find reference switch
        while True:
            if (pidevices[i].device.IsControllerReady()):
                break
    #    pidevices[0].device.POS(pidevices[0].device.axes, 150)  # set center reference to value 150
    return pidevices


def XEnA_close(pidevices):
    for dev in pidevices:
        dev.device.CloseConnection()
    XEnA_store_dict(pidevices) 


def XEnA_store_dict(pidevices, outfile='lib/stages.json'):
    stagedict = list('')
    for dev in pidevices:
        stagedict.append({
            'controller': dev.controller,
            'stage' : dev.stage,
            'usb': dev.usb,
            'lastpos' : dev.lastpos,
            'uname': dev.uname})

    with open(outfile, 'w+') as error:
        json.dump(stagedict, error)
        
def XEnA_read_dict(dictfile):
    with open(dictfile, encoding='utf-8') as data_file:
       stagedict = json.loads(data_file.read())
    return stagedict

def XEnA_move(_pidevice, target):
    # make axes lis
    axes = list('')
    for i in range(len(_pidevice)):
        axes.append(_pidevice[i].axes)
    # move motors
    for i in range(len(_pidevice)):
        _pidevice[i].MOV(axes[i], target[i])
        pitools.waitontarget(_pidevice[i], axes=axes[i])

    # for i in range(len(_pidevice)):
    #     while True:
    #         if _pidevice[i].qONT(axes[i]).get("1") and _pidevice[i].IsControllerReady() and not _pidevice[i].IsMoving().get("1"): #TODO: it appears the query here occurs while still moving... Better option?
    #             sleep(0.1)
    #             print(_pidevice[i].qPOS(axes[i]).get("1"))
    #             break


# stagedict = [
#     {'controller': "C-863.11",
#      'stage' : "M-061.DG",
#      'usb': "0021550017",
#      'lastpos' : 0,
#      'uname': "srcr"},
    
#     {'controller': "C-863.11",
#      'stage' : "M-414.3PD",
#      'lastpos' : 150,
#      'usb': "0195500269",
#      'uname': "srcx"},
    
#     {'controller': "C-863.11",
#      'stage' : "M-414.3PD",
#      'lastpos' : 150,
#      'usb': "0195500299",
#      'uname': "detx"},
    
#     {'controller': "C-663.11",
#      'stage' : "M-404.42S",
#      'lastpos' : 50,
#      'usb': "0020550162",
#      'uname': "cryy"},
    
#     {'controller': "C-663.11",
#      'stage' : "M-404.42S",
#      'lastpos' : 50,
#      'usb': "0020550164",
#      'uname': "cryz"},
    
#     {'controller': "C-663.11",
#      'stage' : "64439200",
#      'lastpos' : 0,
#      'usb': "0020550169",
#      'uname': "cryr"},
    
#     {'controller': "C-663.11",
#      'stage' : "65409200-0000",
#      'lastpos' : 0,
#      'usb': "0021550047",
#      'uname': "cryt"}
#     ]

