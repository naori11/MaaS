# 1. Use the dedicated image based on stack currently used
# As much as possible, use the slim version of the image to reduce the attack surface and the size of the image. 
# In this case, we are using the official Python 3.11 slim image.
FROM python:3.11-slim

# 2. Set the work directory to an appropriate location within the container, such as /app.
# This is where the application code and dependencies will be located.
WORKDIR /app

# 3. Copy the dedicated package files/dependencies list to the container.
COPY requirements.txt .

# 4. Install the dependencies using pip. This will ensure that all the required packages are available in the container for the application to run properly.
RUN pip install -r requirements.txt

# 5. Copy the rest of the application code to the container.
COPY . .

# Why copy the requirements.txt file separately before copying the rest of the application code? 
# This takes advantage of Docker's layer caching mechanism. 
# By copying the requirements.txt file and installing the dependencies before copying the rest of the application code, 
# we can ensure that if there are any changes to the application code, Docker will not have to re-install the 
# dependencies unless there are changes to the requirements.txt file.

# 6. Expose the port that the application will run on. 
# This allows other services or clients to communicate with the application through this port. 
# In this case, we are exposing port 8000, which is commonly used for web applications.
EXPOSE 8000

# 7. Define the command to run the application when the container starts.
# This command will be executed when the container is started, and it will start the application.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]