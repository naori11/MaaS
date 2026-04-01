# Managing Dependencies (python based backend)

## For python based APIs:
- To create the requirements.txt file, use
  - `python -m venv venv` (create a virtual environment)
  - `pip install` the necessary dependencies
  - `pip freeze > requirements.txt`
  - or to automatically fetch the necessary dependencies (static code analysis), use `pipreqs` | `pip install pipreqs` | `pipreqs . --force`

- To separate test file dependencies (for github actions unit test)
  - create a separate requirements-dev.txt file
  - put dependencies mainly for testing only (pytest, httpx)
  - standard dependencies for testing in python is pytest and httpx

## Creating Dockerfiles
- Dockerfile notes are commented under each dockerfile within this project.
- Always create a .dockerignore file. Put the files unnecessary for the deployed state such as unit tests, python caches, venv, .git and .gitignore files.

## Testing Dockerfiles (Buidling and Running docker images)
- `dockerbuild -t 'image_name':'tag' .` | command for building the image based on dockerfile. Must run within the directory of the app.
- `docker run -p 'host_port':'container_port' 'image_name'` | command for running the image. Add -d before image name to detach terminal.
- `docker ps` / `docker ps -a` | command to list running/dead or exited containers
- `docker stop 'container_id'` | shuts down a running container
- `docker rm  'container_id'` | removes the container build
- `docker system prune` | removes every image/build that are unused
- `docker exec -it 'container_id' /bin/sh` or `/bin/bash` | opens a live terminal within the container

## Docker Compose
- Should be made after creating the initial services within the codebase (core business logic)
- Docker compose file should grow alongside the codebase.
- Dockerfile notes are commented under the docker-compose.yml file within this project.
- For environment variable injection for container routing, use the service name within the docker network (ex. http://math-add:8000)

---

- For pulling images (such as database images):
    - Env variables for database config would be set under the `environment:` tag, whichever is necessary.
    - Use `volumes:` to define where to store data when containers or images is stopped or remove. 
        - Right side part is always based on the image, then left is custom.
    - When setting volumes, you have to redefine the volume tag along with the name of the volume that you set onto the end of the dockerfile. This tells the docker engine that this volume should persist independently of any container.
        - `volumes:`
            - `'volume_name':`  

---

- For issues such as the database image loading slower than the services that requires it:
    - instead of calling the image name normally (e.g. - postgres), do the following:

    - for the postgres image itself:
    - `healthcheck:`
      - `test: ["shell":"command"]` # Command to test database status (depends on database image pulled)
      - `interval:` # Number of times to test
      - `timeout:`  # Time to consider as failed test
      - `retries:`  # Number of times to retry command

    - for images that requires to connect to the postgres image:
      - `postgres:` 
        - `condition: service_healthy` # Make sure that the image is healthy before spinning up the service.
