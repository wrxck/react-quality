#!/usr/bin/env python3
"""
Claude Code hook to enforce React quality:
- no inline styles (prefer CSS modules, styled-components, or tailwind)
- accessibility checks (alt text, aria labels, semantic html)
"""

import json
import re
import sys
from pathlib import Path

REACT_EXTENSIONS = {'.tsx', '.jsx'}


def is_react_file(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in REACT_EXTENSIONS


def check_inline_styles(content: str, file_path: str) -> list[str]:
    """check for inline style objects"""
    if not is_react_file(file_path):
        return []

    issues = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        # check for style={{ ... }}
        if re.search(r'style=\{\{', line):
            issues.append(
                f"line {line_num}: inline style detected - prefer CSS modules, styled-components, or tailwind"
            )

        # check for style={someVariable} (slightly less bad but still flagged)
        elif re.search(r'style=\{[a-zA-Z]', line):
            # skip if it's a prop being passed through
            if not re.search(r'style=\{(props\.|\.\.\.)', line):
                issues.append(
                    f"line {line_num}: dynamic style object - prefer CSS classes for maintainability"
                )

    return issues


def check_accessibility(content: str, file_path: str) -> list[str]:
    """check for accessibility issues"""
    if not is_react_file(file_path):
        return []

    issues = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        # check for img without alt
        if re.search(r'<img\b', line) and not re.search(r'\balt=', line):
            # check next few lines in case alt is on another line
            context = '\n'.join(lines[line_num - 1:line_num + 3])
            if not re.search(r'\balt=', context):
                issues.append(f"line {line_num}: <img> missing alt attribute")

        # check for click handlers on non-interactive elements without keyboard support
        if re.search(r'<(div|span|p)\b[^>]*onClick', line):
            context = '\n'.join(lines[line_num - 1:line_num + 3])
            has_keyboard = re.search(r'onKeyDown|onKeyUp|onKeyPress', context)
            has_role = re.search(r'role=', context)
            has_tabindex = re.search(r'tabIndex', context)
            if not (has_keyboard and has_role and has_tabindex):
                issues.append(
                    f"line {line_num}: onClick on non-interactive element - add role, tabIndex, and keyboard handler"
                )

        # check for anchor without href
        if re.search(r'<a\b', line) and not re.search(r'\bhref=', line):
            context = '\n'.join(lines[line_num - 1:line_num + 2])
            if not re.search(r'\bhref=', context):
                issues.append(f"line {line_num}: <a> without href - use button if not a link")

        # check for button without type
        if re.search(r'<button\b', line) and not re.search(r'\btype=', line):
            context = '\n'.join(lines[line_num - 1:line_num + 2])
            if not re.search(r'\btype=', context):
                issues.append(f"line {line_num}: <button> missing type attribute (submit|button|reset)")

        # check for form inputs without labels
        if re.search(r'<input\b', line):
            context = '\n'.join(lines[max(0, line_num - 5):line_num + 3])
            has_label = re.search(r'<label\b', context)
            has_aria_label = re.search(r'aria-label=', context)
            has_aria_labelledby = re.search(r'aria-labelledby=', context)
            has_id_with_label = re.search(r'\bid=[\'"]([^\'"]+)[\'"]', line)

            if not (has_label or has_aria_label or has_aria_labelledby):
                issues.append(f"line {line_num}: <input> should have associated label or aria-label")

        # check for missing aria-label on icon buttons
        if re.search(r'<button\b[^>]*>[^<]*<[^>]*(Icon|icon|svg)', line):
            if not re.search(r'aria-label=', line):
                issues.append(f"line {line_num}: icon button should have aria-label")

    return issues


def check_semantic_html(content: str, file_path: str) -> list[str]:
    """suggest semantic HTML alternatives"""
    if not is_react_file(file_path):
        return []

    issues = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        # check for div that could be semantic
        if re.search(r'<div\b[^>]*className=[\'"][^\'"]*nav', line, re.I):
            issues.append(f"line {line_num}: consider <nav> instead of div for navigation")

        if re.search(r'<div\b[^>]*className=[\'"][^\'"]*header', line, re.I):
            if not re.search(r'modal|card|section', line, re.I):
                issues.append(f"line {line_num}: consider <header> instead of div")

        if re.search(r'<div\b[^>]*className=[\'"][^\'"]*footer', line, re.I):
            if not re.search(r'modal|card|section', line, re.I):
                issues.append(f"line {line_num}: consider <footer> instead of div")

        if re.search(r'<div\b[^>]*className=[\'"][^\'"]*main', line, re.I):
            issues.append(f"line {line_num}: consider <main> instead of div")

        if re.search(r'<div\b[^>]*className=[\'"][^\'"]*article', line, re.I):
            issues.append(f"line {line_num}: consider <article> instead of div")

        if re.search(r'<div\b[^>]*className=[\'"][^\'"]*section', line, re.I):
            issues.append(f"line {line_num}: consider <section> instead of div")

    return issues


def validate(file_path: str, content: str) -> list[str]:
    """run all react quality checks"""
    all_issues = []
    all_issues.extend(check_inline_styles(content, file_path))
    all_issues.extend(check_accessibility(content, file_path))
    all_issues.extend(check_semantic_html(content, file_path))
    return all_issues


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    if not file_path:
        sys.exit(0)

    content = tool_input.get('new_string', '') or tool_input.get('content', '')
    if not content:
        sys.exit(0)

    issues = validate(file_path, content)

    if issues:
        print("react quality issues:", file=sys.stderr)
        for issue in issues[:8]:
            print(f"  • {issue}", file=sys.stderr)
        if len(issues) > 8:
            print(f"  ... and {len(issues) - 8} more", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == '__main__':
    main()
