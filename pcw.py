# http://thepythoncorner.com/dev/how-to-create-a-watchdog-in-python-to-look-for-filesystem-changes/
# sudo apt install python3-pip
# python3 -m pip install watchdog
 
# Known Bugs and Issues
#  Why does it take multiple ctrl-c clicks to exit?

# Testing Required:
#  Check if any data is missed at file swapover and jpg snapshot time.

# Todo:
#  Make it run as a service/startup - learn
#  Tidy up imports - learn
#  Get global variables sorted out - learn
#  Clean up the code and make more pythony - learn.
#  Add some more trigger files?  Perhaps take overriding attributes
#    Have a think...
#  Put parameters at the top of the script as constants
#    AWB?   
#    ????
#  Setting framerate to something other than 30 gets weird results.
#  Do some basic checks.
#  Add a 'script started' logging event.

# Done:
#* Put some file rotation login in
#*   if freespace < x, call the cleanup function 
#*   while freespace is less than x:
#*      delete the oldest file in video
#*      needs to be made a bit resilient in the event of falling below low threshold
#* Add a snapshot jpg between every file change.
#* Put parameters at the top of the script as constants
#*   Paths
#*   Retain files or watch free space.
#*   Video length
#*   Video resolution
#*   Rotate
#*    Brightness
#*   Timestamp
#*   Take snapshot
#* Put on GitHub
#*   Exclude videos folder.
#*  A '1 frame a second' security option
#* Put 'shutter' as a flag triggered every 10 seconds in the main program body.
#* Add some more trigger files?  Perhaps take overriding attributes
#*   Reboot Pi
#* Create a log file.
#* Log Temperature.
#* Added a 'SHUTTEREXISTS' constant in case there is not hardware shutter installed.
#* Log constants to debug
#* Create pi-exit trigger
#* Move the web session stuff to logging.
#* Split Video and Image output folders.
#* Change the timelapse option to take JPGs instead.
#* As the images folder might be sync'd we need an option to keep its size in check (e.g. maximum size of the folder)


import time
import threading
from threading import Condition
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
import os
from os import path
import picamera
from picamera import PiCamera
from datetime import datetime
import io
import logging
import socketserver
from http import server
import datetime as dt
import shutil
import fnmatch
from gpiozero import CPUTemperature

OUTPUTPATHVIDEO = "./video/"
OUTPUTPATHIMAGE = "./sync/PiCamWatcher/image/"
WATCHPATH = "./sync/PiCamWatcher/watch/"
RESOLUTIONX = 1600
RESOLUTIONY = 1200
FRAMEPS = 30
QUALITY = 20 # 1 is best, 40 is worst.``
VIDEOLENGTH = 300 # Recorded videos will rotate at this number of seconds.
TIMELAPSEPERIOD = 60 # Timelapse JPGs will be taken at this number of seconds.
STREAMPORT = 42687
TIMESTAMP = True # Will a timestamp be put on photos and videos?
ROTATION = 270 # Degrees of rotation to orient camera correctly.
BRIGHTNESS = 50
CONTRAST = 0
FREESPACELIMIT = 96 # At how many GB free should old videos be deleted.  Timelapse JPGs will be ignored.
IMAGEFOLDERLIMIT = 50 # Maximum Size of JPG images to be kept (in MB)
TAKESNAPSHOT = True # Take a regular snapshot JPG when recording a video file.
SHUTTEREXISTS = True # Does the camera have a shutter which needs opening?

# trigger_flag  9876543210
# PI-RECORD     0000000001
# PI-STREAM     0000000010
# PI-TLAPSE     0000000100
# PI-STOPRECORD 0000001000
# PI-STOPSTREAM 0000010000
# PI-STOPTLAPSE 0000100000
# PI-STOPALL    0001000000
# PI-STOPSCRIPT 0010000000
# PI-REBOOT     0100000000

# process_flag  9876543210
# Idle          0000000000
# Recording     0000000001
# Streaming     0000000010
# Timelapsing   0000000100

