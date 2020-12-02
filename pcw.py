# Python Script to start and stop Pi Camera based on the existence of named trigger files.
# https://github.com/richardjj27/PiCamWatcher

# Testing Required:
#  Check if any data is missed at file swapover and jpg snapshot time.
#  Setting framerate to something other than 30 gets weird results.
#
# Bugs:
#  Script seems to stop with a thread running and doesn't resolve until a reboot.
#  Threading cuts gaps but creates race conditions.

# Todo:
#  Tidy up imports - learn
#  Clean up the code and make more pythony - learn.
#  Check the regex constant validation.
#  Add an IFTTT option.
#  Maybe we need a 'stop' when space runs out and there are no other options (i.e. the archive filling up?)
#  Paths in ini file shouldn't be forced to lowercase

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
#*   Brightness
#*   Contrast
#*   AWB_Mode   
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
#* Add a 'script started' logging event.
#* Get global variables sorted out - learn
#* Added an archive option for images (keep this sync'd file small for OneDrive)
#* Make the timing between videos and images absolute rather than an arbitrary 'wait for' time period.
#* Tidy up contstants
#* Now creates transient folders if they dont' already exist.
#* Make it run as a service/startup.  Howto in OneNote and sample .service files.
#* Add a 'zero' option to ignore archive/cleaning operations. / solved by just setting image archive path to /dev/null
#* Added a function to allow for a ctrl-c to exit gracefully.
#* Do some validity checks for constants.
#* Moved constants to config file.
#* Added the ability to override constants from withint pi-*** files.
#* At startup, also Use pi-*** to provide overriding config.
#* Make 'convert to MP4' an option (and threaded)
#* Make config text case agnostic
#* Added a 'log system status' function - currently runs every minute.
#* Added more info to logging.
#* Added space left in each target to logging.
#* Archive/purge in a thread.
#* Make the cleanup function more regularly
#* Make 'move' commands use os.command with switches to allow for overwrite
#* Add Audio alerts for events
#* Add option to turn this off or on.
#* Added 'total file count' to status config.
#* Close shutter on exit.

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
from signal import signal, SIGINT
from sys import exit
import configparser
import re

global RUNNINGPATH, BINARYPATH,LOGPATH, VIDEOPATH, IMAGEPATH, IMAGEARCHIVEPATH, WATCHPATH, AUDIOPATH
global RESOLUTIONX, RESOLUTIONY, BRIGHTNESS, CONTRAST, AWBMODE, FRAMEPS, ROTATION, QUALITY
global VIDEOINTERVAL, TIMELAPSEINTERVAL, STREAMPORT, TIMESTAMP
global VIDEOPATHFSLIMIT, IMAGEPATHLIMIT, IMAGEARCHIVEPATHLIMIT, TAKESNAPSHOT, MEDIAFORMAT
global SHUTTEREXISTS
global trigger_flag
global process_flag

trigger_flag = int('000000000000', 2)
process_flag = int('000000000000', 2)

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

# start         0   A
# record        1   R
# stream        2   S
# tlapse        3   T
# stoprecord    4   O
# stopstream    5   P
# stoptlapse    6   Q
# video         7   V
# image         8   I
# reboot        9   B
# exit          10  Z

# VIDEOPATH = "/media/usb/video"
# IMAGEPATH = "/media/usb/picamsync/image"
# IMAGEARCHIVEPATH = "/media/usb/imagearchive" # Real path or 'null'
# WATCHPATH = "/media/usb/picamsync/watch" # Real path

# RESOLUTIONX = 1600 # [<= 1920]
# RESOLUTIONY = 1200 # [<= 1200]
# BRIGHTNESS = 50 # [1 > 100]
# CONTRAST = 0 # [-100 > +100]
# AWBMODE = "auto" # 'off','auto','sunlight','cloudy','shade','tungsten','fluorescent','incandescent','flash','horizon'
# FRAMEPS = 30 # [1-60]
# ROTATION = 0 # Degrees of rotation to orient camera correctly. [0,90,180,270]
# QUALITY = 20 # 1 is best, 40 is worst. [1-40]

# VIDEOINTERVAL = 5 # Recorded videos will rotate at this number of minutes. # [<= 30]
# TIMELAPSEINTERVAL = 1 # Timelapse JPGs will be taken at this number of seconds. [>=5, [<=30]]
# STREAMPORT = 42687 # [>= 30000, <=65535]
# TIMESTAMP = True # Will a timestamp be put on photos and videos? [True or False]

# VIDEOPATHFSLIMIT = 10240 # At how many MB free should old videos be deleted. [>=1024]
# IMAGEPATHLIMIT = 2048 # Maximum Size of JPG images to be kept (in MB) before being moved to IMAGEARCHIVEPATH [>=64]
# IMAGEARCHIVEPATHLIMIT = 2048 # At how many MB free should old images be deleted. [>=64]
# TAKESNAPSHOT = True # Take a regular snapshot JPG when recording a video file. [True or False]
# SHUTTEREXISTS = True # Does the camera have a shutter which needs opening? [True or False]

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
                while (testBit(trigger_flag, 1) != 0):
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
        logging.info(f"{self.client_address[0]} {self.requestline}")
        return

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

