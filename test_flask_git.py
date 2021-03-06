import unittest
from flask_git import Git
from flask import Flask
import os
from repoutils import TempRepo
import shutil
import tempfile

class TestFlaskGitInit(unittest.TestCase):
    """Flask git extension - init""" 
    def setUp(self):  
        self.root_dir = tempfile.mkdtemp()
        self.app = Flask(__name__)
        self.app.config['GIT_REPOPATH'] = self.root_dir

    def test_extension_can_initialize_repo(self):
        git = Git()
        git.init_app(self.app)
        gitfile = os.path.join(self.root_dir,'.git')
        print gitfile
        self.assertFalse(os.path.isdir(gitfile))
        with self.app.app_context():
            git.init_repo()
        self.assertTrue(os.path.isdir(gitfile))
            
    def tearDown(self):
        assert self.root_dir != '/tmp/' and self.root_dir.startswith('/tmp/')
        shutil.rmtree(self.root_dir)


class TestFlaskGitFetches(unittest.TestCase):
    """Flask git extension - fetch commit"""
    def setUp(self):
        self.temprepo = setup_repo()
        self.app = Flask(__name__)
        self.app.config['GIT_REPOPATH'] = self.temprepo.root_dir            

    def test_fetches_all_commits(self):
        git = Git()
        git.init_app(self.app)
        with self.app.app_context():
            commits = git.commits()
            self.assertEquals(3, len(list(commits)))

    def test_fetches_all_commits_for_file_in_regular_order(self):
        git = Git()
        git.init_app(self.app)
        with self.app.app_context():
            commits = list(git.commits_for_path_recent_first('content/hello.md'))
            self.assertEquals(2, len(commits))
            self.assertEquals('second commit', commits[0].message)
            self.assertEquals('first commit', commits[1].message)

            commits = list(git.commits_for_path_recent_first('content/bar.md'))
            self.assertEquals(1, len(commits))

    def test_fetches_all_commits_for_file_in_reverse_order(self):
        git = Git()
        git.init_app(self.app)
        with self.app.app_context():
            commits = list(git.commits_for_path_recent_last('content/hello.md'))
            self.assertEquals(2, len(commits))
            self.assertEquals('first commit', commits[0].message)
            self.assertEquals('second commit', commits[1].message)

            commits = git.commits_for_path_recent_last('content/bar.md')
            self.assertEquals(1, len(list(commits)))
 
    def test_follows_renames(self):
        git = Git()
        git.init_app(self.app)

        # move bar.md to bar2.md
        self.temprepo.delete_contents('content/bar.md')
        self.temprepo.copy_contents('content/bar2.md', medium_sized_content())
        self.temprepo.commit('fourth commit', 400)

        with self.app.app_context():
            commits = list(git.commits_for_path_recent_first('content/bar2.md', follow=True))
            self.assertEquals(2, len(commits))
            self.assertEquals('fourth commit', commits[0].message)
            self.assertEquals('third commit', commits[1].message)

    def tearDown(self):
        self.temprepo.delete()

def setup_repo():
    tr = TempRepo()
    tr.init()
    tr.copy_contents('content/hello.md', 'stuff')
    tr.commit("first commit", 100)
    tr.copy_contents('content/hello.md', 'more stuff')
    tr.commit("second commit", 200)
    tr.copy_contents('content/bar.md', medium_sized_content())
    tr.commit("third commit", 300)
    return tr

def medium_sized_content():
    """the rename algorithm doesn't work well on content that's too small"""
    contents = 'qwertyuiopasdfghjklzxcvbnmqwerty\n'
    contents += 'qwertyuiopasdfghjklzxcvbnmqwerty\n'
    contents += 'qwertyuiopasdfghjklzxcvbnmqwerty\n'
    contents += 'qwertyuiopasdfghjklzxcvbnmqwerty\n'
    return contents
