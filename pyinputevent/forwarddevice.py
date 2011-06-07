
from pyinputevent import InputEvent, SimpleDevice
from keytrans import *
import scancodes as S
import logging

INP_SYNC = InputEvent.new(0, 0, 0)

class ForwardDevice(SimpleDevice):
    def __init__(self, udev, keymap, *args, **kwargs):
        SimpleDevice.__init__(self, *args, **kwargs)
        self.udev = udev # output device
        self.ctrl = False
        self.alt = False
        self.shift = False
        self.state = None
        self.doq = False # queue keystrokes for processing?
        self.mouseev = []
        self.keyev = []
        self.parser = KeymapParser(keymap)

    def send_all(self, events):
        for event in events:
            logging.debug(" --> %r" % event)
            self.udev.send_event(event)

    @property
    def modcode(self):
        code = 0
        if self.shift:
            code += 1
        if self.ctrl:
            code += 2
        if self.alt:
            code += 4
        return code
    def receive(self, event):
        logging.debug("<--  %r" % event)
        if event.etype == S.EV_MSC:
            return
        elif event.etype == S.EV_REL or event.etype == S.EV_ABS:
            self.mouseev.append(event)
            return
        elif event.etype == S.EV_KEY:
            if event.ecode in (S.KEY_LEFTCTRL, S.KEY_RIGHTCTRL):
                self.ctrl = bool(event.evalue)
                return
            elif event.ecode in (S.KEY_LEFTALT, S.KEY_RIGHTALT):
                self.alt = bool(event.evalue)
                return
            elif event.ecode in (S.KEY_LEFTSHIFT, S.KEY_RIGHTSHIFT):
                self.shift = bool(event.evalue)
                return
            else:
                self.send_all(self.parser.process(KeyEvent(event, self.modcode)))
        elif event.etype == 0:
            if self.mouseev:
                self.send_all(self.mouseev + [ INP_SYNC ])
                self.mouseev = []
            #print "-------------- sync --------------"
            return
        else:
            print "Unhandled event: %r" % event
            #self.udev.send_event(event)

