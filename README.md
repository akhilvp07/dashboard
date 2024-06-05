# dashboard
Dashboard to show ping status for configured devices. To be run from Fedora 20.

#Steps
1. Make sure that the dashboard server is running:
    start_dashboard
2. Make sure that the pingstatus sccript is running:
    run_pingstatus
3. Go to browser and enter URL:
    192.168.0.151:8000/

Note:
To check the running status:(2 process should be running)
ps -aux | grep '/home/akhil/dashboard/'

