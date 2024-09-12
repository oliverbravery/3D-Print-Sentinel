# Use Python 3.11 with Slim base image
FROM python:3.11-slim

# Set working directory
WORKDIR /usr/src/app

# Copy the application code into the image
COPY ./conf /conf

# Install libgl1 for OpenCV and weget for downloading the model
RUN apt-get update && apt-get install -y libgl1 libgl1-mesa-glx libglib2.0-0 wget

# Download the machine learning model
RUN wget https://tsd-pub-static.s3.amazonaws.com/ml-models/model-weights-5a6b1be1fa.onnx -O /conf/model/model-weights-5a6b1be1fa.onnx

# Upgrade pip
RUN pip install --upgrade pip

# Install the required Python packages
RUN pip3 install numpy==1.26.4 opencv-python==4.10.0.84 appdaemon==4.4.2 onnxruntime==1.19.2 pyyaml

# Start the AppDaemon service
CMD ["appdaemon", "-c", "/conf"]