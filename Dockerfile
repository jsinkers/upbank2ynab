# Use the official Python image from the Docker Hub
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install cron and other required packages
RUN apt-get update && apt-get install -y cron neovim && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY importer.py .

# Copy crontab file
COPY crontab /etc/cron.d/ynab-cron

# Give execution rights on the cron job
RUN chmod 0644 /etc/cron.d/ynab-cron

# Apply cron job
RUN crontab /etc/cron.d/ynab-cron

# Create the log file to be able to run tail
RUN touch /var/log/cron.log

# Ensure cron can access environment vars passed through docker
# Run cron on container startup and output to log file and to stdout
CMD printenv | grep -v "no_proxy" >> /etc/environment && cron && tail -f /var/log/cron.log