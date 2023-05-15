import os
import json
import pandas as pd
from data import explore_data
from tqdm import tqdm
from typing import List
from code_parser.DFG.extract_dfg import extract_parameter_code_lines

# Input Path

EXAMPLE_DATA_DIR = "data/data_explore/code_search_net_feng"
CODESEARCHNET = "/data/ncc_data/code_search_net_feng"
data_dir = EXAMPLE_DATA_DIR

# 原始文件路径（valid用于example）
lang = "java"
mode = "valid"
raw_file = "raw/{}/{}.jsonl".format(lang, mode)
raw_file_path = os.path.join(data_dir, raw_file)

# 原始文件路径（完整数据：valid/test/train）
mode_list = ["valid", "test", "train"]
lang_list = ["java"]
raw_file_dict = {
    "valid": "",
    "test": "",
    "train": "",
}

for lang in lang_list:
    for mode in mode_list:
        # For example, "/data/ncc_data/code_search_net_feng/raw/java/valid.jsonl"
        raw_file_dict[mode] = os.path.join(CODESEARCHNET, "raw", lang, "{}.jsonl".format(mode))

# Output Path

# （输出）（“文档参数”和“函数参数”）路径
signature_file_dict = {
    "valid": "",
    "test": "",
    "train": ""
}

param_doc_file_dict = {
    "valid": "",
    "test": "",
    "train": ""
}

param_flow_file_dict = {
    "valid": "",
    "test": "",
    "train": ""
}

output_file_dict = {
    "valid": "",
    "test": "",
    "train": ""
}

method_with_param_info_dict = {
    "valid": "",
    "test": "",
    "train": ""
}

# lang_list: ["java"]
# 需要新建signature/java, param_doc/java和param_generation/java文件夹，此处不自动建了
for lang in lang_list:
    for mode in mode_list:
        # For example: /data/ncc_data/code_search_net_feng/signature/java/valid.jsonl
        signature_file_dict[mode] = os.path.join(CODESEARCHNET, "signature", lang, "{}.jsonl".format(mode))
        # For example: /data/ncc_data/code_search_net_feng/param_doc/java/valid.jsonl
        param_doc_file_dict[mode] = os.path.join(CODESEARCHNET, "param_doc", lang, "{}.jsonl".format(mode))
        # For example, /data/ncc_data/code_search_net_feng/param_flow/java/valid.jsonl
        param_flow_file_dict[mode] = os.path.join(CODESEARCHNET, "param_flow", lang, "{}.jsonl".format(mode))
        # For example: /data/ncc_data/code_search_net_feng/param_generation/java/valid.jsonl
        output_file_dict[mode] = os.path.join(CODESEARCHNET, "param_generation", lang, "{}.jsonl".format(mode))
        # For example: /data/ncc_data/code_search_net_feng/method_with_param_info/java/valid.jsonl
        method_with_param_info_dict[mode] = os.path.join(CODESEARCHNET, "method_with_param_info", lang, "{}.jsonl".format(mode))

class SingleProcess:
    @staticmethod
    def extract_parameter_flow(code) -> List:
        param_flow_dict, optimize = extract_parameter_code_lines(code)
        return param_flow_dict, optimize

    @staticmethod
    def extract_signature(code_string):
        """
        normally, a method signature consists of a method name (with type and modifiers) and a list of parameters.
        """
        method_signature = explore_data.extract_signature(code_string)["list"][0]
        optimize = False
        return method_signature, optimize

    @staticmethod
    def extract_param_doc(doc_string):
        param_doc = explore_data.extract_docstring_params(doc_string)
        optimize = False
        return param_doc, optimize

    @classmethod
    def extract_param_info(cls, code_string, doc_string):
        param_doc, optimize_doc = cls.extract_param_doc(doc_string)
        method_signature, optimize_method = cls.extract_signature(code_string)
        param_flow_dict, optimize_flow = cls.extract_parameter_flow(code_string)
        # 做一个对齐与合并
        # 如果函数没有参数，或者文档没有写参数，直接跳过
        if method_signature["parameter number"] == 0 or param_doc["doc_param_num"] == 0:
            param_info = {"No Result": "No parameter or no param doc"}
            optimize = False
            return param_info, optimize


        # 将type和name分开
        # For example:
        # ["type1 name1", "type2 name2"]
        name_list = [param.split()[-1] for param in method_signature["parameter_list"]]
        # For example: [(@param1 name1, doc1), (@param2 name2, doc2)]
        doc_name_dict = {param[0].split()[1]: " ".join(param) for param in param_doc["doc_param"]}

        

        # 按照method名字遍历，并对应到doc_name中,以name作为key
        res_name = []
        res_param_doc = []
        res_param_flow = []
        for param_name in name_list:
            if param_name in doc_name_dict.keys() and \
                    param_name in param_flow_dict.keys():
                res_name.append(param_name)
                res_param_doc.append(doc_name_dict[param_name])
                res_param_flow.append(param_flow_dict[param_name])


        optimize = any([optimize_method, optimize_doc, optimize_flow])
        param_info = {
            "param_list":res_name,
            "param_doc":res_param_doc,
            "param_flow":res_param_flow
        }
        return param_info, optimize



