# Sentinel Configuration File Documentation
The configuration file for Sentinel is located at [`appdaemon/conf/apps/config.ini`](/appdaemon/conf/apps/config.ini). This file is used to configure the Sentinel AppDaemon app to monitor the status of your 3D printer and send notifications when a failure is detected. The configuration file is divided into sections, each with its own set of configuration variables. The following sections describe each of the configuration variables and how to set them.

## [DEFAULT] Section
The `[DEFAULT]` section contains all the default configuration variables for the Sentinel app. These variables are used to configure the behavior of the app and can be overridden in the other sections of the configuration file. It is not recommended to change these variables unless you know what you are doing as they are used to set the default behavior of the app.

## [printer.entities] Section
The `[printer.entities]` section contains the configuration variables for the entities that represent the 3D printer in Home Assistant. These variables are used to configure the entities that the app will monitor to detect failures. The following variables are available in this section:
- **BinaryIsPrintingSensor**: The entity ID of the binary sensor that indicates whether the printer is currently printing. This sensor should be `on` when the printer is printing and `off` when it is not. You can specify the `on` state if it is different in the `PrintingOnState` variable. Defaults to Octoprint's `binary_sensor.octoprint_printing`.
- **PrintingOnState**: The state of the `BinaryIsPrintingSensor` when the printer is printing. This variable is optional and defaults to `on`.
- **PrinterCamera**: The entity ID of the camera that shows the printer. This camera will be used to take a snapshot when a failure is detected. This variable is optional and defaults to the Octoprint camera `camera.octoprint_camera`.
- **PrinterStopButton**: The entity ID of the button that stops the printer. This button will be used to stop the printer when a failure is detected. This variable defaults to the Octoprint button `button.octoprint_stop_job`.

## [program.timings] Section
The `[program.timings]` section contains the configuration variables for the timings of the monitoring program. These variables are used to configure how often the app checks the status of the printer and how long it should wait before automatically stopping the printer. The following variables are available in this section:
- **RunModelInterval**: The interval in seconds at which the app checks the status of the printer. This includes the frequency for the model running when a print is occuring. This variable defaults to `5` seconds.
- **TerminationTime**: The time in seconds that the app waits before automatically stopping the printer when a failure is detected. This variable defaults to `120` seconds (2 minutes).

## [model.detection] Section
The `[model.detection]` section contains the configuration variables for the machine learning model used to detect failures. These variables are used to configure the model inference process and can be used to fine-tune the model's performance. The following variables are available in this section:
- **Threshold**: The threshold value for the model's predictions. If the model predicts a probability of failure greater than this value, a failure is detected. This variable defaults to `0.25`.
- **NMS**: The Non-Maximum Suppression (NMS) threshold for the model's predictions. Used to filter out duplicate predictions. This variable defaults to `0.4`.