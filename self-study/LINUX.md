## Phase 2: Linux Systems & Administration (Ubuntu Native)
> **Goal:** Get comfortable navigating, managing permissions, and inspecting system state directly inside your Ubuntu installation.

### Action Tasks
* **Directory Navigation & File Operations**
  * Practice essential file commands: `ls -la`, `cd`, `mkdir -p`, `cp -r`, `mv`, `rm -rf`.
    * *Note:*
      * __ls__ - for listing files and directories
      
      ---
      
      * __cd__ - for changing directories
      
      ---
      
      * __mkdir__ - for creating directories
      
      ---
      
      * __cp__ - for copying files and renaming
      
      ---
      
      * __mv__ - for moving files
      
      ---
      
      * __rm__ - for removing files and directories
  * Master terminal text processing: `cat`, `less`, `head`, `tail -f`, `grep`, and `find`.
    * *Note:* 
      * __cat [filename]__ - for concatenating and displaying file contents
      
      ---
      
      * __less [filename]__ - for viewing file contents page by page
      
      ---
      
      * __head -n [number] [filename]__ - for displaying the first few lines of a file
      
      ---
      
      * __tail -n [number] [filename]__ - for displaying the last few lines of a file
      
      ---
      
      * __grep "TEXT" [filename]__ - for searching for specific text patterns in files
      * __grep -i "text" [filename]__ - for searching for case-insensitive specific text patterns in files
      * __grep -e "TEXT1|TEXT2" [filename]__ - for searching for multiple text patterns in files
      
      ---
      
      * __find . -type f -name "*.log"__ - for locating files and directories
      * __find . -type f -iname "*app*"__ - case-insensitive, for locating files and directories
      
      ---
      
  * Use shell redirection operators (`|`, `>`, `>>`, `tee`) to filter outputs and log to files.
    * *Note:* 

* **Permissions & Ownership**
  * Practice `chmod` in both absolute mode (`chmod 755`) and symbolic mode (`chmod +x script.sh`).
    * *Note:* 
  * Practice changing file/directory ownership using `chown user:group filename`.
    * *Note:* 
  * Practice user privileges management (`useradd`, `usermod -aG sudo $USER`).
    * *Note:* 

* **Package Management & System Repositories**
  * Update package index and upgrade system (`sudo apt update && sudo apt upgrade`).
    * *Note:* 
  * Inspect source lists under `/etc/apt/sources.list` and `/etc/apt/sources.list.d/`.
    * *Note:* 
  * Practice adding custom GPG keys and APT repositories (e.g., Docker repository setup).
    * *Note:* 
* **Environment Variables & Shell Configuration**
  * Inspect active variables (`env`, `printenv`, `echo $PATH`).
    * *Note:* 
  * Set temporary variables (`export VAR=value`) vs. permanent ones inside `~/.bashrc`.
    * *Note:* 

* **System & Process Monitoring**
  * Practice process management (`ps aux`, `top`, `htop`, `kill -9 <PID>`).
    * *Note:* 
  * Manage system services via `systemctl` (`status`, `start`, `stop`, `enable`, `restart`).
    * *Note:*
