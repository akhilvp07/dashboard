# Dashboard
Dashboard to show ping status for configured devices. To be run from Fedora 20.

## Steps
1. Execute the configure script to do the initial configuration.
```sh
./configure
```

2. Or we may manually do the below steps

    a. Make sure that the dashboard server is running:
    ```sh
    start_dashboard_itp
    ```

    b. Make sure that the pingstatus script is running:
    ```sh
    run_pingstatus_itp
    ```

3. Go to browser and enter URL: [192.168.0.151:8080](http://192.168.0.151:8080/)

## Note:
To check the running status:(2 process should be running)
```sh
ps -aux | grep '/home/akhil/dashboard/'
```
