import shutil

freespace1 = shutil.disk_usage("/home/pi/")
freespace2 = shutil.disk_usage("/mnt/usb256/")

# freespace in MB
# capacity in MB
# % used

if((freespace1.used / freespace1.total) >= 0.9):
    LOGLEVEL = "WARNING"
print(f"Size: {((freespace1.total) / 1048576):,.0f}MB, Free: {((freespace1.free) / 1048576):,.2f}MB, Used: {((freespace1.used / freespace1.total) * 100):,.2f}%")
print(freespace2.total)

[STORAGE]
VIDEOPATHFSLIMIT=10240
IMAGEPATHLIMIT=4096
IMAGEARCHIVEPATHLIMIT=65536
TAKESNAPSHOT=true