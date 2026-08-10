#!/usr/bin/env bash
set -Eeuo pipefail

readonly TAILSCALE_INTERFACE="${TAILSCALE_INTERFACE:-tailscale0}"
readonly TAILSCALE_UDP_PORT="41641"
readonly AISHA_CHAIN="AISHA-INGRESS"

usage() {
    printf 'Usage: %s --dry-run | --apply | --verify\n' "$0"
}

run() {
    if [[ "$MODE" == "dry-run" ]]; then
        printf '+'
        printf ' %q' "$@"
        printf '\n'
    else
        "$@"
    fi
}

ensure_jump() {
    local tool="$1"

    if [[ "$MODE" == "dry-run" ]]; then
        printf '+ %q -C DOCKER-USER -j %q || %q -I DOCKER-USER 1 -j %q\n' \
            "$tool" "$AISHA_CHAIN" "$tool" "$AISHA_CHAIN"
    elif ! "$tool" -C DOCKER-USER -j "$AISHA_CHAIN" 2>/dev/null; then
        "$tool" -I DOCKER-USER 1 -j "$AISHA_CHAIN"
    fi
}

configure_docker_filter() {
    local tool="$1"

    run "$tool" -N "$AISHA_CHAIN" 2>/dev/null || true
    run "$tool" -F "$AISHA_CHAIN"
    run "$tool" -A "$AISHA_CHAIN" -m conntrack --ctstate RELATED,ESTABLISHED -j RETURN
    run "$tool" -A "$AISHA_CHAIN" -i "$TAILSCALE_INTERFACE" -j RETURN
    run "$tool" -A "$AISHA_CHAIN" -p tcp -m multiport --dports 80,443 -j RETURN
    run "$tool" -A "$AISHA_CHAIN" -j DROP
    ensure_jump "$tool"
}

apply_policy() {
    command -v ufw >/dev/null
    command -v iptables >/dev/null
    command -v ip6tables >/dev/null

    run ufw default deny incoming
    run ufw default allow outgoing
    run ufw default deny routed
    run ufw allow 22/tcp comment 'SSH'
    run ufw allow 80/tcp comment 'Traefik HTTP'
    run ufw allow 443/tcp comment 'Traefik HTTPS'
    run ufw allow "$TAILSCALE_UDP_PORT/udp" comment 'Tailscale transport'
    run ufw allow in on "$TAILSCALE_INTERFACE" comment 'Tailnet services'

    configure_docker_filter iptables
    configure_docker_filter ip6tables

    run ufw --force enable
}

verify_policy() {
    local failed=0

    ufw status verbose
    iptables -S DOCKER-USER
    iptables -S "$AISHA_CHAIN"
    ip6tables -S DOCKER-USER
    ip6tables -S "$AISHA_CHAIN"

    ufw status verbose | grep -Fq 'Status: active' || failed=1
    iptables -C DOCKER-USER -j "$AISHA_CHAIN" || failed=1
    ip6tables -C DOCKER-USER -j "$AISHA_CHAIN" || failed=1
    iptables -C "$AISHA_CHAIN" -i "$TAILSCALE_INTERFACE" -j RETURN || failed=1
    iptables -C "$AISHA_CHAIN" -p tcp -m multiport --dports 80,443 -j RETURN || failed=1
    iptables -C "$AISHA_CHAIN" -j DROP || failed=1

    return "$failed"
}

if (($# != 1)); then
    usage >&2
    exit 2
fi

case "$1" in
    --dry-run)
        MODE="dry-run"
        apply_policy
        ;;
    --apply)
        MODE="apply"
        if ((EUID != 0)); then
            printf '%s\n' 'ERROR: --apply must run as root.' >&2
            exit 1
        fi
        apply_policy
        ;;
    --verify)
        MODE="verify"
        if ((EUID != 0)); then
            printf '%s\n' 'ERROR: --verify must run as root.' >&2
            exit 1
        fi
        verify_policy
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
