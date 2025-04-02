#!/usr/bin/env python3

import os
import configparser
import time
import usb.core
import usb.util
import logging
from logging.handlers import RotatingFileHandler

# Constants
CONFIG_FILE = "/etc/antec/sensors.conf"
LOG_DIR = "/var/log/antecflux"
LOG_FILE = os.path.join(LOG_DIR, "antec_display.log")
LOG_SIZE = 10 * 1024 * 1024  # 10 MB
LOG_COUNT = 1  # Number of backup files to keep

def setup_logging():
    """
    Set up logging with rotation when log file reaches 10 MB
    """
    # Create log directory if it doesn't exist
    if not os.path.exists(LOG_DIR):
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            logging.info(f"Created log directory at {LOG_DIR}")
        except PermissionError:
            print(f"Permission denied when creating log directory {LOG_DIR}")
            # Fall back to logging in the current directory if we can't create the log directory
            global LOG_FILE
            LOG_FILE = "antec_display.log"

    # Configure logging with rotation
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_SIZE,
        backupCount=LOG_COUNT
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    # Add console handler for terminal output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    logging.info("Logging system initialized")

def load_config():
    """
    Load sensor configuration from the config file if present.
    :return: Dictionary with 'cpu' and 'gpu' configurations or None if file is missing.
    """
    logging.info(f"Attempting to load config from {CONFIG_FILE}")
    
    if not os.path.exists(CONFIG_FILE):
        logging.warning(f"Config file not found at {CONFIG_FILE}")
        return None

    config = configparser.ConfigParser()
    try:
        config.read(CONFIG_FILE)
        if 'cpu' in config and 'gpu' in config:
            cpu_sensor = config['cpu']['sensor']
            cpu_name = config['cpu']['name']
            gpu_sensor = config['gpu']['sensor']
            gpu_name = config['gpu']['name']
            
            logging.info(f"Loaded config: CPU sensor={cpu_sensor}, name={cpu_name}, "
                         f"GPU sensor={gpu_sensor}, name={gpu_name}")
            
            return {
                "cpu": {"sensor": cpu_sensor, "name": cpu_name},
                "gpu": {"sensor": gpu_sensor, "name": gpu_name}
            }
        else:
            logging.error("Config file does not contain required cpu and gpu sections")
            return None
    except Exception as e:
        logging.error(f"Error reading config file: {e}")
        return None

def find_temp_file(sensor_name, label_name):
    """
    Locate the temperature input file for a given sensor and label.
    :param sensor_name: Name of the sensor (e.g., 'asusec').
    :param label_name: Name of the temperature label (e.g., 'CPU').
    :return: Path to the temperature input file or None if not found.
    """
    logging.info(f"Searching for temperature file: sensor={sensor_name}, label={label_name}")
    
    hwmon_base = "/sys/class/hwmon"
    for hwmon in os.listdir(hwmon_base):
        sensor_path = os.path.join(hwmon_base, hwmon)
        name_file = os.path.join(sensor_path, "name")
        if os.path.exists(name_file):
            with open(name_file, "r") as f:
                if f.read().strip() == sensor_name:
                    logging.debug(f"Found matching sensor {sensor_name} at {sensor_path}")
                    for temp_file in os.listdir(sensor_path):
                        if temp_file.startswith("temp") and temp_file.endswith("_label"):
                            label_path = os.path.join(sensor_path, temp_file)
                            with open(label_path, "r") as f:
                                if f.read().strip() == label_name:
                                    temp_input = label_path.replace("_label", "_input")
                                    logging.info(f"Found temperature file for {label_name}: {temp_input}")
                                    return temp_input
    
    logging.error(f"No temperature file found for sensor={sensor_name}, label={label_name}")
    return None

def list_hwmon_sensors():
    """
    List all available hwmon sensors with their names, temperature labels, and current temperatures.
    :return: A dictionary with sensor paths as keys and available labels with temperatures as values.
    """
    logging.info("Listing available hwmon sensors")
    
    sensors = {}
    hwmon_base = "/sys/class/hwmon"
    if not os.path.exists(hwmon_base):
        logging.error(f"No hwmon directory found at {hwmon_base}!")
        return sensors

    for hwmon in os.listdir(hwmon_base):
        sensor_path = os.path.join(hwmon_base, hwmon)
        name_file = os.path.join(sensor_path, "name")
        if os.path.exists(name_file):
            with open(name_file, "r") as f:
                sensor_name = f.read().strip()
            labels = []
            for temp_file in os.listdir(sensor_path):
                if temp_file.startswith("temp") and temp_file.endswith("_label"):
                    label_path = os.path.join(sensor_path, temp_file)
                    temp_input_path = label_path.replace("_label", "_input")
                    try:
                        with open(label_path, "r") as f:
                            label_name = f.read().strip()
                        if os.path.exists(temp_input_path):
                            with open(temp_input_path, "r") as f:
                                temp_value = float(f.read().strip()) / 1000
                        else:
                            temp_value = None
                        labels.append((temp_file.replace("_label", ""), label_name, temp_value))
                        logging.debug(f"Found sensor: {sensor_name}, label: {label_name}, temp: {temp_value}")
                    except Exception as e:
                        logging.error(f"Error reading label or temperature: {e}")
            sensors[sensor_path] = {"name": sensor_name, "labels": labels}
    
    logging.info(f"Found {len(sensors)} sensor devices")
    return sensors

