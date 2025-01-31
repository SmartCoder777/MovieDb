# Use the official Python image from the Docker Hub
FROM python:3.12

# Install ntpd to sync time
RUN apt-get update && apt-get install -y ntp

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

# Start ntpd and run the application
CMD ["sh", "-c", "service ntp start && gunicorn app:app & python3 bot.py"]
