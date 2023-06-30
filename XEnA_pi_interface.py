# -*- coding: utf-8 -*-
"""
Created on Mon Aug 19 09:48:43 2019

@author: prrta
"""

from pipython import GCSDevice, pitools, GCSError #see PIPython-1.3.4.17/docs/html/a00009.html
import json
import sys

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
                print("")
                print("Connecting "+stagedict['uname']+"...")
                print("    Serial: ",stagedict['usb'], "controller: ", stagedict['controller'], "stage: ", stagedict['stage'])
                try:
                    self.device = GCSDevice(stagedict['controller'])
                    self.device.ConnectUSB(serialnum=stagedict['usb'])
                    print("    Switching on servo...", end="")
                    self.device.SVO(self.device.axes, values=True) # switches on servo
                    print(" done.")
                    if stagedict['referenced'] == False: #The case if we don't want to work with referenced stages
                        print("    Setting reference state to False...", end="")
                        self.device.RON(self.device.axes,values=False)
                        print(" done.")
                    else: #However, if they are to be referenced, we should home them now
                        print("    Homing device...", end="")
                        _pi_home(self)
                        print(" done.")
                        print("    Moving stage to last known position...", end="")
                        self.device.MOV(self.device.axes, stagedict["lastpos"])
                        print(" done.")
                    print("    Setting velocity to "+ str(stagedict['velocity']), end="")
                    self.device.VEL(self.device.axes, values=stagedict['velocity'])
                    print(" done.")
                    print('Connected: {}'.format(self.device.qIDN().strip()))
                
                    self.uname = stagedict['uname']
                    self.usb = stagedict['usb']
                    self.stage = stagedict['stage']
                    self.controller = stagedict['controller']
                    self.lastpos = float(stagedict['lastpos'])
                    self.velocity = float(stagedict['velocity'])       
                except Exception as exc:
                    print("Error:", exc)
                    print("  Device not initialised: "+ stagedict['uname'])
                    self.device = None
                    self.uname = stagedict['uname']
                    self.usb = stagedict['usb']
                    self.stage = stagedict['stage']
                    self.controller = stagedict['controller']
                    self.lastpos = float(stagedict['lastpos'])
                    self.velocity = float(stagedict['velocity'])      
                    


def XEnA_pi_init():
    stages = list('')
    # go through stagedict and initiate each stage
    stagedict = XEnA_read_dict('lib/stages.json')
    for stage in stagedict:
        stages.append(Pidevice(stage))

    return stages

def _pi_home(stage):
    if stage.device.HasFRF(): #stupid thing where HasFRF() returns True even though it's not supported by certain stages
        try:
            stage.device.FRF()
        except GCSError:
            stage.device.FPL()
    while True:
        if (stage.device.IsControllerReady()):
            break
    

def XEnA_pi_home(stages):    # home motors if referenced
    if type(stages) != type(list()):
        stages = [stages]
    for stage in stages:
        if stage.device is not None: 
            if stage.device.qRON(stage.device.axes).get("1") == True:
                # stage should be safe to home
                sys.stdout.write("Homing stage %s ..." %stage.uname)
                _pi_home(stage)
                stage.lastpos = XEnA_qpos(stage)
                sys.stdout.write(" done.\n")
            else:
                # Homing a stage that was listed as not referenced may be dangerous in terms of collisions within the setup... request user input
                valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
                sys.stdout.write("WARNING: Homing unreferenced stages may result in instrumental collisions.\n Are you sure you wish to continue homing? [y/N]")
                choice = input().lower()
                if choice == "": #Default no homing
                    sys.stdout.write("Omitted homing stage %s .\n" %stage.uname)
                elif choice in valid:
                    if valid[choice] is True:
                        #continue homing
                        sys.stdout.write("Homing stage %s ..." %stage.uname)
                        _pi_home(stage)
                        stage.lastpos = XEnA_qpos(stage)
                        sys.stdout.write(" done.\n")
                    else:
                        sys.stdout.write("Omitted homing stage %s .\n" %stage.uname)
                else:
                    sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")
                    
