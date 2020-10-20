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
#* Change the timelapse option to take JPGs instead.
#  Put parameters at the top of the script as constants
#    AWB?   
#    ????
#  An email still image sent every x seconds option
#  A 'take instructions through email' option.  GMail API
#  Setting framerate to something other than 30 gets weird results.

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
##   Take snapshot
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
#* Change the timelapse option to take JPGs instead.
#* Split Video and Image output folders.

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

OUTPUTPATHVIDEO = './output/video/'
OUTPUTPATHIMAGE = './output/image/'
WATCHPATH = "./watch/"
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
FREESPACELIMIT = 96 # At how many GB should old videos be deleted.  Timelapse JPGs will be ignored.
TAKESNAPSHOT = True # Take a regular snapshot JPG when recording a video file.
SHUTTEREXISTS = True # Does the camera have a shutter which needs opening?

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
    if(freespace < FREESPACELIMIT):
        while (freespace < FREESPACELIMIT):
            list_of_files = fnmatch.filter(os.listdir(OUTPUTPATHVIDEO), "RPiR-*.*")
            full_path = [OUTPUTPATHVIDEO + "{0}".format(x) for x in list_of_files]
            oldest_file = min(full_path, key=os.path.getctime)
            logging.info(f"Deleting: {oldest_file}   Freespace: {int(freespace)}GB")
            os.remove(oldest_file)
            freespace = shutil.disk_usage(OUTPUTPATHVIDEO).free / 1073741824
def on_created(event):
    if "pi-record" in event.src_path:
        silentremove(WATCHPATH + "/pi-stream")
        silentremove(WATCHPATH + "/pi-tlapse")
    elif "pi-stoprecord" in event.src_path:
        silentremove(event.src_path)
        silentremove(WATCHPATH + "/pi-record")

    if "pi-tlapse" in event.src_path:
        silentremove(WATCHPATH + "/pi-stream")
        silentremove(WATCHPATH + "/pi-record")
    elif "pi-stoptlapse" in event.src_path:
        silentremove(event.src_path)
        silentremove(WATCHPATH + "//pi-tlapse")

    if "pi-stream" in event.src_path:
        silentremove(WATCHPATH + "/pi-record")
        silentremove(WATCHPATH + "/pi-tlapse")
    elif "pi-stopstream" in event.src_path:
        silentremove(event.src_path)
        silentremove(WATCHPATH + "/pi-stream")

    if "pi-stopall" in event.src_path:
        silentremove(WATCHPATH + "/pi-record")
        silentremove(WATCHPATH + "/pi-stream")
        silentremove(WATCHPATH + "/pi-tlapse")
        silentremove(WATCHPATH + "/pi-stopall")
def silentremove(filename):
    try:
        time.sleep(.5)
        os.remove(filename)
    except:
        pass
