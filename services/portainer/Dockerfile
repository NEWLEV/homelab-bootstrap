FROM busybox:1.36.1-musl AS busybox
FROM portainer/portainer-ce:sts
COPY --from=busybox /bin/busybox /bin/busybox