def select_sensor(sensors):
    """
    Allow the user to select a sensor and a temperature label.
    :param sensors: A dictionary of available sensors and labels.
    :return: The selected temperature file path.
    """
    logging.info("Starting interactive sensor selection")
    
    print("Available sensors:")
    for idx, (sensor_path, info) in enumerate(sensors.items(), start=1):
        print(f"{idx}: {info['name']} ({sensor_path})")
        for label_idx, (temp_file, label, temp) in enumerate(info["labels"], start=1):
            temp_display = f"{temp:.1f}°C" if temp is not None else "N/A"
            print(f"   {label_idx}: {label} ({temp_file}) - {temp_display}")

    sensor_idx = int(input("\nSelect a sensor (number): ")) - 1
    label_idx = int(input("Select a temperature label (number): ")) - 1
    sensor_path = list(sensors.keys())[sensor_idx]
    temp_file = sensors[sensor_path]["labels"][label_idx][0]
    selected_path = os.path.join(sensor_path, f"{temp_file}_input")
    
    sensor_name = sensors[sensor_path]["name"]
    label_name = sensors[sensor_path]["labels"][label_idx][1]
    logging.info(f"User selected sensor: {sensor_name}, label: {label_name}, path: {selected_path}")
    
    return selected_path

def read_temperature(path):
    """
    Read a temperature in millidegrees Celsius from a given file path and convert it to degrees Celsius.
    :param path: Path to the temperature file.
    :return: Temperature in °C (float).
    """
    try:
        with open(path, "r") as f:
            temp = float(f.read().strip()) / 1000
            logging.debug(f"Read temperature from {path}: {temp}°C")
            return temp
    except FileNotFoundError:
        logging.error(f"Error: Temperature source not found at {path}!")
        return 0.0
    except Exception as e:
        logging.error(f"Error reading temperature from {path}: {e}")
        return 0.0

def generate_payload(cpu_temp, gpu_temp):
    """
    Generate the HID payload for the digital display.
    :param cpu_temp: CPU temperature in °C (float).
    :param gpu_temp: GPU temperature in °C (float).
    :return: Payload as a bytes object.
    """
    def encode_temperature(temp):
        integer_part = int(temp // 10)
        tenths_part = int(temp % 10)
        hundredths_part = int((temp * 10) % 10)
        return f"{integer_part:02x}{tenths_part:02x}{hundredths_part:02x}"

    cpu_encoded = encode_temperature(cpu_temp)
    gpu_encoded = encode_temperature(gpu_temp)
    combined_encoded = bytes.fromhex(cpu_encoded + gpu_encoded)
    checksum = (sum(combined_encoded) + 7) % 256
    payload_hex = f"55aa010106{cpu_encoded}{gpu_encoded}{checksum:02x}"
    
    logging.debug(f"Generated payload for CPU: {cpu_temp}°C, GPU: {gpu_temp}°C")
    return bytes.fromhex(payload_hex)

def send_to_device(payload):
    """
    Send the generated payload to the USB device.
    :param payload: Payload as a bytes object.
    """
    VENDOR_ID = 0x2022
    PRODUCT_ID = 0x0522

    try:
        device = usb.core.find(idVendor=VENDOR_ID, idProduct=PRODUCT_ID)
        if device is None:
            logging.error("USB device not found")
            return

        if device.is_kernel_driver_active(0):
            device.detach_kernel_driver(0)
        device.set_configuration()

        cfg = device.get_active_configuration()
        intf = cfg[(0, 0)]

        endpoint = usb.util.find_descriptor(
            intf,
            custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT,
        )

        if endpoint is None:
            logging.error("Could not find OUT endpoint")
            return

        try:
            endpoint.write(payload)
            logging.debug("Successfully sent payload to device")
        except usb.core.USBError as e:
            logging.error(f"Failed to send payload: {e}")

        usb.util.dispose_resources(device)
    except Exception as e:
        logging.error(f"Error communicating with USB device: {e}")

def main():
    # Set up logging first
    setup_logging()
    logging.info("Starting Antec FLUX Pro Display Service")
    
    try:
        config = load_config()
        if config:
            logging.info("Using configuration from config file")
            cpu_path = find_temp_file(config["cpu"]["sensor"], config["cpu"]["name"])
            gpu_path = find_temp_file(config["gpu"]["sensor"], config["gpu"]["name"])
            if not cpu_path or not gpu_path:
                logging.error("Could not find temperature files for sensors specified in the config.")
                return
        else:
            logging.info("No config file found. Falling back to interactive sensor selection.")
            sensors = list_hwmon_sensors()
            if not sensors:
                logging.error("No sensors found!")
                return
            print("\nSelect CPU temperature source:")
            cpu_path = select_sensor(sensors)
            print("\nSelect GPU temperature source:")
            gpu_path = select_sensor(sensors)

        logging.info(f"Using CPU temperature from: {cpu_path}")
        logging.info(f"Using GPU temperature from: {gpu_path}")
        logging.info("Starting temperature monitoring loop")
        
        cycle_count = 0
        while True:
            try:
                cpu_temp = read_temperature(cpu_path)
                gpu_temp = read_temperature(gpu_path)
                
                # Log temperatures at INFO level every 10 cycles, DEBUG level otherwise
                if cycle_count % 10 == 0:
                    logging.info(f"Current temperatures - CPU: {cpu_temp:.1f}°C, GPU: {gpu_temp:.1f}°C")
                else:
                    logging.debug(f"Current temperatures - CPU: {cpu_temp:.1f}°C, GPU: {gpu_temp:.1f}°C")
                
                payload = generate_payload(cpu_temp, gpu_temp)
                send_to_device(payload)
                cycle_count += 1
                time.sleep(0.5)
            except KeyboardInterrupt:
                logging.info("Service stopped by user")
                break
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                time.sleep(5)  # Wait a bit longer before retrying after an error
    except Exception as e:
        logging.critical(f"Fatal error in main function: {e}")
        raise

if __name__ == "__main__":
    main()