class BatchProcess:
    @staticmethod
    def extract_parameter_flow(input_file, output_file):
        """
        针对单个文件，从raw code中抽取parameter flow
        Input: raw_file.jsonl
        Output: param_flow.jsonl
        一行数据对应一行结果
        parameter flow 例子：
        {
            parameter_1: [code_lines_1],
            parameter_2: [code_lines_2],
            ……
        }
        """
        if os.path.exists(output_file):
            os.remove(output_file)
        with open(input_file, 'r') as reader, open(output_file, "a+") as writer:
            for line_number, line in enumerate(tqdm(reader.readlines())):
                data = json.loads(line)
                code_string = data["code"]
                # CodeSearchNet的代码片段只有单独函数
                # 需要包装一个类，让它变成一个完整的Java类结构，解析器才能正确解析
                code_string = f"class main {{\n{code_string}\n}}"
                if line_number in [38264, 67442, 73855, 129430, 138053, 146944, 153570, 153582]:
                    param_flow_dict = {"No Result": "Method without Parameter"}
                    json.dump(param_flow_dict, writer)
                    writer.write("\n")
                    continue
                param_flow_dict, optimize = SingleProcess.extract_parameter_flow(code_string)

                if optimize == True:
                    print(line_number)

                json.dump(param_flow_dict, writer)
                writer.write("\n")
    
    def extract_param_info(input_file, output_file):
        """
        针对单个文件，从raw code中抽取parameter flow
        Input: raw:valid/test/train.jsonl
        Output: method_with_param_info:valid/test/train.jsonl
        一行数据对应一行结果
        """
        if os.path.exists(output_file):
            os.remove(output_file)
        with open(input_file, 'r') as reader, open(output_file, "a+") as writer:
            for line_number, line in enumerate(tqdm(reader.readlines())):
                data = json.loads(line)
                code_string = data["code"]
                doc_string = data["docstring"]
                # CodeSearchNet的代码片段只有单独函数
                # 需要包装一个类，让它变成一个完整的Java类结构，解析器才能正确解析
                code_string = f"class main {{\n{code_string}\n}}"
                if line_number in [38264, 67442, 73855, 129430, 138053, 146944, 153570, 153582]:
                    res = {"No Result": "Method without Parameter"}
                    json.dump(res, writer)
                    writer.write("\n")
                    continue
                res, optimize = SingleProcess.extract_param_info(code_string, doc_string)

                if optimize == True:
                    print(line_number)

                json.dump(res, writer)
                writer.write("\n")

    @staticmethod
    def test_by_line(input_file, 
                    extract_function=SingleProcess.extract_parameter_flow, 
                    line_number=0):

        with open(input_file, 'r') as reader:
            line = reader.readlines()[line_number]
            data = json.loads(line)
            code_string = data["code"]
            doc_string = data["docstring"]

            # CodeSearchNet的代码片段只有单独函数
            # 需要包装一个类，让它变成一个完整的Java类结构，解析器才能正确解析
            code_string = f"class main {{\n{code_string}\n}}"

            if extract_function.__name__ == "extract_param_doc":
                param_doc = extract_function(doc_string)
                return param_doc

            if extract_function.__name__ == "extract_param_info":
                res, optimize = extract_function(code_string, doc_string)
                return res
            res, optimize = extract_function(code_string)
            return res


def debug_batch_process():
    code = """class RootNode { 
        public static AuthenticationScheme basic(String userName, String password) {
            final BasicAuthScheme scheme = new BasicAuthScheme();
            scheme.setUserName(userName);
            scheme.setPassword(password);
            b = password;
            while(True){
                c = b + b;
                scheme.setPassword(c);
            }
            return scheme;
        }
    }"""
    # param_flow_dict = SingleProcess.extract_parameter_flow(code)

    valid_file = "data/data_explore/code_search_net_feng/raw/java/valid.jsonl"
    test_file = "data/data_explore/code_search_net_feng/raw/java/valid.jsonl"
    train_file = "/data/ncc_data/code_search_net_feng/raw/java/train.jsonl"

    # f = SingleProcess.extract_parameter_flow
    # param_flow_dict = BatchProcess.test_by_line(valid_file, f, 3)

    # param_flow_dict = BatchProcess.test_by_line(train_file, f, 1563)
    # param_flow_dict = BatchProcess.test_by_line(train_file, f, 67443)
    # param_flow_dict = BatchProcess.test_by_line(train_file, f, 38264)
    # param_flow_dict = BatchProcess.test_by_line(train_file, f, 129430)

    # f = SingleProcess.extract_signature
    # signature = BatchProcess.test_by_line(train_file, f, 0)

    # f = SingleProcess.extract_param_doc
    # param_doc = BatchProcess.test_by_line(train_file, f, 0)

    # f = SingleProcess.extract_param_info
    # res = BatchProcess.test_by_line(train_file, f, 233)

    f = SingleProcess.extract_param_info
    res = BatchProcess.test_by_line(valid_file, f, 5)

    # BatchProcess.extract_parameter_flow(raw_file, param_flow_file)
    print("debug")



if __name__ == "__main__":
    """
    python -m data.batch_data_process
    """

    debug_batch_process()

    mode_list = ["valid", "test", "train"]
    # mode_list = ["valid"]
    for mode in mode_list:
        BatchProcess.extract_param_info(raw_file_dict[mode], method_with_param_info_dict[mode])

        # BatchProcess.extract_parameter_flow(raw_file_dict[mode], param_flow_file_dict[mode])