def picamstartrecord():
    global record_thread_status
    global shutter_open
    if(SHUTTEREXISTS is True):
        logging.info("Open Shutter")
        shutter_open = True
    camera = PiCamera()
    camera.resolution = (RESOLUTIONX, RESOLUTIONY)
    camera.rotation = ROTATION
    camera.brightness = BRIGHTNESS
    camera.contrast = CONTRAST
    camera.framerate = FRAMEPS
    videoprefix = "RPiR-"

    while record_thread_status is True:
        if(TIMESTAMP is True):
            camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            camera.annotate_background = picamera.Color('black')
        camera.start_recording(OUTPUTPATHVIDEO + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.h264', format='h264', quality=QUALITY)
        logging.info(f"Recording: {OUTPUTPATHVIDEO + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.h264'}")
        CleanOldFiles()
        filetime = 0
        while record_thread_status is True and filetime <= VIDEOLENGTH:
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
    if(SHUTTEREXISTS is True):
        logging.info("Close Shutter")
        shutter_open = False
    camera.close()
    time.sleep(1)
def picamstarttlapse():
    global tlapse_thread_status
    global shutter_open
    if(SHUTTEREXISTS is True):
        logging.info("Open Shutter")
        shutter_open = True
    camera = PiCamera()
    camera.resolution = (1600, 1200)
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

    if(SHUTTEREXISTS is True):
        logging.info("Close Shutter")
        shutter_open = False
    camera.close()
    time.sleep(1)
def picamstartstream():
    global stream_thread_status
    global shutter_open
    if(SHUTTEREXISTS is True):
        logging.info("Open Shutter")
        shutter_open = True
    
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

    time.sleep(1)
    if(SHUTTEREXISTS is True):
        logging.info("Close Shutter")
        shutter_open = False

if __name__ == "__main__":
    patterns = "*"
    ignore_patterns = ""
    ignore_directories = True
    case_sensitive = False
    my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
    my_event_handler.on_created = on_created
    my_observer = Observer()
    my_observer.schedule(my_event_handler, WATCHPATH, recursive=False)
    my_observer.start()

    global record_thread_status
    record_thread_status = False
    global stream_thread_status
    stream_thread_status = False
    global tlapse_thread_status
    tlapse_thread_status = False
    global shutter_open
    shutter_open = False
    
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
    logging.debug(f"FREESPACELIMIT = {FREESPACELIMIT}")
    logging.debug(f"TAKESNAPSHOT = {TAKESNAPSHOT}")
    logging.debug(f"SHUTTEREXISTS = {SHUTTEREXISTS}")
    
    record_thread = threading.Thread(target = picamstartrecord)
    stream_thread = threading.Thread(target = picamstartstream)          
    tlapse_thread = threading.Thread(target = picamstarttlapse)

    if(path.exists(WATCHPATH + "/pi-record") == True and path.exists(WATCHPATH + "/pi-stream") == True):
        silentremove(WATCHPATH + "/pi-stream")

    if(path.exists(WATCHPATH + "/pi-record") == True and path.exists(WATCHPATH + "/pi-tlapse") == True):
        silentremove(WATCHPATH + "/pi-record")

    if(path.exists(WATCHPATH + "/pi-tlapse") == True and path.exists(WATCHPATH + "/pi-stream") == True):
        silentremove(WATCHPATH + "/pi-stream")

    if(path.exists(WATCHPATH + "/pi-tlapse") == True and path.exists(WATCHPATH + "/pi-stream") == True and path.exists(WATCHPATH + "/pi-record") == True):
        silentremove(WATCHPATH + "/pi-stream")
        silentremove(WATCHPATH + "/pi-record")

    try:
        while True:
            time.sleep(1)

            if(path.exists(WATCHPATH + "/pi-stop") is True):
                logging.info("Force Quit Instruction ")
                silentremove(WATCHPATH + "/pi-stop")
                os._exit(1)

            if(path.exists(WATCHPATH + "/pi-reboot") is True):
                logging.info("Force Reboot Instruction ")
                silentremove(WATCHPATH + "/pi-reboot")
                os.system("sudo reboot now >/dev/null 2>&1")    

            if(path.exists(WATCHPATH + "/pi-record") is True and record_thread.is_alive() is False and stream_thread.is_alive() is False and tlapse_thread.is_alive() is False):
                record_thread_status = True
                record_thread.start()
                logging.info(f"Start Record : {record_thread}, {record_thread.is_alive()}, {record_thread_status}, {threading.active_count()}")

            if(path.exists(WATCHPATH + "/pi-tlapse") == True and record_thread.is_alive() is False and stream_thread.is_alive() is False and tlapse_thread.is_alive() is False):
                tlapse_thread_status = True
                tlapse_thread.start()
                logging.info(f"Start Timelapse : {tlapse_thread}, {tlapse_thread.is_alive()}, {tlapse_thread_status}, {threading.active_count()}")

            elif(path.exists(WATCHPATH + "/pi-stream") == True and record_thread.is_alive() is False and stream_thread.is_alive() is False and tlapse_thread.is_alive() is False):
                stream_thread_status = True
                stream_thread.start()
                logging.info(f"Start Stream : {stream_thread}, {stream_thread.is_alive()}, {stream_thread_status}, {threading.active_count()}")

            elif(path.exists(WATCHPATH + "/pi-record") == False and record_thread.is_alive() is True):
                record_thread_status = False
                record_thread.join()
                record_thread = threading.Thread(target = picamstartrecord)
                logging.info(f"Stop Record : {record_thread}, {record_thread.is_alive()}, {record_thread_status}, {threading.active_count()}")

            elif(path.exists(WATCHPATH + "/pi-tlapse") == False and  tlapse_thread.is_alive() is True):
                tlapse_thread_status = False
                tlapse_thread.join()
                tlapse_thread = threading.Thread(target = picamstartrecord)
                logging.info(f"Stop Timelapse : {tlapse_thread}, {tlapse_thread.is_alive()}, {tlapse_thread_status}, {threading.active_count()}")

            elif(path.exists(WATCHPATH + "/pi-stream") == False and stream_thread.is_alive() is True):
                stream_thread_status = False
                stream_thread.join()
                stream_thread = threading.Thread(target = picamstartstream)
                logging.info(f"Stop Stream : {stream_thread}, {stream_thread.is_alive()}, {stream_thread_status}, {threading.active_count()}")

            # Make sure the shutter is open every ten seconds.
            if(int(dt.datetime.now().strftime('%S')) % 10 == 3):
                if(shutter_open is True and SHUTTEREXISTS is True):
                    os.system("shutter 99 >/dev/null 2>&1")
                else:
                    os.system("shutter 1 >/dev/null 2>&1")
            
            # Log temperature every minute.
            if(int(dt.datetime.now().strftime('%S')) % 60 == 15):
                logging.debug(f"Temperature = {CPUTemperature().temperature}C")

    except KeyboardInterrupt:
        #record_thread.join()
        #stream_thread.join()
        my_observer.stop()
        my_observer.join()

