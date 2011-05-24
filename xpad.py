#!/usr/bin/python

from xbmcclient import *
from pyinputevent import * 
from socket import *
from keytrans import *
import select
import scancodes as S
import logging
import getopt
import sys
import fcntl

class EventClient(Controller):
    def __init__(self, name):
        self.server = XBMCClient(name)
        self.name = name
        self.server.connect()
        self.bMap = {S.BTN_A: "a",
                     S.BTN_B: "b",
                     S.BTN_X: "x",
                     S.BTN_Y: "y",
                     S.BTN_BACK: "back",
                     S.BTN_TL: "white",
                     S.BTN_TR: "black",
                     S.BTN_START: "start",
                     S.BTN_MODE: "....Xbox",
                     S.BTN_THUMBL: "leftthumbbutton",
                     S.BTN_THUMBR: "rightthumbbutton"}
        self.hatMap = {S.ABS_HAT0X: {-1: "dpadleft", 1: "dpadright"},
                       S.ABS_HAT0Y: {-1: "dpadup", 1: "dpaddown"}}
        self.axisMap= {S.ABS_Z: ("", "leftanalogtrigger", 128, 0),
                       S.ABS_RZ: ("", "rightanalogtrigger", 128, 0),
                       S.ABS_X: ("leftthumbstickleft", "leftthumbstickright", 1, 12000),
                       S.ABS_Y: ("leftthumbstickup", "leftthumbstickdown", 1, 12000),
                       S.ABS_RX: ("rightthumbstickleft", "rightthumbstickright", 1, 12000),
                       S.ABS_RY: ("rightthumbstickup", "rightthumbstickdown", 1, 12000)}

        self.hatPos = {}
        for k in self.hatMap:
            self.hatPos[k] = 0
        
        self.axisPos = {}
        for k in self.axisMap:
            self.axisPos[k] = 0


    def format_timestamp(self, timestamp, fmt="%Y-%m-%d.%H:%M.%f"):
        return datetime.datetime.fromtimestamp(float(timestamp))\
            .strftime(fmt)
    def format_event(self, event):
        return "%s %s" % (self.format_timestamp(event.timestamp), event)
    def handle_keyup(self, keyevent):
        if (keyevent.keycode in self.bMap):
            print "Key %s released" % self.bMap[keyevent.keycode]
            self.server.send_button_state(map="XG", button=self.bMap[keyevent.keycode], down=0)
        print self.format_event(keyevent)
    def handle_keydown(self, keyevent):
        if (keyevent.keycode in self.bMap):
            print "Key %s pressed" % self.bMap[keyevent.keycode]
            self.server.send_button_state(map="XG", button=self.bMap[keyevent.keycode], down=1)

        print self.format_event(keyevent)
    def handle_move(self, moveevent):
        print self.format_event(moveevent)

    def to_deadzone(self, value, deadzone):
        if (value < 0 and value <= -deadzone):
            value = int((float(value + deadzone)/float(32768 - deadzone))*32768)
            return value # We need to do some linear scaling
        elif (value > 0 and value > deadzone):
            value = int((float(value - deadzone)/float(32767 - deadzone))*32767)
            return value # We need to do some more scaling
        return 0

    def handle_events(self, events):
        for event in events:
            if (event.etype == 3):
                if (event.ecode in self.hatMap):
                    kMap = self.hatMap[event.ecode]

                    if (self.hatPos[event.ecode] != 0):
                        print "Key %s released" % kMap[self.hatPos[event.ecode]]
                        self.server.send_button_state(map="XG", button=kMap[self.hatPos[event.ecode]], down=0)
                    
                    if (event.evalue in kMap):
                        self.hatPos[event.ecode] = event.evalue
                        print "Key %s pressed" % kMap[event.evalue]
                        self.server.send_button_state(map="XG", button=kMap[event.evalue], down=1)
                    else:
                        self.hatPos[event.ecode] = 0
                elif (event.ecode in self.axisMap):
                    aMap = self.axisMap[event.ecode]
                    oValue = self.axisPos[event.ecode]
                    value = self.to_deadzone(event.evalue, aMap[3])
                    if (oValue != value):
                        if (oValue < 0 and value >= 0):
                            print "Axis %s at %d" % (aMap[0], 0)
                            self.server.send_button_state(map="XG", button=aMap[0], amount=0)
                        elif (oValue > 0 and value <= 0):
                            print "Axis %s at %d" % (aMap[1], 0)
                            self.server.send_button_state(map="XG", button=aMap[1], amount=0)
                        
                        if (value < 0):
                            print "Axis %s at %d" % (aMap[0], aMap[2] * -value)
                            self.server.send_button_state(map="XG", button=aMap[0], amount=aMap[2] * -value, axis=1)
                        if (value > 0):
                            print "Axis %s at %d" % (aMap[1], aMap[2] * value)
                            self.server.send_button_state(map="XG", button=aMap[1], amount=aMap[2] * value, axis=1)
                        
                        self.axisPos[event.ecode] = value

            #if (event.etype != 3 or (event.ecode == 17 or event.ecode == 16 or event.ecode == S.ABS_Z or event.ecode == S.ABS_RZ or event.ecode == S.ABS_X)):
            #    print self.format_event(event)

def main(args, controller=None):
    import select
    if controller is None:
        controller = EventClient("xpad")
    fds = {}
    poll = select.poll()
    for dev in args:
        type, dev = dev.split(":",1)
        dev = HIDevice(controller, dev, type)
        fds[dev.fileno()] = dev
        poll.register(dev, select.POLLIN | select.POLLPRI)
    while True:
        for x,e in poll.poll():
            dev = fds[x]
            dev.read()

if __name__ == '__main__':
    main(sys.argv[1:])

# vim: smartindent tabstop=4 expandtab shiftwidth=4 softtabstop=4
