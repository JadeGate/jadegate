---
name: webpage-screenshot
description: Take a screenshot of a webpage using headless browser navigation
---

# Webpage Screenshot

Take a screenshot of a webpage using headless browser navigation

## When to Use

- User wants to take screenshot
- User wants to webpage screenshot
- Keywords: screenshot, webpage, capture, browser

## Required Parameters

- **url** (string): URL to screenshot

## Output

- **image_path** (string): Path to saved screenshot
- **width** (number): Page width
- **height** (number): Page height

## Security

- Sandbox level: standard
- Max execution time: 30000ms
- Network whitelist: *
- JadeGate verified: Yes (5-layer security check passed)

## Execution Flow

Entry: `nav` -> 6 steps -> Exit: `ret_ok`, `ret_fail`
