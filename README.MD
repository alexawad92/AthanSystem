Athan System  
To run this from host system:
1- SSH to the PI
2- navigate to the app location 
3- source venu/bin/activate
4- export DISPLAY=:0
5- python main.py
6- redo on a new shell steps 1 to 4 then run chromium --kiosk http://localhost:5000
7- you can also use local browser to go to http://10.0.0.40:5000/


The backend should start as a service when PI starts, from SSH session and after PI had been rebooted, you can run sudo systemctl status athan and you will see that service is running. For the FE, we created /home/alexawad/.config/autostart/athan-chromium.desktop 