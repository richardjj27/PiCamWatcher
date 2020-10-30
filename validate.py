import configparser
import re

# http://gamon.webfactional.com/regexnumericrangegenerator/

def validate_config(input, rule, default):
    pattern = re.compile(rule)
    #print(pattern)
    #print(f"input: {input}")
    if(pattern.match(input)):
        output = input
        print(f"output: {input} = match")
    else:
        output = default
        print(f"output: {default} = default")
    
    if(output == "terminate"):
        os._exit(1)

    return output

def read_constants(config_file):

    global RUNNINGPATH, BINARYPATH,LOGPATH, VIDEOPATH,IMAGEPATH, IMAGEARCHIVEPATH, WATCHPATH
    global RESOLUTIONX, RESOLUTIONY, BRIGHTNESS, CONTRAST, AWBMODE, FRAMEPS, ROTATION, QUALITY
    global VIDEOPATH, TIMELAPSEINTERVAL, STREAMPORT, TIMESTAMP
    global VIDEOPATHFSLIMIT, IMAGEPATHLIMIT, IMAGEARCHIVEPATHLIMIT, TAKESNAPSHOT
    global SHUTTEREXISTS

    config = configparser.ConfigParser()
    config.read(config_file)

    VIDEOPATH = validate_config(config['PATH']['VIDEOPATH'], "^/|(/[\w-]+)+$", "terminate") # reasonable file path with no trailing /
    IMAGEPATH = validate_config(config['PATH']['IMAGEPATH'], "^/|(/[\w-]+)+$", "terminate") # reasonable file path with no trailing /
    IMAGEARCHIVEPATH = validate_config(config['PATH']['IMAGEARCHIVEPATH'], "^/|(/[\w-]+)+$", "terminate") # reasonable file path with no trailing /
    WATCHPATH = validate_config(config['PATH']['WATCHPATH'], "^/|(/[\w-]+)+$", "terminate") # reasonable file path with no trailing /

    RESOLUTIONX = validate_config(config['CAMERA']['RESOLUTIONX'], "^(6[4-8][0-9]|69[0-9]|[7-9][0-9]{2}|1[0-8][0-9]{2}|19[01][0-9]|1920)$", 800) # 640 > 1920
    RESOLUTIONY = validate_config(config['CAMERA']['RESOLUTIONY'], "^(48[0-9]|49[0-9]|[5-9][0-9]{2}|1[0-5][0-9]{2}|1600)$", 480) # 480 > 1600
    BRIGHTNESS = validate_config(config['CAMERA']['BRIGHTNESS'], "^([1-9]|[1-8][0-9]|9[0-9]|100)$", "50") # 1 > 100
    CONTRAST = validate_config(config['CAMERA']['CONTRAST'], "^-?([0-9]|[1-8][0-9]|9[0-9]|100)$", "0") # -100 > +100
    AWBMODE = validate_config(config['CAMERA']['AWBMODE'], "(?:^|(?<= ))(off|auto|sunlight|cloudy|shade|tungsten|fluorescent|incandescent|flash|horizon)(?:(?= )|$)", "auto") # off|auto|sunlight|cloudy|shade|tungsten|fluorescent|incandescent|flash|horizon
    FRAMEPS = validate_config(config['CAMERA']['FRAMEPS'], "^([1-9]|[1-5][0-9]|60)$", "30") # 1 > 60
    ROTATION = validate_config(config['CAMERA']['ROTATION'], "(?:^|(?<= ))(0|90|180|270)(?:(?= )|$)", "0") # 0|90|180|270
    QUALITY = validate_config(config['CAMERA']['QUALITY'], "^([1-9]|[1-3][0-9]|40)$", "20") # 1 > 40

    VIDEOINTERVAL = validate_config(config['OUTPUT']['VIDEOINTERVAL'], "^([1-9]|[12][0-9]|30)$", "30") # 1 > 30
    TIMELAPSEINTERVAL = validate_config(config['OUTPUT']['TIMELAPSEINTERVAL'], "^([5-9]|[12][0-9]|30)$", "30") # 5 > 30
    STREAMPORT =  validate_config(config['OUTPUT']['STREAMPORT'], "^([3-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$", 42687) # 30000 > 65535
    TIMESTAMP =  validate_config(config['OUTPUT']['TIMESTAMP'], "(?:^|(?<= ))(True|False)(?:(?= )|$)", "True") # True|False

    VIDEOPATHFSLIMIT = validate_config(config['STORAGE']['VIDEOPATHFSLIMIT'], "x", "10240") # 1024+
    IMAGEPATHLIMIT = validate_config(config['STORAGE']['IMAGEPATHLIMIT'], "x", "2048") # 64+
    IMAGEARCHIVEPATHLIMIT = validate_config(config['STORAGE']['IMAGEARCHIVEPATHLIMIT'], "x", "2048") # 64+ 
    TAKESNAPSHOT = validate_config(config['STORAGE']['TAKESNAPSHOT'], "(?:^|(?<= ))(True|False)(?:(?= )|$)", "True") # True|False

    SHUTTEREXISTS = validate_config(config['MISC']['SHUTTEREXISTS'], "(?:^|(?<= ))(True|False)(?:(?= )|$)", "True") # True|False

read_constants("./pcw.ini")
#print(RUNNINGPATH)
#print(RESOLUTIONX)
