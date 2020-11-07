import shutil

freespace1 = shutil.disk_usage("/home/pi/").free / 1048576
freespace2 = shutil.disk_usage("/mnt/usb256/").free / 1048576

print(freespace1)
print(freespace2)