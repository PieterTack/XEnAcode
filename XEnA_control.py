# -*- coding: utf-8 -*-
"""
Created on Tue Aug 13 10:05:01 2019

@author: prrta
This code handles the XasXes commands, as supplied by the xx_terminal
"""

import numpy as np
import time as tm
import atexit
import XEnA_pi_interface
import XEnA_tube_control
import threading
import signal


R_CRYSTAL = 500. # mm
D_SI440 = 0.960 # Angstrom
D_SI331 = 1.246 # Angstrom
HC = 12.39 # keV*A

class Crystal():
    def __init__(self, dlattice=D_SI440, curvrad=R_CRYSTAL):
        self.dlattice = dlattice # in Angstrom
        self.curvrad = curvrad   # in mm

srcx, srcr, detx = None, None, None #just defining these as None to get rid of warnings in mv(energy) code
dspace = Crystal()



def _arg_validity(*args):
    for _pidevice in args:
        myVars = locals().copy()
        devicename = [i for i, j in myVars.items() if j == _pidevice][0]
        if devicename not in myVars:
            syntax = "Syntax Error: Unknown device <"+devicename+">"
            raise SyntaxError(syntax)
            
    return True
    

# depending on cmd_base, call different functions to execute
def wm(*args):
    '''Retreive the current position of the specified devices.\n    Syntax: wm(<name1> {, <name2>})'''
    if len(args) < 1:
        syntax = "Syntax Error: Please provide a motor name.\n    wm(<name1> {, <name2>})"
        raise SyntaxError(syntax)
    
    positions = list('')
    for _pidevice in args:
        if _pidevice.device is None:
            positions.append(_pidevice.lastpos)
        else:
            positions.append(_pidevice.device.qPOS(_pidevice.device.axes).get("1"))
    print("\n    ")
    for i in range(0, len(args), 5):
        print("    "+"".join(n.uname.center(20) for n in args[i:i+5]))
        print("    "+"".join(str("%.4f" % pos).center(20) for pos in positions[i:i+5])+'\n')

def wall():
    '''Retreive the current position of all devices.\n    Syntax: wall()'''
    positions = list('')
    for _pidevice in _devices:
        if _pidevice.device is None:
            positions.append(_pidevice.lastpos)
        else:
            positions.append(_pidevice.device.qPOS(_pidevice.device.axes).get("1"))
    print("\n    ")
    for i in range(0, len(positions), 5):
        print("    "+"".join(n.uname.center(20) for n in _devices[i:i+5]))
        print("    "+"".join(str("%.4f" % pos).center(20) for pos in positions[i:i+5])+'\n')

def wa():
    '''Retreive the current position of all devices.\n    Syntax: wa()'''
    wall()

def home(*args):
    '''Home a motor stage to the reference position \n   Syntax: home(<name1> {,<name2>, ...})'''
    if len(args) < 1:
        syntax = "Syntax Error: Please provide a motor name.\n    home(<name1>,{,<name2>, ...})"
        raise SyntaxError(syntax)

    for _pidevice in args:
        if _arg_validity(_pidevice) is True:
            XEnA_pi_interface.XEnA_pi_home(_pidevice)
    
def mv(*args, d=dspace): #'pos' in keV for energy, 'd' in Angstrom
    '''Move a motor stage to the defined absolute position. \n   Syntax: mv(<name1>, <pos1> {,<name2>, <pos2>})'''
    if len(args) <= 1 or len(args) % 2 != 0:
        syntax = "Syntax Error: Please provide a motor name and position.\n    mv(<name1>, <pos1> {,<name2>, <pos2>})"
        raise SyntaxError(syntax)

    if _arg_validity(args[::2]) is True:
        for _pidevice, pos in np.asarray((args[::2],args[1::2])).T:
            pos = float(pos)
            if _pidevice.uname == 'energy':
                sin_ang = HC/(2*pos*d.dlattice)
                if -1 < sin_ang < 1: 
                    ang_rad = np.arcsin(sin_ang)
                    ang_deg = ang_rad * 180/np.pi
                    dist = d.curvrad/np.tan(ang_rad)
                    srcx_mv = 366 - dist
                    detx_mv = srcx_mv + 27
                    print("Source angle = " + "{:.4f}".format(ang_deg) + "\n" 
                          + "Source translation = " + "{:.4f}".format(srcx_mv) 
                          + "\n" + "Detector translation = " + "{:.4f}".format(detx_mv))
                    if 95 < dist < 366:
                        mv(srcx, srcx_mv, detx, detx_mv, srcr, ang_deg, d=d)
                        _pidevice.lastpos = pos
                    else:
                        print("ERROR: Invalid setup, position not reachable")
                else:
                    print("Invalid setup, unobtainable Bragg angle: ", sin_ang)
            else:
                XEnA_pi_interface.XEnA_move(_pidevice, pos)
            XEnA_pi_interface.XEnA_store_dict(_devices)


