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
#  1 second security option needs a bit of tweaking - video plays at full speed.
#  Put parameters at the top of the script as constants
#    Brightness
#    Anything else?
#  Move the web session stuff to logging.
#  An email stills every x seconds option
#  A 'take instructions through email' option.  GMail API

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

OUTPUTPATH = './video/'
WATCHPATH = "./watch"
RESOLUTIONX = 1600
RESOLUTIONY = 1200
FRAMEPS = 30
QUALITY = 1
VIDEOLENGTH = 300
STREAMPORT = 42687
TIMESTAMP = False
ROTATION = 180
FREESPACELIMIT = 16
TAKESNAPSHOT = True
SHUTTEREXISTS = True

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
    freespace = shutil.disk_usage(OUTPUTPATH).free / 1073741824
    if(freespace < FREESPACELIMIT):
        while (freespace < FREESPACELIMIT):
            list_of_files = fnmatch.filter(os.listdir(OUTPUTPATH), "RPiR-*.*")
            full_path = [OUTPUTPATH + "{0}".format(x) for x in list_of_files]
            oldest_file = min(full_path, key=os.path.getctime)
            logging.info(f"Deleting: {oldest_file}   Freespace: {int(freespace)}GB")
            os.remove(oldest_file)
            freespace = shutil.disk_usage(OUTPUTPATH).free / 1073741824
