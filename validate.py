import logging

import os
import configparser
import re

def read_config(config_file, section, item, rule, default, retain = ""):
    # Function to read a line from a config file and validate against a stated regular expression.
    # http://gamon.webfactional.com/regexnumericrangegenerator/
    
    config = configparser.ConfigParser()
    pattern = re.compile(rule)

    config.read(config_file)

    try:
        input = config[section][item]
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
    return output

def read_constants(config_file):
    global RUNNINGPATH, BINARYPATH,LOGPATH, VIDEOPATH,IMAGEPATH, IMAGEARCHIVEPATH, WATCHPATH
    global RESOLUTIONX, RESOLUTIONY, BRIGHTNESS, CONTRAST, AWBMODE, FRAMEPS, ROTATION, QUALITY
    global VIDEOINTERVAL, TIMELAPSEINTERVAL, STREAMPORT, TIMESTAMP
    global VIDEOPATHFSLIMIT, IMAGEPATHLIMIT, IMAGEARCHIVEPATHLIMIT, TAKESNAPSHOT
    global SHUTTEREXISTS

    config = configparser.ConfigParser()
    config.read(config_file)

    VIDEOPATH = read_config(config_file,"PATH", "VIDEOPATH", "^/|(/[\w-]+)+$", "terminate") # reasonable file path with no trailing
    IMAGEPATH = read_config(config_file,"PATH", "IMAGEPATH", "^/|(/[\w-]+)+$", "terminate") # reasonable file path with no trailing
    IMAGEARCHIVEPATH = read_config(config_file,"PATH", "IMAGEARCHIVEPATH", "^/|(/[\w-]+)+$", "terminate") # reasonable file path with no trailing
    WATCHPATH = read_config(config_file,"PATH", "WATCHPATH", "^/|(/[\w-]+)+$", "terminate") # reasonable file path with no trailing

    RESOLUTIONX = read_config(config_file,"CAMERA", "RESOLUTIONX", "^(6[4-8][0-9]|69[0-9]|[7-9][0-9]{2}|1[0-8][0-9]{2}|19[01][0-9]|1920)$", "800") # 640 > 1920
    RESOLUTIONY = read_config(config_file,"CAMERA", "RESOLUTIONY", "^(48[0-9]|49[0-9]|[5-9][0-9]{2}|1[0-5][0-9]{2}|1600)$", "480") # 480 > 1600
    BRIGHTNESS = read_config(config_file,"CAMERA", "BRIGHTNESS", "^([1-9]|[1-8][0-9]|9[0-9]|100)$", "50") # 1 > 100
    CONTRAST = read_config(config_file,"CAMERA", "CONTRAST", "^-?([0-9]|[1-8][0-9]|9[0-9]|100)$", "0") # -100 > +100
    AWBMODE = read_config(config_file,"CAMERA", "AWBMODE", "(?:^|(?<= ))(off|auto|sunlight|cloudy|shade|tungsten|fluorescent|incandescent|flash|horizon)(?:(?= )|$)", "auto") # off|auto|sunlight|cloudy|shade|tungsten|fluorescent|incandescent|flash|horizon
    FRAMEPS = read_config(config_file,"CAMERA", "FRAMEPS", "^([1-9]|[1-5][0-9]|60)$", "30") # 1 > 60
    ROTATION = read_config(config_file,"CAMERA", "ROTATION", "(?:^|(?<= ))(0|90|180|270)(?:(?= )|$)", "0") # 0|90|180|270
    QUALITY = read_config(config_file,"CAMERA", "QUALITY", "^([1-9]|[1-3][0-9]|40)$", "20") # 1 > 40

    VIDEOINTERVAL = read_config(config_file,"OUTPUT", "VIDEOINTERVAL", "^([1-9]|[12][0-9]|30)$", "30") # 1 > 30
    TIMELAPSEINTERVAL = read_config(config_file,"OUTPUT", "TIMELAPSEINTERVAL", "^([5-9]|[12][0-9]|30)$", "30") # 5 > 30
    STREAMPORT =  read_config(config_file,"OUTPUT", "STREAMPORT", "^([3-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$", "42687") # 30000 > 65535
    TIMESTAMP =  read_config(config_file,"OUTPUT", "TIMESTAMP", "(?:^|(?<= ))(True|False)(?:(?= )|$)", "True") # True|False

    VIDEOPATHFSLIMIT = read_config(config_file,"STORAGE", "VIDEOPATHFSLIMIT", "x", "10240") # 1024+
    IMAGEPATHLIMIT = read_config(config_file,"STORAGE", "IMAGEPATHLIMIT", "x", "2048") # 64+
    IMAGEARCHIVEPATHLIMIT = read_config(config_file,"STORAGE", "IMAGEARCHIVEPATHLIMIT", "x", "2048") # 64+ 
    TAKESNAPSHOT = read_config(config_file,"STORAGE", "TAKESNAPSHOT", "(?:^|(?<= ))(True|False)(?:(?= )|$)", "True") # True|False

    SHUTTEREXISTS = read_config(config_file,"MISC", "SHUTTEREXISTS", "(?:^|(?<= ))(True|False)(?:(?= )|$)", "True") # True|False


    # VIDEOPATH = validate_config(config['PATH']['VIDEOPATH'], "^/|(/[\w-]+)+$", "terminate") + "/" # reasonable file path with no trailing /
    # IMAGEPATH = validate_config(config['PATH']['IMAGEPATH'], "^/|(/[\w-]+)+$", "terminate") + "/" # reasonable file path with no trailing /
    # IMAGEARCHIVEPATH = validate_config(config['PATH']['IMAGEARCHIVEPATH'], "^/|(/[\w-]+)+$", "terminate") + "/" # reasonable file path with no trailing /
    # WATCHPATH = validate_config(config['PATH']['WATCHPATH'], "^/|(/[\w-]+)+$", "terminate") + "/" # reasonable file path with no trailing /

    # RESOLUTIONX = validate_config(config['CAMERA']['RESOLUTIONX'], "^(6[4-8][0-9]|69[0-9]|[7-9][0-9]{2}|1[0-8][0-9]{2}|19[01][0-9]|1920)$", 800) # 640 > 1920
    # RESOLUTIONY = validate_config(config['CAMERA']['RESOLUTIONY'], "^(48[0-9]|49[0-9]|[5-9][0-9]{2}|1[0-5][0-9]{2}|1600)$", 480) # 480 > 1600
    # BRIGHTNESS = validate_config(config['CAMERA']['BRIGHTNESS'], "^([1-9]|[1-8][0-9]|9[0-9]|100)$", "50") # 1 > 100
    # CONTRAST = validate_config(config['CAMERA']['CONTRAST'], "^-?([0-9]|[1-8][0-9]|9[0-9]|100)$", "0") # -100 > +100
    # AWBMODE = validate_config(config['CAMERA']['AWBMODE'], "(?:^|(?<= ))(off|auto|sunlight|cloudy|shade|tungsten|fluorescent|incandescent|flash|horizon)(?:(?= )|$)", "auto") # off|auto|sunlight|cloudy|shade|tungsten|fluorescent|incandescent|flash|horizon
    # FRAMEPS = validate_config(config['CAMERA']['FRAMEPS'], "^([1-9]|[1-5][0-9]|60)$", "30") # 1 > 60
    # ROTATION = validate_config(config['CAMERA']['ROTATION'], "(?:^|(?<= ))(0|90|180|270)(?:(?= )|$)", "0") # 0|90|180|270
    # QUALITY = validate_config(config['CAMERA']['QUALITY'], "^([1-9]|[1-3][0-9]|40)$", "20") # 1 > 40

    # VIDEOINTERVAL = validate_config(config['OUTPUT']['VIDEOINTERVAL'], "^([1-9]|[12][0-9]|30)$", "30") # 1 > 30
    # TIMELAPSEINTERVAL = validate_config(config['OUTPUT']['TIMELAPSEINTERVAL'], "^([5-9]|[12][0-9]|30)$", "30") # 5 > 30
    # STREAMPORT =  validate_config(config['OUTPUT']['STREAMPORT'], "^([3-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$", 42687) # 30000 > 65535
    # TIMESTAMP =  validate_config(config['OUTPUT']['TIMESTAMP'], "(?:^|(?<= ))(True|False)(?:(?= )|$)", "True") # True|False

    # VIDEOPATHFSLIMIT = validate_config(config['STORAGE']['VIDEOPATHFSLIMIT'], "x", "10240") # 1024+
    # IMAGEPATHLIMIT = validate_config(config['STORAGE']['IMAGEPATHLIMIT'], "x", "2048") # 64+
    # IMAGEARCHIVEPATHLIMIT = validate_config(config['STORAGE']['IMAGEARCHIVEPATHLIMIT'], "x", "2048") # 64+ 
    # TAKESNAPSHOT = validate_config(config['STORAGE']['TAKESNAPSHOT'], "(?:^|(?<= ))(True|False)(?:(?= )|$)", "True") # True|False

    # SHUTTEREXISTS = validate_config(config['MISC']['SHUTTEREXISTS'], "(?:^|(?<= ))(True|False)(?:(?= )|$)", "True") # True|False

