"""Strict Backlog.md 1.53 flat subset; task metadata never asserts fencing."""

import hashlib
import json
import re
import base64

from .model import digest

FORMAT = 'backlog-md-1.53-subset-v1'
TASK_ID = r'[a-z][a-z0-9]*-[0-9]+(?:\.[0-9]+)*'
FIELDS = {
    'id', 'title', 'status', 'assignee', 'dependencies', 'reporter', 'created_date',
    'updated_date', 'due_date', 'labels', 'milestone', 'references', 'documentation',
    'modified_files', 'parent_task_id', 'subtasks', 'priority', 'type', 'project',
    'ordinal', 'onStatusChange',
}
LISTS = {'assignee', 'dependencies', 'labels', 'references', 'documentation', 'modified_files', 'subtasks'}


def task_id(value):
    if not isinstance(value, str) or not re.fullmatch(TASK_ID, value.lower()):
        raise ValueError('Backlog work requires an exact prefixed numeric task ID')
    return value.lower()


def validate_work(work):
    fields = {'format', 'directories', 'ready_statuses', 'done_status', 'actors'}
    if not isinstance(work, dict) or set(work) != fields or work['format'] != FORMAT:
        raise ValueError('Explicit supported Backlog work configuration required')
    directories = work['directories']
    if not isinstance(directories, list) or not directories or not all(
            isinstance(path, str) and re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)+', path)
            for path in directories):
        raise ValueError('Backlog directories must be explicit safe repository-relative directories')
    if any(a == b or a.startswith(b + '/') for i, a in enumerate(directories)
           for j, b in enumerate(directories) if i != j):
        raise ValueError('Backlog corpus directories must not overlap')
    ready, done = work['ready_statuses'], work['done_status']
    if (not isinstance(ready, list) or not ready or not all(isinstance(v, str) and v.strip() == v and v for v in ready)
            or len(set(ready)) != len(ready) or not isinstance(done, str) or not done
            or done.strip() != done or done in ready):
        raise ValueError('Backlog legal and completed statuses must be explicit and distinct')
    actors = work['actors']
    if (not isinstance(actors, dict) or not actors or not all(
            isinstance(key, str) and re.fullmatch(r'@?[A-Za-z0-9_-]+', key)
            and isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', value)
            for key, value in actors.items()) or len({key.lower() for key in actors}) != len(actors)):
        raise ValueError('Backlog actor mapping must be explicit and unambiguous')
    return work


def scalar(value):
    value = value.strip()
    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError('Unsupported Backlog quoted scalar') from exc
        if not isinstance(parsed, str):
            raise ValueError('Backlog scalar must be a string')
        return parsed
    if value.startswith("'"):
        if not re.fullmatch(r"'(?:[^']|'')*'", value):
            raise ValueError('Unsupported Backlog quoted scalar')
        return value[1:-1].replace("''", "'")
    if (not value or any(c in value for c in ':#[]{}&*!|>\t') or value.startswith(('-', '?', '%'))
            or value.lower() in ('null', '~', 'true', 'false', 'yes', 'no', 'on', 'off')):
        raise ValueError('Unsupported or ambiguous Backlog scalar')
    return value


def flow_list(value):
    if not value.startswith('[') or not value.endswith(']'):
        raise ValueError('Backlog lists require explicit flow/block string lists')
    body = value[1:-1].strip()
    if not body:
        return []
    items = []
    while body:
        if body.startswith('"'):
            try:
                _, end = json.JSONDecoder().raw_decode(body)
            except json.JSONDecodeError as exc:
                raise ValueError('Unsupported Backlog list') from exc
        elif body.startswith("'"):
            match = re.match(r"'(?:[^']|'')*'", body)
            if not match:
                raise ValueError('Unsupported Backlog list')
            end = match.end()
        else:
            end = body.find(',') if ',' in body else len(body)
        items.append(scalar(body[:end]))
        body = body[end:].strip()
        if not body:
            break
        if not body.startswith(',') or not body[1:].strip():
            raise ValueError('Unsupported Backlog list delimiter')
        body = body[1:].strip()
    return items


