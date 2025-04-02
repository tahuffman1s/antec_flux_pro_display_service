#!/bin/bash

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root. Re-running with sudo..."
    exec sudo "$0" "$@"
fi

USER_HOME="$HOME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/antecflux.service"
UDEV_RULES="$SCRIPT_DIR/99-antec-flux-display.rules"
PYTHON_FILE="$SCRIPT_DIR/antec_display_service.py"
CONFIG_FILE="$SCRIPT_DIR/sensors.conf"
DESTINATION="/opt/antecfluxpro"
LOG_DIR="/var/log/antecflux"

echo "INSTALLING ANTEC FLUX PRO SERVICE"

echo "Checking dependencies"

if command -v python &>/dev/null; then
	echo "Python is installed. Continuing installation"
else
	echo "Python is not installed. Exiting."
	exit 1
fi	

if command -v pip &>/dev/null; then
	echo "Pip is installed. Continuing installation"
else
	echo "Pip is not installed. Exiting."
	exit 1
fi	

echo "Creating $DESTINATION"
sudo mkdir -p $DESTINATION
python -m venv "$DESTINATION" || { echo "Failed to create venv"; exit 1; }
echo "Venv created"
echo "Installing pyusb and required packages"
"$DESTINATION/bin/pip" install --upgrade pip
"$DESTINATION/bin/pip" install pyusb logging || { echo "Failed to install dependencies"; exit 1; }

echo "Setting up log directory"
sudo mkdir -p "$LOG_DIR"
sudo chmod 755 "$LOG_DIR"
echo "Log directory created at $LOG_DIR"

if [[ -f "$SERVICE_FILE" ]]; then 
	echo "Copying service file"
	sudo cp "$SERVICE_FILE" "/etc/systemd/system/antecflux.service"
	if [[ $? -eq 0 ]]; then
	    echo "Success!"
	else
	    echo "Command failed. Exiting."
	    exit 1
	fi
else
	echo "$SERVICE_FILE not detected. Exiting"
	exit 1
fi

echo "Copying service file done!"

if [[ -f "$PYTHON_FILE" ]]; then
	echo "Copying python file"
	sudo cp "$PYTHON_FILE" "$DESTINATION/antec_display_service.py"	
	if [[ $? -eq 0 ]]; then
	    echo "Success!"
	else
	    echo "Command failed. Exiting."
	    exit 1 
	fi
else
	echo "No python file detected. Exiting"
fi
	
echo "Copying python file done!"

if [[ -f "$CONFIG_FILE" ]]; then
	echo "Copying config file"
	# Create /etc/antec directory if it doesn't exist
	sudo mkdir -p /etc/antec
	sudo cp "$CONFIG_FILE" "/etc/antec/sensors.conf"	
	if [[ $? -eq 0 ]]; then
	    echo "Success!"
	else
	    echo "Command failed. Exiting. Please run the script and create a config file."
	    exit 1
	fi
else
	echo "Command failed. Exiting. Please run the script and create a config file."
	exit 1
fi

echo "Copying config file done!"

if [[ -f "$UDEV_RULES" ]]; then
	echo "Copying udev rules"
	sudo cp "$UDEV_RULES" "/etc/udev/rules.d/99-antec-flux-display.rules"  
	if [[ $? -eq 0 ]]; then
	    echo "Success!"
	else
	    echo "Command failed. Exiting."
	    exit 1
	fi
else
	echo "No udev rules found. Exiting"
	exit 1
fi

echo "Copying udev rules done!"
echo "Reloading udev rules"
sudo udevadm control --reload-rules || { echo "Reloading udev rules failed. Exiting"; exit 1; }
echo "Reloaded udev rules"
echo "Triggering udev rules"
sudo udevadm trigger || { echo "Triggering udev rules failed. Exiting"; exit 1; }
echo "Setting up service"
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable --now antecflux.service
echo "DONE"
