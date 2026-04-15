import re
from pathlib import Path

source_file = Path('/Users/jessiezhu/Library/Mobile Documents/iCloud~com~nssurge~inc/Documents/WgetCloud Local.conf')
rules_file = Path('/Users/jessiezhu/Documents/GitHub/Acceleration-Rules/rules.ini')
target_dir = Path('/Users/jessiezhu/Documents/GitHub/Acceleration-Rules/list')

if not target_dir.exists():
    raise FileNotFoundError(f"Directory does not exist: {target_dir}")

def load_rulesets_from_custom(path: Path) -> list[tuple[str, str | None]]:
    entries: list[tuple[str, str | None]] = []
    in_custom = False

    with open(path, 'r') as f:
        for raw in f:
            line = raw.strip()

            if line.startswith('[') and line.endswith(']'):
                section_name = line[1:-1].strip().lower()
                if section_name == 'custom':
                    in_custom = True
                    continue
                if in_custom:
                    break
                continue

            if not in_custom or not line.startswith('ruleset='):
                continue

            payload = line[len('ruleset='):]
            if ',' not in payload:
                continue

            search_key, rest = payload.split(',', 1)
            search_key = search_key.strip()

            target_name = None
            match = re.search(r'/([^/]+\.list)(?:$|\?)', rest.strip())
            if match:
                target_name = match.group(1)

            entries.append((search_key, target_name))

    return entries


def resolve_target_file_name(search_key: str, parsed_name: str | None, stems: dict[str, str]) -> str | None:
    if parsed_name:
        return parsed_name

    candidates = [stem for stem in stems if search_key == stem or search_key.endswith(stem)]
    if not candidates:
        return None

    best_stem = max(candidates, key=len)
    return stems[best_stem]


def normalize_matched_line(line: str, search_key: str) -> str:
    value = line.strip()
    value = re.sub(r',extended-matching$', '', value)
    value = re.sub(r',extended-maching$', '', value)

    escaped_key = re.escape(search_key)
    value = re.sub(rf',"{escaped_key}"(?=,no-resolve$|$)', '', value)
    value = re.sub(rf',{escaped_key}(?=,no-resolve$|$)', '', value)

    return value


def match_rule_line(line: str, search_key: str) -> bool:
    value = line.strip()
    keys = [search_key, f'"{search_key}"']
    suffixes = ['', ',extended-matching', ',extended-maching', ',no-resolve']

    for key in keys:
        for suffix in suffixes:
            if value.endswith(f',{key}{suffix}'):
                return True
    return False


def merge_into_list_file(path: Path, new_lines: list[str]) -> int:
    if not path.exists():
        path.touch()

    merged: list[str] = []
    seen: set[str] = set()

    for item in new_lines:
        if not item or item in seen:
            continue
        seen.add(item)
        merged.append(item)

    with open(path, 'w') as f:
        if merged:
            f.write('\n'.join(merged) + '\n')
        else:
            f.write('')

    return len(new_lines)


with open(source_file, 'r') as f:
    source_lines = f.readlines()

existing_list_files = [p.name for p in target_dir.glob('*.list')]
stems_to_files = {Path(name).stem: name for name in existing_list_files}

ruleset_entries = load_rulesets_from_custom(rules_file)
processed = 0

for search_key, parsed_target_name in ruleset_entries:
    target_name = resolve_target_file_name(search_key, parsed_target_name, stems_to_files)
    if not target_name:
        print(f"Skip {search_key}: no target .list file resolved")
        continue

    target_file = target_dir / target_name

    matched: list[str] = []
    seen_match: set[str] = set()

    for line in source_lines:
        if not match_rule_line(line, search_key):
            continue
        normalized = normalize_matched_line(line, search_key)
        if normalized in seen_match:
            continue
        seen_match.add(normalized)
        matched.append(normalized)

    added_count = merge_into_list_file(target_file, matched)
    processed += 1
    print(f"{search_key} -> {target_name}: added {added_count} lines")

print(f"Done. Processed {processed} ruleset entries.")
