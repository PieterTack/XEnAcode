# -*- coding: utf-8 -*-
"""
Created on Tue Aug 13 10:05:01 2019

@author: prrta
This code handles the XasXes commands, as supplied by the xx_terminal
"""

import XEnA_pi_interface
import time as tm

R_CRYSTAL = 50. # cm
D_SI440 = 0.960 # Angstrom
D_SI331 = 1.246 # Angstrom

# depending on cmd_base, call different functions to execute
def wm(_pidevice):
    return _pidevice.qPOS(_pidevice.axes).get("1")

def wall(_pidevices):
    pos = list('')
    for i in range(len(_pidevices)):
        pos.append(_pidevices[i].qPOS(_pidevices[i].axes).get("1"))
    return pos
    
def mv(_pidevice, pos):
    XEnA_pi_interface.XEnA_pi_move(_pidevice, pos)

def mvr(_pidevice, step):
    goto_pos = list('')
    for i in range(len(_pidevice)):
        current_pos = _pidevice[i].qPOS(_pidevice[i].axes).get("1")
        goto_pos.append(current_pos+step[i])
    mv(_pidevice, goto_pos)

def ascan(_pidevice, start, end, nstep, time):
    step = (end-start)/nstep
    mv([_pidevice], [start])
    for i in range(int(nstep)+1):
        # measure
        data_acq(time)
        if i < nstep:
            mvr([_pidevice], [step])

def dscan(_pidevice, rstart, rend, nstep, time):
    current_pos = _pidevice.qPOS(_pidevice.axes).get("1")
    ascan(_pidevice, current_pos+rstart, current_pos+rend, nstep, time)
    # at end of dscan return to original position
    mv([_pidevice], [current_pos])

def mesh(_pidevice1, _pidevice2, start1, end1, nstep1, start2, end2, nstep2, time):
    step1 = (end1-start1)/nstep1
    step2 = (end2-start2)/nstep2
    mv([_pidevice1, _pidevice2], [start1, start2])
    for i in range(int(nstep1)+1):
        for j in range(int(nstep2)+1):
            # measure
            print("step: ",i,j)
            data_acq(time)
            if j < nstep2:
                mvr([_pidevice1, _pidevice2], [0, step2])
            else:
                if i < nstep1:
                    mv([_pidevice1, _pidevice2], [start1+(i+1)*step1 ,start2])            
    
def dmesh(_pidevice1, _pidevice2, rstart1, rend1, nstep1, rstart2, rend2, nstep2, time):
    current_pos1 = _pidevice1.qPOS(_pidevice1.axes).get("1")
    current_pos2 = _pidevice2.qPOS(_pidevice2.axes).get("1")
    mesh(_pidevice1, _pidevice2, current_pos1+rstart1, current_pos1+rend1, nstep1, current_pos2+rstart2, current_pos2+rend2, nstep2, time)
    # at end of dscan return to original position
    mv([_pidevice1, _pidevice2], [current_pos1, current_pos2])
    
def data_acq(time):
    tm.sleep(time)

def find_motor_id(_pidevices, uname):
    for k in range(len(_pidevices)):
        if _pidevices[k].uname == uname:
            return k
    return -1
        

