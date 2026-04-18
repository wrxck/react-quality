# react-quality

[![CI](https://github.com/wrxck/react-quality/actions/workflows/ci.yml/badge.svg)](https://github.com/wrxck/react-quality/actions/workflows/ci.yml)

Enforce React quality standards in Claude Code sessions.

## What it checks

- No inline styles (prefer CSS modules, styled-components, or Tailwind)
- Accessibility: alt text on images, keyboard handlers on clickable divs, button types, input labels
- Semantic HTML suggestions (nav, header, footer, main, article, section)

## Installation

```
claude plugin marketplace add wrxck/claude-plugins
claude plugin install react-quality@wrxck-claude-plugins
```
