openclaw() {
    set -a
    source "$HOME/.config/openclaw/secrets.env"
    set +a

    export NODE_COMPILE_CACHE=/var/tmp/openclaw-compile-cache
    export OPENCLAW_NO_RESPAWN=1

    command "$HOME/.npm-global/bin/openclaw" "$@"
    local rc=$?

    unset OPENCLAW_GATEWAY_TOKEN OPENCLAW_DISCORD_TOKEN
    unset NODE_COMPILE_CACHE OPENCLAW_NO_RESPAWN

    return "$rc"
}
