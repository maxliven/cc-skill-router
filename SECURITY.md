# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1.0 | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in cc-skill-router, please open a private security advisory on GitHub:

https://github.com/maxliven/cc-skill-router/security/advisories/new

We aim to respond within 7 days and will keep you informed throughout the remediation process.

## Security Notes

- cc-skill-router runs entirely locally and makes no network calls.
- No API keys, credentials, or telemetry are collected.
- The registry is stored as plain JSON in `~/.skill-router/index.json` by default.