def XEnA_qpos(stage):
    return float(stage.device.qPOS(stage.device.axes).get("1"))+stage.offset

def XEnA_close(stages):
    print("Disconnecting stages...", end="")
    for stage in stages:
        stage.device.CloseConnection()
    print(" done.")
    XEnA_store_dict(stages) 


def XEnA_store_dict(stages, outfile='lib/stages.json'):
    stagedict = list('')
    for stage in stages:
        stagedict.append({
            'controller': stage.controller,
            'stage' : stage.stage,
            'usb': stage.usb,
            'lastpos' : stage.lastpos,
            'offset' : stage.offset,
            'velocity' : stage.velocity,
            'referenced': stage.referenced,
            'uname': stage.uname})

    with open(outfile, 'w+') as error:
        json.dump(stagedict, error)
        
def XEnA_read_dict(dictfile):
    with open(dictfile, encoding='utf-8') as data_file:
       stagedict = json.loads(data_file.read())
    return stagedict

def XEnA_move(stage, target):
    #pretended as an absolute move, but under the hood is a relative move to allow for movement of unreferenced stages
    if type(stage) != type(Pidevice('dummy')):
        syntax = "Type Error: Unknown device type <"+type(stage)+">"
        raise TypeError(syntax)
        
    if stage.device is None:
        syntax = "Key Error: device not appropriately initialised: "+stage.uname
        raise KeyError(syntax)

    if stage.uname == 'dummy':
        stage.lastpos = target
    else:
        # move motors in relative step to allow for unreferenced motor movement.
        rmove = target - XEnA_qpos(stage)
        stage.device.MVR(stage.device.axes, rmove)
        pitools.waitontarget(stage.device, axes=stage.device.axes)
        stage.lastpos = target




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
#       'offset' : 0,           #NOTE: stage_position + offset = lastpos
#       'velocity' : 5,
#       'referenced' : False,   #NOTE: setting referenced to True will reference the stage on initialisation, which could cause collisions in some cases!
#       'uname': "srcr"},
    
#     {'controller': "C-863.11",
#       'stage' : "M-414.3PD",
#       'usb': "0195500269",
#       'lastpos' : 150,
#       'offset' : 0,
#       'velocity' : 10,
#       'referenced' : True,
#       'uname': "srcx"},
    
#     {'controller': "C-863.11",
#       'stage' : "M-414.3PD",
#       'usb': "0195500299",
#       'lastpos' : 150,
#       'offset' : 0,
#       'velocity' : 10,
#       'referenced' : True,
#       'uname': "detx"},
    
#     {'controller': "C-663.11",
#       'stage' : "M-404.42S",
#       'usb': "0020550162",
#       'lastpos' : 50,
#       'offset' : 0,
#       'velocity' : 1.5,
#       'referenced' : True,
#       'uname': "cryy"},
    
#     {'controller': "C-663.11",
#       'stage' : "M-404.42S",
#       'usb': "0020550164",
#       'lastpos' : 50,
#       'offset' : 0,
#       'velocity' : 1.5,
#       'referenced' : True,
#       'uname': "cryz"},
    
#     {'controller': "C-663.11",
#       'stage' : "64439200",
#       'usb': "0020550169",
#       'lastpos' : 0,
#       'offset' : 0,
#       'velocity' : 5,
#       'referenced' : False,
#       'uname': "cryr"},
    
#     {'controller': "C-663.12",
#       'stage' : "65409200-0000",
#       'usb': "0021550047",
#       'lastpos' : 0,
#       'offset' : 0,
#       'velocity' : 1.5,
#       'referenced' : True,
#       'uname': "cryt"},

#     {'controller': None,
#       'stage' : None,
#       'usb': None,
#       'lastpos' : 0,
#       'offset' : 0,
#       'velocity' : 0,
#       'referenced' : True,
#       'uname': "dummy"},

#     {'controller': None,
#       'stage' : None,
#       'usb': None,
#       'lastpos' : 0,
#       'offset' : 0,
#       'velocity' : 0,
#       'referenced' : True,
#       'uname': "energy"}
#     ]