def parse_task(data):
    if not isinstance(data, bytes) or len(data) > 1_000_000:
        raise ValueError('Backlog task bytes unavailable or too large')
    try:
        text = data.decode('utf-8').replace('\r\n', '\n')
    except UnicodeError as exc:
        raise ValueError('Backlog task must be UTF-8') from exc
    lines = text.splitlines()
    if not lines or lines[0] != '---' or '---' not in lines[1:]:
        raise ValueError('Backlog task requires delimited frontmatter')
    fields, current = {}, None
    for line in lines[1:lines.index('---', 1)]:
        if not line or line.startswith('#'):
            continue
        if line.startswith('  - '):
            if current not in LISTS or not isinstance(fields.get(current), list):
                raise ValueError('Unsupported Backlog block list')
            fields[current].append(scalar(line[4:]))
            continue
        match = re.fullmatch(r'([A-Za-z][A-Za-z0-9_]*):(?: (.*))?', line)
        if not match or match[1] not in FIELDS or match[1] in fields:
            raise ValueError('Unsupported or duplicate Backlog frontmatter field')
        key, value = match[1], match[2] or ''
        if key == 'assignee' and value and not value.startswith('['):
            fields[key] = [scalar(value)]
        else:
            fields[key] = flow_list(value) if key in LISTS and value else ([] if key in LISTS else scalar(value))
        current = key if key in LISTS and not value else None
    if not {'id', 'title', 'status', 'assignee', 'dependencies'} <= fields.keys():
        raise ValueError('Backlog authority fields are required')
    fields['id'] = task_id(fields['id'])
    fields['dependencies'] = [task_id(v) for v in fields['dependencies']]
    if len(set(fields['dependencies'])) != len(fields['dependencies']):
        raise ValueError('Duplicate Backlog dependency')
    return fields


def corpus(files, work):
    validate_work(work)
    if not isinstance(files, dict) or not files or len(files) > 500:
        raise ValueError('Complete bounded Backlog corpus required (1..500 tasks)')
    tasks, identity = {}, {}
    for path, data in files.items():
        if (not isinstance(path, str) or any(c in path for c in '\r\n\t\\')
                or not any(path.startswith(folder + '/') and '/' not in path[len(folder) + 1:]
                           for folder in work['directories']) or not path.endswith('.md')):
            raise ValueError('Unsupported Backlog task path')
        parsed = parse_task(data)
        identifier = parsed['id']
        if path.rsplit('/', 1)[1].split(' - ', 1)[0].lower() != identifier or identifier in tasks:
            raise ValueError('Backlog filename/ID mismatch or duplicate task ID')
        tasks[identifier] = parsed
        identity[path] = hashlib.sha256(data).hexdigest()
    visiting, visited = set(), set()

    def visit(identifier):
        if identifier not in tasks:
            raise ValueError('Missing Backlog dependency')
        if identifier in visiting:
            raise ValueError('Backlog dependency cycle')
        if identifier in visited:
            return
        visiting.add(identifier)
        for dependency in tasks[identifier]['dependencies']:
            visit(dependency)
        visiting.remove(identifier)
        visited.add(identifier)

    for identifier in tasks:
        visit(identifier)
    return {'tasks': tasks, 'identity': digest(identity)}


