# -*- coding: utf-8 -*-
"""
Created on Tue Aug 13 10:05:01 2019

@author: prrta
This code handles the XasXes commands, as supplied by the xx_terminal
"""

import numpy as np
import time as tm
import atexit
import XEnA_pi_interface as Xpi
import XEnA_tube_control
import threading
import signal


R_CRYSTAL = 500. # mm
D_SI440 = 0.960 # Angstrom
D_SI331 = 1.246 # Angstrom
HC = 12.398 # keV*A

class Crystal():
    def __init__(self, dlattice=D_SI440, curvrad=R_CRYSTAL):
        self.dlattice = dlattice # in Angstrom
        self.curvrad = curvrad   # in mm

srcx, srcr, detx = None, None, None #just defining these as None to get rid of warnings in mv(energy) code
dspace = Crystal()

def EtoMotPos(energy, d=dspace, verbose=True):
    sin_ang = HC/(2*energy*d.dlattice)
    if -1 < sin_ang < 1: 
        srcr_rad = np.arcsin(sin_ang)
        srcr_deg = (srcr_rad * 180/np.pi)-90.
        dist = d.curvrad/np.tan(srcr_rad)
        srcx_pos = 366 - dist  # these values are related to mechanical offsets of the instrument
        detx_pos = srcx_pos + 27
        if verbose:
            print("srcr encoder position = " + "{:.4f}".format(srcr_deg) + "\n" 
                  + "srcx encoder position = " + "{:.4f}".format(srcx_pos) 
                  + "\n" + "detx encoder position = " + "{:.4f}".format(detx_pos)
                  + "\n" + "Relative distance = " + "{:.4f}".format(2*dist))
        return (srcx_pos, detx_pos, srcr_deg, dist)  #returns the theoretical positions (encoder values) of the motors
    else:
        raise ValueError("ERROR: Unreachable energy for this crystal. Sin(theta): %s" %sin_ang)

def MotPostoE(d=dspace): #Note: this function only provides estimate energy position, 
            #as it does not take into account the srcr or physical crystal position
    # detx_pos = Xpi.XEnA_qpos(detx)
    srcx_pos = Xpi.XEnA_qpos(srcx)
    dist = 366 - srcx_pos  # these values are related to mechanical offsets of the instrument
    srcr_rad = np.arctan(d.curvrad/dist)
    sin_ang = np.sin(srcr_rad)
    energy = HC/(2*sin_ang*d.dlattice)
    print("Estimated current energy = %.4f" % energy)
    return energy

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
    for _stage in args:
        if _stage.device is None:
            positions.append(_stage.lastpos)
        else:
            positions.append(Xpi.XEnA_qpos(_stage))
    print("\n    ")
    for i in range(0, len(args), 5):
        print("    "+"".join(n.uname.center(20) for n in args[i:i+5]))
        print("    "+"".join(str("%.4f" % pos).center(20) for pos in positions[i:i+5])+'\n')

def wall():
    '''Retreive the current position of all devices.\n    Syntax: wall()'''
    _positions = list('')
    for _stage in _stages:
        if _stage.device is None:
            _positions.append(_stage.lastpos)
        else:
            _positions.append(Xpi.XEnA_qpos(_stage))
    print("\n    ")
    for i in range(0, len(_positions), 5):
        print("    "+"".join(n.uname.center(20) for n in _stages[i:i+5]))
        print("    "+"".join(str("%.4f" % pos).center(20) for pos in _positions[i:i+5])+'\n')

def wa():
    '''Retreive the current position of all devices.\n    Syntax: wa()'''
    wall()

def home(*args):
    '''Home a motor stage to the reference position \n   Syntax: home(<name1> {,<name2>, ...})'''
    if len(args) < 1:
        syntax = "Syntax Error: Please provide a motor name.\n    home(<name1>,{,<name2>, ...})"
        raise SyntaxError(syntax)

    for _stage in args:
        if _arg_validity(_stage) is True:
            Xpi.XEnA_pi_home(_stage)
    
