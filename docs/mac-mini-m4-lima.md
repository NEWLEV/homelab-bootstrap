# Apple M4 Mac Mini Lima Deployment

This note records the validated path for running Aisha on an Apple M4 Mac mini
without installing Linux directly on Apple Silicon hardware.

## Scope

- Host hardware: Apple M4 Mac mini, 16 GB RAM
- Host operating system: macOS 26.6.2
- Guest runtime: Lima 2.2.0 using the macOS `vz` virtualization backend
- Guest operating system: Debian 12 `arm64`
- Guest name: `aisha-macmini`
- Guest resources: 6 vCPUs, 10 GiB RAM, 70 GiB root disk
- Durable data disk: 80 GiB Lima disk named `aisha-data`
- Repository path in guest: `/srv/data/git/homelab-bootstrap`

This is a VM deployment profile. The bootstrap installer is still run inside a
Debian-family Linux guest, not on macOS.

## Host Setup

Install Lima under the macOS user account:

```bash
mkdir -p "$HOME/.local/src" "$HOME/.local/bin"
cd "$HOME/.local/src"
curl -fL -o lima-2.2.0-Darwin-arm64.tar.gz \
  https://github.com/lima-vm/lima/releases/download/v2.2.0/lima-2.2.0-Darwin-arm64.tar.gz
tar -xzf lima-2.2.0-Darwin-arm64.tar.gz -C "$HOME/.local"
```

Create the data disk:

```bash
export PATH="$HOME/.local/bin:$PATH"
limactl disk create aisha-data --size 80GiB --format qcow2 -y
```

Create `~/.lima/aisha-macmini.yaml`:

```yaml
minimumLimaVersion: 2.0.0
base:
- template:debian-12
vmType: vz
arch: aarch64
cpus: 6
memory: 10GiB
disk: 70GiB
mounts: []
containerd:
  system: false
  user: false
additionalDisks:
- name: aisha-data
  format: true
  fsType: ext4
provision:
- mode: system
  script: |
    #!/bin/sh
    set -eu
    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y ca-certificates curl git jq sudo gnupg lsb-release openssh-server
```

Start the guest:

```bash
limactl start "$HOME/.lima/aisha-macmini.yaml" -y --timeout=20m --progress
```

## Guest Storage Preparation

Lima mounts the extra disk at `/mnt/lima-aisha-data`. Aisha also needs the same
ext4 filesystem mounted at `/srv/data` and declared in `/etc/fstab`:

```bash
uuid="$(sudo blkid -s UUID -o value /dev/vdb1)"
sudo mkdir -p /srv/data
printf 'UUID=%s /srv/data ext4 defaults,noatime 0 2\n' "$uuid" | sudo tee -a /etc/fstab
sudo mount /srv/data
sudo mkdir -p /srv/data/{git,logs,services,backups,scratch}
sudo chown -R "$USER:$USER" /srv/data
```

Validate the mount:

```bash
findmnt /srv/data
df -hT /srv/data
```

Expected validated result:

```text
/srv/data /dev/vdb1 ext4 rw,noatime
```

The same filesystem may also appear at `/mnt/lima-aisha-data` because Lima
manages the attached disk. The installer accepts the deployment when `/srv/data`
is a separate ext4 filesystem with an fstab entry.

## Bootstrap

Clone and validate:

```bash
cd /srv/data/git
git clone https://github.com/NEWLEV/homelab-bootstrap.git
cd homelab-bootstrap

./install.sh --list
./install.sh --dry-run
./install.sh --validate-manifest
```

Apply:

```bash
./install.sh --apply --yes
```

Restart the guest so group membership changes are visible:

```bash
limactl stop aisha-macmini --force
limactl start aisha-macmini -y --timeout=10m
```

## Validated Evidence

The 2026-09-12 Mac mini deployment validated:

- `./install.sh --dry-run`
- `./install.sh --validate-manifest`
- `./install.sh --apply --yes`
- guest restart after Docker group changes
- `git diff --check` inside the guest repository
- clean guest repository status
- Docker data root at `/srv/data/services/docker`
- Docker Engine `29.8.0`
- Docker Compose `v5.5.1`
- Tailscale `1.102.4` authenticated as `aisha-macmini`
- SOPS `3.13.3` installed for encrypted secret restore
- active `docker` and `containerd` services
- `/srv/data` mounted from `/dev/vdb1` as ext4 with `noatime`
- non-secret core services started on the guest tailnet IP
- Compose tailnet host references parameterized for non-Aisha hosts
- Tailscale Serve HTTPS root published to the local Traefik entrypoint

The bootstrap phases completed successfully:

1. `system`
2. `storage`
3. `docker`

## Operational Notes

The macOS host currently reaches the guest through Lima:

```bash
export PATH="$HOME/.local/bin:$PATH"
limactl shell aisha-macmini
```

Tailnet-native administration is available after installing and authenticating
Tailscale inside the Debian guest:

```text
aisha-macmini.tail4553c9.ts.net
100.96.211.56
```

The 2026-09-12 non-secret service surface was verified at:

```text
https://aisha-macmini.tail4553c9.ts.net/ 200
http://100.96.211.56:8000 200
http://100.96.211.56:8080 200
http://100.96.211.56:9000 307
http://100.96.211.56:19999 200
http://100.96.211.56:3001 302
```

Secret-backed services remain blocked until runtime secrets are restored:

```text
SOPS_AGE_KEY_FILE
/srv/data/services/local-rag/secrets/api-token
/srv/data/services/openclaw/secrets.env
/home/chaliceclaw.guest/.config/openclaw/secrets.env
/srv/data/services/hermes/hermes.env
```

The Mac mini deployment uses a separate SOPS bundle and Age recipient:

```text
AISHA_SECRETS_BUNDLE=secrets/aisha-macmini.enc.yaml
SOPS_AGE_KEY_FILE=/srv/data/services/age/aisha-macmini.agekey
recipient=age1p8h774x7ty2v62239hw0sdyd6840k4wkemwv4uu2nej78ss655ms2uvg08
```

Do not commit Tailscale auth keys, node keys, or other secrets.

After Local RAG and OpenClaw are started, the compose-backed chat surface is
available through Traefik at:

```text
https://aisha-macmini.tail4553c9.ts.net/aisha/
```

The older `/openclaw` shortcut is only published when a native loopback gateway
is present on the VM.
