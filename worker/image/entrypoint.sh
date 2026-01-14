#!/bin/bash
set -e

# Setup SSH Access
mkdir -p ~/.ssh
chmod 700 ~/.ssh

if [ ! -z "$SSH_PUBLIC_KEY" ]; then
    echo "$SSH_PUBLIC_KEY" > ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
fi

# Start SSH (as root, requires sudo if running as user, or use non-privileged port)
# Container runs as 'smart-agents', so we need sudo.
sudo service ssh start

# Start VNC/Desktop Environment
./start_all.sh
./novnc_startup.sh

# Keep the container running
tail -f /dev/null
