import enum
from pickletools import optimize
from typing import List, Tuple
from code_parser.build import so_file
from tree_sitter import Language, Parser
from code_parser.DFG.DFG import DFG_java
from code_parser.DFG.ParameterDFG import param_DFG_java
from code_parser.build import extract_method_declaration
from .DFG_utils import extract_method_parameter
import itertools
import json

from .DFG_utils import tree_to_token_index, index_to_code_token

dfg_function = param_DFG_java

#remove comments, tokenize code and extract dataflow     
def extract_dataflow(code, parser, lang):
    #remove comments
    try:
        code=remove_comments_and_docstrings(code,lang)
    except:
        pass    
    #obtain dataflow
    if lang=="php":
        code="<?php"+code+"?>"    
    try:
        tree = parser[0].parse(bytes(code,'utf8'))    
        root_node = tree.root_node  
        tokens_index=tree_to_token_index(root_node)     
        code=code.split('\n')
        code_tokens=[index_to_code_token(x,code) for x in tokens_index]  
        index_to_code={}
        for idx,(index,code) in enumerate(zip(tokens_index,code_tokens)):
            index_to_code[index]=(idx,code)  
        try:
            DFG,_=parser[1](root_node,index_to_code,{}) 
        except:
            DFG=[]
        DFG=sorted(DFG,key=lambda x:x[1])
        indexs=set()
        for d in DFG:
            if len(d[-1])!=0:
                indexs.add(d[1])
            for x in d[-1]:
                indexs.add(x)
        new_DFG=[]
        for d in DFG:
            if d[1] in indexs:
                new_DFG.append(d)
        dfg=new_DFG
    except:
        dfg=[]
    return code_tokens,dfg


class Node:
    def __init__(self, code: str, start_end_tuple: Tuple) -> None:
        self.code = code
        self.start_end_point = start_end_tuple
        # e.g., (0, 0) -> line 1, position 1
        self.start_line = start_end_tuple[0][0]
        # e.g., (0, 5) -> line1, position 5
        self.end_line = start_end_tuple[1][0]

        # 左闭右开
        self.line_number = list(range(self.start_line, self.end_line + 1))
    
    def __repr__(self) -> str:
        return f"<code: \"{self.code}\" -> Node object>"

        
        
        self.code_line = source_code[self.start_line:self.end_line]

def extract_dataflow(code, tree_sitter_parser):
    tree = tree_sitter_parser.parse(code.encode())
    root_node = tree.root_node

    tokens_index=tree_to_token_index(root_node)     
    code=code.split('\n')
    code_tokens=[index_to_code_token(x,code) for x in tokens_index]  
    index_to_code_dict={}
    node_dict = {}

    for idx,(index,code) in enumerate(zip(tokens_index,code_tokens)):
        # For example: index_to_code_dict[((0, 0), (0, 5))] = (0, 'class')
        index_to_code_dict[index]=(idx,code)

        node_dict[idx] = Node(code=code, start_end_tuple=index)
        

    
    # 以上将所有tree的节点遍历出来了
    try:
        DFG, _ = dfg_function(root_node, index_to_code_dict, {}) 
    except:
        DFG=[]
    DFG=sorted(DFG,key=lambda x:x[1])
    indexs=set() 
    for d in DFG:
        if len(d[-1])!=0:
            indexs.add(d[1])
        for x in d[-1]:
            indexs.add(x)
    new_DFG=[]
    for d in DFG:
        if d[1] in indexs:
            new_DFG.append(d)
    dfg = new_DFG
    return code_tokens, dfg, node_dict

def test_extract_method_parameter():
    JAVA_LANGUAGE = Language(so_file, 'java')

    tree_sitter_parser = Parser()
    tree_sitter_parser.set_language(JAVA_LANGUAGE)

    code = """class RootNode {
        public static AuthenticationScheme basic(String userName, String password) {
            final BasicAuthScheme scheme = new BasicAuthScheme();
            scheme.setUserName(userName);
            scheme.setPassword(password);
            b = password;
            c = b + b;
            return scheme;
        }
    }"""
    tree = tree_sitter_parser.parse(code.encode())
    root_node = tree.root_node
    method_with_parameter = extract_method_parameter(root_node)

    assert method_with_parameter["method_name"] == "basic"
    assert method_with_parameter["parameter_list"][0]["parameter_name"] == "userName"
    assert method_with_parameter["parameter_list"][1]["parameter_name"] == "password"
    
    print(json.dumps(method_with_parameter, indent=4))
    """
    {
        "method_name": "basic",
        "parameter_list": [
            {
                "parameter_type": "String",
                "parameter_name": "userName",
                "name_start_end_point": ((1,56),(1,64))
            },
            {
                "parameter_type": "String",
                "parameter_name": "password",
                "name_start_end_point": ((1,73),(1,81))
            }
        ]
    }
    """

