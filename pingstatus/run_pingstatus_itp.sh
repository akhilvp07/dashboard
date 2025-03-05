#!/bin/bash

BIN_PATH=~/bin

# Function to run the pingstatus_itp script with the --sync flag
do_pingstatus_check() {
  #nohup $BIN_PATH/pingstatus_itp --sync &> /dev/null &
  nohup $BIN_PATH/pingstatus_itp --sync > /dev/null 2>&1 &
}

do_pingstatus_check

while true; do
    sleep 3600  # Sleep for 1 hour (3600 seconds)
    do_pingstatus_check
done

