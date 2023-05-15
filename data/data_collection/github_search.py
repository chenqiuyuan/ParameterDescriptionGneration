from github import Github
from time import sleep
import os

COLLECTION_DIR = "data/data_collection"
# 记录搜索到的结果(以及星数)
RESULT_FILE = "top_1000_java_list.txt"

with open(os.path.join(COLLECTION_DIR, "github_token.txt")) as f:
    token = f.read()

g = Github(token)

def search_github(search_result_file, language="java"):
    repository_path_java = os.path.join(COLLECTION_DIR, search_result_file)
    repo_dict = {}

    # 因为网络问题，连续跑四次，查漏补缺
    for _ in range(4):
        java_repositories = g.search_repositories(query='language:' + language, sort='stars', order='desc')
        for repo in java_repositories:
            record = "stars:{} url:{}".format(str(repo.stargazers_count), repo.clone_url)
            print(record)
            repo_dict[repo.clone_url] = repo.stargazers_count
            sleep(0.5)


    sorted_repo = sorted(repo_dict.items(), key=lambda x: x[1], reverse=True)
    print(len(sorted_repo))

    with open(repository_path_java, "w") as f:
            for clone_url, stars in sorted_repo:
                record = "stars:{} url:{}".format(str(stars), clone_url)
                print(clone_url)
                f.write(record)
                f.write("\n")

            print("记录列表文件：" + repository_path_java)

    
    assert len(sorted_repo) > 1000, "Not enough dirs, it should be larger than 1000 (sometimes 1020)"



if __name__ == "__main__":
    search_github(RESULT_FILE)