RUNNINGPATH = "./" # Real path
LOGPATH = "./logs/" # Real path
BINARYPATH = "./bin/" # Real path

read_constants("./pcw.ini")

# Setup logging (quiet background)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%d-%b-%y %H:%M:%S', filename=LOGPATH + "picamwatcher.log", filemode='w')
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

    # Log the constants

logging.debug(f"VIDEOPATH = {VIDEOPATH}")
logging.debug(f"IMAGEPATH = {IMAGEPATH}")
logging.debug(f"IMAGEARCHIVEPATH = {IMAGEARCHIVEPATH}")

logging.debug(f"WATCHPATH = {WATCHPATH}")
logging.debug(f"RESOLUTIONX = {RESOLUTIONX}")
logging.debug(f"RESOLUTIONY = {RESOLUTIONY}")
logging.debug(f"BRIGHTNESS = {BRIGHTNESS}")
logging.debug(f"CONTRAST = {CONTRAST}")
logging.debug(f"AWBMODE = {AWBMODE}")
logging.debug(f"FRAMEPS = {FRAMEPS}")
logging.debug(f"ROTATION = {ROTATION}°")
logging.debug(f"QUALITY = {QUALITY}")

logging.debug(f"VIDEOINTERVAL = {VIDEOINTERVAL} minutes")
logging.debug(f"TIMELAPSEINTERVAL = {TIMELAPSEINTERVAL} seconds")
logging.debug(f"STREAMPORT = {STREAMPORT}")

