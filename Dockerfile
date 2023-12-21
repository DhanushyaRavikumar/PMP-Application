# Use an official Python runtime as a parent image
FROM python:3.8

# Set the working directory to /app
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Set the FLASK_APP environment variable to the name of your main Flask file
ENV FLASK_APP=main.py

# Expose the port that the Flask application will run ons
EXPOSE 8080

# Run the command to start the Flask application
CMD ["python","main.py"]
