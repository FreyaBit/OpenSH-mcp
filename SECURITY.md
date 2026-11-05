# OpenSH-mcp — Security review policy

Check URL/path formatting and SSRF, key redaction in API responses/logs, MCP transport origin and CORS, API rate/timeouts, untrusted remote text, tool schema, user-provided key scope, and no accidental publishing of library tokens.

Perform only offline/synthetic tests and do not use real keys or live external services without explicit authorization. Every security finding must cite exact SHA, affected input, exploit consequence, safe reproduction and narrow fix; never invent severity or weaken fail-closed controls. Private issues should be reported privately to owner or via enabled GitHub advisories, not with public exploit steps. This file does not imply official audit or operational readiness.
