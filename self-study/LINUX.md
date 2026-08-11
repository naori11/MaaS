## Phase 2: Linux Systems & Administration (Ubuntu Native)

> **Goal:** Get comfortable navigating, managing permissions, and inspecting system state directly inside your Ubuntu installation.

### Action Tasks

- **Directory Navigation & File Operations**
  - Practice essential file commands: `ls -la`, `cd`, `mkdir -p`, `cp -r`, `mv`, `rm -rf`.
    - _Note:_
      - **ls** - for listing files and directories

      ***
      - **cd** - for changing directories

      ***
      - **mkdir** - for creating directories

      ***
      - **cp** - for copying files and renaming

      ***
      - **mv** - for moving files

      ***
      - **rm** - for removing files and directories

      ***
  - Master terminal text processing: `cat`, `less`, `head`, `tail -f`, `grep`, and `find`.
    - _Note:_
      - **cat [filename]** - for concatenating and displaying file contents

      ***
      - **less [filename]** - for viewing file contents page by page

      ***
      - **head -n [number] [filename]** - for displaying the first few lines of a file

      ***
      - **tail -n [number] [filename]** - for displaying the last few lines of a file

      ***
      - **grep "TEXT" [filename]** - for searching for specific text patterns in files
      - **grep -i "text" [filename]** - for searching for case-insensitive specific text patterns in files
      - **grep -e "TEXT1|TEXT2" [filename]** - for searching for multiple text patterns in files

      ***
      - **find . -type f -name "\*.log"** - for locating files and directories
      - **find . -type f -iname "_app_"** - case-insensitive, for locating files and directories

      ***

  - Use shell redirection operators (`|`, `>`, `>>`, `tee`) to filter outputs and log to files.
    - _Note:_
      - **&&** - run multiple commands sequentially, only if the previous command succeeds

      ***
      - **||** - run multiple commands sequentially, only if the previous command fails

      ***
      - **|** - redirects output to the next command in a pipeline

      ***
      - **>** - redirects output to a file, overwriting it if it already exists

      ***
      - **>>** - redirects output to a file, appending it to the end if it already exists

      ***
      - **tee** - redirects output to both the terminal and a file

      ***

- **Permissions & Ownership**
  - Practice `chmod` in both absolute mode (`chmod 755`) and symbolic mode (`chmod +x script.sh`).
    - _Note:_
      - **chmod [number][number][number] [filename]** - set permissions using a numeric mode (e.g., `chmod 755 file.txt`)

      ***
      - **chmod +r/w/x [filename]** - add read, write, or execute permissions to a file

      ***
      - **chmod -r/w/x [filename]** - remove read, write, or execute permissions from a file

      ***
  - Practice changing file/directory ownership using `chown user:group filename`.
    - _Note:_
      - **chown user:group [filename]** - change the owner and/or group ownership of a file or directory

      ***
  - Practice user privileges management (`useradd`, `usermod -aG sudo $USER`).
    - _Note:_
      - **useradd [username]** - create a new user account

      ***
      - **usermod -aG sudo [username]** - add a user to the sudo group to grant administrative privileges

      ***

- **Package Management & System Repositories**
  - Update package index and upgrade system (`sudo apt update && sudo apt upgrade`).
    - _Note:_
      - **sudo apt update** - update the local package index with the latest available versions from repositories

      ***
      - **sudo apt upgrade** - install the latest upgrades for all currently installed packages

      ***
  - Inspect source lists under `/etc/apt/sources.list` and `/etc/apt/sources.list.d/`.
    - _Note:_
      - **/etc/apt/sources.list** - main configuration file containing the list of active APT repositories

      ***
      - **/etc/apt/sources.list.d/** - directory for adding separate `.list` files for third-party or custom repositories

      ***
  - Practice adding custom GPG keys and APT repositories (e.g., Docker repository setup).
    - _Note:_
      - **curl -fsSL [GPG_KEY_URL] | sudo gpg --dearmor -o [PATH]** - download and add custom GPG keys for verifying repository packages (e.g., Docker setup)

      ***
      - **echo "deb [arch=... signed-by=...] [URL] [SUITE] [COMPONENTS]" | sudo tee /etc/apt/sources.list.d/[name].list** - add a new third-party APT repository to the system sources list

      ***

- **Environment Variables & Shell Configuration**
  - Inspect active variables (`env`, `printenv`, `echo $PATH`).
    - _Note:_
      - **env** / **printenv** - display all active environment variables in the current shell session

      ***
      - **echo $PATH** - print the value of the PATH variable, showing directories where the shell searches for executable commands

      ***
  - Set temporary variables (`export VAR=value`) vs. permanent ones inside `~/.bashrc`.
    - _Note:_
      - **export VAR=value** - set a temporary environment variable for the current shell session and its child processes

      ***
      - **~/.bashrc** - a shell script run every time a new interactive shell is opened; add variable exports here to make them permanent

      ***

- **System & Process Monitoring**
  - Practice process management (`ps aux`, `top`, `htop`, `kill -9 <PID>`).
    - _Note:_
      - **ps aux** - list all running processes on the system with detailed information (user, PID, CPU/Memory usage, command)

      ***
      - **top** - display real-time, dynamic view of system processes and resource usage

      ***
      - **htop** - an interactive, user-friendly process viewer (improved version of top)

      ***
      - **kill -9 [PID]** - forcefully terminate a process by sending the SIGKILL signal using its Process ID

      ***
  - Manage system services via `systemctl` (`status`, `start`, `stop`, `enable`, `restart`).
    - _Note:_
      - **systemctl status [service]** - show the current running status and recent logs of a system service

      ***
      - **systemctl start [service]** - start a system service

      ***
      - **systemctl stop [service]** - stop a running system service

      ***
      - **systemctl enable [service]** - configure a service to start automatically at system boot

      ***
      - **systemctl restart [service]** - stop and then immediately start a system service

      ***
