import shutil
import os

def get_foldersize(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size

freespace1 = shutil.disk_usage("/home/pi/")
freespace2 = shutil.disk_usage("/mnt/usb256/")

print(get_size("/mnt/usb256/"))

# freespace in MB
# capacity in MB
# % used

if((freespace1.used / freespace1.total) >= 0.9):
    LOGLEVEL = "WARNING"
print(f"Size: {((freespace1.total) / 1048576):,.0f}MB, Free: {((freespace1.free) / 1048576):,.2f}MB, Used: {((freespace1.used / freespace1.total) * 100):,.2f}%")
print(freespace2.total)

