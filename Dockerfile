# 1. Use the official Playwright image as the base.
# Pinning to a specific version ensures our builds are reproducible.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# 2. Set the working directory inside the container.
# This is where our application files will live.
WORKDIR /app

# 3. Copy the requirements file first.
# This takes advantage of Docker's layer caching. The dependencies
# will only be re-installed if requirements.txt changes.
COPY requirements.txt .

# 4. Install the Python dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application code into the container.
COPY . .

# 6. Specify the command to run when the container starts.
# This executes our Python script.
CMD ["python", "run.py"]