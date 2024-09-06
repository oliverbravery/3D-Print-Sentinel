# Use the base image for Home Assistant
FROM ghcr.io/home-assistant/home-assistant:stable

# Copy the configuration files into the image
COPY ./config /config

# Ensure the entire config directory is readable and writable
RUN chmod -R 777 /config
