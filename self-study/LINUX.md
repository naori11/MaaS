# Phase 2: Linux Systems & Administration (Ubuntu Native)

> **Goal:** Build confidence in navigating, managing permissions, inspecting system state, and administering services directly within an Ubuntu/Debian environment.

---

## 1. Directory Navigation & File Operations

### Core Commands

| Command / Pattern | Description | Example / Usage |
| :--- | :--- | :--- |
| `ls -la` | List all files (including hidden `.` files) with detailed attributes (permissions, owner, size, date). | `ls -lh` (human-readable sizes) |
| `cd [path]` | Change current working directory. | `cd ..` (up one), `cd ~` (home), `cd -` (previous) |
| `pwd` | Print current working directory path. | `pwd` |
| `mkdir -p [dir]` | Create directories, including parent directories if they don't exist. | `mkdir -p project/src/utils` |
| `cp -r [src] [dest]` | Copy files or directories recursively. | `cp -r ./templates ./backup/` |
| `mv [src] [dest]` | Move or rename files and directories. | `mv old_name.txt new_name.txt` |
| `rm -rf [path]` | Remove files or directories recursively (`-r`) and forcefully (`-f`). Use with caution! | `rm -rf ./temp_build` |

---

## 2. Terminal Text Processing & Search

### File Viewing & Paging

- `cat [file]` — Concatenate and print entire file content to terminal.
  - *Example:* `cat /etc/os-release`
- `less [file]` — Interactive pager for navigating large files without loading entire file to memory (Press `q` to quit, `/` to search).
  - *Example:* `less /var/log/syslog`
- `head -n [N] [file]` — Output the first `N` lines of a file (default is 10).
  - *Example:* `head -n 20 access.log`
- `tail -n [N] [file]` — Output the last `N` lines of a file.
  - *Example:* `tail -n 50 error.log`
- `tail -f [file]` — Follow / stream file updates in real-time (useful for live logs).
  - *Example:* `tail -f /var/log/nginx/access.log`

### Search & Pattern Matching (`grep` & `find`)

- `grep [pattern] [file]` — Search for lines matching a pattern.
  - `grep "error" app.log` — Basic case-sensitive search.
  - `grep -i "error" app.log` — Case-insensitive search (`-i`).
  - `grep -rn "TODO" ./src` — Recursive search with line numbers (`-r` recursive, `-n` line numbers).
  - `grep -E "pattern1|pattern2" file.txt` — Extended regular expressions search.
- `find [path] [expression]` — Search the filesystem hierarchy for files/directories matching criteria.
  - `find . -type f -name "*.log"` — Find all `.log` files in current directory.
  - `find . -type f -iname "*app*"` — Case-insensitive search for files containing "app".
  - `find /var/log -type f -mtime -7` — Find files modified within the last 7 days.

---

## 3. Shell Redirection & Pipeline Operators

| Operator | Purpose | Explanation & Example |
| :--- | :--- | :--- |
| `\|` | **Pipe** | Routes stdout of left command as stdin to right command: `cat app.log \| grep "ERROR"` |
| `>` | **Redirect (Overwrite)** | Writes stdout to a file, overwriting existing content: `echo "initial" > config.txt` |
| `>>` | **Redirect (Append)** | Appends stdout to the end of a file: `echo "new line" >> audit.log` |
| `2>` / `2>&1` | **Error Redirection** | Redirect stderr (`2> errors.txt`) or combine stderr with stdout (`cmd > out.txt 2>&1`). |
| `tee [file]` | **T-Split** | Prints stdout to screen AND writes/appends to file: `make build \| tee build.log` |
| `&&` | **AND Operator** | Runs the next command only if the preceding command succeeded (exit code 0): `mkdir build && cd build` |
| `\|\|` | **OR Operator** | Runs the next command only if the preceding command failed (exit code != 0): `ping -c 1 host \|\| echo "Host unreachable"` |

---

## 4. Permissions & Ownership

### File Permission Format (`rwx`)

```text
  User (u)    Group (g)   Others (o)
  r  w  x     r  w  x     r  w  x
 (4)(2)(1)   (4)(2)(1)   (4)(2)(1)
```

### Changing Permissions (`chmod`)

- **Numeric / Absolute Mode:**
  - `chmod 755 [file]` — User: `rwx` (7), Group: `r-x` (5), Others: `r-x` (5). Standard for scripts & executables.
  - `chmod 644 [file]` — User: `rw-` (6), Group: `r--` (4), Others: `r--` (4). Standard for general files.
  - `chmod 600 [file]` — User: `rw-` (6), Group: `---` (0), Others: `---` (0). Standard for private keys (e.g. SSH keys).