def on_created(event):
    if "pi-record" in event.src_path:
        silentremove("./watch/pi-stream")
        silentremove("./watch/pi-tlapse")
    elif "pi-stoprecord" in event.src_path:
        silentremove(event.src_path)
        silentremove("./watch/pi-record")

    if "pi-tlapse" in event.src_path:
        silentremove("./watch/pi-stream")
        silentremove("./watch/pi-record")
    elif "pi-stoptlapse" in event.src_path:
        silentremove(event.src_path)
        silentremove("./watch/pi-tlapse")

    if "pi-stream" in event.src_path:
        silentremove("./watch/pi-record")
        silentremove("./watch/pi-tlapse")
    elif "pi-stopstream" in event.src_path:
        silentremove(event.src_path)
        silentremove("./watch/pi-stream")

    if "pi-stopall" in event.src_path:
        silentremove("./watch/pi-record")
        silentremove("./watch/pi-stream")
        silentremove("./watch/pi-tlapse")
        silentremove("./watch/pi-stopall")
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
    
    if(record_mode == "tlapse"):
        camera.framerate = 1
        videoprefix = "RPiT-"
    else:
        camera.framerate = FRAMEPS
        videoprefix = "RPiR-"

    if(TIMESTAMP is True):
        camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    camera.rotation = ROTATION
    camera.annotate_background = picamera.Color('black')
    
    while record_thread_status is True:
        camera.capture(OUTPUTPATH + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.jpg')
        camera.start_recording(OUTPUTPATH + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.h264', format='h264', quality=QUALITY)
        logging.info(f"Recording: {OUTPUTPATH + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.h264'}")
        CleanOldFiles()
        filetime = 0
        while record_thread_status is True and filetime <= VIDEOLENGTH:
            time.sleep(1)
            # Take a snapshot jpg every minute(ish)
            if(int(dt.datetime.now().strftime('%S')) % 60 == 0 and TAKESNAPSHOT is True):
                logging.debug(f"Take snapshot {OUTPUTPATH + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.jpg'}")
                camera.capture(OUTPUTPATH + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.jpg')
            filetime += 1
        time.sleep(.5) 
        camera.stop_recording()
    if(SHUTTEREXISTS is True):
        logging.info("Close Shutter")
        shutter_open = False
    camera.close()
    time.sleep(1)
    
    shutter_open = False
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
        camera.start_recording(output, format='mjpeg', quality=40)
        try:
            address = ('', STREAMPORT)
            server = StreamingServer(address, StreamingHandler)
            threadstream = threading.Thread(target = server.serve_forever)
            threadstream.daemon = True
            logging.info(f"Open Streaming on port {STREAMPORT}")
            threadstream.start()
            while stream_thread_status is True:
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
    global shutter_open
    shutter_open = False
    record_mode = "record"
    
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%d-%b-%y %H:%M:%S', filename='./debug.log', filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

    logging.debug(f"OUTPUTPATH = {OUTPUTPATH}")
    logging.debug(f"WATCHPATH = {WATCHPATH}")
    logging.debug(f"RESOLUTIONX = {RESOLUTIONX}")
    logging.debug(f"RESOLUTIONY = {RESOLUTIONY}")
    logging.debug(f"FRAMEPS = {FRAMEPS}")
    logging.debug(f"QUALITY = {QUALITY}")
    logging.debug(f"VIDEOLENGTH = {VIDEOLENGTH}")
    logging.debug(f"STREAMPORT = {STREAMPORT}")
    logging.debug(f"TIMESTAMP = {TIMESTAMP}")
    logging.debug(f"ROTATION = {ROTATION}")
    logging.debug(f"FREESPACELIMIT = {FREESPACELIMIT}")
    logging.debug(f"TAKESNAPSHOT = {TAKESNAPSHOT}")
    logging.debug(f"SHUTTEREXISTS = {SHUTTEREXISTS}")
    
    record_thread = threading.Thread(target = picamstartrecord)
    stream_thread = threading.Thread(target = picamstartstream)

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

            if(path.exists(WATCHPATH + "/pi-record") is True and record_thread.is_alive() is False and stream_thread.is_alive() is False):
                record_thread_status = True
                record_mode = "record"
                record_thread.start()
                logging.debug(f"Start Record : {record_thread}, {record_thread.is_alive()}, {record_thread_status}, {threading.active_count()}")

            if(path.exists(WATCHPATH + "/pi-tlapse") == True and record_thread.is_alive() is False and stream_thread.is_alive() is False):
                record_thread_status = True
                record_mode = "tlapse"
                record_thread.start()
                logging.debug(f"Start TLapse : {record_thread}, {record_thread.is_alive()}, {record_thread_status}, {threading.active_count()}")

            elif(path.exists(WATCHPATH + "/pi-stream") == True and record_thread.is_alive() is False and stream_thread.is_alive() is False):
                stream_thread_status = True
                stream_thread.start()
                logging.debug(f"Start Stream : {stream_thread}, {stream_thread.is_alive()}, {stream_thread_status}, {threading.active_count()}")

            elif(path.exists(WATCHPATH + "/pi-record") == False and record_mode == "record" and record_thread.is_alive() is True):
                record_thread_status = False
                record_thread.join()
                record_thread = threading.Thread(target = picamstartrecord)
                logging.debug(f"Stop Record : {record_thread}, {record_thread.is_alive()}, {record_thread_status}, {threading.active_count()}")

            elif(path.exists(WATCHPATH + "/pi-tlapse") == False and record_mode == "tlapse" and record_thread.is_alive() is True):
                record_thread_status = False
                record_thread.join()
                record_thread = threading.Thread(target = picamstartrecord)
                logging.debug(f"Stop Record : {record_thread}, {record_thread.is_alive()}, {record_thread_status}, {threading.active_count()}")

            elif(path.exists(WATCHPATH + "/pi-stream") == False and stream_thread.is_alive() is True):
                stream_thread_status = False
                stream_thread.join()
                stream_thread = threading.Thread(target = picamstartstream)
                logging.debug(f"Stop Stream : {stream_thread}, {stream_thread.is_alive()}, {stream_thread_status}, {threading.active_count()}")

            # Make sure the shutter is open every ten seconds.
            if(int(dt.datetime.now().strftime('%S')) % 10 == 0):
                if(shutter_open is True and SHUTTEREXISTS is True):
                    os.system("shutter 99 >/dev/null 2>&1")
                else:
                    os.system("shutter 1 >/dev/null 2>&1")
            
            # Log temperature every minute.
            if(int(dt.datetime.now().strftime('%S')) % 60 == 0):
                logging.debug(f"Temperature = {CPUTemperature().temperature}C")

    except KeyboardInterrupt:
        #record_thread.join()
        #stream_thread.join()
        my_observer.stop()
        my_observer.join()

