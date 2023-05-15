import pandas as pd
import json
import os

DATA_DIR = "/data/ncc_data"
# download data and extract it in raw dir
CODE_SEARCH_NET_FENG_DIR = os.path.join(DATA_DIR, "code_search_net_feng", "raw") 

# LANGUAGE = ["go", "java", "javascript", "php", "python", "ruby"]
# We use Java language
LANGUAGE = ["java"]

DATA_SPLIT = ["valid", "train", "test"]

def count_data():
    for lang in LANGUAGE:
        for split in DATA_SPLIT:
            data_file = os.path.join(CODE_SEARCH_NET_FENG_DIR, lang, f"{split}.jsonl")
            with open(data_file) as f:
                
                data = pd.read_json(f, lines=True)
                print(data["code_token"].describe())
                print(233)

if __name__ == "__main__":
    """
    python -m data.draw_table
    """
    count_data()
    print(233)
    pass