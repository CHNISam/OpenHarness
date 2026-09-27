import unittest

from openharness.backlog import authorize, corpus, parse_task, validate_work
from openharness.model import default_config, validate_config


def settings():
    return {'format': 'backlog-md-1.53-subset-v1',
            'directories': ['backlog/tasks', 'backlog/completed'],
            'ready_statuses': ['To Do', 'In Progress'], 'done_status': 'Done',
            'actors': {'@alice': 'alice', '@bob': 'bob'}}


def configuration():
    config = default_config('owner/repo', 'main')
    config.update(profile='github-backlog-v1', work=settings())
    config['authorities']['work'] = 'repository-backlog'
    return config


def task(identifier='task-1', status='To Do', assignee='["@alice"]', dependencies='[]'):
    return (f'---\nid: {identifier}\ntitle: Example\nstatus: {status}\n'
            f'assignee: {assignee}\ndependencies: {dependencies}\nlabels: []\n'
            'created_date: 2026-09-27\n---\n\n## Description\nOpaque body\n').encode()


class BacklogTests(unittest.TestCase):
    def test_config_requires_explicit_profile_and_single_authority(self):
        self.assertEqual(configuration(), validate_config(configuration()))
        for mutation in ('mirror', 'format', 'actor_alias', 'overlap'):
            config = configuration()
            if mutation == 'mirror':
                config['authorities']['work'] = 'github-issues'
            elif mutation == 'format':
                config['work']['format'] = 'yaml-any'
            elif mutation == 'actor_alias':
                config['work']['actors']['@ALICE'] = 'bob'
            else:
                config['work']['directories'].append('backlog/tasks/nested')
            with self.assertRaises(ValueError, msg=mutation):
                validate_config(config)
        existing = default_config('owner/repo', 'main')
        existing['work'] = settings()
        with self.assertRaises(ValueError):
            validate_config(existing)

    def test_flat_serializer_formats_and_crlf_have_same_authority(self):
        inline = parse_task(task())
        block = parse_task(task(assignee="\n  - '@alice'", dependencies='[]').replace(b'\n', b'\r\n'))
        self.assertEqual(inline, block)
        self.assertEqual(['@alice'], inline['assignee'])
        self.assertEqual(['@alice'], parse_task(task(assignee='@alice'))['assignee'])

    def test_quoted_strings_do_not_create_fields_or_yaml_objects(self):
        data = task().replace(b'title: Example', b'title: "Example: # text"')
        self.assertEqual('Example: # text', parse_task(data)['title'])
        data = data.replace(b'"Example: # text"', b"'It''s quoted'")
        self.assertEqual("It's quoted", parse_task(data)['title'])

    def test_unsupported_or_ambiguous_frontmatter_fails_closed(self):
        for replacement in (b'assignee: *owner', b'assignee: &owner ["@alice"]',
                            b'assignee: {user: alice}', b'assignee: !!str alice',
                            b'"assignee": ["@alice"]', b'assignee: ["@alice"] # hidden',
                            b'assignee: |\n  @alice', b'assignee: ["@alice"]\nassignee: ["@bob"]'):
            with self.assertRaises(ValueError, msg=repr(replacement)):
                parse_task(task().replace(b'assignee: ["@alice"]', replacement))
        with self.assertRaises(ValueError):
            parse_task(task().replace(b'labels: []', b'new_authority: owner'))

    def test_immutable_corpus_rejects_duplicates_paths_and_unknown_dependency(self):
        files = {'backlog/tasks/task-1 - Example.md': task()}
        self.assertEqual('task-1', authorize(corpus(files, settings()), settings(), 'task-1', 'alice')['id'])
        for extra in ('backlog/completed/task-1 - Duplicate.md', 'backlog/tasks/wrong - Name.md',
                      'backlog/tasks/nested/task-1 - Example.md'):
            with self.assertRaises(ValueError):
                corpus({**files, extra: task()}, settings())
        with self.assertRaises(ValueError):
            corpus({'backlog/tasks/task-1 - Example.md': task(dependencies='[task-2]')}, settings())

    def test_dependencies_must_be_complete_and_graph_acyclic(self):
        files = {'backlog/tasks/task-1 - Example.md': task(dependencies='[task-2]'),
                 'backlog/completed/task-2 - Prerequisite.md': task('task-2', 'Done')}
        self.assertEqual(['task-2'], authorize(corpus(files, settings()), settings(), 'task-1', 'alice')['dependencies'])
        files['backlog/completed/task-2 - Prerequisite.md'] = task('task-2', 'To Do')
        with self.assertRaisesRegex(ValueError, 'dependency'):
            authorize(corpus(files, settings()), settings(), 'task-1', 'alice')
        files['backlog/completed/task-2 - Prerequisite.md'] = task('task-2', 'Done', dependencies='[task-1]')
        with self.assertRaisesRegex(ValueError, 'cycle'):
            corpus(files, settings())

    def test_current_assignment_status_and_actor_are_required(self):
        for assignee, status, actor in (('[]', 'To Do', 'alice'), ('["@unknown"]', 'To Do', 'alice'),
                                       ('["@alice", "@bob"]', 'To Do', 'alice'),
                                       ('["@alice"]', 'Done', 'alice'),
                                       ('["@alice"]', 'To Do', 'bob')):
            with self.assertRaises(ValueError):
                authorize(corpus({'backlog/tasks/task-1 - Example.md': task(status=status, assignee=assignee)}, settings()),
                          settings(), 'task-1', actor)

    def test_any_corpus_byte_drift_changes_identity(self):
        files = {'backlog/tasks/task-1 - Example.md': task()}
        original = corpus(files, settings())['identity']
        files[next(iter(files))] += b'Changed description\n'
        self.assertNotEqual(original, corpus(files, settings())['identity'])

    def test_configuration_requires_explicit_nonconflicting_statuses(self):
        config = settings()
        config['ready_statuses'].append('Done')
        with self.assertRaises(ValueError):
            validate_work(config)


if __name__ == '__main__':
    unittest.main()
