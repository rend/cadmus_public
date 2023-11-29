#! usr/bin/bash
sudo apt-get update -y
sudo pip install pip-tools
sudo pip-compile /workspaces/cadmus_public/requirements.in
sudo pip-sync /workspaces/cadmus_public/requirements.txt