def mv(*args, d=dspace): #'pos' in keV for energy, 'd' in Angstrom
    '''Move a motor stage to the defined absolute position. \n   Syntax: mv(<name1>, <pos1> {,<name2>, <pos2>})'''
    if len(args) <= 1 or len(args) % 2 != 0:
        syntax = "Syntax Error: Please provide a motor name and position.\n    mv(<name1>, <pos1> {,<name2>, <pos2>})"
        raise SyntaxError(syntax)

    if _arg_validity(args[::2]) is True:
        for _stage, _pos in np.asarray((args[::2],args[1::2])).T:
            _pos = float(_pos)
            if _stage.uname == 'energy':
                try:
                    srcx_pos, detx_pos, srcr_pos, dist = EtoMotPos(_pos, verbose=False) #returns the theoretical encoder positions, 
                    if 95 < dist < 366: # these values are related to physical encoder stage limits (collisions etc.)
                        #   consider user-supplied offset for further move
                        mv(srcx, srcx_pos+srcx.offset, detx, detx_pos+detx.offset, srcr, srcr_pos+srcr.offset, d=d)
                        _stage.lastpos = _pos
                    else:
                        raise ValueError("ERROR: moving energy out of bounds. Collision potential! Dist: %s" %dist)
                except ValueError as er:
                    print(er)
            else:
                Xpi.XEnA_move(_stage, _pos)
            Xpi.XEnA_store_dict(_stages)

def mvr(*args, d=dspace):
    '''Move a motor stage to the defined relative position. \n   Syntax: mvr(<name1>, <pos1> {,<name2>, <pos2>})'''
    if len(args) <= 1 or len(args) % 2 != 0:
        syntax = "Syntax Error: Please provide a motor name and position.\n    mvr(<name1>, <pos1> {,<name2>, <pos2>})"
        raise SyntaxError(syntax)

    if _arg_validity(args[::2]) is True:
        for _stage, _step in np.asarray((args[::2],args[1::2])).T:
            if _stage.uname == 'energy' or _stage.uname == "dummy":
                goto_pos = _stage.lastpos+_step
            else:
                goto_pos = Xpi.XEnA_qpos(_stage)+_step
            mv(_stage, goto_pos, d=d)

def ascan(*args):
    '''Perform an absolute scan by moving the specified device from start pos to end pos in a discrete amount of steps, acquiring <time> seconds at each position.\n   Syntax: ascan(<name>, <start>, <end>, <nsteps>, <time>)'''
    if len(args) != 5 :
        syntax = "Syntax Error: Incorrect number of arguments.\n    ascan(<name>, <start>, <end>, <nsteps>, <time>)"
        raise SyntaxError(syntax)
    
    _stage, _start, _end, _nstep, _time = args
    if _arg_validity(_stage) is True:
        _step = (_end-_start)/_nstep
        mv(_stage, _start)
        for i in range(int(_nstep)+1):
            # measure
            _data_acq(_time)
            if i < _nstep:
                mvr(_stage, _step)

def dscan(*args):
    '''Perform a relative scan by moving the specified device from rel. start pos to rel. end pos in a discrete amount of steps, acquiring <time> seconds at each position.\n   Syntax: dscan(<name>, <rstart>, <rend>, <nsteps>, <time>)'''
    if len(args) != 5 :
        syntax = "Syntax Error: Incorrect number of arguments.\n    dscan(<name>, <rstart>, <rend>, <nsteps>, <time>)"
        raise SyntaxError(syntax)

    _stage, _rstart, _rend, _nstep, _time = args
    if _arg_validity(_stage) is True:
        if _stage.device is None:
            _current_pos = _stage.lastpos
        else:
            _current_pos = Xpi.XEnA_qpos(_stage)
        ascan(_stage, _current_pos+_rstart, _current_pos+_rend, _nstep, _time)
        # at end of dscan return to original position
        mv(_stage, _current_pos)

