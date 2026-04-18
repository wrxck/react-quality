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


def strip_strings_and_comments(code: str) -> str:
    out = list(code)
    i = 0
    n = len(code)
    state = None
    while i < n:
        ch = code[i]
        if state is None:
            if ch == "'" or ch == '"':
                state = ch
                i += 1
                continue
            if ch == '`':
                state = '`'
                i += 1
                continue
            i += 1
            continue
        if state == "'" or state == '"':
            if ch == '\\' and i + 1 < n:
                if code[i] != '\n':
                    out[i] = ' '
                if code[i + 1] != '\n':
                    out[i + 1] = ' '
                i += 2
                continue
            if ch == state:
                state = None
                i += 1
                continue
            if ch != '\n':
                out[i] = ' '
            i += 1
            continue
        if state == '`':
            if ch == '\\' and i + 1 < n:
                if code[i] != '\n':
                    out[i] = ' '
                if code[i + 1] != '\n':
                    out[i + 1] = ' '
                i += 2
                continue
            if ch == '$' and i + 1 < n and code[i + 1] == '{':
                i += 2
                depth = 1
                while i < n and depth > 0:
                    c2 = code[i]
                    if c2 == '{':
                        depth += 1
                    elif c2 == '}':
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                    i += 1
                continue
            if ch == '`':
                state = None
                i += 1
                continue
            if ch != '\n':
                out[i] = ' '
            i += 1
            continue
    return ''.join(out)


def is_react_file(file_path: str) -> bool:
    return Path(file_path).suffix.lower() in REACT_EXTENSIONS


def check_inline_styles(scrubbed: str, file_path: str) -> list[str]:
    """check for inline style objects"""
    if not is_react_file(file_path):
        return []

    issues = []
    lines = scrubbed.split('\n')

    for line_num, line in enumerate(lines, 1):
        if re.search(r'style=\{\{', line):
            issues.append(
                f"line {line_num}: inline style detected - prefer CSS modules, styled-components, or tailwind"
            )
        elif re.search(r'style=\{[a-zA-Z]', line):
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
        if re.search(r'<img\b', line) and not re.search(r'\balt=', line):
            context = '\n'.join(lines[line_num - 1:line_num + 3])
            if not re.search(r'\balt=', context):
                issues.append(f"line {line_num}: <img> missing alt attribute")

        if re.search(r'<(div|span|p)\b[^>]*onClick', line):
            context = '\n'.join(lines[line_num - 1:line_num + 3])
            has_keyboard = re.search(r'onKeyDown|onKeyUp|onKeyPress', context)
            has_role = re.search(r'role=', context)
            has_tabindex = re.search(r'tabIndex', context)
            if not (has_keyboard and has_role and has_tabindex):
                issues.append(
                    f"line {line_num}: onClick on non-interactive element - add role, tabIndex, and keyboard handler"
                )

        if re.search(r'<a\b', line) and not re.search(r'\bhref=', line):
            context = '\n'.join(lines[line_num - 1:line_num + 2])
            if not re.search(r'\bhref=', context):
                issues.append(f"line {line_num}: <a> without href - use button if not a link")

        if re.search(r'<button\b', line) and not re.search(r'\btype=', line):
            context = '\n'.join(lines[line_num - 1:line_num + 2])
            if not re.search(r'\btype=', context):
                issues.append(f"line {line_num}: <button> missing type attribute (submit|button|reset)")

        if re.search(r'<input\b', line):
            context = '\n'.join(lines[max(0, line_num - 5):line_num + 3])
            has_label = re.search(r'<label\b', context)
            has_aria_label = re.search(r'aria-label=', context)
            has_aria_labelledby = re.search(r'aria-labelledby=', context)
            has_id_with_label = re.search(r'\bid=[\'"]([^\'"]+)[\'"]', line)

            if not (has_label or has_aria_label or has_aria_labelledby):
                issues.append(f"line {line_num}: <input> should have associated label or aria-label")

        if re.search(r'<button\b[^>]*>[^<]*<[^>]*(Icon|icon|svg)', line):
            if not re.search(r'aria-label=', line):
                issues.append(f"line {line_num}: icon button should have aria-label")

    return issues


def _has_class_token(line: str, token: str) -> bool:
    pattern = r'className=[\'"]([^\'"]*)[\'"]'
    for m in re.finditer(pattern, line):
        classes = m.group(1).split()
        if token in classes:
            return True
    return False


def check_semantic_html(content: str, file_path: str) -> list[str]:
    """suggest semantic HTML alternatives"""
    if not is_react_file(file_path):
        return []

    issues = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        if not re.search(r'<div\b', line):
            continue

        if _has_class_token(line, 'nav'):
            issues.append(f"line {line_num}: consider <nav> instead of div for navigation")

        if _has_class_token(line, 'header'):
            if not re.search(r'modal|card|section', line, re.I):
                issues.append(f"line {line_num}: consider <header> instead of div")

        if _has_class_token(line, 'footer'):
            if not re.search(r'modal|card|section', line, re.I):
                issues.append(f"line {line_num}: consider <footer> instead of div")

        if _has_class_token(line, 'main'):
            issues.append(f"line {line_num}: consider <main> instead of div")

        if _has_class_token(line, 'article'):
            issues.append(f"line {line_num}: consider <article> instead of div")

        if _has_class_token(line, 'section'):
            issues.append(f"line {line_num}: consider <section> instead of div")

    return issues


def validate(file_path: str, content: str) -> list[str]:
    """run all react quality checks"""
    scrubbed = strip_strings_and_comments(content)
    all_issues = []
    all_issues.extend(check_inline_styles(scrubbed, file_path))
    all_issues.extend(check_accessibility(content, file_path))
    all_issues.extend(check_semantic_html(content, file_path))
    return all_issues


def extract_content(tool_input: dict) -> str:
    edits = tool_input.get('edits')
    if isinstance(edits, list) and edits:
        return '\n'.join(e.get('new_string', '') for e in edits)
    return tool_input.get('new_string', '') or tool_input.get('content', '')


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    tool_input = input_data.get('tool_input', {})
    file_path = tool_input.get('file_path', '')

    if not file_path:
        sys.exit(0)

    content = extract_content(tool_input)
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
