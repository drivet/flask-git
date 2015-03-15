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
        app.config.setdefault('GIT_SEARCH_PATH', '')

    def init_repo(self):
        print current_app.config['GIT_REPOPATH']
        return pygit2.init_repository(current_app.config['GIT_REPOPATH'], False)

    def open_repo(self):
        if current_app.config['GIT_SEARCH_PATH']:
            config_level = pygit2.GIT_CONFIG_LEVEL_GLOBAL
            search_path = current_app.config['GIT_SEARCH_PATH']
            pygit2.settings.search_path[config_level] = search_path
        return pygit2.Repository(current_app.config['GIT_REPOPATH'])

    @property
    def repository(self):
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, 'git_repo'):
                ctx.git_repo = self.open_repo()
            return ctx.git_repo

    def commits(self, sort_mode=pygit2.GIT_SORT_TIME):
        ref = self.repository.lookup_reference('refs/heads/master')
        return self.repository.walk(ref.target, sort_mode)

    # git commits store the entire snapshot of the repo, which makes it
    # somewhat inconvenient to find the history of a file.  Basically, we
    # have to find all those commits associated with a change in the SHA of
    # the file who's history we're tracking
   
    def commits_for_path_recent_first(self, path, follow=False):
        last_oid_of_file = None
        last_commit = None
        current_path = path
        for commit in self.commits(pygit2.GIT_SORT_TIME):
            if current_path in commit.tree:
                # we found a commit where the file exists in the repo at
                # the time of this commit.  Is its SHA different from the
                # SHA that we've previously seen for this file?
                current_oid = commit.tree[current_path].id
                if current_oid != last_oid_of_file and last_oid_of_file:
                    # this commit seems to have changed the oid of the file
                    yield last_commit
                last_oid_of_file = current_oid
            elif last_oid_of_file: 
                # this commit seems to contain no mention of the file.
                # BUT we have a record of the file existing in a
                # previous (more recent) commit. I guess this means
                # we've past the creation of the file, so yield the
                # last commit here
                if follow:
                    diff = self.repository.diff(commit.tree, last_commit.tree)
                    diff.find_similar()

                    renamed = False
                    for patch in diff:
                        if patch.status == 'R' and patch.new_file_path == current_path:
                            # the current_path is the "new" path in a
                            # rename patch.  This indicates that the file
                            # was renamed here from the "old" path
                            yield last_commit
                            current_path = patch.old_file_path
                            last_oid_of_file = commit.tree[current_path].id
                            renamed = True
                            break

                    if not renamed:
                        last_oid_of_file = None
                        yield last_commit
                else:
                    last_oid_of_file = None
                    yield last_commit
            last_commit = commit

        if last_oid_of_file:
            yield last_commit
        
    def commits_for_path_recent_last(self, path):
        last_oid_of_file = None
        for commit in self.commits(pygit2.GIT_SORT_REVERSE):
            if path in commit.tree: 
                # we found a commit where the file exists in the repo at
                # the time of this commit.  Is its SHA different from the
                # SHA that we've previously seen for this file?
                current_oid = commit.tree[path].id
                if current_oid != last_oid_of_file:
                    # this commit seems to have changed the oid of the file
                    # or it's the first one we've seen
                    yield commit
                    last_oid_of_file = current_oid
            else: 
                # the commit seems to contain no mention of the file.
                # Maybe we haven't seen it yet, maybe it was deleted.
                # Either way clear the last SHA.
                last_oid_of_file = None


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