# [(parameter_1, code_lines_1), (parameter_2, code_lines_2)]
def extract_parameter_code_lines(code, draw_figure=False) -> List[str]:
    # 抽取函数的parameter
    JAVA_LANGUAGE = Language(so_file, 'java')
    tree_sitter_parser = Parser()
    tree_sitter_parser.set_language(JAVA_LANGUAGE)

    tree = tree_sitter_parser.parse(code.encode())
    root_node = tree.root_node
    method_with_parameter = extract_method_parameter(root_node)

    # 该函数没有parameter，未进行优化，返回False
    if len(method_with_parameter["parameter_list"]) == 0:
        return {"No Result": "Method without Parameter"}, False

    code_line = code.split("\n")

    # 抽取函数的dataflow
    code_tokens, data_flow, node_dict = extract_dataflow(code, tree_sitter_parser)

    data_flow_dict = {}
    for node in data_flow:
        key = node[1]
        value = node
        data_flow_dict[key] = value
    

    # 将parameter对应到node_dict中，根据start_end_point定位
    start_end_point_to_node = {}
    for index, node in node_dict.items():
        start_end_point = node.start_end_point
        start_end_point_to_node[start_end_point] = (index, node)

    parameter_node_list = []

    for parameter in method_with_parameter["parameter_list"]:
        start_end_point = parameter["name_start_end_point"]
        node = start_end_point_to_node[start_end_point]
        parameter_node_list.append(node)
    """For example:
    [(9, code: "userName" <Node object>), (12, code: "password" <Node object>)]
    """

    # 遍历data flow中的各个path
    visited_flow = [[]]
    optimize = False
    max_recursion_count = 0
    MAX_PATH_LENGTH = 30
    MAX_PATH = 50
    def dfs_flow(data_flow_dict, current_node_index, visited, recursion_level):
        nonlocal max_recursion_count
        nonlocal MAX_PATH_LENGTH
        nonlocal optimize
        max_recursion_count = max(max_recursion_count, recursion_level)
        visited.append(current_node_index)

        # TODO: Optimize it
        if len(visited) > MAX_PATH_LENGTH or recursion_level > MAX_PATH_LENGTH:
            optimize = True
            return None

        if current_node_index not in data_flow_dict.keys():
            # 该节点没有被纳入graph中，这条遍历完毕
            visited_flow.append(visited)
            return None
        
        node_index_list = data_flow_dict[current_node_index][4]

        if len(node_index_list) > 0:
            for node_index in node_index_list:
                if node_index not in visited:
                    dfs_flow(data_flow_dict, node_index, visited.copy(), recursion_level=recursion_level+1)
            
        else:
            # 没有其他节点指向该节点，这条遍历完毕
            visited_flow.append(visited)

    for current_node_index in data_flow_dict.keys():

        dfs_flow(data_flow_dict, current_node_index, [], recursion_level=0)
        # print(max_recursion_count)

    # 筛选paramter相关的path，只遍历一遍visited flow

    # 初始化字典: 每个parameter的数据流
    param_flow_dict = {parameter[0]: [] for parameter in parameter_node_list}
    param_merge_flow_dict = {parameter[0]: [] for parameter in parameter_node_list}

    for flow_path in visited_flow:
        for parameter in parameter_node_list:
            parameter_node_index = parameter[0]
            if parameter_node_index in flow_path:
                # For example [[1, 2], [2, 3, 4]]
                param_flow_dict[parameter_node_index].append(flow_path)
                # For example [1, 2, 2, 3, 4]
                param_merge_flow_dict[parameter_node_index].extend(flow_path)

    if draw_figure:
        return data_flow_dict, param_flow_dict, node_dict

    param_code_line_dict = {parameter[0]: [] for parameter in parameter_node_list}
    for parameter_node_index, merge_flow_list in param_merge_flow_dict.items():
        merge_flow_set = list(set(merge_flow_list))
        related_node_list = [node_dict[idx] for idx in merge_flow_set]
        # related_code_line: 与节点相关联的代码行数，或者说节点所在的代码行数
        related_code_line_list = [node.line_number for node in related_node_list]
        # 对涉及的代码行去重并排序
        # 合并list
        merge_related_line_number_list = list(itertools.chain.from_iterable(related_code_line_list))
        # 去重
        merge_related_line_number_list = list(set(merge_related_line_number_list))
        # 排序
        merge_related_line_number_list = sorted(merge_related_line_number_list)
        # 定位回源代码
        merge_related_code_line_list = [code_line[idx] for idx in merge_related_line_number_list]
        param_code_line_dict[parameter_node_index] = merge_related_code_line_list

    result = {node_dict[param_node_index].code: code_line_list 
        for param_node_index, code_line_list in param_code_line_dict.items()}
    
    return result, optimize

if __name__ == "__main__":
    """
    python -m code_parser.DFG.extract_dfg
    """
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

    code2 = """class main{
        public static void ParameterFlow(int x, int y){
            int result;
            int irrelevant = 0;
            if (y < z){
                result = y;
            }
            else{
                result = x;
            }
            irrelevant += 1;
            System.out.println(irrelevant);
            return result;
        }
        }"""

    # 9: [[9], [37, 39, 9], [39, 9], [56, 37, 39, 9]]
    # 12: [[12], [25, 12], [30, 32, 12], [32, 12], [56, 30, 32, 12]]
    param_flow_dict, optimize_res = extract_parameter_code_lines(code2)
    print(param_flow_dict)