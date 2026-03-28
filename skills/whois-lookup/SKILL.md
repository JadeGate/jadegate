---
name: whois-lookup
description: Query WHOIS information for a domain via public API
---

# WHOIS Domain Lookup

Query WHOIS information for a domain via public API

## When to Use

- User wants to whois lookup
- User wants to domain whois
- Keywords: whois, domain, lookup, registrar

## Required Parameters

- **domain** (string): Domain to query

## Output

- **registrar** (string): Domain registrar
- **created** (string): Creation date
- **expires** (string): Expiry date
- **raw** (string): Raw WHOIS data

## Security

- Sandbox level: strict
- Max execution time: 30000ms
- Network whitelist: whois.freeaitools.xyz
- JadeGate verified: Yes (5-layer security check passed)

## Execution Flow

Entry: `fetch` -> 6 steps -> Exit: `ret_ok`, `ret_fail`