def mvr(*args, d=dspace):
    '''Move a motor stage to the defined relative position. \n   Syntax: mvr(<name1>, <pos1> {,<name2>, <pos2>})'''
    if len(args) <= 1 or len(args) % 2 != 0:
        syntax = "Syntax Error: Please provide a motor name and position.\n    mvr(<name1>, <pos1> {,<name2>, <pos2>})"
        raise SyntaxError(syntax)

    if _arg_validity(args[::2]) is True:
        for _pidevice, step in np.asarray((args[::2],args[1::2])).T:
            if _pidevice.uname == 'energy' or _pidevice.uname == "dummy":
                goto_pos = _pidevice.lastpos+step
            else:
                current_pos = _pidevice.device.qPOS(_pidevice.device.axes).get("1")
                goto_pos = current_pos+step
            mv(_pidevice, goto_pos, d=d)

def ascan(*args):
    '''Perform an absolute scan by moving the specified device from start pos to end pos in a discrete amount of steps, acquiring <time> seconds at each position.\n   Syntax: ascan(<name>, <start>, <end>, <nsteps>, <time>)'''
    if len(args) != 5 :
        syntax = "Syntax Error: Incorrect number of arguments.\n    ascan(<name>, <start>, <end>, <nsteps>, <time>)"
        raise SyntaxError(syntax)
    
    _pidevice, _start, _end, _nstep, _time = args
    if _arg_validity(_pidevice) is True:
        _step = (_end-_start)/_nstep
        mv(_pidevice, _start)
        for i in range(int(_nstep)+1):
            # measure
            _data_acq(_time)
            if i < _nstep:
                mvr(_pidevice, _step)

def dscan(*args):
    '''Perform a relative scan by moving the specified device from rel. start pos to rel. end pos in a discrete amount of steps, acquiring <time> seconds at each position.\n   Syntax: dscan(<name>, <rstart>, <rend>, <nsteps>, <time>)'''
    if len(args) != 5 :
        syntax = "Syntax Error: Incorrect number of arguments.\n    dscan(<name>, <rstart>, <rend>, <nsteps>, <time>)"
        raise SyntaxError(syntax)

    _pidevice, _rstart, _rend, _nstep, _time = args
    if _arg_validity(_pidevice) is True:
        if _pidevice.device is None:
            _current_pos = _pidevice.lastpos
        else:
            _current_pos = _pidevice.qPOS(_pidevice.device.axes).get("1")
        ascan(_pidevice, _current_pos+_rstart, _current_pos+_rend, _nstep, _time)
        # at end of dscan return to original position
        mv(_pidevice, _current_pos)

def mesh(*args):
    '''Perform an absolute 2D scan by moving the specified devices from start pos to end pos in a discrete amount of steps, acquiring <time> seconds at each position.\n
    The first device is the slow motor, i.e. this one moves least during the scan.\n
        Syntax: mesh(<slow1>, <start1>, <end1>, <nsteps1>, <fast2>, <start2>, <end2>, <nsteps2>, <time>)'''
    if len(args) != 9 :
        syntax = "Syntax Error: Incorrect number of arguments.\n    Syntax: mesh(<slow1>, <start1>, <end1>, <nsteps1>, <fast2>, <start2>, <end2>, <nsteps2>, <time>)"
        raise SyntaxError(syntax)
        
    _pidevice1, _start1, _end1, _nstep1, _pidevice2, _start2, _end2, _nstep2, _time = args
    _step1 = (_end1-_start1)/_nstep1
    _step2 = (_end2-_start2)/_nstep2
    mv(_pidevice1, _start1, _pidevice2, _start2)
    for i in range(int(_nstep1)+1):
        for j in range(int(_nstep2)+1):
            # measure
            print("step: ",i,j)
            _data_acq(_time)
            if j < _nstep2:
                mvr(_pidevice1, 0, _pidevice2, _step2)
            else:
                if i < _nstep1:
                    mv(_pidevice1, _start1+(i+1)*_step1, _pidevice2, _start2)            
    