- **Symbolic Mode:**
  - `chmod +x script.sh` — Add executable permission for all users.
  - `chmod u+w,go-r file.txt` — Add write to owner; remove read from group and others.
  - `chmod -R 755 /var/www/html` — Apply permissions recursively to folder contents.

### Ownership & User Management (`chown` & `useradd`)

- `chown [user]:[group] [file/dir]` — Change owner and group.
  - *Example:* `sudo chown -R www-data:www-data /var/www/html`
- `useradd -m -s /bin/bash [username]` — Create a new user account with a home directory (`-m`) and default shell (`-s`).
  - *Example:* `sudo useradd -m -s /bin/bash deployer`
- `usermod -aG sudo [username]` — Append (`-a`) the user to the `sudo` group (`-G`) for administrative privileges.
  - *Example:* `sudo usermod -aG sudo deployer`
- `passwd [username]` — Set or change user password.

---

## 5. Package Management & System Repositories (APT)

- `sudo apt update` — Fetch the latest package lists and metadata from configured repositories.
- `sudo apt upgrade -y` — Upgrade all installed packages to their newest available versions.
- `sudo apt install -y [package]` — Install a new package.
- `sudo apt remove [package]` / `sudo apt purge [package]` — Remove package (use `purge` to remove configuration files too).
- `sudo apt autoremove -y` — Remove orphan dependencies that are no longer required.

### Custom Repositories & GPG Keys

- **Sources configuration paths:**
  - `/etc/apt/sources.list` — Primary system repository configuration.
  - `/etc/apt/sources.list.d/` — Directory for external / third-party repository lists (`*.list`).
- **Adding GPG key & third-party repository (e.g. Docker):**
  ```bash
  # 1. Download and dearmor GPG key
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

  # 2. Add repository source list
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  # 3. Update index to reflect new repository
  sudo apt update
  ```

---

## 6. Environment Variables & Shell Configuration

### Inspecting & Setting Variables

- `printenv` / `env` — Display all environment variables in current shell session.
- `printenv [VAR_NAME]` or `echo $[VAR_NAME]` — Display value of a specific variable.
  - *Example:* `echo $PATH` (shows directories where shell looks for executable binaries).
  - *Example:* `echo $USER`, `echo $HOME`
- `export VAR="value"` — Set an environment variable for the current session and child processes.
  - *Example:* `export NODE_ENV="production"`

### Persistence (`~/.bashrc` vs `/etc/environment`)

- `~/.bashrc` / `~/.profile` — Per-user configuration executed when opening a non-login / login shell.
  - *To make variables permanent:* Append `export MY_VAR="value"` to `~/.bashrc` and run `source ~/.bashrc` to reload.
- `/etc/environment` — System-wide environment variable definitions (key-value pairs, available to all users).

---

## 7. System & Process Monitoring

### Process Inspection & Management

- `ps aux` — Snapshot of all running processes with user, PID, CPU/Memory %, and execution command.
- `ps aux | grep [process_name]` — Find PID for a specific running program.
- `top` — Real-time interactive process viewer and CPU/RAM resource monitor.
- `htop` — Enhanced, colorful interactive process manager (install via `sudo apt install htop`).
- `kill [PID]` — Terminate process gracefully using `SIGTERM` (15).
- `kill -9 [PID]` — Forcefully terminate unresponsive process immediately using `SIGKILL` (9).
- `pkill [process_name]` — Kill processes by name instead of PID (e.g. `pkill nginx`).

### Service Management (`systemd` / `systemctl`)

| Command | Action | Example |
| :--- | :--- | :--- |
| `systemctl status [service]` | View live execution status, active state, and recent logs. | `sudo systemctl status nginx` |
| `systemctl start [service]` | Start an inactive service. | `sudo systemctl start docker` |
| `systemctl stop [service]` | Stop an active running service. | `sudo systemctl stop docker` |
| `systemctl restart [service]` | Restart a service (stop then start). | `sudo systemctl restart nginx` |
| `systemctl reload [service]` | Reload configuration files without dropping active connections. | `sudo systemctl reload nginx` |
| `systemctl enable [service]` | Configure service to start automatically on system boot. | `sudo systemctl enable docker` |
| `systemctl disable [service]` | Prevent service from starting automatically on boot. | `sudo systemctl disable apache2` |
| `journalctl -u [service] -f` | Stream and follow real-time logs for a specific systemd unit. | `journalctl -u docker -f` |
