# 3D-Print-Sentinel
**3D-Print-Sentinel** is a Docker-based solution that integrates **Home Assistant**, **OctoPrint**, and a custom **AppDaemon** app to automatically monitor 3D prints locally using machine learning. This project also enables secure remote access to Home Assistant via Cloudflared, allowing you to keep track of your prints from anywhere without exposing your local network. This solution can run entirely on a **Raspberry Pi**, making it accessible and easy to set up with minimal hardware requirements.

The machine learning and notification system can be setup as a **standalone service** for those who already have a homeassistant setup. It can be customised via the [config file](/appdaemon/conf/apps/config.ini) to use any entities (such as [Klipper](https://www.klipper3d.org) homeassistant entities) instead of Octoprint entities if that is prefered. See the [standalone setup instructions](#standalone-docker-failure-detection--notification-setup) for more information.

## Features
- **Local 3D Print Monitoring**: Uses on-device machine learning to detect potential print errors in real time using the [Obico (Spaghetti Detective)](https://github.com/TheSpaghettiDetective/obico-server/tree/release) model.
- **Automatic Print Pausing**: If an error is detected, an actionable notification is sent to your phone. If not dismissed within 2 minutes, the print will be automatically stopped.
- **OctoPrint Integration**: Seamlessly connects with OctoPrint to monitor print status and health.
- **Home Assistant**: Provides a centralized dashboard to manage 3D printer monitoring and smart home devices.
- **Notification System**: Sends alerts to your phone when a print error is detected through the Home Assistant app with image snapshots.
- **Secure Remote Access**: Access your Home Assistant instance remotely through a secure Cloudflared tunnel without exposing local ports.
- **Dockerized**: Easy to deploy and manage with Docker Compose.
- **Raspberry Pi Compatible**: Designed to run on a Raspberry Pi with minimal hardware requirements (including the machine learning).

## Setup Guide
- [Full Docker Setup](#full-docker-setup-homeassistant-octoprint--appdaemon)
- [Standalone Docker Setup](#standalone-docker-failure-detection--notification-setup)
### Full Docker Setup (HomeAssistant, Octoprint & Appdaemon)
This setup works on any machine with Docker and Docker Compose installed. If you are using a Raspberry Pi, follow the specific setup guide below. 

1. Clone this repository:
   ```bash
   git clone https://github.com/oliverbravery/3D-Print-Sentinel.git
   cd 3D-Print-Sentinel
   ```
2. Create a `.env` file with the your cloudflared tunnel token (see the [Cloudflared Tunnel Setup section](#cloudflared-tunnel-setup) below for more information):
   ```bash
   TUNNEL_TOKEN=<your cloudflared tunnel token>
   ```
3. Start the homeassistant container with Docker Compose:
   ```bash
   docker compose up --build -d homeassistant
   ```
4. Access Home Assistant at `http://localhost:8123` and complete the setup wizard.
5. Obtain from the Home Assistant UI a long-lived access token for the AppDaemon integration. Go to your profile, then `Long-Lived Access Tokens`, and create a new token. 
6. Create a `secrets.yaml` file in the `appdaemon/conf` directory following this template, where `HASS_TOKEN` is the long-lived access token obtained in the previous step:
   ```
   HASS_TOKEN: <the HASS long-lived access token>
   LATITUDE: <your latitude>
   LONGITUDE: <your longitude>
   ELEVATION: <your elevation>
   TIME_ZONE: <your time zone (e.g. GMT)>
   ```
7. Start the remaining containers:
   ```bash
   docker compose up --build -d
   ```
> **Note**: For some unknown reason, to connect to Home Assistant using your Cloudflare domain, you will need to use the app. The web interface will not work, giving the error 'error while loading page ...'.

### Standalone Docker Failure Detection & Notification Setup
The following setup shows how to install and setup just the failure detection and notification (Appdaemon) service to be connected with a HomeAssistant instance.

1. Clone this repository:
   ```bash
   git clone https://github.com/oliverbravery/3D-Print-Sentinel.git
   cd 3D-Print-Sentinel
   ```
2. Obtain from the Home Assistant UI a long-lived access token for the AppDaemon integration. Go to your profile, then `Long-Lived Access Tokens`, and create a new token. 
3. Create a `secrets.yaml` file in the `appdaemon/conf` directory following this template, where `HASS_TOKEN` is the long-lived access token obtained in the previous step:
   ```
   HASS_TOKEN: <the HASS long-lived access token>
   LATITUDE: <your latitude>
   LONGITUDE: <your longitude>
   ELEVATION: <your elevation>
   TIME_ZONE: <your time zone (e.g. GMT)>
   ```
4. Edit the configuration file at [`appdaemon/conf/apps/config.ini`](/appdaemon/conf/apps/config.ini) with your desired configuration variables. The default configuration of the file is for an Octoprint setup.
5. Run the container using the following command:
   ```bash
   docker compose up --build appdaemon -d
   ```

### Additional Raspberry Pi Steps
In addition to the general Docker setup, the Raspberry Pi requires a few additional steps to optimize performance and enable the machine learning model.

It is highly recommended to use a Raspberry Pi 5 with at least 4GB of RAM for optimal performance. An [M.2 SSD is also recommended](https://www.raspberrypi.com/documentation/accessories/m2-hat-plus.html) as home assistant performs alot of read and write operations.

- **Restart octoprint container when printer turns on**: Octoprint does not have functionality to automatically detect and connect to a printer if it loses connection or is turned off. To solve this, we can use these commands to restart the octoprint container when the pi detects a printer is connected:
```bash
sudo nano /etc/udev/rules.d/99-usb-serial.rules # Open the file in the nano text editor
SUBSYSTEM=="tty", KERNEL=="ttyACM0", ACTION=="add", RUN+="/usr/bin/docker restart octoprint appdaemon" # Add this line to the file, save and exit
sudo udevadm control --reload-rules && sudo udevadm trigger # Reload the udev rules
```
- **Installing Docker on Pi**: The following commands work to install Docker on a Raspberry Pi (you can follow any other guide if you prefer):
```bash
curl -fsSL https://get.docker.com -o get-docker.sh # Download the Docker installation script
sudo sh get-docker.sh # Run the Docker installation script
sudo usermod -aG docker ${USER} # Add the current user to the Docker group
sudo su - ${USER} # Refresh the user group
docker version # Check the Docker version to verify the installation
sudo apt install docker-compose -y # Install Docker Compose
sudo systemctl enable docker # Enable Docker to start on boot
```

### Cloudflared Tunnel Setup
We can access homeassistant remotely through a secure Cloudflared tunnel. This requires a Cloudflare domain and a Cloudflared tunnel token. If you do not require this functionality, remove the `cloudflared` service from the `docker-compose.yml` file. 

It is assumed that you already have a domain set up on Cloudflare.
1. Visit the [Cloudflare Zero Trust dashboard](https://one.dash.cloudflare.com).
2. Go to `Networks` -> `Tunnels` and create a new tunnel.
3. Choose `Cloudflared` as the tunnel type and copy the tunnel token starting 'eyJh...' (from the brew install command for example). This token should be added to the `.env` file as `TUNNEL_TOKEN`.
4. To connect the tunnel to your domain, from the tunnels page, click the three dots on the right of the tunnel and select `Configure`. Go to the `Public Hostname` section and click `Add hostname`.
5. Choose your own subdomain and domain then in the `Service` dropdown, set the type to `HTTP` and the url to `homeassistant:8123`. Click `Save`.
The tunnel should now be connected to your domain. 

You can access homeassistant remotely at `https://<subdomain>.<domain>`through any of the home assistant apps! Note: For some reason you have to use the app as you can't access it through a browser using the cloudflare domain.

## Usage
- **Home Assistant**: Access the Home Assistant dashboard at `http://localhost:8123` to monitor your 3D prints and manage your smart home devices. If you set up the Cloudflared tunnel, you can access Home Assistant remotely at `https://<subdomain>.<domain>`.
- **OctoPrint**: Access the OctoPrint dashboard at `http://localhost:80` to manage your 3D printer and start prints.
- **Print Notifications**: Receive actionable notifications on your phone when a print error is detected. This system will automatically start whenever a print starts. You can dismiss the notification to continue the print or let it automatically stop after 2 minutes. You must have the Home Assistant app installed and set up to receive notifications on your phone. If you set up the Cloudflared tunnel, use the remote URL to access the app (e.g. `https://<subdomain>.<domain>`).
