# Use a specific, stable version of Python
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the specific requirements file for this agent
COPY fetch_services/agents/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the necessary directories for the Fleet Manager to run.
# This creates a smaller, more secure, and more efficient Docker image.
COPY config/ /app/config/
COPY fetch_services/ /app/fetch_services/

# The command that Render will use to start the agent
CMD ["python", "fetch_services/agents/fleet_manager_agent.py"]

