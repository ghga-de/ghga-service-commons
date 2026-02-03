FROM mcr.microsoft.com/devcontainers/python:3.0.5-3.13-trixie

ENV PYTHONUNBUFFERED=1

# Update and upgrade system packages for latest security fixes
RUN apt-get update && apt-get upgrade -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# Update args in docker-compose.yaml to set the UID/GID of the "vscode" user.
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN if [ "$USER_GID" != "1000" ] || [ "$USER_UID" != "1000" ]; then groupmod --gid $USER_GID vscode && usermod --uid $USER_UID --gid $USER_GID vscode; fi

# [Option] Install Node.js
ARG INSTALL_NODE="false"
ARG NODE_VERSION="lts/*"
RUN if [ "${INSTALL_NODE}" = "true" ]; then su vscode -c "umask 0002 && . /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"; fi

# Copy install and launcher script to bin:
COPY ./dev_install /bin

# Install secondary Python version
USER vscode
RUN <<EOF
curl -sS https://pyenv.run | /bin/sh
INIT_PYENV='
export PYENV_ROOT="$HOME/.pyenv"
[ -d "$PYENV_ROOT/bin" ] && export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
'
echo "$INIT_PYENV" >> ~/.profile
echo "$INIT_PYENV" >> ~/.bashrc
. ~/.profile
pyenv install --skip-existing 3.10
pyenv global system 3.10
EOF

CMD ["sleep", "infinity"]
