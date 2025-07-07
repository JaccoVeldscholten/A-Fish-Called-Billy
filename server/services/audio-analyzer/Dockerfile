# Use a lightweight, official Python base image
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the analyzer application
COPY analyzer.py .

# Stel de environment variabele in om de Flask app te vinden
ENV FLASK_APP=analyzer.py

# Expose the port on which the server runs
EXPOSE 5004

# Command to start the Flask server
CMD ["flask", "run", "--host=0.0.0.0", "--port=5004"]