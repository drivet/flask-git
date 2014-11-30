import tempfile
import os
import pygit2
import shutil
import time

class TempRepo(object):
    def __init__(self):
        self.root_dir = None
        self.repo = None
        self.files = []
        self.has_parent = False

    def init(self):
        self.root_dir = tempfile.mkdtemp()
        os.chdir(self.root_dir)
        assert os.getcwd().startswith('/tmp/')
        self.repo = pygit2.init_repository(self.root_dir)

    def copy_contents(self, repofile, contents):
        path = os.path.join(self.root_dir, repofile)
        dirname = os.path.dirname(path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        with open(path, 'w') as f:
            f.write(contents)
        self.files.append(repofile)
    
    def commit(self, message, date=time.time(), author=None):
        index = self.repo.index
        index.read()
        for f in self.files:
            index.add(f)
        index.write()
        treeid = index.write_tree()
        if author:
            sig = pygit2.Signature(author, 'alice@authors.tld', date, 0)
        else:
            sig = pygit2.Signature('Alice Author', 'alice@authors.tld', date, 0)
        self.repo.create_commit('HEAD', sig, sig, message, treeid, self._parent())
        self.has_parent = True

    def _parent(self):
        if self.has_parent:
            return [self.repo.head.target]
        else:
            return []

    def delete(self): 
        assert self.root_dir != '/tmp/' and self.root_dir.startswith('/tmp/')
        shutil.rmtree(self.root_dir)
