import adbase as ad
from lib.detection_model import *
import cv2
from configparser import ConfigParser

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
        
        self.printer_status = self.adapi.get_entity(self.printer_status_entity) # get the printer status
        self.print_camera = self.adapi.get_entity(self.printer_camera_entity) # get the camera
        self.stop_print_button = self.adapi.get_entity(self.printer_stop_button_entity) # get the stop print button
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
        if isinstance(value, type):
            return value
        raise RuntimeError("Invalid Config File")
        
    def load_config(self):
        """
        Loads the variables from the config file.
        """
        config = ConfigParser()
        config.read('config.ini')
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
        
        
    def run_every_c(self, cb_args):
        '''
        This function is called every x seconds to take a snapshot of the print job and run the detection model.
        It will send a notification if an issue is detected.
        '''
        # check if the printer is on and a notification has not already been sent
        if self.printer_status.is_state(self.printer_printing_state) and self.cancel_handle == None:
            # if the printer is on, take a snapshot and run the detection model
            self.print_camera.call_service("snapshot", filename="/media/snapshot.jpg")
            custom_image_bgr = cv2.imread("/shared_media/snapshot.jpg")
            detections = detect(self.net_main_1, custom_image_bgr, thresh=self.detection_threshold, nms=self.detection_nms)
            detection_count = len(detections)
            self.adapi.log(f"Detected {detection_count} issues")
            # if an issue is detected, send a notification
            if detection_count > 1:
                self.adapi.call_service("notify/notify", message="An issue with your 3D print has been detected. The print will be stopped if not dismissed.", 
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
                # start the timer to stop the print job in x minutes if not dismissed
                self.cancel_handle = self.adapi.run_in(self.cancel_print_callback, self.print_termination_time)
            
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