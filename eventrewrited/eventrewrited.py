#!/usr/bin/python

from uinput import UInputDevice
from forwarddevice import ForwardDevice
import select
import logging
import getopt
import sys
import fcntl
import os

def detect_remote(vendor, product, bus = '0003'):
    fd = file("/proc/bus/input/devices")
    entry = {}
    mouse = None
    kbd = None
    sline = 'Bus=' + bus + ' Vendor=' + vendor + ' Product=' + product
    for line in fd:
        line = line.strip()
        if not line and entry:
            if sline in entry['I']:
                ev = None
                ismouse = False
                hl = entry['H'].split('=')[1]
                for h in hl.split(' '):
                    if 'mouse' in h:
                        ismouse = True
                    if 'event' in h:
                        ev = h
                if ismouse:
                    mouse = ev
                else:
                    kbd = ev
        elif line:
            l, r = line.split(":", 1)
            r = r.strip()
            entry[l] = r
    return mouse, kbd


#

def usage():
    print "-p --path=<dir>: Path to pymaps"
    print "-f --foreground: Run in the foreground"

def main(options):
    devices = []
    logging.info("pymap: " + options['path'])
    for keymap in os.listdir(options['path']):
        vendor, product = keymap.split('.')[0].split('_')
        logging.info("Scanning: %s %s" % (vendor, product))
        mousedev, kbddev = detect_remote(vendor, product)
        if (mousedev != None):
            mousedev = "/dev/input/%s" % mousedev
        if (kbddev != None):
            kbddev = "/dev/input/%s" % kbddev 
        if (mousedev != None or kbddev != None):
            devices.append([mousedev, kbddev, "%s/%s" % (options['path'], keymap)])

    if len(devices) == 0:
        logging.error("No remote detected")
        sys.exit(1)
    
    logging.info("Found devices %r" % devices)

    # setup polling
    poll = select.poll()
    fds = {}
    
    for mousedev, kbddev, keymap in devices:
        logging.info("Creating Udev device")
        udev = UInputDevice("lircd", 0x0, 0x1, 1)
        udev.create()
        logging.info("Udev device created")
        for devpath in mousedev, kbddev:
            # Mouse or keyboard dev could be None
            if (devpath == None):
                continue

            logging.info("Listening on: %s" % devpath)
            dev = ForwardDevice(udev, keymap, devpath, devpath)
            poll.register(dev, select.POLLIN | select.POLLPRI)
            fcntl.ioctl(dev.fileno(), 0x40044590, 1)
            fds[dev.fileno()] = dev
    if (options['foreground'] == False):
        logging.info("Forking into background")
        # Taken from http://code.activestate.com/recipes/278731-creating-a-daemon-the-python-way/
        try:
            pid = os.fork()
        except OSError, e:
            raise Exception, "%s [%d]" % (e.strerror, e.errno)

        if (pid == 0): # first child
            os.setsid()
            try:
                # Fork a second child and exit immediately to prevent zombies.
                pid = os.fork()
            except OSError, e:
                raise Exception, "%s [%d]" % (e.strerror, e.errno)
            if (pid == 0):  # The second child.
                # Since the current working directory may be a mounted filesystem, we
                # avoid the issue of not being able to unmount the filesystem at
                # shutdown time by changing it to the root directory.
                os.chdir("/")
            else:
                os._exit(0) # Exit parent (the first child) of the second child.
        else:
            os._exit(0) # Exit parent of the first child.
    
    logging.info("Starting poller")

    while True:
        for x,e in poll.poll():
            dev = fds[x]
            dev.read()

if __name__ == '__main__':
    logger = logging.getLogger()
    try:
        opts, args = getopt.getopt(sys.argv[1:], "vqpf", ["pymap=", "foreground"])
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    options = {'path': None, 'foreground': False}
    for opt, arg in opts:
        if opt == "-v":
            logger.setLevel(logger.getEffectiveLevel()-10)
        elif opt == "-q":
            logger.setLevel(logger.getEffectiveLevel()+10)
        elif opt in ("-p", "--pymap"):
            options['path'] = arg
        elif opt in ("-f", "--foreground"):
            options['foreground'] = true
        else:
            assert False, "unhandled option"
    if (options['path'] == None):
        options['path'] = os.path.dirname(__file__) + '/pymap.d'

    main(options)
