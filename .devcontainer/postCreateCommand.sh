#! usr/bin/bash
sudo apt-get update -y
sudo pip install pip-tools
sudo pip-compile /workspaces/cadmus/requirements.in
sudo pip-sync /workspaces/cadmus/requirements.txt