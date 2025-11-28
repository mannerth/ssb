# Python base image
FROM python:3.11

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (if any)
# RUN apt-get update && apt-get install -y ...

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code, configuration, and data
COPY src/ ./src/
COPY config/ ./config/
COPY data/ ./data/

# Command to run the application
CMD ["python", "src/app_gui.py"]
