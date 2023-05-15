import nltk
import json
from nltk.tag.stanford import StanfordPOSTagger
from nltk.data import load
# from parser import build
from code_parser import build, visualize_ast
import os

# alienware
stanford_tag_dir = "/mnt/c/Users/38013/OneDrive/Code/ParameterDescriptionGneration/stanford-postagger"

# Huawei laptop
# stanford_tag_dir = "D:/Onedrive/Code/ParameterDescriptionGneration/stanford-postagger"
path_to_model = os.path.join(stanford_tag_dir, "models/english-bidirectional-distsim.tagger")
path_to_jar = os.path.join(stanford_tag_dir, "stanford-postagger.jar")

import os
java_path = "C:/Program Files (x86)/Common Files/Oracle/Java/javapath"
os.environ['JAVAHOME'] = java_path


# is string token
is_string = lambda identifier: \
    len(identifier) > 1 and identifier[0] == identifier[-1] and (identifier[0] == '\'' or identifier[0] == '\"')

class CharType():
    null = 0
    upper = 1
    lower = 2
    digit = 3
    operator = 4
    link = 5

    @staticmethod
    def type(char: str) -> int:
        if len(char) == 0:
            return CharType.null
        elif char == '_':
            return CharType.link
        elif str.isdigit(char):
            return CharType.digit
        elif str.isalpha(char):
            if str.isupper(char):
                return CharType.upper
            elif str.lower(char):
                return CharType.lower
        else:
            return CharType.operator

def split_identifier(identifier, str_flag=True, **kwargs):
    '''
    test samples:
         ASTFunc_name23nameNameFF_ -> AST Func name23 name Name FF
         INF -> INF
         &&= -> &&=
         {_Func_name__} -> { Func name }
         __main__ -> main

    :param identifier: variable name
    :param str_flag: true -> return raw string; false return splitted string tokens
    :return: splited subtokens
    '''

    if is_string(identifier):
        if str_flag:
            # skip string
            return [identifier]
        else:
            identifier = identifier[1:-1].strip()

    if len(identifier) > 1:
        # skip comment
        if len(identifier) > 1 and (identifier[:2] == '//' or \
                                    (identifier[:2] == '/*' and identifier[-2:] == '*/') \
            ):
            return []
    else:
        return [identifier]

    subtoken_type = CharType.null
    tmp = ''
    subtokens = []

    for char in identifier:
        current_type = CharType.type(char)
        if current_type == CharType.link:  # skip '_'
            if len(tmp) == 0:
                pass
            else:
                subtokens.append(tmp)
                tmp = ''
            subtoken_type = CharType.null
        else:
            if subtoken_type == CharType.null:
                tmp = char
                subtoken_type = CharType.type(char)
            else:
                if subtoken_type == current_type:  # previous char type equals current char type, append it
                    tmp += char
                else:
                    if (subtoken_type == CharType.upper or subtoken_type == CharType.lower) \
                        and current_type == CharType.digit:
                        # previous char type is alpha and current char type is digit, append it,
                        # and change current char type to digit
                        # eg. name 2 -> name2
                        tmp += char
                        subtoken_type = CharType.digit
                    elif subtoken_type == CharType.upper and current_type == CharType.lower:
                        if len(tmp) > 1:
                            # ASTT r -> AST Tr
                            subtokens.append(tmp[:-1])
                            tmp = tmp[-1] + char
                        else:
                            # T r -> Tr
                            tmp += char
                        subtoken_type = current_type
                    elif subtoken_type == CharType.lower and current_type == CharType.upper:
                        # name F -> name F
                        subtokens.append(tmp)
                        tmp = char
                        subtoken_type = current_type
                    elif subtoken_type == CharType.digit and \
                        (current_type == CharType.upper or current_type == CharType.lower):
                        # name23 N/n -> name23 N/n
                        subtokens.append(tmp)
                        tmp = char
                        subtoken_type = current_type
                    elif subtoken_type == CharType.operator and (not current_type == CharType.operator):
                        # { n -> { n
                        subtokens.append(tmp)
                        tmp = char
                        subtoken_type = current_type
                    elif (not subtoken_type == CharType.operator) and current_type == CharType.operator:
                        # name } -> name }
                        subtokens.append(tmp)
                        tmp = char
                        subtoken_type = current_type
                    else:
                        raise Exception
    if len(tmp) > 0:
        subtokens.append(tmp)
    return subtokens