PAGE="""\
<html>
<body>
<center><img src="stream.mjpg" width="640" height="480"></center>
</body>
</html>
"""

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)
class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while stream_thread_status is True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.debug(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            self.send_error(404)
            self.end_headers()
    def log_message(self, format, *args):
        logging.debug(f"{self.client_address[0]} {self.requestline}")
        return
class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def CleanOldFiles():
    freespace = shutil.disk_usage(OUTPUTPATHVIDEO).free / 1073741824
    # clean video files (based on free space)
    if(freespace < FREESPACELIMIT):
        while (freespace < FREESPACELIMIT):
            list_of_files = fnmatch.filter(os.listdir(OUTPUTPATHVIDEO), "RPiR-*.*")
            full_path = [OUTPUTPATHVIDEO + "{0}".format(x) for x in list_of_files]
            oldest_file = min(full_path, key=os.path.getctime)
            logging.debug(f"Freespace: {int(freespace)}GB")
            silentremove(oldest_file)
            # os.remove(oldest_file)
            freespace = shutil.disk_usage(OUTPUTPATHVIDEO).free / 1073741824
    
    # clean image files (based on folder size)
    imageusedspace = (sum(d.stat().st_size for d in os.scandir(OUTPUTPATHIMAGE) if d.is_file())/1048576)
    if(imageusedspace > IMAGEFOLDERLIMIT):
        while (imageusedspace > IMAGEFOLDERLIMIT):
            list_of_files = fnmatch.filter(os.listdir(OUTPUTPATHIMAGE), "RPi*.*")
            full_path = [OUTPUTPATHIMAGE + "{0}".format(x) for x in list_of_files]
            oldest_file = min(full_path, key=os.path.getctime)
            logging.debug(f"Used Space: {int(imageusedspace)}MB")
            silentremove(oldest_file)
            # os.remove(oldest_file)
            imageusedspace = (sum(d.stat().st_size for d in os.scandir(OUTPUTPATHIMAGE) if d.is_file())/1048576)

# def on_created(event):
#     if "pi-record" in event.src_path:
#         silentremove(WATCHPATH + "/pi-stream")
#         silentremove(WATCHPATH + "/pi-tlapse")
#     elif "pi-stoprecord" in event.src_path:
#         silentremove(event.src_path)
#         silentremove(WATCHPATH + "/pi-record")

#     if "pi-tlapse" in event.src_path:
#         silentremove(WATCHPATH + "/pi-stream")
#         silentremove(WATCHPATH + "/pi-record")
#     elif "pi-stoptlapse" in event.src_path:
#         silentremove(event.src_path)
#         silentremove(WATCHPATH + "//pi-tlapse")

#     if "pi-stream" in event.src_path:
#         silentremove(WATCHPATH + "/pi-record")
#         silentremove(WATCHPATH + "/pi-tlapse")
#     elif "pi-stopstream" in event.src_path:
#         silentremove(event.src_path)
#         silentremove(WATCHPATH + "/pi-stream")

#     if "pi-stopall" in event.src_path:
#         silentremove(WATCHPATH + "/pi-record")
#         silentremove(WATCHPATH + "/pi-stream")
#         silentremove(WATCHPATH + "/pi-tlapse")
#         silentremove(WATCHPATH + "/pi-stopall")

# testBit() returns a nonzero result, 2**offset, if the bit at 'offset' is one.
def testBit(int_type, offset):
    mask = 1 << offset
    return(int_type & mask)

# setBit() returns an integer with the bit at 'offset' set to 1.
def setBit(int_type, offset):
    mask = 1 << offset
    return(int_type | mask)

# clearBit() returns an integer with the bit at 'offset' cleared.
def clearBit(int_type, offset):
    mask = ~(1 << offset)
    return(int_type & mask)
 
# toggleBit() returns an integer with the bit at 'offset' inverted, 0 -> 1 and 1 -> 0.
def toggleBit(int_type, offset):
    mask = 1 << offset
    return(int_type ^ mask)

def on_created(event):
    global trigger_flag
    if "pi-record" in event.src_path:
        trigger_flag = setBit(trigger_flag, 0)
    if "pi-stream" in event.src_path:
        trigger_flag = setBit(trigger_flag, 1)
    if "pi-tlapse" in event.src_path:
        trigger_flag = setBit(trigger_flag, 2)
    if "pi-stoprecord" in event.src_path:
        trigger_flag = setBit(trigger_flag, 3)
        silentremove(event.src_path)
        silentremove(WATCHPATH + "/pi-record")
    if "pi-stopstream" in event.src_path:
        trigger_flag = setBit(trigger_flag, 4)
        silentremove(event.src_path)
        silentremove(WATCHPATH + "/pi-stream")
    if "pi-stoptlapse" in event.src_path:
        trigger_flag = setBit(trigger_flag, 5)
        silentremove(event.src_path)
        silentremove(WATCHPATH + "/pi-tlapse")
    if "pi-stopall" in event.src_path:
        trigger_flag = setBit(trigger_flag, 6)
        silentremove(event.src_path)
        silentremove(WATCHPATH + "/pi-record")
        silentremove(WATCHPATH + "/pi-stream")
        silentremove(WATCHPATH + "/pi-tlapse")
    if "pi-stopscript" in event.src_path:
        trigger_flag = setBit(trigger_flag, 7)
        silentremove(event.src_path)
    if "pi-reboot" in event.src_path:
        trigger_flag = setBit(trigger_flag, 8)
        silentremove(event.src_path)

def on_deleted(event):
    global trigger_flag
    if "pi-record" in event.src_path:
        trigger_flag = setBit(trigger_flag, 3)
    if "pi-stream" in event.src_path:
        trigger_flag = setBit(trigger_flag, 4)
    if "pi-tlapse" in event.src_path:
        trigger_flag = setBit(trigger_flag, 5)

def silentremove(filename):
    try:
        time.sleep(.5)
        logging.debug(f"Deleting: {filename}")
        os.remove(filename)
    except:
        pass

def silentremoveexcept(keeppath, keepfilename):
    # put some code here
    for entry in os.scandir(keeppath):
        if ((entry.name) != keepfilename and entry.name.startswith("pi-") and entry.is_file()):
            silentremove(entry.path)

def open_shutter():
    if(SHUTTEREXISTS is True) and (int(dt.datetime.now().strftime('%S')) % 5 == 3):
        os.system("shutter 1 >/dev/null 2>&1")

def close_shutter():
    if(SHUTTEREXISTS is True) and (int(dt.datetime.now().strftime('%S')) % 5 == 3):
        os.system("shutter 99 >/dev/null 2>&1")

def picamstartrecord():
    global trigger_flag
    global process_flag
    
    camera = PiCamera()
    camera.resolution = (RESOLUTIONX, RESOLUTIONY)
    camera.rotation = ROTATION
    camera.brightness = BRIGHTNESS
    camera.contrast = CONTRAST
    camera.framerate = FRAMEPS
    videoprefix = "RPiR-"

    while (testBit(process_flag, 0) != 0):
        if(TIMESTAMP is True):
            camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            camera.annotate_background = picamera.Color('black')
        camera.start_recording(OUTPUTPATHVIDEO + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.h264', format='h264', quality=QUALITY)
        logging.info(f"Recording: {OUTPUTPATHVIDEO + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.h264'}")
        CleanOldFiles()
        filetime = 0
        while (testBit(process_flag, 0) != 0) and filetime <= VIDEOLENGTH:
            if(TAKESNAPSHOT is True):
                camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                camera.annotate_background = picamera.Color('black')
            time.sleep(1)
            # Take a snapshot jpg every minute(ish)
            if(int(dt.datetime.now().strftime('%S')) % 60 == 0):
                logging.debug(f"Take Snapshot Image : {OUTPUTPATHIMAGE + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.jpg'}")
                camera.capture(OUTPUTPATHIMAGE + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.jpg')
            filetime += 1
        time.sleep(.5) 
        camera.stop_recording()
    camera.close()
    trigger_flag = clearBit(trigger_flag, 0)
    time.sleep(1)
def picamstarttlapse():
    global trigger_flag
    global process_flag
    
    camera = PiCamera()
    camera.resolution = (RESOLUTIONX, RESOLUTIONY)
    camera.rotation = ROTATION
    camera.brightness = BRIGHTNESS
    camera.contrast = CONTRAST
    videoprefix = "RPiT-"

    while tlapse_thread_status is True:
        # more stuff in here...
        if(TIMESTAMP is True):
            camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            camera.annotate_background = picamera.Color('black')
        logging.info(f"Take Timelapse Image : {OUTPUTPATHIMAGE + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.jpg'}")
        camera.capture(OUTPUTPATHIMAGE + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.jpg')
        time.sleep(TIMELAPSEPERIOD)
    camera.close()
    time.sleep(1)
def picamstartstream():
    global trigger_flag
    global process_flag
    
    with picamera.PiCamera(resolution='640x480', framerate=12) as camera:
        global output
        output = StreamingOutput()
        #Uncomment the next line to change your Pi's Camera rotation (in degrees)
        camera.rotation = ROTATION
        camera.brightness = BRIGHTNESS
        camera.contrast = CONTRAST
        camera.start_recording(output, format='mjpeg', quality=40)
        try:
            address = ('', STREAMPORT)
            server = StreamingServer(address, StreamingHandler)
            threadstream = threading.Thread(target = server.serve_forever)
            threadstream.daemon = True
            logging.info(f"Open Streaming on port {STREAMPORT}")
            threadstream.start()
            while stream_thread_status is True:
                if(TIMESTAMP is True):
                    camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    camera.annotate_background = picamera.Color('black')
                time.sleep(1)
            server.shutdown()
            logging.info("Stop Streaming")
            #camera.stop_recording()
        except KeyboardInterrupt:
            pass
        finally:
            #server.server_close()
            camera.stop_recording()

if __name__ == "__main__":
    patterns = "*"
    ignore_patterns = ""
    ignore_directories = True
    case_sensitive = False
    my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
    my_event_handler.on_created = on_created
    my_event_handler.on_deleted = on_deleted
    my_observer = Observer()
    my_observer.schedule(my_event_handler, WATCHPATH, recursive=False)

    global stream_thread_status
    stream_thread_status = False
    global tlapse_thread_status
    tlapse_thread_status = False
    global trigger_flag
    trigger_flag = int('000000000000', 2)
    global process_flag
    process_flag = int('000000000000', 2)
    
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%d-%b-%y %H:%M:%S', filename='./debug.log', filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

    logging.debug(f"OUTPUTPATHVIDEO = {OUTPUTPATHVIDEO}")
    logging.debug(f"OUTPUTPATHIMAGE = {OUTPUTPATHIMAGE}")
    logging.debug(f"WATCHPATH = {WATCHPATH}")
    logging.debug(f"RESOLUTIONX = {RESOLUTIONX}")
    logging.debug(f"RESOLUTIONY = {RESOLUTIONY}")
    logging.debug(f"FRAMEPS = {FRAMEPS}")
    logging.debug(f"QUALITY = {QUALITY}")
    logging.debug(f"VIDEOLENGTH = {VIDEOLENGTH}")
    logging.debug(f"TIMELAPSEPERIOD = {TIMELAPSEPERIOD}")
    logging.debug(f"STREAMPORT = {STREAMPORT}")
    logging.debug(f"TIMESTAMP = {TIMESTAMP}")
    logging.debug(f"ROTATION = {ROTATION}")
    logging.debug(f"BRIGHTNESS = {BRIGHTNESS}")
    logging.debug(f"CONTRAST = {CONTRAST}")
    logging.debug(f"FREESPACELIMIT = {FREESPACELIMIT}GB")
    logging.debug(f"IMAGEFOLDERLIMIT = {IMAGEFOLDERLIMIT}MB")
    logging.debug(f"TAKESNAPSHOT = {TAKESNAPSHOT}")
    logging.debug(f"SHUTTEREXISTS = {SHUTTEREXISTS}")
    logging.info(f"Waiting for something to do.")
    # Set initial state if (single or multiple) files exist.

    if(path.exists(WATCHPATH + "pi-record") is True):
        trigger_flag = setBit(trigger_flag, 0)
        silentremoveexcept(WATCHPATH, "pi-record")

    elif(path.exists(WATCHPATH + "pi-tlapse") is True):
        trigger_flag = setBit(trigger_flag, 1)
        silentremoveexcept(WATCHPATH, "pi-tlapse")

    elif(path.exists(WATCHPATH + "pi-stream") is True):
        trigger_flag = setBit(trigger_flag, 2)
        silentremoveexcept(WATCHPATH, "pi-stream")
    else:
        # Delete everything.
        # trigger_flag = setBit(trigger_flag, 3)
        # trigger_flag = setBit(trigger_flag, 4)
        # trigger_flag = setBit(trigger_flag, 5)
        silentremoveexcept(WATCHPATH, "pi-^^^")

    # Start watching for events...
    my_observer.start()

    record_thread = threading.Thread(target = picamstartrecord)
    stream_thread = threading.Thread(target = picamstartstream)          
    tlapse_thread = threading.Thread(target = picamstarttlapse)

    try:
        while True:
            print(format(trigger_flag, '010b') + " " + format(process_flag, '010b'))
            # Stop Record (bit 3)
            if(testBit(trigger_flag, 3) != 0):
                trigger_flag = clearBit(trigger_flag, 3)
                process_flag = clearBit(process_flag, 0)
                record_thread.join()
                record_thread = threading.Thread(target = picamstartrecord)
                logging.info(f"Stop Record : {record_thread}, {record_thread.is_alive()}, {threading.active_count()}")
                

            # Stop Stream (bit 4)
            if(testBit(trigger_flag, 4) != 0):
                trigger_flag = setBit(trigger_flag, 4)
                # stop stream
                trigger_flag = setBit(process_flag, 1)
                    
            # Stop TimeLapse (bit 5)
            if(testBit(trigger_flag, 5) != 0):
                trigger_flag = setBit(trigger_flag, 5)
                # stop tlapse
                trigger_flag = setBit(process_flag, 2)

            # Stop everything (bit 6)
            if(testBit(trigger_flag, 6) != 0):
                process_flag = clearBit(process_flag, 0)
                process_flag = clearBit(process_flag, 1)
                process_flag = clearBit(process_flag, 2)

            # Make sure nothing is running
            if(testBit(process_flag, 0) + testBit(process_flag, 1) + testBit(process_flag, 2) == 0):
                close_shutter()     
                # Start Record (bit 0)
                if(testBit(trigger_flag, 0) != 0):
                    record_thread.start()
                    process_flag = setBit(process_flag, 0)
                    logging.info(f"Start Record : {record_thread}, {record_thread.is_alive()}, {threading.active_count()}")

                # Start Stream (bit 1)
                if(testBit(trigger_flag, 1) != 0):
                    pass

                # Start TimeLapse (bit 2)
                if(testBit(trigger_flag, 2) != 0):
                    pass
            else:
                open_shutter()

            # Exit Script (bit 7)
            if(testBit(trigger_flag, 7) != 0):
                logging.info("Force Quit Script Instruction ")
                silentremove(WATCHPATH + "/pi-stopscript")
                os._exit(1)

            # Reboot Device (bit 8)
            if(testBit(trigger_flag, 8) != 0):
                logging.info("Force Reboot Instruction ")
                silentremove(WATCHPATH + "/pi-reboot")
                os.system("sudo reboot now >/dev/null 2>&1")    

            # Log temperature every minute.
            if(int(dt.datetime.now().strftime('%S')) % 60 == 15):
                logging.debug(f"Temperature = {CPUTemperature().temperature}C")

            time.sleep(1)

    

    except KeyboardInterrupt:
        #record_thread.join()
        #stream_thread.join()
        my_observer.stop()
        my_observer.join()