def get_foldersize(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                try:
                    total_size += os.path.getsize(fp)
                except:
                    pass
    return total_size

def logsystemstatus():             
    # Log Temperature
    #logging.debug("========================================================================================")
    if(CPUTemperature().temperature) > 75:
        logging.warning(f"***TEMPERATURE      {(CPUTemperature().temperature):.1f}°C")
    elif (CPUTemperature().temperature) > 65:
        logging.debug(f"#**TEMPERATURE      {(CPUTemperature().temperature):.1f}°C")
    elif (CPUTemperature().temperature) > 55:
        logging.debug(f"# *TEMPERATURE      {(CPUTemperature().temperature):.1f}°C")
    else:       
        logging.info(f"#  TEMPERATURE      {(CPUTemperature().temperature):.1f}°C")

    # Log disk capacity usage
    vp_usage = shutil.disk_usage(VIDEOPATH)
    ip_usage = shutil.disk_usage(IMAGEPATH)
    ap_usage = shutil.disk_usage(IMAGEARCHIVEPATH)
    rp_usage = shutil.disk_usage(RUNNINGPATH)

    vp_size = get_foldersize(VIDEOPATH)
    ip_size = get_foldersize(IMAGEPATH)
    ap_size = get_foldersize(IMAGEARCHIVEPATH)

    vp_left = (vp_usage.free - (VIDEOPATHFSLIMIT * 1048576 ))
    ip_left = ((IMAGEPATHLIMIT * 1048576) - ip_size)
    ap_left = ((IMAGEARCHIVEPATHLIMIT * 1048576 ) - ap_size)

    vp_count = len(os.listdir(VIDEOPATH))
    ip_count = len(os.listdir(IMAGEPATH))
    ap_count = len(os.listdir(IMAGEARCHIVEPATH))
    
    logging.debug(f"#  VIDEOPATH        VolS: {((vp_usage.total) / 1048576):,.0f}MB, VolF: {((vp_usage.free) / 1048576):,.0f}MB, VolU: {((vp_usage.used / vp_usage.total) * 100):.1f}%, FolU: {((vp_size) / 1048576):,.0f}MB ({vp_count}), FolF: {((vp_left) / 1048576):,.0f}MB")
    logging.debug(f"#  IMAGEPATH        VolS: {((ip_usage.total) / 1048576):,.0f}MB, VolF: {((ip_usage.free) / 1048576):,.0f}MB, VolU: {((ip_usage.used / ip_usage.total) * 100):.1f}%, FolU: {((ip_size) / 1048576):,.0f}MB ({ip_count}), FolF: {((ip_left) / 1048576):,.0f}MB")
    logging.debug(f"#  IMAGEARCHIVEPATH VolS: {((ap_usage.total) / 1048576):,.0f}MB, VolF: {((ap_usage.free) / 1048576):,.0f}MB, VolU: {((ap_usage.used / ap_usage.total) * 100):.1f}%, FolU: {((ap_size) / 1048576):,.0f}MB ({ap_count}), FolF: {((ap_left) / 1048576):,.0f}MB")
    logging.debug(f"#  RUNNINGPATH      VolS: {((rp_usage.total) / 1048576):,.0f}MB, VolF: {((rp_usage.free) / 1048576):,.0f}MB, VolU: {((rp_usage.used / rp_usage.total) * 100):.1f}%")
    logging.debug(f"#  FLAGS            TRIGGERFLAG: {trigger_flag:010b}, PROCESSFLAG: {process_flag:010b}")
    logging.debug(f"#  RECORDTHREAD     {record_thread}")
    logging.debug(f"#  STREAMTHREAD     {stream_thread}")
    logging.debug(f"#  TLAPSETHREAD     {tlapse_thread}")
    #logging.debug("========================================================================================")

def cleanoldfiles():
    freespace = shutil.disk_usage(VIDEOPATH).free / 1048576
    # clean video files (based on free space) > trash
    if(freespace < VIDEOPATHFSLIMIT):
        while (freespace < VIDEOPATHFSLIMIT):
            list_of_files = fnmatch.filter(os.listdir(VIDEOPATH), "RPi*.*")
            full_path = [VIDEOPATH + "/{0}".format(x) for x in list_of_files]
            oldest_file = min(full_path, key=os.path.getctime)
            silentremove(oldest_file, " (" + ('{:,.2f}'.format(freespace)) + "MB)")
            freespace = shutil.disk_usage(VIDEOPATH).free / 1048576
    
    # clean image files (based on folder size) > archive
    imageusedspace = (sum(d.stat().st_size for d in os.scandir(IMAGEPATH) if d.is_file()) / 1048576)
    if(imageusedspace > IMAGEPATHLIMIT):
        while (imageusedspace > IMAGEPATHLIMIT):
            list_of_files = fnmatch.filter(os.listdir(IMAGEPATH), "RPi*.*")
            full_path = [IMAGEPATH + "/{0}".format(x) for x in list_of_files]
            oldest_file = min(full_path, key=os.path.getctime)
            if(IMAGEARCHIVEPATH.lower() != "null"):
                silentmove(oldest_file, IMAGEARCHIVEPATH, " (" + ('{:,.2f}'.format(imageusedspace)) + "MB)")
            else:
                silentremove(oldest_file, " (" + ('{:,.2f}'.format(imageusedspace)) + "MB)")
            imageusedspace = (sum(d.stat().st_size for d in os.scandir(IMAGEPATH) if d.is_file()) / 1048576)

    # clean archive image files (based on folder size) > trash
    if(IMAGEARCHIVEPATH.lower() != "null"):
        imageusedspace = (sum(d.stat().st_size for d in os.scandir(IMAGEARCHIVEPATH) if d.is_file()) / 1048576)
        if(imageusedspace > IMAGEARCHIVEPATHLIMIT):
            while (imageusedspace > IMAGEARCHIVEPATHLIMIT):
                list_of_files = fnmatch.filter(os.listdir(IMAGEARCHIVEPATH), "RPi*.*")
                full_path = [IMAGEARCHIVEPATH + "/{0}".format(x) for x in list_of_files]
                oldest_file = min(full_path, key=os.path.getctime)
                silentremove(oldest_file, " (" + ('{:,.2f}'.format(imageusedspace)) + "MB)")
                imageusedspace = (sum(d.stat().st_size for d in os.scandir(IMAGEARCHIVEPATH) if d.is_file()) / 1048576)

def testBit(int_type, offset):
    # testBit() returns a nonzero result, 2**offset, if the bit at 'offset' is one.
    mask = 1 << offset
    return(int_type & mask)

def setBit(int_type, offset):
    # setBit() returns an integer with the bit at 'offset' set to 1.
    mask = 1 << offset
    return(int_type | mask)

def clearBit(int_type, offset):
    # clearBit() returns an integer with the bit at 'offset' cleared.
    mask = ~(1 << offset)
    return(int_type & mask)

def toggleBit(int_type, offset):
    # toggleBit() returns an integer with the bit at 'offset' inverted, 0 -> 1 and 1 -> 0.
    mask = 1 << offset
    return(int_type ^ mask)

def read_config(config_file, section, item, rule, default, retain = ""):
    # Function to read a line from a config file and validate against a stated regular expression.
    # http://gamon.webfactional.com/regexnumericrangegenerator/
    
    config = configparser.ConfigParser()
    pattern = re.compile(rule)

    try:
        config.read(config_file)
    except:
        if(default == "retain"):
            output = retain
        else:
            output = default

    try:
        input = (config[section][item])
        if(pattern.match(input)):
            output = input
        elif(default == "terminate"):
            os._exit(1)
        else:
            output = default
    except:
        if(default == "retain"):
            output = retain
        else:
            output = default

    # if the value is new or has changed, log it.
    if(output != retain):
        logging.debug(f"%  {item} = {output}")
    return output

def on_created(event):
    global trigger_flag
    global RESOLUTIONX, RESOLUTIONY, BRIGHTNESS, CONTRAST, AWBMODE, FRAMEPS, ROTATION, QUALITY
    global VIDEOINTERVAL, TIMELAPSEINTERVAL, SNAPSHOTINTERVAL, STREAMPORT, TIMESTAMP

    # check for constants changed in new trigger file.

    src_filename = os.path.basename(event.src_path)

    if ("pi-record" == src_filename) or ("pi-stream" == src_filename) or ("pi-tlapse" == src_filename):
        # These values can be overridden within the trigger file.
        RESOLUTIONX = int(read_config(event.src_path, "CAMERA", "RESOLUTIONX", "^(6[4-8][0-9]|69[0-9]|[7-9][0-9]{2}|1[0-8][0-9]{2}|19[01][0-9]|1920)$", "retain", RESOLUTIONX)) # 640 > 1920
        RESOLUTIONY = int(read_config(event.src_path, "CAMERA", "RESOLUTIONY", "^(48[0-9]|49[0-9]|[5-9][0-9]{2}|1[0-5][0-9]{2}|1600)$", "retain", RESOLUTIONY)) # 480 > 1600
        BRIGHTNESS = int(read_config(event.src_path, "CAMERA", "BRIGHTNESS", "^([1-9]|[1-8][0-9]|9[0-9]|100)$", "retain", BRIGHTNESS)) # 1 > 100
        CONTRAST = int(read_config(event.src_path, "CAMERA", "CONTRAST", "^-?([0-9]|[1-8][0-9]|9[0-9]|100)$", "retain", CONTRAST)) # -100 > +100
        AWBMODE = read_config(event.src_path, "CAMERA", "AWBMODE", "(?:^|(?<= ))(off|auto|sunlight|cloudy|shade|tungsten|fluorescent|incandescent|flash|horizon)(?:(?= )|$)", "retain", AWBMODE) # off|auto|sunlight|cloudy|shade|tungsten|fluorescent|incandescent|flash|horizon
        FRAMEPS = int(read_config(event.src_path, "CAMERA", "FRAMEPS", "^([1-9]|[1-5][0-9]|60)$", "retain", FRAMEPS)) # 1 > 60
        ROTATION = int(read_config(event.src_path, "CAMERA", "ROTATION", "(?:^|(?<= ))(0|90|180|270)(?:(?= )|$)", "retain", ROTATION)) # 0|90|180|270
        QUALITY = int(read_config(event.src_path, "CAMERA", "QUALITY", "^([1-9]|[1-3][0-9]|40)$", "retain", QUALITY)) # 1 > 40

        VIDEOINTERVAL = int(read_config(event.src_path, "OUTPUT", "VIDEOINTERVAL", "^([1-9]|[12][0-9]|30)$", "retain", VIDEOINTERVAL)) # 1 > 30
        TIMELAPSEINTERVAL = int(read_config(event.src_path, "OUTPUT", "TIMELAPSEINTERVAL", "^([5-9]|[12][0-9]|30)$", "retain", TIMELAPSEINTERVAL)) # 5 > 30
        SNAPSHOTINTERVAL = int(read_config(CONFIG_FILE,"OUTPUT", "SNAPSHOTINTERVAL", "^([5-9]|[12][0-9]|30)$", "retain", SNAPSHOTINTERVAL)) # 15 > 30

        STREAMPORT = int(read_config(event.src_path, "OUTPUT", "STREAMPORT", "^([3-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$", "retain", STREAMPORT)) # 30000 > 65535
        TIMESTAMP = read_config(event.src_path, "OUTPUT", "TIMESTAMP", "(?:^|(?<= ))(True|False)(?:(?= )|$)", "retain", TIMESTAMP) # True|False

    if "pi-record" == src_filename:
        silentremoveexcept(WATCHPATH, "pi-record")
        trigger_flag = setBit(trigger_flag, 0)
    if "pi-stream" == src_filename:
        silentremoveexcept(WATCHPATH, "pi-stream")
        trigger_flag = setBit(trigger_flag, 1)
    if "pi-tlapse" == src_filename:
        silentremoveexcept(WATCHPATH, "pi-tlapse")
        trigger_flag = setBit(trigger_flag, 2)
    if "pi-stoprecord" == src_filename:
        silentremove(event.src_path)
        silentremove(WATCHPATH + "pi-record")
    if "pi-stopstream" == src_filename:
        silentremove(event.src_path)
        silentremove(WATCHPATH + "pi-stream")
    if "pi-stoptlapse" == src_filename:
        silentremove(event.src_path)
        silentremove(WATCHPATH + "pi-tlapse")
    if "pi-stopall" == src_filename:
        trigger_flag = setBit(trigger_flag, 6)
        silentremove(event.src_path)
        silentremove(WATCHPATH + "pi-record")
        silentremove(WATCHPATH + "pi-stream")
        silentremove(WATCHPATH + "pi-tlapse")
    if "pi-stopscript" == src_filename:
        trigger_flag = setBit(trigger_flag, 7)
        silentremove(event.src_path)
    if "pi-reboot" == src_filename:
        trigger_flag = setBit(trigger_flag, 8)
        silentremove(event.src_path)

def on_deleted(event):
    global trigger_flag
    src_filename = os.path.basename(event.src_path)
    
    if "pi-record" == src_filename:
        trigger_flag = setBit(trigger_flag, 3)
    if "pi-stream" == src_filename:
        trigger_flag = setBit(trigger_flag, 4)
    if "pi-tlapse" == src_filename:
        trigger_flag = setBit(trigger_flag, 5)

def silentremove(filename, message = ""):
    try:
        logging.info(f"d  Delete : {filename}{message}")
        os.remove(filename)
    except:
        pass

def silentmove(filename, destination, message = ""):
    #try:
    logging.info(f"d  Archive : {filename}{message}")
    os.system("mv " + filename + " " + destination + ">/dev/null 2>&1")
        #shutil.move(filename, destination)
    #except:
    #    pass

def silentremoveexcept(keeppath, keepfilename):
    for entry in os.scandir(keeppath):
        if ((entry.name) != keepfilename and entry.name.startswith("pi-") and entry.is_file()):
            silentremove(entry.path)

def createfolder(foldername):
    try:
        os.makedirs(foldername)
        logging.info(f"   Create Folder : {foldername}")
    except:
        pass

def playsound(event):
    if(PLAYSOUND == 'true'):
        logging.debug(f"=  Start Sound : {event}.mp3")
        os.system("(mpg321 -g 15 " + AUDIOPATH + "/" + event + ".mp3&>/dev/null &) >/dev/null 2>&1")
        #logging.debug(f"=Finish Sound : {event}")

def open_shutter():
    if(SHUTTEREXISTS == 'true') and ((int(time.time()) % 25) == 3):
        # logging.info("shutter open")
        os.system(BINARYPATH + "/shutter 99 >/dev/null 2>&1")

def close_shutter():
    if(SHUTTEREXISTS == 'true') and ((int(time.time()) % 25) == 3):
        # logging.info("shutter closed")
        os.system(BINARYPATH + "/shutter 0 >/dev/null 2>&1")

def converttomp4(filename):
    convertstring = "ffmpeg -r " + str(FRAMEPS) + " -i " + VIDEOPATH + "/" + filename + ".h264 -vcodec copy " + VIDEOPATH + "/" + filename + ".mp4"
    logging.info(f"c  Converting : {filename}.h264 to mp4")
    os.system(convertstring + " >/dev/null 2>&1")
    if(MEDIAFORMAT == "mp4"):
        silentremove(VIDEOPATH + "/" + filename + ".h264", " (converted)")

def picamstartrecord():
    global trigger_flag
    global process_flag
    global record_thread

    playsound("record")
    time.sleep(1)
    timelapsedelta = 0

    #logging.info("1")
    print("x")
    camera = PiCamera()
    print("y")
    print(camera)
    camera.resolution = (RESOLUTIONX, RESOLUTIONY)
    camera.rotation = ROTATION
    camera.brightness = BRIGHTNESS
    camera.contrast = CONTRAST
    camera.awb_mode = AWBMODE
    camera.framerate = FRAMEPS
    if(TIMESTAMP == 'true'):
        camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        camera.annotate_background = picamera.Color('black')
    videoprefix = "RPiR-"

    #logging.info("2")

    # add a delay to ensure recording starts > 5 and < 55 to avoid clashing with the snapshot image.
    # while (int(time.time()) % 60 <= 5 or int(time.time()) % 60 >= 55):
    #     time.sleep(5)

    while (testBit(trigger_flag, 0) != 0):
        filetime = int(time.time() / (VIDEOINTERVAL * 60))
        #cleanoldfiles()
        
        #logging.info("3")
        outputfilename = datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S')
        playsound("video")
        camera.start_recording(VIDEOPATH + "/" + outputfilename + '.h264', format='h264', quality=QUALITY)
        logging.info(f"V+ Start Recording Video : {VIDEOPATH}/{outputfilename}.h264")
        while (testBit(trigger_flag, 0) != 0) and (int(time.time() / (VIDEOINTERVAL * 60)) <= filetime):
            
            #logging.info("4")
            if(TIMESTAMP == 'true'):
                camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if(TAKESNAPSHOT == 'true'):
                time.sleep(1)
                # Take a snapshot jpg every {SNAPSHOTINTERVAL} seconds
                if(int((time.time() + 5) / SNAPSHOTINTERVAL) > timelapsedelta):
                    logging.info(f"I  Take Snapshot Image : {IMAGEPATH + '/' + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.jpg'}")
                    playsound("image")
                    camera.capture(IMAGEPATH + "/" + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.jpg')
                    timelapsedelta = (int((time.time() + 5) / SNAPSHOTINTERVAL))
        camera.stop_recording()
        logging.info(f"V- Stop Recording Video : {VIDEOPATH}/{outputfilename}.h264")
        if(MEDIAFORMAT == "mp4" or MEDIAFORMAT == "both"):
            convert_thread = threading.Thread(target=converttomp4, args=(outputfilename,), name = 'convert_thread', daemon = True)
            convert_thread.start()
            logging.debug(f"#  CONVERTTHREAD     {convert_thread}")

    #logging.info("5")
    camera.close()
    process_flag = clearBit(process_flag, 0)
    
    #logging.info("6")
    time.sleep(1)

def picamstartstream():
    global trigger_flag
    global process_flag
    global stream_thread
    
    playsound("stream")
    time.sleep(1)

    with picamera.PiCamera(resolution='640x480', framerate=12) as camera:
        global output
        output = StreamingOutput()
        #Uncomment the next line to change your Pi's Camera rotation (in degrees)
        camera.rotation = ROTATION
        camera.brightness = BRIGHTNESS
        camera.contrast = CONTRAST
        camera.awb_mode = AWBMODE
        if(TIMESTAMP == 'true'):
            camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            camera.annotate_background = picamera.Color('black')
        camera.start_recording(output, format='mjpeg', quality=40)
        try:
            address = ('', STREAMPORT)
            server = StreamingServer(address, StreamingHandler)
            threadstream = threading.Thread(target = server.serve_forever)
            threadstream.daemon = True
            logging.info(f"S  Open Streaming on port : {STREAMPORT}")
            threadstream.start()
            while (testBit(trigger_flag, 1) != 0):
                if(TIMESTAMP == 'true'):
                    camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                time.sleep(2)
            server.shutdown()
            time.sleep(2)
            #logging.info("Stop Streaming")
            #camera.stop_recording()
        except KeyboardInterrupt:
            pass
        finally:
            #server.server_close()
            camera.stop_recording()
            process_flag = clearBit(process_flag, 1)

def handler(signal_received, frame):
    # Handle any cleanup here
    logging.info("Exiting gracefully")
    close_shutter()
    playsound("exit")
    os._exit(1)

def picamstarttlapse():
    global trigger_flag
    global process_flag
    global tlapse_thread

    playsound("tlapse")
    time.sleep(1)

    camera = PiCamera()
    camera.resolution = (RESOLUTIONX, RESOLUTIONY)
    camera.rotation = ROTATION
    camera.brightness = BRIGHTNESS
    camera.contrast = CONTRAST
    camera.awb_mode = AWBMODE
    if(TIMESTAMP == 'true'):
        camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        camera.annotate_background = picamera.Color('black')
    videoprefix = "RPiT-"

    #filetime = int(time.time() / TIMELAPSEINTERVAL)
    while (testBit(trigger_flag, 2) != 0):
        filetime = int(time.time() / TIMELAPSEINTERVAL)
        #cleanoldfiles()
        if(TIMESTAMP == 'true'):
            camera.annotate_text = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logging.info(f"I  Take Timelapse Image : {IMAGEPATH + '/' + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.jpg'}")
        playsound("image")
        camera.capture(IMAGEPATH + "/" + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.jpg')
        while (testBit(trigger_flag, 2) != 0) and (int(time.time() / TIMELAPSEINTERVAL) <= filetime):
            time.sleep(.5)
    camera.close()
    process_flag = clearBit(process_flag, 2)
    time.sleep(1)

if __name__ == "__main__":
    # Get constants from ini file.  
    RUNNINGPATH = os.path.dirname(os.path.realpath(__file__))
    LOGPATH = RUNNINGPATH + "/logs"
    BINARYPATH = RUNNINGPATH + "/bin"
    CONFIG_FILE = RUNNINGPATH + "/pcw.ini"

    # Intercept Ctrl-C to gracefully exit
    signal(SIGINT, handler)

    # Setup logging (quiet background)
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)-20s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S', filename=LOGPATH + '/pcw-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.log', filemode='w')
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)-20s %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S")
    console.setFormatter(formatter)
    logging.getLogger().addHandler(console)

    logging.debug(f"%  RUNNINGPATH = {RUNNINGPATH}")
    logging.debug(f"%  LOGPATH = {LOGPATH}")
    logging.debug(f"%  BINARYPATH = {BINARYPATH}")
    logging.debug(f"%  CONFIG_FILE = {CONFIG_FILE}")

    VIDEOPATH = read_config(CONFIG_FILE,"PATH", "VIDEOPATH", "^/|(/[\w-]+)+$", "terminate") # reasonable file path with no trailing slash
    IMAGEPATH = read_config(CONFIG_FILE,"PATH", "IMAGEPATH", "^/|(/[\w-]+)+$", "terminate") # reasonable file path with no trailing slash
    IMAGEARCHIVEPATH = read_config(CONFIG_FILE,"PATH", "IMAGEARCHIVEPATH", "^/|(/[\w-]+)+$", "terminate") # reasonable file path with no trailing slash (or null)
    WATCHPATH = read_config(CONFIG_FILE,"PATH", "WATCHPATH", "^/|(/[\w-]+)+$", "terminate") # reasonable file path with no trailing slash
    AUDIOPATH = read_config(CONFIG_FILE,"PATH", "AUDIOPATH", "^/|(/[\w-]+)+$", "terminate") # reasonable file path with no trailing slash

    RESOLUTIONX = int(read_config(CONFIG_FILE,"CAMERA", "RESOLUTIONX", "^(6[4-8][0-9]|69[0-9]|[7-9][0-9]{2}|1[0-8][0-9]{2}|19[01][0-9]|1920)$", "800")) # 640 > 1920
    RESOLUTIONY = int(read_config(CONFIG_FILE,"CAMERA", "RESOLUTIONY", "^(48[0-9]|49[0-9]|[5-9][0-9]{2}|1[0-5][0-9]{2}|1600)$", "480")) # 480 > 1600
    BRIGHTNESS = int(read_config(CONFIG_FILE,"CAMERA", "BRIGHTNESS", "^([1-9]|[1-8][0-9]|9[0-9]|100)$", "50")) # 1 > 100
    CONTRAST = int(read_config(CONFIG_FILE,"CAMERA", "CONTRAST", "^-?([0-9]|[1-8][0-9]|9[0-9]|100)$", "0")) # -100 > +100
    AWBMODE = read_config(CONFIG_FILE,"CAMERA", "AWBMODE", "(?:^|(?<= ))(off|auto|sunlight|cloudy|shade|tungsten|fluorescent|incandescent|flash|horizon)(?:(?= )|$)", "auto") # off|auto|sunlight|cloudy|shade|tungsten|fluorescent|incandescent|flash|horizon
    FRAMEPS = int(read_config(CONFIG_FILE,"CAMERA", "FRAMEPS", "^([1-9]|[1-5][0-9]|60)$", "30")) # 1 > 60
    ROTATION = int(read_config(CONFIG_FILE,"CAMERA", "ROTATION", "(?:^|(?<= ))(0|90|180|270)(?:(?= )|$)", "0")) # 0|90|180|270
    QUALITY = int(read_config(CONFIG_FILE,"CAMERA", "QUALITY", "^([1-9]|[1-3][0-9]|40)$", "20")) # 1 > 40

    VIDEOINTERVAL = int(read_config(CONFIG_FILE,"OUTPUT", "VIDEOINTERVAL", "^([1-9]|[12][0-9]|30)$", "30")) # 1 > 30
    TIMELAPSEINTERVAL = int(read_config(CONFIG_FILE,"OUTPUT", "TIMELAPSEINTERVAL", "^([5-9]|[12][0-9]|30)$", "30")) # 5 > 30
    SNAPSHOTINTERVAL = int(read_config(CONFIG_FILE,"OUTPUT", "SNAPSHOTINTERVAL", "^([5-9]|[12][0-9]|30)$", "30")) # 15 > 30

    STREAMPORT = int(read_config(CONFIG_FILE,"OUTPUT", "STREAMPORT", "^([3-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$", "42687")) # 30000 > 65535
    TIMESTAMP =  read_config(CONFIG_FILE,"OUTPUT", "TIMESTAMP", "(?:^|(?<= ))(true|false)(?:(?= )|$)", "true") # True|False
    MEDIAFORMAT = read_config(CONFIG_FILE,"OUTPUT", "MEDIAFORMAT", "(?:^|(?<= ))(h264|mp4|both)(?:(?= )|$)", "h264") # True|False

    VIDEOPATHFSLIMIT = int(read_config(CONFIG_FILE,"STORAGE", "VIDEOPATHFSLIMIT", "", "10240")) # 1024+
    IMAGEPATHLIMIT = int(read_config(CONFIG_FILE,"STORAGE", "IMAGEPATHLIMIT", "", "2048")) # 64+
    IMAGEARCHIVEPATHLIMIT = int(read_config(CONFIG_FILE,"STORAGE", "IMAGEARCHIVEPATHLIMIT", "", "2048")) # 64+ 
    TAKESNAPSHOT = read_config(CONFIG_FILE,"STORAGE", "TAKESNAPSHOT", "(?:^|(?<= ))(true|false)(?:(?= )|$)", "true") # True|False

    SHUTTEREXISTS = read_config(CONFIG_FILE,"MISC", "SHUTTEREXISTS", "(?:^|(?<= ))(true|false)(?:(?= )|$)", "true") # True|False
    PLAYSOUND = read_config(CONFIG_FILE,"MISC", "PLAYSOUND", "(?:^|(?<= ))(true|false)(?:(?= )|$)", "true") # True|False
    
    playsound("start")
    time.sleep(1)

    # Create file system watcher.
    my_event_handler = PatternMatchingEventHandler(patterns=['*pi-*'], ignore_patterns=[], ignore_directories=True, case_sensitive=True)
    my_event_handler.on_created = on_created
    my_event_handler.on_deleted = on_deleted
    my_observer = Observer()
    my_observer.schedule(my_event_handler, WATCHPATH, recursive=False)

    record_thread = threading.Thread(target = picamstartrecord, name = 'record_thread')
    stream_thread = threading.Thread(target = picamstartstream, name = 'stream_thread')
    tlapse_thread = threading.Thread(target = picamstarttlapse, name = 'tlapse_thread')

    # Create any missing, transient folders
    createfolder(VIDEOPATH)
    createfolder(IMAGEPATH)
    if(IMAGEARCHIVEPATH.lower() != "null"):
        createfolder(IMAGEARCHIVEPATH)
    createfolder(WATCHPATH)

    # cleanoldfiles()
    # logsystemstatus()

    # Start watching for events...
    my_observer.start()

    # Set initial state if (single or multiple) files exist.
    # Make this section fake a file creation (rename then copy back) to trigger the event properly.
    if(path.exists(WATCHPATH + "/pi-record") is True):
        shutil.move(WATCHPATH + "/pi-record", WATCHPATH + "/pi-record.tmp")
        shutil.copy(WATCHPATH + "/pi-record.tmp", WATCHPATH + "/pi-record")

    elif(path.exists(WATCHPATH + "/pi-stream") is True):
        shutil.move(WATCHPATH + "/pi-stream", WATCHPATH + "/pi-stream.tmp")
        shutil.copy(WATCHPATH + "/pi-stream.tmp", WATCHPATH + "/pi-stream")

    elif(path.exists(WATCHPATH + "/pi-tlapse") is True):
        shutil.move(WATCHPATH + "/pi-tlapse", WATCHPATH + "/pi-tlapse.tmp")
        shutil.copy(WATCHPATH + "/pi-tlapse.tmp", WATCHPATH + "/pi-tlapse")

    else:
        # Delete everything.
        silentremoveexcept(WATCHPATH, "pi-^^^")

    statuslapsedelta = 0

    # if(int(time.time() / SNAPSHOTINTERVAL) > timelapsedelta):
    #     logging.info(f"Snapshot: {IMAGEPATH + '/' + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.jpg'}")
    #     playsound("image")
    #     camera.capture(IMAGEPATH + "/" + datetime.now().strftime(videoprefix + '%Y%m%d-%H%M%S') + '.jpg')
    #     timelapsedelta = (int(time.time() / SNAPSHOTINTERVAL))

    try:
        while True:
            # Log system status every 1 minutes.
            if(int((time.time() + 15) / 60) > statuslapsedelta):
                cleanoldfiles()
                logsystemstatus()
                statuslapsedelta = (int((time.time() + 15) / 60))
            
            if(testBit(trigger_flag, 3) != 0):
                # Stop Record (bit 3)
                trigger_flag = clearBit(trigger_flag, 3)
                logging.info(f"O  Stop Recording Thread Triggered : {record_thread}, {record_thread.is_alive()}, {threading.active_count()}") 
                trigger_flag = clearBit(trigger_flag, 0)
                while testBit(process_flag, 0) != 0:
                    time.sleep(1)
                record_thread.join()
                logging.info(f"O  Stop Recording Thread Completed : {record_thread}, {record_thread.is_alive()}, {threading.active_count()}")
                playsound("stoprecord")
                record_thread = threading.Thread(target = picamstartrecord, name = 'record_thread')

            if(testBit(trigger_flag, 4) != 0):
                # Stop Stream (bit 4)
                trigger_flag = clearBit(trigger_flag, 4)
                logging.info(f"P  Stop Streaming Thread Triggered : {stream_thread}, {stream_thread.is_alive()}, {threading.active_count()}")
                trigger_flag = clearBit(trigger_flag, 1)
                while testBit(process_flag, 1) != 0:
                    time.sleep(1)
                logging.info(f"P  Stop Streaming Thread Completed: {stream_thread}, {stream_thread.is_alive()}, {threading.active_count()}")
                playsound("stopstream")
                stream_thread = threading.Thread(target = picamstartstream, name = 'stream_thread')   

            if(testBit(trigger_flag, 5) != 0):
                # Stop TimeLapse (bit 5)
                trigger_flag = clearBit(trigger_flag, 5)
                logging.info(f"Q  Stop TimeLapse Thread Triggered : {tlapse_thread}, {tlapse_thread.is_alive()}, {threading.active_count()}")  
                trigger_flag = clearBit(trigger_flag, 2) 
                while testBit(process_flag, 2) != 0:
                    time.sleep(1)                
                tlapse_thread.join()
                logging.info(f"Q  Stop TimeLapse Thread Completed : {tlapse_thread}, {tlapse_thread.is_alive()}, {threading.active_count()}")
                playsound("stoptlapse")
                tlapse_thread = threading.Thread(target = picamstarttlapse, name = 'tlapse_thread')

            if(testBit(trigger_flag, 6) != 0):
                # Stop everything (bit 6)
                process_flag = clearBit(trigger_flag, 3)
                process_flag = clearBit(trigger_flag, 4)
                process_flag = clearBit(trigger_flag, 5)

            # Make sure nothing is running
            if(testBit(process_flag, 0) + testBit(process_flag, 1) + testBit(process_flag, 2) == 0):
                # Make sure nothing is running
                close_shutter()
                
                if((int(time.time()) % 10) == 5):
                    logging.debug(f"   Waiting for something to do.")
          
                if(testBit(trigger_flag, 0) != 0):
                    # Start Record (bit 0)
                    record_thread.start()
                    process_flag = setBit(process_flag, 0)
                    logging.info(f"R  Start Recording Thread : {record_thread}, {record_thread.is_alive()}, {threading.active_count()}")

                if(testBit(trigger_flag, 1) != 0):
                    # Start Stream (bit 1)
                    stream_thread.start()
                    process_flag = setBit(process_flag, 1)
                    logging.info(f"S  Start Streaming Thread : {stream_thread},  {stream_thread.is_alive()}, {threading.active_count()}")

                if(testBit(trigger_flag, 2) != 0):
                    # Start TimeLapse (bit 2)
                    tlapse_thread.start()
                    process_flag = setBit(process_flag, 2)
                    logging.info(f"T  Start TimeLapse Thread : {tlapse_thread}, {tlapse_thread.is_alive()}, {threading.active_count()}")
            else:
                open_shutter()

            if(testBit(trigger_flag, 7) != 0):
                # Exit Script (bit 7)
                logging.info("Z  Force Quit Script Instruction ")
                silentremove(WATCHPATH + "/pi-stopscript")
                os._exit(1)
            
            if(testBit(trigger_flag, 8) != 0):
                # Reboot Device (bit 8)
                logging.info("B  Force Reboot Instruction ")
                playsound("reboot")
                silentremove(WATCHPATH + "/pi-reboot")
                os.system("sudo reboot now >/dev/null 2>&1")    

            time.sleep(1)

    except KeyboardInterrupt:
        my_observer.stop()
        my_observer.join()

