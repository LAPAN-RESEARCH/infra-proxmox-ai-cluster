# Ubuntu Server Setup

## Base Packages

```bash
sudo apt update
sudo apt full-upgrade -y

sudo apt install -y \
  qemu-guest-agent \
  openssh-server \
  curl \
  ca-certificates \
  gnupg \
  git \
  jq \
  htop \
  tmux \
  unzip \
  rsync \
  build-essential \
  python3 \
  python3-venv \
  python3-pip \
  vim
```

---

# SSH Hardening

## Public Key Authentication

Public keys:

```text
~/.ssh/id_ed25519.pub
~/.ssh/id_ed25519_holhos.pub
```

Important:

The username/comment at the end of the public key:

```text
ssh-ed25519 AAAA... hugo@hugodepaula
```

is only a label and does not need to match the Ubuntu VM username.

---
