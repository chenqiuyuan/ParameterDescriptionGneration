"""
# 输入1：Java源文件
# 输入2：codesearchnet

# 输出格式

[java]

[docstring]

[parameter]

[doc_parameter]

[count]
method_parameter_num = 2
doc_parameter_num = 1

"""
import json
import os
import re
from tqdm import tqdm
from code_parser import build

from numpy import extract

SAMPLE_NUM = 20

DATA_DIR = "/data/ncc_data"
EXAMPLE_DATA_DIR = "data/data_explore/code_search_net_feng"
EXPLORE_FILE = "data/data_explore/code_search_net_example.txt"

MODE = "valid"
LANGUAGE = "java"


MODALITIES = [
    'code', 
    'docstring',
    'code_tokens', 
    'docstring_tokens',
]


def show_raw_example(data_dir, explore_file, lang, mode, show_number):
    writer = open(explore_file, 'w')
    print('[{}]'.format(lang), file=writer)

    raw_file = "raw/{}/{}.jsonl".format(lang, mode)
    path = os.path.join(data_dir, raw_file)
    with open(path, 'r') as reader:
        for num in range(show_number):
            line = reader.readline()
            data = json.loads(line)
            for modality in MODALITIES:
                print("Sample Number: {}".format(num), file=writer)
                print("-" * 88, file=writer)
                print('[{}]:'.format(modality), file=writer)

                print(data[modality], file=writer)
                print('\n', file=writer)
    
    writer.close()

def extract_signature_from_file(raw_file, signature_file):
    """
    针对单个文件，从raw code中抽取parameter
    Input: raw_file
    Output: signature_file
    一行数据对应一行结果
    """
    if os.path.exists(signature_file):
        os.remove(signature_file)
    with open(raw_file, 'r') as reader, open(signature_file, "a+") as writer:
        for line in tqdm(reader.readlines()):
            data = json.loads(line)
            code_string = data["code"]
            # CodeSearchNet的代码片段只有单独函数
            # 需要包装一个类，让它变成一个完整的Java类结构，解析器才能正确解析
            code_string = "class main { %s }" % code_string
            signature_list = extract_signature(code_string)
            json.dump(signature_list, writer)
            writer.write("\n")

def extract_signature(code_string):
    return build.extract_method_declaration(code_string)

def extract_docstring_params(doc_string):
    pattern = re.compile(r'(@param [a-z_][a-zA-Z1-9_]*) (.*)')

    matched_params = pattern.findall(doc_string)

    param_res = {
        "doc_param_num": len(matched_params),
        "doc_param": matched_params
    }
    return param_res

def extract_docstring_params_from_file(raw_file, doc_param_file):
    with open(raw_file) as f1, open(doc_param_file, "a+") as f2:
        f2.seek(0);f2.truncate() # 清空
        for line in tqdm(f1.readlines()):
            doc_string = json.loads(line)["docstring"]
            # core function
            param_res = extract_docstring_params(doc_string)
            json.dump(param_res, f2)
            f2.write("\n")

def test_show_raw_example():
    show_raw_example(EXAMPLE_DATA_DIR, EXPLORE_FILE, LANGUAGE, MODE, SAMPLE_NUM)
    
def show_extracted_signature(raw_file, signature_file, show_line_list=[1, 2, 3], show_file="data/data_explore/show_signature.txt"):
    
    with open(raw_file) as f1, open(signature_file) as f2:
        raw_code = f1.readlines()
        signature = f2.readlines()

    print("Total code snippets in the file: %s" % len(raw_code))

    with open(show_file, "a") as f:
        # 清空文件
        f.seek(0);f.truncate()
        for line in show_line_list:
            assert line > 0
            line -= 1
            assert line < len(raw_code), "Not enough lines"
            code = json.loads(raw_code[line])
            sig = json.loads(signature[line])
            print("Sample Line %s" % (line+1)  + "="*88, file=f)
            print("\n[raw]", file=f)
            print(code, file=f)
            print("\n[code]", file=f)
            print(code["code"], file=f)
            print("\n[doctring]", file=f)
            print(code["docstring"], file=f)
            print("\n[signature]", file=f)
            print(sig, file=f)
            method_list = json.dumps(sig["list"], indent=2)
            print(method_list, file=f)
            print("\n", file=f)
    return show_file


