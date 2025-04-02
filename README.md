# Antec FLUX Pro Temperature Display Service

A Linux service that enables the Antec FLUX Pro case's built-in temperature display to show real-time CPU and GPU temperatures from your system sensors.

## Overview

This service connects to the Antec FLUX Pro's USB temperature display device and sends it current temperature readings from your system's hardware sensors. The display will show both CPU and GPU temperatures simultaneously, updating multiple times per second.

## Features

- Automatically detects and connects to the Antec FLUX Pro temperature display
- Configurable sensor sources for both CPU and GPU temperatures
- Interactive sensor selection mode if no configuration is provided
- Runs as a systemd service for automatic startup
- Detailed logging with automatic rotation (logs capped at 10MB)

## Requirements

- Linux system with systemd
- Python 3
- USB connection to Antec FLUX Pro case with temperature display
- Hardware monitoring sensors (hwmon) for CPU and GPU temperatures

## Installation

1. Clone or download this repository
2. Run the installation script:

```bash
chmod +x install.sh
sudo ./install.sh
```

The installer will:
- Create a Python virtual environment at `/opt/antecfluxpro`
- Install necessary dependencies (pyusb)
- Set up the systemd service
- Configure udev rules for USB device access
- Create log directories
- Start the service

## Configuration

The service uses sensors.conf to determine which hardware sensors to read temperatures from. By default, it's installed to `/etc/antec/sensors.conf`.

Example configuration:

```ini
[cpu]
sensor = k10temp
name = Tccd1

[gpu]
sensor = amdgpu
name = junction
```

Where:
- `sensor`: The hwmon driver name (see `/sys/class/hwmon/hwmon*/name`)
- `name`: The specific temperature label to use from that sensor

If no configuration file is found or if the specified sensors aren't available, the service will start in interactive mode, allowing you to select sensors manually.

### Finding Your Sensors

To find available sensors on your system, you can:

1. Check `/sys/class/hwmon/hwmon*/name` for sensor driver names
2. For each sensor, check temperature labels in `/sys/class/hwmon/hwmon*/temp*_label`

Common sensor names:
- AMD CPUs: `k10temp`
- Intel CPUs: `coretemp`
- AMD GPUs: `amdgpu`
- NVIDIA GPUs: `nvidia`

## Logging

The service now includes comprehensive logging:

- Log files are stored in `/var/log/antecflux/antec_display.log`
- Logs automatically rotate when they reach 10MB in size
- One backup log file is retained (antec_display.log.1)
- Logs include timestamps, log levels, and detailed messages
- All service activity is logged, including:
  - Service startup and configuration
  - Sensor detection and readings
  - Display communication
  - Errors and exceptions

## Troubleshooting

If the display isn't working:

1. Check if the service is running:
   ```bash
   systemctl status antecflux.service
   ```

2. View the logs for error messages:
   ```bash
   less /var/log/antecflux/antec_display.log
   ```

3. Ensure the device is detected:
   ```bash
   lsusb | grep 2022:0522
   ```

4. Check if the correct sensors are configured in `/etc/antec/sensors.conf`

5. Restart the service:
   ```bash
   sudo systemctl restart antecflux.service
   ```

## Uninstallation

To remove the service:

```bash
sudo systemctl stop antecflux.service
sudo systemctl disable antecflux.service
sudo rm /etc/systemd/system/antecflux.service
sudo rm -rf /opt/antecfluxpro
sudo rm /etc/udev/rules.d/99-antec-flux-display.rules
sudo rm -rf /var/log/antecflux
sudo rm -rf /etc/antec
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

This service was originally created by [AKoskovich](https://github.com/AKoskovich/antec_flux_pro_display_service) to enable functionality of the Antec FLUX Pro temperature display on Linux systems.

This fork expands on the original work by adding detailed logging functionality with rotation capabilities, improved error handling, and more comprehensive documentation. The core functionality to interface with the Antec FLUX Pro display remains based on AKoskovich's excellent original implementation.

Special thanks to AKoskovich for creating and sharing the initial version of this service, which made it possible for Linux users to utilize the temperature display feature of their Antec FLUX Pro cases.