logging.debug(f"TIMESTAMP = {TIMESTAMP}")
logging.debug(f"VIDEOPATHFSLIMIT = {VIDEOPATHFSLIMIT} MB")
logging.debug(f"IMAGEPATHLIMIT = {IMAGEPATHLIMIT}MB")
logging.debug(f"IMAGEARCHIVEPATHLIMIT = {IMAGEARCHIVEPATHLIMIT} MB")
logging.debug(f"TAKESNAPSHOT = {TAKESNAPSHOT}")
logging.debug(f"SHUTTEREXISTS = {SHUTTEREXISTS}")

#print(RUNNINGPATH)
#print(RESOLUTIONX)
print("override")

RESOLUTIONX = read_config("extra.ini", "CAMERA", "RESOLUTIONX", "^(6[4-8][0-9]|69[0-9]|[7-9][0-9]{2}|1[0-8][0-9]{2}|19[01][0-9]|1920)$", "retain", RESOLUTIONX) # 640 > 1920
RESOLUTIONY = read_config("extra.ini", "CAMERA", "RESOLUTIONY", "^(48[0-9]|49[0-9]|[5-9][0-9]{2}|1[0-5][0-9]{2}|1600)$", "retain", RESOLUTIONY) # 480 > 1600
BRIGHTNESS = read_config("extra.ini", "CAMERA", "BRIGHTNESS", "^([1-9]|[1-8][0-9]|9[0-9]|100)$", "retain", BRIGHTNESS) # 1 > 100
CONTRAST = read_config("extra.ini", "CAMERA", "CONTRAST", "^-?([0-9]|[1-8][0-9]|9[0-9]|100)$", "retain", CONTRAST) # -100 > +100
AWBMODE = read_config("extra.ini", "CAMERA", "AWBMODE", "(?:^|(?<= ))(off|auto|sunlight|cloudy|shade|tungsten|fluorescent|incandescent|flash|horizon)(?:(?= )|$)", "retain", AWBMODE) # off|auto|sunlight|cloudy|shade|tungsten|fluorescent|incandescent|flash|horizon
FRAMEPS = read_config("extra.ini", "CAMERA", "FRAMEPS", "^([1-9]|[1-5][0-9]|60)$", "retain", FRAMEPS) # 1 > 60
ROTATION = read_config("extra.ini", "CAMERA", "ROTATION", "(?:^|(?<= ))(0|90|180|270)(?:(?= )|$)", "retain", ROTATION) # 0|90|180|270
QUALITY = read_config("extra.ini", "CAMERA", "QUALITY", "^([1-9]|[1-3][0-9]|40)$", "retain", QUALITY) # 1 > 40

VIDEOINTERVAL = read_config("extra.ini", "OUTPUT", "VIDEOINTERVAL", "^([1-9]|[12][0-9]|30)$", "retain", VIDEOINTERVAL) # 1 > 30
TIMELAPSEINTERVAL = read_config("extra.ini", "OUTPUT", "TIMELAPSEINTERVAL", "^([5-9]|[12][0-9]|30)$", "retain", TIMELAPSEINTERVAL) # 5 > 30
STREAMPORT =  read_config("extra.ini", "OUTPUT", "STREAMPORT", "^([3-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$", "retain", STREAMPORT) # 30000 > 65535
TIMESTAMP =  read_config("extra.ini", "OUTPUT", "TIMESTAMP", "(?:^|(?<= ))(True|False)(?:(?= )|$)", "retain", TIMESTAMP) # True|False
logging.debug(f"VIDEOPATH = {VIDEOPATH}")

print(os.path.basename("path/to/file/sample.txt"))