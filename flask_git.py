import pygit2
from flask import current_app

# Find the stack on which we want to store the database connection.
# Starting with Flask 0.9, the _app_ctx_stack is the correct one,
# before that we need to use the _request_ctx_stack.
try:
    from flask import _app_ctx_stack as stack
except ImportError:
    from flask import _request_ctx_stack as stack


class Git(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('GIT_REPOPATH', '/tmp')

    def init_repo(self):
        return pygit2.init_repository(current_app.config['GIT_REPOPATH'], False)

    def open_repo(self):
        return pygit2.Repository(current_app.config['GIT_REPOPATH'])

    @property
    def repository(self):
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, 'git_repo'):
                ctx.git_repo = self.open_repo()
            return ctx.git_repo

    def commits(self, sort_mode = pygit2.GIT_SORT_TIME):
        ref = self.repository.lookup_reference('refs/heads/master')
        return self.repository.walk(ref.target, sort_mode)

    def commits_for_path(self, path, sort_mode = pygit2.GIT_SORT_TIME):
        for commit in self.commits(sort_mode):
            if path in commit.tree:
                yield commit

    def commit_files(self, files, author, committer, message):
        repo =  self.repository
        index = repo.index
        index.read()
        for f in files:
            index.add(f)
        index.write()
        treeid = index.write_tree()
        repo.create_commit('refs/heads/master',
                           author, committer, message,
                           treeid, [repo.head.target])