def dmesh(*args):
    '''Perform a relative 2D scan by moving the specified devices from start pos to end pos in a discrete amount of steps, acquiring <time> seconds at each position.\n
    The first device is the slow motor, i.e. this one moves least during the scan.\n
        Syntax: dmesh(<slow1>, <rstart1>, <rend1>, <nsteps1>, <fast2>, <rstart2>, <rend2>, <nsteps2>, <time>)'''
    if len(args) != 9 :
        syntax = "Syntax Error: Incorrect number of arguments.\n    Syntax: dmesh(<slow1>, <rstart1>, <rend1>, <nsteps1>, <fast2>, <rstart2>, <rend2>, <nsteps2>, <time>)"
        raise SyntaxError(syntax)

    _pidevice1, _rstart1, _rend1, _nstep1, _pidevice2, _rstart2, _rend2, _nstep2, _time = args
    if _pidevice1.device is None:
        _current_pos1 = _pidevice1.lastpos
    else:
        _current_pos1 = _pidevice1.device.qPOS(_pidevice1.device.axes).get("1")
    if _pidevice2.device is None:
        _current_pos2 = _pidevice2.lastpos
    else:
        _current_pos2 = _pidevice2.device.qPOS(_pidevice2.device.axes).get("1")
    mesh(_pidevice1, _pidevice2, _current_pos1+_rstart1, _current_pos1+_rend1, _nstep1, _current_pos2+_rstart2, _current_pos2+_rend2, _nstep2, _time)
    # at end of dscan return to original position
    mv(_pidevice1, _current_pos1, _pidevice2, _current_pos2)
    
def set(*args):
    '''Set a device current position to the defined position.\n
        Syntax: set(<name>, <setpos>)'''
    if len(args) != 2:
        syntax = "Syntax Error: Please provide a motor name and position.\n   set(<name>, <setpos>)"
        raise SyntaxError(syntax)
    
    _pidevice, _setpos = args

    if type(_pidevice) is type(XEnA_pi_interface.Pidevice('dummy')):
        if _pidevice.device is not None:#TODO: also allow setting unreferenced motors
            print("At this time we do not allow the override of writing physical motor positions. Please only set dummy or energy motors.")
        else:
            _pidevice.lastpos = float(_setpos)
    elif type(_pidevice) is type(Crystal()):
        _pidevice.dlattice = _setpos
    else:
        syntax = "Type Error: unknown device type: "+ str(type(_pidevice))+"\n   Please provide a Crystal() or Pidevice() object as argument."
        raise TypeError(syntax)
    XEnA_pi_interface.XEnA_store_dict(_devices)

        
def crystal():
    '''Obtain the current crystal dspace value (in Angstrom) used for energy movements.\n
        Syntax: which(dspace)'''
    suffix = ''
    if dspace.dlattice == D_SI440:
        suffix = '(D_SI440)'
    elif dspace.dlattice == D_SI331:
        suffix =  '(D_SI331)'
    print("    The current crystal dspace is: "+"{:.4f}".format(dspace.dlattice) +" Angström. "+suffix)

    
def _data_acq(time):
    tm.sleep(time)

def _handle_ctrlc():
    print("ctrl+c event registered")


if __name__ == "__main__":
    #start tube control window spawn
    tubethread = threading.Thread(target=XEnA_tube_control.run)
    tubethread.start()

        # initiate PI devices and generate local variables for each device uname
    _devices = XEnA_pi_interface.XEnA_pi_init()
    _myVars = locals()
    for dev in _devices:
        _myVars[dev.uname] = dev


    atexit.register(XEnA_pi_interface.XEnA_close, _devices) #on exit of program should close all connections
    signal.signal(signal.SIGINT, _handle_ctrlc) #stop motors
    
