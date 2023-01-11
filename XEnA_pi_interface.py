# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 09:48:43 2019

@author: prrta
"""

from pipython import GCSDevice, pitools #see PIPython-1.3.4.17/docs/html/a00009.html
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

        if type(stagedict) is str:
                self.device = None
                self.uname = stagedict
                self.usb = None
                self.stage = None
                self.controller = None
                self.lastpos = 0
                self.velocity = None
        else:
            if stagedict['uname'] == 'dummy' or stagedict['uname'] == 'energy':
                self.device = None
                self.uname = stagedict['uname']
                self.usb = None
                self.stage = None
                self.controller = None
                self.lastpos = stagedict['lastpos']
                self.velocity = None
            else:
                print("Connecting "+stagedict['uname']+"...")
                print("    Serial: ",stagedict['usb'], "controller: ", stagedict['controller'], "stage: ", stagedict['stage'])
                try:
                    self.device = GCSDevice(stagedict['controller'])
                    self.device.ConnectUSB(serialnum=stagedict['usb'])
                    # self.device.CLR() #reset motor
                    print("    Switching on servo...")
                    self.device.SVO(self.device.axes, values=True) # switches on servo
                    # print("    Switching on velocity control...")
                    # print(self.device.qVCO(axes=self.device.axes))
                    # self.device.VCO(self.device.axes, values=True) # switches on velocity control
                    print("    Setting velocity to ", stagedict['velocity'])
                    self.device.VEL(self.device.axes, values=stagedict['velocity'])
                    print('connected: {}'.format(self.device.qIDN().strip()))
                
                    self.uname = stagedict['uname']
                    self.usb = stagedict['usb']
                    self.stage = stagedict['stage']
                    self.controller = stagedict['controller']
                    self.lastpos = stagedict['lastpos']
                    self.velocity = stagedict['velocity']        
                except Exception as exc:
                    print("Error:", exc)
                    self.device = None
                    self.uname = stagedict['uname']
                    self.usb = stagedict['usb']
                    self.stage = stagedict['stage']
                    self.controller = stagedict['controller']
                    self.lastpos = stagedict['controller']
                    self.velocity = stagedict['velocity']        
                    


def XEnA_pi_init():
    pidevices = list('')
    # go through stagedict and initiate each stage
    stagedict = XEnA_read_dict('lib/stages.json')
    for stage in stagedict:
        pidevices.append(Pidevice(stage))

    # home motors
    for i in range(len(pidevices)):
        # pidevices[i].device.FRF(pidevices[i].device.axes)  # find reference switch
        while True:
            if (pidevices[i].device.IsControllerReady()):
                break
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
            'velocity' : dev.velocity,
            'uname': dev.uname})

    with open(outfile, 'w+') as error:
        json.dump(stagedict, error)
        
def XEnA_read_dict(dictfile):
    with open(dictfile, encoding='utf-8') as data_file:
       stagedict = json.loads(data_file.read())
    return stagedict

def XEnA_move(pidevice, target):
    if type(pidevice) != __main__.Pidevice:
        syntax = "Type Error: Unknown device type <"+type(pidevice)+">"
        raise TypeError(syntax)

    if pidevice.uname == 'dummy':
        pidevice.lastpos = target
    else:
        # move motors
        pidevice.device.MOV(pidevice.device.axes, target)
        pitools.waitontarget(pidevice.device, axes=pidevice.device.axes)
        pidevice.lastpos = target

    # for i in range(len(_pidevice)):
    #     while True:
    #         if _pidevice[i].qONT(axes[i]).get("1") and _pidevice[i].IsControllerReady() and not _pidevice[i].IsMoving().get("1"): #TODO: it appears the query here occurs while still moving... Better option?
    #             sleep(0.1)
    #             print(_pidevice[i].qPOS(axes[i]).get("1"))
    #             break



#Useful commands:
    # pidevice.HLT() #Halt the motion of given 'axes' smoothly.
    # pidevice.JOG() #Start motion with the given (constant) velocity for 'axes'
    # pidevice.MNL()/MPL() #Move 'axes' to negative/positive limit switch.
    # pidevice.RBT() #Reboot controller, error check will be disabled temporarily.
    # pidevice.REF() #Reference 'axes'.
    # pidevice.StopAll() (or STP()) #Stop all axes abruptly (by sending "#24")
    

# stagedict = [
#     {'controller': "C-863",
#       'stage' : "M-061.DG",
#       'usb': "0021550017",
#       'lastpos' : 0,
#       'velocity' : 5,
#       'uname': "srcr"},
    
#     {'controller': "C-863.11",
#       'stage' : "M-414.3PD",
#       'usb': "0195500269",
#       'lastpos' : 150,
#       'velocity' : 10,
#       'uname': "srcx"},
    
#     {'controller': "C-863.11",
#       'stage' : "M-414.3PD",
#       'usb': "0195500299",
#       'lastpos' : 150,
#       'velocity' : 10,
#       'uname': "detx"},
    
#     {'controller': "C-663.11",
#       'stage' : "M-404.42S",
#       'usb': "0020550162",
#       'lastpos' : 50,
#       'velocity' : 1.5,
#       'uname': "cryy"},
    
#     {'controller': "C-663.11",
#       'stage' : "M-404.42S",
#       'usb': "0020550164",
#       'lastpos' : 50,
#       'velocity' : 1.5,
#       'uname': "cryz"},
    
#     {'controller': "C-663.11",
#       'stage' : "64439200",
#       'usb': "0020550169",
#       'lastpos' : 0,
#       'velocity' : 5,
#       'uname': "cryr"},
    
#     {'controller': "C-663.12",
#       'stage' : "65409200-0000",
#       'usb': "0021550047",
#       'lastpos' : 0,
#       'velocity' : 1.5,
#       'uname': "cryt"},

#     {'controller': None,
#       'stage' : None,
#       'usb': None,
#       'lastpos' : 0,
#       'velocity' : None,
#       'uname': "dummy"},

#     {'controller': None,
#       'stage' : None,
#       'usb': None,
#       'lastpos' : 0,
#       'velocity' : None,
#       'uname': "energy"}
#     ]

