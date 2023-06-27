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
                self.lastpos = float(stagedict['lastpos'])
                self.velocity = None
            else:
                print("Connecting "+stagedict['uname']+"...")
                print("    Serial: ",stagedict['usb'], "controller: ", stagedict['controller'], "stage: ", stagedict['stage'])
                try:
                    self.device = GCSDevice(stagedict['controller'])
                    self.device.ConnectUSB(serialnum=stagedict['usb'])
                    print("    Switching on servo...")
                    self.device.SVO(self.device.axes, values=True) # switches on servo
                    if stagedict['referenced'] == False:
                        print("    Setting reference state to False...")
                        self.device.RON(self.device.axes,values=False)
                    print("    Switching on velocity control...")
                    print(self.device.qVCO(axes=self.device.axes))
                    self.device.VCO(self.device.axes, values=True) # switches on velocity control
                    print("    Setting velocity to ", stagedict['velocity'])
                    self.device.VEL(self.device.axes, values=stagedict['velocity'])
                    print('connected: {}'.format(self.device.qIDN().strip()))
                
                    self.uname = stagedict['uname']
                    self.usb = stagedict['usb']
                    self.stage = stagedict['stage']
                    self.controller = stagedict['controller']
                    self.lastpos = float(stagedict['lastpos'])
                    self.velocity = float(stagedict['velocity'])       
                except Exception as exc:
                    print("Error:", exc)
                    self.device = None
                    self.uname = stagedict['uname']
                    self.usb = stagedict['usb']
                    self.stage = stagedict['stage']
                    self.controller = stagedict['controller']
                    self.lastpos = float(stagedict['lastpos'])
                    self.velocity = float(stagedict['velocity'])      
                    


def XEnA_pi_init():
    pidevices = list('')
    # go through stagedict and initiate each stage
    stagedict = XEnA_read_dict('lib/stages.json')
    for stage in stagedict:
        pidevices.append(Pidevice(stage))

    return pidevices


def XEnA_pi_home(pidevices):    # home motors if referenced
    for _pidevice in pidevices:
        if _pidevice.device is not None and _pidevice.device.qRON(_pidevice.device.axes) == True:
            _pidevice.device.FRF(_pidevice.device.axes)  # find reference switch
            while True:
                if (_pidevice.device.IsControllerReady()):
                    _pidevice.lastpos = _pidevice.device.qPOS(_pidevice.device.axes).get("1")
                    break


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
    #pretended as an absolute move, but under the hood is a relative move to allow for movement of unreferenced stages
    if type(pidevice) != type(Pidevice('dummy')):
        syntax = "Type Error: Unknown device type <"+type(pidevice)+">"
        raise TypeError(syntax)
        
    if pidevice.device is None:
        syntax = "Key Error: device not appropriately initialised: "+pidevice.uname
        raise KeyError(syntax)
        

    if pidevice.uname == 'dummy':
        pidevice.lastpos = target
    else:
        # move motors in relative step to allow for unreferenced motor movement.
        rmove = target - float(pidevice.device.qPOS(pidevice.device.axes).get("1"))
        pidevice.device.MVR(pidevice.device.axes, rmove)
        pitools.waitontarget(pidevice.device, axes=pidevice.device.axes)
        pidevice.lastpos = target




#Useful commands:
    # self.device.CLR() #Clear the status of 'axes'.
        # The following actions are done by CLR(): Switches the servo on.
        # Resets error to 0. If the stage has tripped a limit switch, CLR() will
        # move it away from the limit switch until the limit condition is no
        # longer given, and the target position is set to the current position
    # pidevice.HLT() #Halt the motion of given 'axes' smoothly.
    # pidevice.JOG() #Start motion with the given (constant) velocity for 'axes'
    # pidevice.MNL()/MPL() #Move 'axes' to negative/positive limit switch.
    # pidevice.RBT() #Reboot controller, error check will be disabled temporarily.
    # pidevice.REF() #Reference 'axes'.  ==> RON(self, axes, values=None): Set referencing mode for given 'axes'.
            #DFH(self, axes=None): Define the current positions of 'axes' as the axis home position
            #POS()
    # JOG(self, axes, values=None): Start motion with the given (constant) velocity for 'axes'.
    # pidevice.StopAll() (or STP()) #Stop all axes abruptly (by sending "#24")
    

# stagedict = [
#     {'controller': "C-863",
#       'stage' : "M-061.DG",
#       'usb': "0021550017",
#       'lastpos' : 0,
#       'velocity' : 5,
#       'referenced' : True,
#       'uname': "srcr"},
    
#     {'controller': "C-863.11",
#       'stage' : "M-414.3PD",
#       'usb': "0195500269",
#       'lastpos' : 150,
#       'velocity' : 10,
#       'referenced' : True,
#       'uname': "srcx"},
    
#     {'controller': "C-863.11",
#       'stage' : "M-414.3PD",
#       'usb': "0195500299",
#       'lastpos' : 150,
#       'velocity' : 10,
#       'referenced' : True,
#       'uname': "detx"},
    
#     {'controller': "C-663.11",
#       'stage' : "M-404.42S",
#       'usb': "0020550162",
#       'lastpos' : 50,
#       'velocity' : 1.5,
#       'referenced' : True,
#       'uname': "cryy"},
    
#     {'controller': "C-663.11",
#       'stage' : "M-404.42S",
#       'usb': "0020550164",
#       'lastpos' : 50,
#       'velocity' : 1.5,
#       'referenced' : True,
#       'uname': "cryz"},
    
#     {'controller': "C-663.11",
#       'stage' : "64439200",
#       'usb': "0020550169",
#       'lastpos' : 0,
#       'velocity' : 5,
#       'referenced' : False,
#       'uname': "cryr"},
    
#     {'controller': "C-663.12",
#       'stage' : "65409200-0000",
#       'usb': "0021550047",
#       'lastpos' : 0,
#       'velocity' : 1.5,
#       'referenced' : True,
#       'uname': "cryt"},

#     {'controller': None,
#       'stage' : None,
#       'usb': None,
#       'lastpos' : 0,
#       'velocity' : 0,
#       'referenced' : True,
#       'uname': "dummy"},

#     {'controller': None,
#       'stage' : None,
#       'usb': None,
#       'lastpos' : 0,
#       'velocity' : 0,
#       'referenced' : True,
#       'uname': "energy"}
#     ]