def authorize(observation, work, identifier, actor):
    identifier = task_id(identifier)
    task = observation['tasks'].get(identifier)
    if task is None or task['status'] not in work['ready_statuses']:
        raise ValueError('Backlog task is missing or not legal current work')
    actors = {key.lower(): value.lower() for key, value in work['actors'].items()}
    assigned = task['assignee']
    if len(assigned) != 1 or assigned[0].lower() not in actors:
        raise ValueError('Backlog task requires one explicitly mapped executor')
    executor = actors[assigned[0].lower()]
    if not isinstance(actor, str) or actor.lower() != executor:
        raise ValueError('Backlog executor is not currently assigned')
    checked = set()

    def complete(dependency):
        if dependency in checked:
            return
        row = observation['tasks'][dependency]
        if row['status'] != work['done_status']:
            raise ValueError('Backlog dependency is not complete')
        checked.add(dependency)
        for parent in row['dependencies']:
            complete(parent)

    for dependency in task['dependencies']:
        complete(dependency)
    return {'id': identifier, 'title': task['title'], 'status': task['status'],
            'actor': executor, 'identity': observation['identity'], 'dependencies': sorted(checked)}


def corpus_entries(entries, work):
    """Select the declared corpus, rejecting special files and ambiguous layouts."""
    if not isinstance(entries, list):
        raise ValueError('Complete Backlog tree unavailable')
    selected, seen = {}, set()
    directories = work['directories']
    ancestors = {folder.rsplit('/', i)[0] for folder in directories for i in range(1, folder.count('/') + 1)}
    for item in entries:
        path = item.get('path')
        if not isinstance(path, str) or path in seen:
            raise ValueError('Malformed or duplicate immutable tree path')
        seen.add(path)
        inside = any(path.startswith(folder + '/') for folder in directories)
        if path in ancestors or path in directories:
            if item.get('type') != 'tree' or item.get('mode') != '040000':
                raise ValueError('Backlog corpus ancestor must be a regular Git tree')
        elif inside and item.get('type') != 'tree':
            if item.get('type') != 'blob' or item.get('mode') not in ('100644', '100755'):
                raise ValueError('Backlog corpus must contain regular files')
            if path.endswith('.md') and path.rsplit('/', 1)[1].lower() != 'readme.md':
                if not re.fullmatch(r'[0-9a-f]{40}', item.get('sha', '')):
                    raise ValueError('Backlog immutable blob identity missing')
                selected[path] = item['sha']
    if not selected or len(selected) > 500:
        raise ValueError('Complete bounded Backlog corpus required (1..500 tasks)')
    return selected


def read_corpus(config, revision, api):
    if not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Backlog reads require an immutable canonical revision')
    prefix = f'repos/{config["repository"]}'
    tree = api(f'{prefix}/git/trees/{revision}?recursive=1')
    if not isinstance(tree, dict) or tree.get('truncated') is not False:
        raise ValueError('Complete immutable Backlog tree unavailable')
    selected = corpus_entries(tree.get('tree'), config['work'])
    files = {}
    for path, sha in selected.items():
        blob = api(f'{prefix}/git/blobs/{sha}')
        if not isinstance(blob, dict) or blob.get('sha') != sha or blob.get('encoding') != 'base64':
            raise ValueError('Immutable Backlog blob unavailable')
        try:
            data = base64.b64decode(''.join(blob['content'].split()), validate=True)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            raise ValueError('Malformed Backlog blob bytes') from exc
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if actual != sha:
            raise ValueError('Immutable Backlog blob identity mismatch')
        files[path] = data
    return {**corpus(files, config['work']), 'revision': revision}


def local_corpus(repo, revision, work):
    """Read committed task bytes, never candidate-controlled working files."""
    import subprocess
    entries = []
    for row in repo.git('ls-tree', '-r', '-t', '-z', revision).split('\0'):
        if not row:
            continue
        metadata, path = row.split('\t', 1)
        mode, kind, sha = metadata.split(' ')
        entries.append({'path': path, 'mode': mode, 'type': kind, 'sha': sha})
    selected = corpus_entries(entries, work)
    files = {}
    for path, sha in selected.items():
        result = subprocess.run(['git', '-C', str(repo.root), 'cat-file', 'blob', sha], capture_output=True, timeout=60)
        if result.returncode:
            raise ValueError('Committed Backlog blob unavailable')
        files[path] = result.stdout
    return {**corpus(files, work), 'revision': revision}