def do(_pidevices, commands, verbal=None):
    # first disect command in its single parts
    #   several commands can be split by semicolon
    commands = commands.split(';')
    for i in range(len(commands)):
        # go over command and dissect it. The main command is the first 'word' in the string
        command = commands[i].split(' ')    
        # identify, validate and send proper commands
        if command[0] == 'wm':
            # this command can be followed by any amount of motor names.
            if len(command) <= 1:
                syntax = "Syntax Help: Please provide a motor name.\n    wm <name>"
                print(syntax)
                if verbal:
                    verbal.add_output(syntax)
            else:
                #   verify motor names, and return values
                val_names = list('')
                val_pos = list('')
                for j in range(1,len(command)):
                    mot_id = find_motor_id(_pidevices, command[j])
                    if mot_id != -1:
                        val_names.append(command[j])
                        val_pos.append(wm(_pidevices[mot_id].device))
                # return message to terminal
                if verbal:
                    verbal.add_output("\n    "+"".join(name.center(20) for name in val_names))
                    verbal.add_output("    "+"".join(str("%.4f" % pos).center(15) for pos in val_pos)+'\n')
            
        elif command[0] == 'wall':
            val_names = list('')
            for j in range(len(_pidevices)):
                val_names.append(_pidevices[j].uname)
            devs = list('')
            for dev in _pidevices:
                devs.append(dev.device)
            val_pos = wall(devs)
            # return message to terminal
            if verbal:
                verbal.add_output("\n    "+"".join(name.center(20) for name in val_names))
                verbal.add_output("    "+"".join(str("%.4f" % pos).center(15) for pos in val_pos)+'\n')
            
        elif command[0] == 'wa':
            val_names = list('')
            for j in range(len(_pidevices)):
                val_names.append(_pidevices[j].uname)
            devs = list('')
            for dev in _pidevices:
                devs.append(dev.device)
            val_pos = wall(devs)
            # return message to terminal
            if verbal:
                verbal.add_output("\n    "+"".join(name.center(20) for name in val_names))
                verbal.add_output("    "+"".join(str("%.4f" % pos).center(15) for pos in val_pos)+'\n')
            
        elif command[0] == 'mv':
            # mv is followed by motor name and float
            if len(command) <= 2:
                syntax = "Syntax Help: Please provide a motor name and position.\n    mv <name> <position>"
                print(syntax)
                if verbal:
                    verbal.add_output(syntax)
            #   i.e. mv samx 0 samy 0
            else:
                devs = list('')
                pos = list('')
                for j in range(1,len(command),2):
                    mot_id = find_motor_id(_pidevices, command[j])
                    if mot_id != -1:
                        devs.append(_pidevices[mot_id].device)
                        pos.append(float(command[j+1]))
                mv(devs, pos)
            
        elif command[0] == 'mvr':
            # mvr is followed by motor name and float
            if len(command) <= 2:
                syntax = "Syntax Help: Please provide a motor name and relative distance.\n    mvr <name> <dist>"
                print(syntax)
                if verbal:
                    verbal.add_output(syntax)
                #   i.e. mvr samx 10 samy -10
            else:
                devs = list('')
                steps = list('')
                for j in range(1,len(command),2):
                    mot_id = find_motor_id(_pidevices, command[j])
                    if mot_id != -1:
                        devs.append(_pidevices[mot_id].device)
                        steps.append(float(command[j+1]))
                mvr(devs, steps)

        elif command[0] == 'ascan':
            # ascan is followed by motor name, start, end, nstep, time
            #   i.e. ascan samx 0 10 5 1
            if len(command) != 6:
                syntax = "Syntax Help: Please provide a motor name, start position, end position, amount of steps and acquisition time.\n    ascan <name> <start> <stop> <# steps> <time>"
                print(syntax)
                if verbal:
                    verbal.add_output(syntax)
            else:
                mot_id = find_motor_id(_pidevices, command[1])
                if mot_id != -1:
                    ascan(_pidevices[mot_id].device, float(command[2]), float(command[3]), float(command[4]), float(command[5]))
            
        elif command[0] == 'dscan':
            # dscan is followed by motor name, rstart, rend, nstep, time
            #   i.e. dscan samx -10 10 5 1
            if len(command) != 6:
                syntax = "Syntax Help: Please provide a motor name, relative start position, relative end position, amount of steps and acquisition time.\n    dscan <name> <rel. start> <rel. stop> <# steps> <time>"
                print(syntax)
                if verbal:
                    verbal.add_output(syntax)
            else:
                mot_id = find_motor_id(_pidevices, command[1])
                if mot_id != -1:
                    dscan(_pidevices[mot_id].device, float(command[2]), float(command[3]), float(command[4]), float(command[5]))

        elif command[0] == 'mesh':
            # mesh is followed by motor name, start, end, nstep, motor name2, start2, end2, nstep2, time
            #   i.e. mesh samx 0 10 5 samz 0 10 5 1
            if len(command) != 10:
                syntax = "Syntax Help:\n    mesh <name1> <start1> <stop1> <# steps1> <name2> <start2> <stop2> <# steps2> <time>\n      <name1> is outer loop, <name2> is inner loop (moves most)"
                print(syntax)
                if verbal:
                    verbal.add_output(syntax)
            else:
                mot_id1 = find_motor_id(_pidevices, command[1])
                mot_id2 = find_motor_id(_pidevices, command[5])
                if mot_id1 != -1 and mot_id2 != -1 and mot_id1 != mot_id2:
                    mesh(_pidevices[mot_id1].device, _pidevices[mot_id2].device, float(command[2]), float(command[3]), float(command[4]), float(command[6]), float(command[7]), float(command[8]), float(command[9]))
                    
        elif command[0] == 'dmesh':
            # dmesh is followed by motor name, rstart, rend, nstep, motor name2, rstart2, rend2, nstep2, time
            #   i.e. dmesh samx -10 10 5 samz 0 10 5 1
            if len(command) != 10:
                syntax = "Syntax Help:\n    dmesh <name1> <rel.start1> <rel.stop1> <# steps1> <name2> <rel.start2> <rel.stop2> <# steps2> <time>\n      <name1> is outer loop, <name2> is inner loop (moves most)"
                print(syntax)
                if verbal:
                    verbal.add_output(syntax)
            else:
                mot_id1 = find_motor_id(_pidevices, command[1])
                mot_id2 = find_motor_id(_pidevices, command[5])
                if mot_id1 != -1 and mot_id2 != -1 and mot_id1 != mot_id2:
                    dmesh(_pidevices[mot_id1].device, _pidevices[mot_id2].device, float(command[2]), float(command[3]), float(command[4]), float(command[6]), float(command[7]), float(command[8]), float(command[9]))

        elif command[0] == '':
            if verbal:
                verbal.add_output(command[0])

        else:
            syntax = "ERROR: Unknown Command: "+ command[0]
            print(syntax)
            if verbal:
                verbal.add_output(syntax)
    
        # somehow couple back info to terminal screen (e.g. would be nice to see umv update during move...)
    