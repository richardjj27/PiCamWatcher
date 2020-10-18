import datetime as dt
second = int(dt.datetime.now().strftime('%S'))
print(f"{second}")
if(int(dt.datetime.now().strftime('%S')) % 10 == 0):
    print("thats a hit!")