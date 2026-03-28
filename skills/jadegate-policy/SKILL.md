---
name: jadegate-policy
description: View and customize JadeGate security policies. Control network whitelists, blocked domains, rate limits, and human approval requirements.
---

# Security Policy Manager

View and customize JadeGate security policies. Control network whitelists, blocked domains, rate limits, and human approval requirements.

## When to Use

- User wants to customize security rules
- User asks about what JadeGate blocks or allows
- User wants to configure rate limits or approval workflows

## Usage

```bash
jadegate policy show                   # View current policy
jadegate policy init                   # Create customizable policy file
```

## Default Policy

- **Blocked domains**: 169.254.169.254, metadata.google, localhost
- **Blocked files**: /etc/shadow, ~/.ssh/id_*, ~/.aws/credentials
- **Blocked actions**: shell_exec, process_spawn, kernel_module
- **Require approval**: email_send, git_push, file_delete
- **Rate limit**: 60 calls/minute
- **Max call depth**: 20
- **Circuit breaker**: trips after 5 failures

## Python SDK

```python
import jadegate
jadegate.activate(policy="my-policy.json")
jadegate.activate(policy={"max_calls_per_minute": 30})
```
