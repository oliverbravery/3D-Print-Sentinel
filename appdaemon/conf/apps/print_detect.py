import adbase as ad
from lib.detection_model import *
import cv2
from configparser import ConfigParser
import requests
import yaml
import os
import numpy as np

class PrintDetect(ad.ADBase):
    '''
    This class is used to detect issues with a 3D print job using the machine learning model. 
    It takes a snapshot of the print job every x seconds (5 by default) and runs the detection model on the image.
    If an issue is detected, a notification is sent to the user with the option to stop the print job.
    When an error is detected, the print job will be stopped in x minutes (2 by default) if not dismissed via the notification.
    '''
    
    def initialize(self):
        self.cancel_handle = None # handle for the cancel function
        self.adapi = self.get_ad_api() # get the AppDaemon API
        
        # paths to the model files
        self.model_cfg = "/conf/model/model.cfg"
        self.model_meta = "/conf/model/model.meta"
        self.model_weights = "/conf/model/model-weights-5a6b1be1fa.onnx"
        
        # load all configuration file variables
        self.load_config()
        self.load_secret_values()
        
        self.printer_status = self.adapi.get_entity(self.printer_status_entity) # get the printer status
        self.print_camera = self.adapi.get_entity(self.printer_camera_entity) # get the camera
        self.stop_print_button = self.adapi.get_entity(self.printer_stop_button_entity) # get the stop print button
        self.extruder_temp_sensor = self.adapi.get_entity(self.extruder_temp_sensor_entity) # get the extruder temperature sensor
        self.extruder_target_temp_sensor = self.adapi.get_entity(self.extruder_target_temp_sensor_entity) # get the extruder target temperature sensor
        self.net_main_1 = load_net(self.model_cfg, self.model_meta, self.model_weights) # load the ml model
        
        self.adapi.run_every(self.run_every_c, "now", self.detection_interval) # run the detection every x seconds
        self.adapi.listen_event(self.handle_action, "mobile_app_notification_action") # listen for mobile app notification actions (e.g. stop print or dismiss)
        
    @staticmethod
    def get_config_value(config: ConfigParser, group: str, id: str, type: type) -> any:
        """
        Get a value from the config file or the default. 

        Args:
            config (ConfigParser): The configuration file parser
            group (str): The group the value belongs to
            id (str): The id of the value to retreive
            type (type): The expected type of the value wanted to be retrieved.

        Raises:
            RuntimeError: Raise error if the retreived type is not the same as the one extected.

        Returns:
            any: The value.
        """
        value = config[group][id] or config['DEFAULT'][id]
        try:
            value = type(value)
            return value
        except ValueError:
            raise RuntimeError(f"Invalid Config File. {group} {id} must be of type {type}.")
        
    def load_secret_values(self) -> None:
        """
        Load the secret values from the secrets.yaml file needed for requesting the camera snapshot.
        """
        secrets_path = os.path.join(os.path.dirname(__file__), '..', 'secrets.yaml')
        with open(secrets_path, 'r') as file:
            secrets = yaml.safe_load(file)
        self.hass_token = secrets.get('HASS_TOKEN')
        self.hass_hostname = secrets.get('HASS_HOSTNAME')
    
    def load_config(self):
        """
        Loads the variables from the config file.
        """
        config = ConfigParser()
        config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
        self.printer_status_entity: str = PrintDetect.get_config_value(config=config, group='printer.entities', 
                                                                id='BinaryIsPrintingSensor', type=str)
        self.printer_printing_state: str = PrintDetect.get_config_value(config=config, group='printer.entities', 
                                                                id='PrintingOnState', type=str)
        self.printer_camera_entity: str = PrintDetect.get_config_value(config=config, group='printer.entities', 
                                                                id='PrinterCamera', type=str)
        self.printer_stop_button_entity: str = PrintDetect.get_config_value(config=config, group='printer.entities', 
                                                                id='PrinterStopButton', type=str)
        self.detection_interval: int = PrintDetect.get_config_value(config=config, group='program.timings', 
                                                                id='RunModelInterval', type=int)
        self.print_termination_time: int = PrintDetect.get_config_value(config=config, group='program.timings', 
                                                                id='TerminationTime', type=int)
        self.detection_threshold: float = PrintDetect.get_config_value(config=config, group='model.detection', 
                                                                id='Threshold', type=float)
        self.detection_nms: float = PrintDetect.get_config_value(config=config, group='model.detection', 
                                                                id='NMS', type=float)
        self.extruder_temp_sensor_entity: str = PrintDetect.get_config_value(config=config, group='notifications.entities', 
                                                                id='ExtruderTempSensor', type=str)
        self.extruder_target_temp_sensor_entity: str = PrintDetect.get_config_value(config=config, group='notifications.entities', 
                                                                id='ExtruderTargetTempSensor', type=str)
        self.notification_on_warp_up: bool = True if PrintDetect.get_config_value(config=config, group='notifications.config',
                                                                id='NotifyOnWarmup', type=str) == 'True' else False
        
    def get_camera_snapshot(self):
        """
        Get the camera snapshot and decode it into an image.

        Returns:
            The decoded image.
        """
        url = f"{self.hass_hostname}/media/local/snapshot.jpg"
        headers = {
            'Authorization': f'Bearer {self.hass_token}'
        }
        response = requests.request("GET", url, headers=headers, data={}, stream=True)
        if response.status_code != 200:
            self.adapi.log(f"Error getting camera snapshot: {response.status_code}")
            return None
        arr = np.asarray(bytearray(response.raw.read()), dtype=np.uint8)
        cv2_img = cv2.imdecode(arr, -1)
        return cv2_img
    
    def perform_detection(self) -> int:
        """
        Take a snapshot of the print job and run the detection model on the image.

        Returns:
            int: The number of issues detected. 0 if a snapshot could not be taken.
        """
        self.print_camera.call_service("snapshot", filename="/media/snapshot.jpg")
        custom_image_bgr = self.get_camera_snapshot()
        if custom_image_bgr is None:
            self.adapi.log("Failed to get camera snapshot, skipping detection for this cycle.")
            return 0
        detections = detect(self.net_main_1, custom_image_bgr, thresh=self.detection_threshold, nms=self.detection_nms)
        detection_count = len(detections)
        self.adapi.log(f"Detected {detection_count} issues")
        return detection_count
    
    def send_detection_notification_and_countdown(self):
        """
        Send a notification to the user that an issue has been detected and start the countdown to stop the print job.
        """
        self.adapi.call_service("notify/notify", message=f"An issue with your 3D print has been detected. The print will be stopped in {self.print_termination_time} seconds if not dismissed.", 
                                title="3D Print Issue Detected",
                                data={
                                    "image": "/media/local/snapshot.jpg",
                                    "actions": [
                                        {
                                            "action": "STOP_PRINT_JOB",
                                            "title": "Stop Print"
                                        },
                                        {
                                            "action": "DISMISS_NOTIFICATION",
                                            "title": "Dismiss"
                                        }
                                    ],
                                    "push": {
                                        "interruption-level": "critical"
                                    }})
        self.cancel_handle = self.adapi.run_in(self.cancel_print_callback, self.print_termination_time)
        
    def notify_on_warmup(self):
        """
        Notify the user when the printer is almost warmed up
        """
        if self.extruder_temp_sensor.state < 0.9 * self.extruder_target_temp_sensor.state:
            self.adapi.call_service("notify/notify", 
                                    message="The 3D printer has almost warmed up. Remove any excess filament before your print starts.", 
                                    title="3D Printer Warming Up",
                                    data={
                                        "image": "/media/local/snapshot.jpg"
                                    })
        
    def extra_notifications_router(self):
        """
        Check if extra notifications are needed.
        """
        if self.notification_on_warp_up:
            self.notify_on_warmup()
        
    def run_every_c(self, cb_args):
        '''
        This function is called every x seconds to take a snapshot of the print job and run the detection model.
        It will send a notification if an issue is detected.
        '''
        # check if the printer is on and a notification has not already been sent
        if self.printer_status.is_state(self.printer_printing_state) and self.cancel_handle == None:
            # call the extra notifications router to check if any extra notifications are needed
            self.extra_notifications_router()
            # if the printer is on, take a snapshot and run the detection model
            detection_count = self.perform_detection()
            # if an issue is detected, send a notification
            if detection_count > 1:
                self.send_detection_notification_and_countdown()

    def handle_action(self, event_name, data, kwargs):
        '''
        This is a routing function called when a mobile app notification action is received.
        It will run the appropriate function based on the action received.
        '''
        self.adapi.log(f"Received action: {data}")
        if data["action"] == "STOP_PRINT_JOB":
            self.stop_print_job()
        elif data["action"] == "DISMISS_NOTIFICATION":
            self.dismiss_print_cancel()
            
    def cancel_print_callback(self, cb_args):
        '''
        A callback function for when the timer to stop the print job is called.
        '''
        self.stop_print_job()
            
    def stop_print_job(self):
        '''
        This function is called to stop the print job. 
        It will send a notification to the user and call the stop print button.
        '''
        self.dismiss_print_cancel()
        self.stop_print_button.call_service("press")
        self.adapi.call_service("notify/notify", message="The 3D print has been stopped due to an issue.", title="3D Print Stopped")
        
    def dismiss_print_cancel(self):
        '''
        This function is called to dismiss the print issue notification.
        It will cancel the timer to stop the print job and send a notification to the user that the issue has been dismissed.
        '''
        if self.cancel_handle is not None:
            self.adapi.cancel_timer(self.cancel_handle)
            self.cancel_handle = None
        self.adapi.call_service("notify/notify", message="The 3D print issue has been dismissed.", title="3D Print Issue Dismissed")