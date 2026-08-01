# ADR 0001: MCP Client and Transport

- Status: Accepted
- Date: 2026-08-01

## Context

Aisha needs a supported path for clients to call MCP servers. The client choice determines transport, authentication, exposure, and gateway placement. Small on-device models may not be reliable tool callers, so the architecture must not assume that path works before it is tested.

## Decision

- Support both laptop and on-device MCP clients.
- The primary supported and acceptance-tested path for v2.0 is a laptop client connecting to Aisha over the tailnet.
- On-device clients such as Open WebUI may use the same gateway, but remain experimental until validated.
- The MCP gateway will expose the single remote endpoint.
- Remote access will use streamable HTTP where supported, protected by authentication and tailnet-only exposure.
- Local stdio may be used between the gateway and individual MCP servers where appropriate.
- The project will not assume that a small on-device model can reliably call tools.

## Consequences

- Laptop-first support provides a reliable acceptance path.
- The gateway must support remote authenticated transport.
- On-device MCP support cannot block v2.0.
- Tool permissions and negative tests must be enforced at the gateway and server layers.

## Validation

- A laptop client can call each approved MCP server through the gateway over the tailnet.
- Authentication is required.
- On-device support is documented as experimental until separately validated.