def count_parameters(signature_file, param_doc_file):
    """
    可以用更少的循环完成统计，但没必要，因为降低了可读性。
    每个逻辑可以分别复用。
    """
    total_method = 0
    total_parameter = 0
    total_doc_param = 0

    with open(signature_file) as f1:
        lines = f1.readlines()
        total_code_snippet = len(lines)
        signature_list = [json.loads(jline) for jline in lines]
        
        for signature in signature_list:
            total_method += signature["method_num"]
            for method in signature["list"]:
                total_parameter += method["parameter number"]

    with open(param_doc_file) as f2:
        lines = f2.readlines()
        param_doc_list = [json.loads(jline) for jline in lines]
        for param_doc in param_doc_list:
            total_doc_param += param_doc["doc_param_num"]
    
    param_zero_num = 0
    param_not_enough_num = 0
    param_enough_num = 0
    exception_num = 0

    has_param_method_num = 0
    no_param_method_num = 0

    for signature, param_doc in zip(signature_list, param_doc_list):
        actual_param_num = 0
        doc_param_num = 0
        for method in signature["list"]:
            actual_param_num += method["parameter number"]
        doc_param_num = param_doc["doc_param_num"]

        # 直接排除掉没有参数的函数
        if actual_param_num != 0:
            has_param_method_num += 1
        else:
            no_param_method_num += 1
            continue

        # 最后通过相加验证一下是否有统计错漏
        # 文档参数数量为0
        if doc_param_num == 0:
            param_zero_num += 1
        # 文档参数数量不为0，但是依然小于函数参数（不够）
        elif doc_param_num < actual_param_num and doc_param_num != 0:
            param_not_enough_num += 1
        # 文档参数数量等于函数参数数量
        elif doc_param_num == actual_param_num:
            param_enough_num += 1
        else:
        # 一般来说文档参数数量不会超过函数参数数量，但是写文档的人有他的自由
        # 发现的一个例外：行数2198
        # 'protected List<CommentTreeElement> parseRecursive(JSONObject main) throws RedditParseException '
            print("you shouldn't be here")
            exception_num += 1
            has_param_method_num -= 1

    # 参数总数缺失率：1 - @param的数量/总的函数中的param的数量
    param_rate = total_doc_param / total_parameter
    x0 = "%d/%d=%.2f%%" % (total_doc_param, total_parameter, param_rate * 100)
    # 参数总数缺失率：1 - @param的数量/总的函数中的param的数量
    missing_rate = 1 - total_doc_param / total_parameter
    x1 = "%d/%d=%.2f%%" % (total_doc_param, total_parameter, missing_rate * 100)
    # 不足率：@param数量不足（但是>1）的函数数量/总函数数量
    not_enough_rate = param_not_enough_num / has_param_method_num
    x2 = "%d/%d=%.2f%%" % (param_not_enough_num, has_param_method_num, not_enough_rate * 100)
    # 缺失率：没有param的函数数量/总函数数量
    zero_rate = param_zero_num / has_param_method_num
    x3 = "%d/%d=%.2f%%" % (param_zero_num, has_param_method_num, zero_rate * 100)
    # 完备率：@param符合规范的函数数量/总函数数量
    enough_rate = param_enough_num / has_param_method_num
    x4 = "%d/%d=%.2f%%" % (param_enough_num, has_param_method_num, enough_rate * 100)
    
    print("参数总数占比：@param的数量/总的函数中的param的数量：%s" % x0)
    print("参数总数缺失率：1 - @param的数量/总的函数中的param的数量：%s" % x1)
    print("不足率：@param数量不足（但是大于0）的函数数量/总函数数量：%s" % x2)
    print("缺失率：没有param的函数数量/总函数数量：%s" % x3)
    print("完备率：@param符合规范的函数数量/总函数数量 %s" % x4)

    # assert 不足率+缺失率+完备率+例外 == 100% 
    total_rate = not_enough_rate + zero_rate + enough_rate
    assert total_rate == 1
    total = param_zero_num + param_not_enough_num + param_enough_num
    assert total == has_param_method_num



if __name__ == "__main__":
    """
    python -m data.explore_data
    """

    lang = "java"
    mode = "valid"
    data_dir = EXAMPLE_DATA_DIR
    raw_file = "raw/{}/{}.jsonl".format(lang, mode)
    raw_file_path = os.path.join(data_dir, raw_file)

    signature_file = "signatures/{}/{}.jsonl".format(lang, mode)
    signature_file_path = os.path.join(data_dir, signature_file)

    param_doc_file = "param_doc/{}/{}.jsonl".format(lang, mode)
    param_doc_file_path = os.path.join(data_dir, param_doc_file)

    # 数据中有问题的例子
    # 行数：2198，doc param比函数参数多
    # 行数：3025，函数抽取有误（抽多了），文档不匹配
    # 行数：4168，函数抽取有误（抽多了），文档不匹配
    show_file_path = show_extracted_signature(raw_file_path, signature_file_path, show_line_list=[2198,])
    print("OK! Please explore the example in via show file path: %s" % show_file_path)
    # extract_docstring_params_from_file(raw_file_path, param_doc_file_path)

    # 抽取函数参数
    # extract_signature_from_file(raw_file_path, signature_file_path)
    # print("OK! file path: %s" % signature_file_path)
    count_parameters(signature_file_path, param_doc_file_path)
    print("统计完成! 原始文件: \n %s \n %s" % (signature_file_path, param_doc_file_path))