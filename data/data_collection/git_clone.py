from pickle import GLOBAL
import shutil
import git
import os
from datetime import datetime


class Progress(git.remote.RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        print('update(%s/%s), Message:%s' % (cur_count, max_count, message))
        if cur_count == max_count:
            print("OK")

def get_url_list(file_path):
    repo_list = []
    with open(file_path) as f:
        repo_list_str = list(f.readlines())
        for repo_record in repo_list_str:
            star_str, repo_str = repo_record.split()
            # star = star_str.strip("stars:")

            repo = repo_str.strip("url:")
            # repo = repo.replace("https:", "git:")
            repo = repo.strip()

            repo_list.append(repo)
    return repo_list


REPO_LIST_FILE_PATH = "data/data_collection/top_10_java_list.txt"
JAVA_REPO_LIST = get_url_list(REPO_LIST_FILE_PATH)

# CSHARP_DIR = "/mnt/qiuyuan/Data/top_1000_csharp/projects"
JAVA_DIR = "data/data_example/top10_java"
REPO_DIR = os.path.join(JAVA_DIR, "projects")
JAVA_LOG_FILE = os.path.join(JAVA_DIR, "top_10_java_log.txt")


# check global variable JAVA_REPO_LIST
# assert len(JAVA_REPO_LIST) == len(list(set(JAVA_REPO_LIST)))
# assert len(JAVA_REPO_LIST) == 10
print(JAVA_REPO_LIST)

def test_clone_one():
    clone_one(JAVA_REPO_LIST[1], REPO_DIR)


def clone_one(git_url, to_dir, rank=None):
    # assert git_url.startswith("git://"), git_url
    assert not git_url.endswith("\n")

    repo_name = git_url.split("/")[-1]
    repo_name = repo_name.replace(".git", "")
    if rank:
        repo_name = rank + repo_name
    to_path = os.path.join(to_dir, repo_name)
    assert not os.path.exists(to_path), to_path

    repo = git.Repo.clone_from(git_url, to_path, progress=Progress())

    assert os.path.exists(to_path)
    pull_info = repo.git.pull()

    assert pull_info == "Already up to date."
    print(to_path + "\nok")
    return git_url, pull_info


def clone_list(repo_list, to_dir, log_file):
    with open(log_file, "w") as f:
        start = datetime.now().strftime("Time: %Y-%m-%d %H:%M\n")
        f.write(start)
    for index, repo in enumerate(repo_list):
        # e.g., top0001, top0002, top0003 etc.
        rank = "top%s_" % str(index+1).rjust(4, "0")
        git_url, pull_info = clone_one(repo, to_dir, rank)
        message = "%s || %s\n" % (git_url, pull_info)
        now = datetime.now().strftime("Time: %Y-%m-%d %H:%M\n")
        with open(log_file, "a+") as f:
            f.write(message)
            f.write(now)


def main():
    # test_clone_one()

    # check global variable REPO_DIR
    print("REPO directory:" + REPO_DIR)
    # for _, dir, file in os.walk(REPO_DIR):
    #     assert dir == [], "repo dir should be empty"
    #     assert file == [], "repo dir should be empty"
    clone_list(JAVA_REPO_LIST, REPO_DIR, JAVA_LOG_FILE)


if __name__ == "__main__":
    main()
