from git import Repo
from datetime import datetime
import os

# LIST_FILE_PATH = "/home/qiuyuan/Data/top_1000_csharp/top_1000_charp_list 202012161859.txt"
REPO_DIR = "/home/qiuyuan/Data/top_1000_csharp/projects"
PULL_LOG = "/home/qiuyuan/Data/top_1000_csharp/update_log.txt"


repo_dirs = []
for root, dirs, _ in os.walk(REPO_DIR):
    for d in dirs:
        git_repo = os.path.join(root, d, ".git")
        assert os.path.exists(git_repo), "the repo does not exist" + git_repo
        repo_dirs.append(git_repo)
    break

print(len(repo_dirs))
print(repo_dirs)

time = datetime.now().strftime("Time: %Y-%m-%d %H:%M\n")
with open(PULL_LOG, "a+") as f:
    f.write(time)
    for git_repo in repo_dirs:
        repo = Repo(git_repo)
        assert repo is not None, "The repo doesn't exit" + repo

        try:
            repo.git.fetch('--all')
            repo.git.reset('--hard', 'origin/master')
            repo.git.fetch()
            res = repo.git.pull()
            print(res)
            message = "%s || %s\n" % (git_repo, res)
            f.write(message)
        except Exception as e:
            print("______Exception: %s" % git_repo)
            print(e)
