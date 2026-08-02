# Releasing Aisha

## Version domains

Aisha has separate version domains:

1. The Homelab Bootstrap appliance version.
2. Individual service and component versions.

The appliance version must not be inferred from a component version.

Local RAG currently has application version `0.11.0`, defined in
`services/local-rag/app/main.py`. Changing that component version does not
change the appliance version unless an appliance release explicitly includes
the change.

## Release model

Appliance releases use Semantic Versioning:

```text
vMAJOR.MINOR.PATCH
