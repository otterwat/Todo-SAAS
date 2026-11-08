FROM python:3.11-slim

WORKDIR /app

# Copy requirements first to speed up future builds
COPY requirements.txt .

# Run your build command
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app files
COPY . .

# Expose the port your app will run on
EXPOSE 8000

# Docker will use compose.yaml's command, but this serves as a good default
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