class ParameterDescriptionGeneration:
    def __init__(self, stanford_pos_tagger=True):
        if stanford_pos_tagger:
            self.stanford_tagger = StanfordPOSTagger(path_to_model, path_to_jar=path_to_jar)

    def build_ast(self, code_string):
        res = build.build_recursiveAST(code_string)
        return res

    def convert_method_call(self, code_string):
        capture = {
            # verb
            "action": [],
            # noun phrase
            "theme": [],
            # prepositional phrases
            "secondary_args": [],
            # (optional) return type
            "return": []
        }

        
        # 获得method invocation并判断动名词
        print(code_string)

        new_ast_dict = build.parse_new_ast(code_string)
        recursive_new_dict = build.parse_recursive_new_ast(code_string)

        visualize_ast.visualize_code_ast(recursive_new_dict)
        print("Visualized!")


        ast_dict = new_ast_dict

        def find_node_by_type(ast, type: str):
            node_list = []
            for node in ast.values():
                if node["type"] == type:
                    node_list.append(node)
            return node_list

        def find_child_node_by_field_name(node, ast_dict, name: str):
            assert "children" in node.keys(), "No child node"
            node_list = []
            for child_index in node["children"]:
                if ast_dict[child_index]["field_name"] == name:
                    node = ast_dict[child_index]
                    node_list.append(node)
            return node_list

        def find_child_node_by_type(node, ast_dict, type: str):
            assert "children" in node.keys(), "No child node"
            node_list = []
            for child_index in node["children"]:
                if ast_dict[child_index]["type"] == type:
                    node = ast_dict[child_index]
                    node_list.append(node)
            return node_list
        # 根据grammar: https://github.com/tree-sitter/tree-sitter-java/blob/ac14b4b1884102839455d32543ab6d53ae089ab7/grammar.js#L1162
        # 针对 method_invocation 编写规则
        expression_node = find_node_by_type(ast_dict, "expression_statement")[0]

        method_invocation_node = find_child_node_by_type("method_invocation")[0]

        # assert method_invocation_node["type"] == "method_invocation"

        method_invocation_node = find_node_by_type(ast_dict, "method_invocation")

        # 函数调用的最后一个identifier，其field_name是
        invocation_name_node = find_child_node_by_field_name(method_invocation_node, ast_dict, "name")[0]
        invocation_name = invocation_name_node["value"]
        # In Java, a method implements an operation and typically begins with a verb phrase
        string_split = split_identifier(invocation_name)

        capture["action"] = string_split[0]

        # 函数调用的参数列表
        arguments_node = find_child_node_by_field_name(method_invocation_node, ast_dict, "arguments")[0]
        assert arguments_node["type"] == "argument_list", "Wrong type of argument node."

        argument_list = find_child_node_by_type(arguments_node, ast_dict, "identifier")

        if len(argument_list) > 0:
            value = argument_list[0]["value"]
            capture["theme"] = value
        else:
            capture["theme"] = ""

        field_access_node = find_child_node_by_field_name(method_invocation_node, ast_dict, "object")[0]
        object_list = []
        def dfs(node, ast_dict):
            field_name = node["field_name"]
            type = node["type"]
            
            if "children" not in node.keys():
                if field_name in ["object", "field"]:
                    if type == "identifier":
                        value = node["value"]
                        object_list.append(value)
            elif "children" in node.keys(): 
                for child_idx in node["children"]:
                    dfs(ast_dict[child_idx], ast_dict)
            # return object_list
        
        dfs(field_access_node, ast_dict)

        capture['secondary_args'] = object_list[0]

        template = f"{capture['action']} {capture['theme']} to {capture['secondary_args']} and get {capture['return']}"
        print(template)

    

    def variable_lexicalization(self, variable_with_type: str):
        """
        noun phrases that represent variables
        According to NLTK:
        JJ: Adjective
        NN: Noun
        VB: Verb
        """
        type, variable = variable_with_type.split()
        split_type = split_identifier(type)
        split_variable = split_identifier(variable)

        split_type = [x.lower() for x in split_type]
        split_variable = [x.lower() for x in split_variable]
        # type_pos = nltk.pos_tag(split_type)
        # variable_pos = nltk.pos_tag(split_variable, tagset="universal")

        type_pos = self.stanford_tagger.tag(split_type)
        variable_pos = self.stanford_tagger.tag(split_variable)

        natural_language = variable_with_type
        # if variable_pos[0][1] == "JJ":
        #     split_type, split_variable = split_variable, split_type
        # elif type_pos[0][1] == "VB":
        #     split_type, split_variable = split_variable, split_type
        if type_pos[0][1] == "JJ":
            pass
        else:
            split_type, split_variable = split_variable, split_type
        nl = [*split_type, *split_variable]
        seen = set()
        seen_add = seen.add
        natural_language = [x for x in nl[::-1] if not (x in seen or seen_add(x))][::-1]
        natural_language = " ".join(natural_language)
        return natural_language


class TestParameterDescriptionGeneration:
    def __init__(self) -> None:
        self.param_des_gen = ParameterDescriptionGeneration()
        with open("run/input.example") as f:
            self.example_code = f.read()


    def test_variable_lexicalization(self):
        variable_1 = "Document current"
        text_1 = self.param_des_gen.variable_lexicalization(variable_1)
        # assert text_1 == "current documentation"

        variable_2 = "CallFrame parentFrame"
        text_2 = self.param_des_gen.variable_lexicalization(variable_2)
        # assert text_2 == "parent call frame"


        variable_3 = "Selectable item"
        text_3 = self.param_des_gen.variable_lexicalization(variable_3)

    def test_method_call(self):
        method_call_list = [
            "a.b.outputStream.printTable(message, index)",
            "result = outputStream.printTable(message, message)"

        ]
        call = method_call_list[0]

        generate_text_list = []
        for call in method_call_list:
            generate_text_list.append(self.param_des_gen.convert_method_call(call))
        
        print(generate_text_list)
        


        text_1 = "print message to output stream"
        # action theme secondary-args
        # and get return-type [if M returns a value]
        call_2 = "removeWall(oldWall)"

        text_2 = "remove old wall"

        call_3 = "addItem (itemURL)"

        text_3 = "Add item, given item"

        call_4 = "f.getContentPane().add(view.getComponent(), CENTER)"

        text_4 = "Add component of drawing view to content pane of frame"

    def run_test(self):
        # self.test_variable_lexicalization()
        # self.test_build_ast()
        self.test_method_call()

# prepositional phrase

example_list = [
    "Document current",
    "CallFrame parentFrame",
    "Selectable item",
    "os.print(msg)",
]

expected_list = []


if __name__ == "__main__":
    """
    python -m run.approach
    """
    # nltk.load("maxent_treebank_pos_tagger/PY3/english.pickle")
    test = TestParameterDescriptionGeneration()
    test.run_test()
