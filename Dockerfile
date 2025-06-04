# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies from docker-packages.txt
COPY docker-packages.txt .
# Update package lists and install packages
RUN apt-get update && apt-get install -y --no-install-recommends $(cat docker-packages.txt) && \
    # Clean up apt cache to reduce image size
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && which streamlit && ls -l $(which streamlit)

# Copy the rest of your application code
COPY . .

# Expose the port Streamlit uses
EXPOSE 8502

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0"] 