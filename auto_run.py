import os
import time

while True:
    os.system("pkill -f main.py")  # kill previous instance
    os.system("python main.py &")  # run new instance
    time.sleep(1)