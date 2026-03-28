---
name: github-create-issue
description: Create a new issue on a GitHub repository via API
---

# GitHub Issue Creator

Create a new issue on a GitHub repository via API

## When to Use

- User wants to create issue
- User wants to github issue
- Keywords: github, issue, api, repository

## Required Parameters

- **repo** (string): Repository in owner/repo format
- **title** (string): Issue title
- **body** (string): Issue body
- **token** (string): GitHub personal access token

## Output

- **issue_number** (number): Created issue number
- **url** (string): Issue URL

## Security

- Sandbox level: strict
- Max execution time: 30000ms
- Network whitelist: api.github.com
- JadeGate verified: Yes (5-layer security check passed)

## Execution Flow

Entry: `build` -> 6 steps -> Exit: `ret_ok`, `ret_fail`