def mesh(*args):
    '''Perform an absolute 2D scan by moving the specified devices from start pos to end pos in a discrete amount of steps, acquiring <time> seconds at each position.\n
    The first device is the slow motor, i.e. this one moves least during the scan.\n
        Syntax: mesh(<slow1>, <start1>, <end1>, <nsteps1>, <fast2>, <start2>, <end2>, <nsteps2>, <time>)'''
    if len(args) != 9 :
        syntax = "Syntax Error: Incorrect number of arguments.\n    Syntax: mesh(<slow1>, <start1>, <end1>, <nsteps1>, <fast2>, <start2>, <end2>, <nsteps2>, <time>)"
        raise SyntaxError(syntax)
        
    _stage1, _start1, _end1, _nstep1, _stage2, _start2, _end2, _nstep2, _time = args
    _step1 = (_end1-_start1)/_nstep1
    _step2 = (_end2-_start2)/_nstep2
    mv(_stage1, _start1, _stage2, _start2)
    for i in range(int(_nstep1)+1):
        for j in range(int(_nstep2)+1):
            # measure
            print("step: ",i,j)
            _data_acq(_time)
            if j < _nstep2:
                mvr(_stage1, 0, _stage2, _step2)
            else:
                if i < _nstep1:
                    mv(_stage1, _start1+(i+1)*_step1, _stage2, _start2)            
    
def dmesh(*args):
    '''Perform a relative 2D scan by moving the specified devices from start pos to end pos in a discrete amount of steps, acquiring <time> seconds at each position.\n
    The first device is the slow motor, i.e. this one moves least during the scan.\n
        Syntax: dmesh(<slow1>, <rstart1>, <rend1>, <nsteps1>, <fast2>, <rstart2>, <rend2>, <nsteps2>, <time>)'''
    if len(args) != 9 :
        syntax = "Syntax Error: Incorrect number of arguments.\n    Syntax: dmesh(<slow1>, <rstart1>, <rend1>, <nsteps1>, <fast2>, <rstart2>, <rend2>, <nsteps2>, <time>)"
        raise SyntaxError(syntax)

    _stage1, _rstart1, _rend1, _nstep1, _stage2, _rstart2, _rend2, _nstep2, _time = args
    if _stage1.device is None:
        _current_pos1 = _stage1.lastpos
    else:
        _current_pos1 = Xpi.XEnA_qpos(_stage1)
    if _stage2.device is None:
        _current_pos2 = _stage2.lastpos
    else:
        _current_pos2 = Xpi.XEnA_qpos(_stage2)
    mesh(_stage1, _current_pos1+_rstart1, _current_pos1+_rend1, _nstep1, _stage2, _current_pos2+_rstart2, _current_pos2+_rend2, _nstep2, _time)
    # at end of dscan return to original position
    mv(_stage1, _current_pos1, _stage2, _current_pos2)
    
def set(*args):
    '''Set a device current position to the defined position.\n
        Syntax: set(<name>, <setpos>)'''
    if len(args) != 2:
        syntax = "Syntax Error: Please provide a motor name and position.\n   set(<name>, <setpos>)"
        raise SyntaxError(syntax)
    
    _stage, _setpos = args

    if type(_stage) is type(Xpi.Pidevice('dummy')):
        if _stage.device is not None:
            #TODO: test offset handling
            # Instead of changing the encoder value, we'll simply redefine the offset with respect to the encoder value.
            #   Note that in time this could become meaningless for unreferenced stages
            _stage.lastpos = float(_setpos)
            _stage.offset = _setpos - Xpi.XEnA_qpos(_stage)
        elif _stage.uname == "energy": # when setting energy, this implies setting detx, srcx and srcr offsets.
            try:
                srcx_pos, detx_pos, srcr_pos, _ = EtoMotPos(_setpos)
                set(srcx, srcx_pos)
                set(detx, detx_pos)
                set(srcr, srcr_pos)
            except ValueError as er:
                print(er)
        else:
            _stage.lastpos = float(_setpos)
    elif type(_stage) is type(Crystal()):
        _stage.dlattice = _setpos
    else:
        syntax = "Type Error: unknown device type: "+ str(type(_stage))+"\n   Please provide a Crystal() or Pidevice() object as argument."
        raise TypeError(syntax)
    Xpi.XEnA_store_dict(_stages)

        
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
    _stages = Xpi.XEnA_pi_init()
    _myVars = locals()
    for dev in _stages:
        _myVars[dev.uname] = dev


    atexit.register(Xpi.XEnA_close, _stages) #on exit of program should close all connections
    signal.signal(signal.SIGINT, _handle_ctrlc) #stop motors
    
