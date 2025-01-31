# Use the official Python image from the Docker Hub
FROM python:3.12

# Install chrony to sync time
RUN apt-get update && apt-get install -y chrony

# Copy the configuration file for chrony
COPY chrony.conf /etc/chrony/chrony.conf

# Set the working directory in the container
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install the dependencies specified in requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port that the app runs on
EXPOSE 8000

# Start chronyd and run the application
CMD ["sh", "-c", "chronyd && gunicorn app:app & python3 bot.py"]
