Managing Dependencies (python based backend)

For python based APIs:
- To create the requirements.txt file, use 
    -   python -m venv venv (create a virtual environment)
    -   pip install the necessary dependencies
    -   pip freeze > requirements.txt
    -   or to automatically fetch the necessary dependencies (static code analysis), use pipreqs | pip install pipreqs | pipreqs . --force

- To separate test file dependencies (for github actions unit test)
    -   create a separate requirements-dev.txt file
    -   put dependencies mainly for testing only (pytest, httpx)
    -   standard dependencies for testing in python is pytest and httpx


Creating Dockerfiles
-   Dockerfile notes are commented under each dockerfile within this project.
-   Always create a .dockerignore file. Put the files unnecessary for the deployed state such as unit tests, python caches, venv, .git and .gitignore files.

Testing Dockerfiles (Buidling and Running docker images)
-   dockerbuild -t 'image_name':'tag' . | command for building the image based on dockerfile. Must run within the directory of the app.
-   docker run -p 'host_port':'container_port' 'image_name' | command for running the image. Add -d before image name to detach terminal.
-   docker ps / docker ps -a | command to list running/dead or exited containers
-   docker stop 'container_id' | shuts down a running container
-   docker rm  'container_id' | removes the container build


-   docker system prune | removes every image/build that are unused
-   docker exec -it 'container_id' /bin/sh or /bin/bash | opens a live terminal within the container