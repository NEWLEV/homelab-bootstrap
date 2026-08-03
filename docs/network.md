# Network

## Purpose

This document describes the networking architecture of the Aisha homelab, including remote access, service exposure, firewall configuration, DNS, and network verification.

---

# Network Overview

The Aisha homelab is designed around a simple principle:

- Services communicate over the local Docker network whenever possible.
- Administrative access is performed over SSH.
- Remote access is provided through Tailscale.
- Only explicitly approved services are exposed outside the host.

---

# Network Components

| Component | Purpose |
|----------|---------|
| SSH | Administrative access |
| Tailscale | Secure remote access |
| Docker | Internal container networking |
| Traefik | Reverse proxy |
| Firewall | Restrict inbound traffic |

---

# Host Information

Display the current network configuration:

```bash
hostnamectl

hostname -I

ip addr
```

Verify routing:

```bash
ip route
```

---

# SSH

SSH provides administrative access to the host.

Verify:

```bash
systemctl status ssh

ss -tln | grep :22
```

Connect:

```bash
ssh <user>@<hostname>
```

---

# Tailscale

Tailscale provides encrypted remote access without exposing SSH directly to the Internet.

Verify:

```bash
tailscale status

tailscale ip
```

Expected:

- Node connected
- Assigned Tailscale IPv4 and IPv6 addresses
- Peer connectivity established

---

# Docker Networking

Containers communicate over Docker-managed networks.

List networks:

```bash
docker network ls
```

Inspect a network:

```bash
docker network inspect <network>
```

List container IP addresses:

```bash
docker inspect <container>
```

---

# Reverse Proxy

Traefik provides HTTP(S) routing for services.

Configuration:

```text
compose/networking/traefik.yml
```

Verify:

```bash
docker compose ps

docker compose logs traefik
```

---

# Service Discovery

Docker automatically provides DNS resolution for containers attached to the same network.

Container names should be used instead of hard-coded IP addresses.

Example:

```
http://local-rag:8080
```

---

# Firewall

Firewall configuration is managed by:

```text
security/firewall.sh
```

Verify firewall status:

```bash
sudo iptables -L

sudo nft list ruleset
```

Use the command appropriate for the firewall backend in use.

---

# Listening Services

Display listening TCP services:

```bash
ss -tln
```

Display listening UDP services:

```bash
ss -uln
```

Review any unexpected open ports.

---

# DNS

Verify name resolution:

```bash
getent hosts github.com
```

Verify connectivity:

```bash
ping github.com
```

---

# Connectivity Checks

Verify Internet connectivity:

```bash
ping 1.1.1.1
```

Verify DNS:

```bash
ping github.com
```

Verify Docker networking:

```bash
docker network ls
```

Verify Tailscale:

```bash
tailscale status
```

---

# Network Troubleshooting

## No Internet Connectivity

Check:

```bash
ip route

ping 1.1.1.1
```

---

## DNS Failure

Check:

```bash
cat /etc/resolv.conf

getent hosts github.com
```

---

## SSH Unavailable

Verify:

```bash
systemctl status ssh

ss -tln | grep :22
```

---

## Tailscale Offline

Verify:

```bash
tailscale status
```

Restart if necessary:

```bash
sudo systemctl restart tailscaled
```

---

## Docker Networking Issues

Inspect networks:

```bash
docker network ls

docker network inspect <network>
```

---

## Reverse Proxy Issues

Review logs:

```bash
docker compose logs traefik
```

Confirm the service is running:

```bash
docker compose ps
```

---

# Security Guidelines

- Use Tailscale for remote administration whenever possible.
- Restrict publicly exposed services to those explicitly required.
- Keep the firewall enabled.
- Prefer Docker service names over fixed IP addresses.
- Do not expose internal-only services directly to the Internet.
- Review listening ports after configuration changes.

---

# Verification Checklist

- [ ] SSH is operational.
- [ ] Tailscale is connected.
- [ ] Docker networks are healthy.
- [ ] Required services are reachable.
- [ ] Firewall rules are active.
- [ ] No unexpected ports are listening.
- [ ] DNS resolution is functioning.
- [ ] Internet connectivity is available.
