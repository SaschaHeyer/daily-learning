# Use the official Python image with a slim variant for smaller size
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the application files
COPY app.py /app
COPY firestore_handler.py /app
COPY requirements.txt /app
COPY scraper.py /app
COPY conversation.py /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that the Flask app runs on
EXPOSE 8080

# Command to run the Flask app
CMD ["python", "app.py"]
