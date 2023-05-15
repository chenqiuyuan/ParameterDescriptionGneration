import os
import json
from re import A
from tree_sitter import Language, Parser, Tree, TreeCursor

from code_parser import visualize_ast
from .utils import util_ast

__TREE_SITTER_LIBS_DIR__ = "tree_sitter_libs"
YOUR_LANGUAGE = 'java'

so_file = os.path.join(__TREE_SITTER_LIBS_DIR__, f'{YOUR_LANGUAGE}.so')
lib_dir = os.path.join(__TREE_SITTER_LIBS_DIR__, "tree-sitter-java")

def build_so():
    print(f"Build {YOUR_LANGUAGE}.so, and save it at {__TREE_SITTER_LIBS_DIR__}")
    Language.build_library(
        # your language parser file, we recommend build *.so file for each language
        so_file,
        # Include one or more languages
        [lib_dir],
    )

def parse(code):
    JAVA_LANGUAGE = Language(so_file, 'java')

    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)

    tree = parser.parse(code)
    return tree

def parse_ast(code_string):
    parser = TreeSitterASTParser(SO_FILE=os.path.join(__TREE_SITTER_LIBS_DIR__, f"java.so"), LANGUAGE="java")
    ast = parser.parse_raw_ast(code_string, MIN_AST_SIZE=0)
    return ast

def parse_new_ast(code_string):
    parser = TreeSitterASTParser(SO_FILE=os.path.join(__TREE_SITTER_LIBS_DIR__, f"java.so"), LANGUAGE="java")
    new_ast = parser.parse_new_tree(code_string, MIN_AST_SIZE=0)

    return new_ast

def parse_recursive_ast(code_string):
    parser = TreeSitterASTParser(SO_FILE=os.path.join(__TREE_SITTER_LIBS_DIR__, f"java.so"), LANGUAGE="java")
    recursive_ast = parser.parse_recursive_ast(code_string)
    return recursive_ast

def parse_recursive_new_ast(code_string):
    parser = TreeSitterASTParser(SO_FILE=os.path.join(__TREE_SITTER_LIBS_DIR__, f"java.so"), LANGUAGE="java")
    recursive_new_ast = parser.parse_recursive_new_tree(code_string)
    return recursive_new_ast

class TreeSitterASTParser(object):
    '''parse code data into ast'''
    __slots__ = ('parser', 'to_lower', 'LANGUAGE', 'operators',)

    def __init__(self, SO_FILE, LANGUAGE, to_lower=False, operators_file=None):
        self.parser = Parser()
        try:
            assert os.path.exists(SO_FILE), FileExistsError(
                f"{SO_FILE} does not exist, automatically download TreeSitter parse file {LANGUAGE}.so."
            )
        except FileExistsError as err:
            # LOGGER.warning(err)
            # from ncc.utils.hub.tree_sitter.download import download
            # download(LANGUAGE)
            pass

        self.parser.set_language(Language(SO_FILE, LANGUAGE))
        self.LANGUAGE = LANGUAGE
        self.to_lower = to_lower

        if operators_file is None:
            operators_file = os.path.join(os.path.dirname(__file__), 'operators.json')
        with open(operators_file, 'r') as reader:
            self.operators = json.load(reader)

    def subcode(self, start, end, code_lines):
        '''
        extract substring from code lines
        :param start: start point
        :param end: end point
        :param code_lines: codes.split('\n')
        :return: substring of code
        '''
        if start[0] == end[0]:
            return code_lines[start[0]][start[1]:end[1]]
        elif start[0] < end[0]:
            sub_code_lines = [code_lines[start[0]][start[1]:]]
            for line_num in range(start[0] + 1, end[0]):
                sub_code_lines.append(code_lines[line_num])
            sub_code_lines.append(code_lines[end[0]][:end[1]])
            return b'\n'.join(sub_code_lines)
        else:
            return b'\n'
            raise NotImplemented

    def define_node_type(self, token):
        '''
        in tree_sitter library, operator and keyword nodes are no pre-define node type, like:
        [type: 'def'/'&&', value: 'def'/'&&']
        :param token: node value
        :return: if token is operator, its type will be EN name
                  if token is keyword, its type will be {}Kw
        '''
        is_keyword = True
        for chr in token:
            if str.isalpha(chr):
                continue
            else:
                is_keyword = False
                break
        if is_keyword:
            return '{}_keyword'.format(str.lower(token))
        else:
            if self.operators and (token in self.operators):
                return self.operators[token]
            else:
                return token

    def build_tree(self, root, code_lines, append_index=False):
        '''
        build ast with tree_sitter, operator and keyword has no pre-defined type
        :param root: ast tree root node
        :param code_lines: [...], ...
        :return:
            [
                {'type': "node_type", 'children': "node_ids(List)", ‘children’: “node_ids(List)” }, # non-leaf node
                {'type': "node_type", 'children': "node_ids(List)", ‘value’: “node_value(str)” }, # leaf node
                ...
            ]
        '''
        ast_tree = {}

        def dfs(cur_node, parent_node_idx):
            children = [child for child in cur_node.children if child.start_point != child.end_point]
            if len(children) == 0:
                # current node has no child node, it's leaf node, build a leaf node
                new_node_idx = len(ast_tree)
                if cur_node.is_named:
                    # leaf node's value is None. we have to extract its value from source code
                    value = self.subcode(cur_node.start_point, cur_node.end_point, code_lines).decode()
                    if not value:  # value='', delete current node
                        return
                    ast_tree[new_node_idx] = {
                        'type': cur_node.type, 
                        'parent': parent_node_idx,
                        'value': value,
                    }
                    if append_index:
                        ast_tree[new_node_idx]["index"] = [cur_node.start_point, cur_node.end_point]
                    ast_tree[parent_node_idx]['children'].append(new_node_idx)
                else:
                    # leaf node is operator or keyword
                    ast_tree[new_node_idx] = {
                        'type': self.define_node_type(cur_node.type),
                        'parent': parent_node_idx,
                        'value': cur_node.type,
                    }
                    if append_index:
                        ast_tree[new_node_idx]["index"] = [cur_node.start_point, cur_node.end_point]
                    ast_tree[parent_node_idx]['children'].append(new_node_idx)
            else:
                # current node has many child nodes
                cur_node_idx = len(ast_tree)
                ast_tree[cur_node_idx] = {'type': cur_node.type, 'parent': parent_node_idx, 'children': []}
                # update parent node's children
                if parent_node_idx is not None:
                    ast_tree[parent_node_idx]['children'].append(cur_node_idx)
                # update current node's children
                for child_node in children:
                    dfs(child_node, parent_node_idx=cur_node_idx)

        dfs(root, parent_node_idx=None)
        return ast_tree

    def build_recursive_tree(self, root, code_lines):
        '''
        build ast with tree_sitter, operator and keyword has no pre-defined type
        '''
        ast_tree_count = []

        def dfs(current_node, parent_node_idx):
            children = [child for child in current_node.children if child.start_point != child.end_point]
            ast_tree_count.append("COUNT")
            current_node_idx = len(ast_tree_count)
            if len(children) == 0:
                if current_node.is_named:
                    # leaf node's value is None. we have to extract its value from source code
                    value = self.subcode(current_node.start_point, current_node.end_point, code_lines).decode()
                    if not value:  # value='', delete current node
                        return
                    leaf_node = {
                        'parent': parent_node_idx,
                        'index': current_node_idx,
                        'type': current_node.type,
                        'value': value,
                    }
                    return leaf_node
                else:
                    # leaf node is operator or keyword
                    leaf_node = {
                        'parent': parent_node_idx,
                        'index': current_node_idx,
                        'type': self.define_node_type(current_node.type),
                        'value': current_node.type,
                    }
                    return leaf_node
            else:
                # current node has many child nodes
                sub_tree = [dfs(child_node, parent_node_idx=current_node_idx) for child_node in children]

                non_leaf_node = {
                    'parent': parent_node_idx, 
                    'index': current_node_idx,
                    'type': current_node.type, 
                    'children': sub_tree
                }
                return non_leaf_node
        
        return dfs(root, parent_node_idx=None)

    def extract_method_declaration(self, code):
        """signature 包含函数名和参数列表
        signature = {
            "method_index_in_code_snippet": 0,
            "string": str,
            "method_name": str,
            "parameter_list": [],
            "parameter number": 0,
        }
        """
        tree_sitter_tree = self.parser.parse(code.encode())

        root_node =  tree_sitter_tree.root_node
        code_lines = [line.encode() for line in code.split('\n')]

        signature_list = []
        def dfs(cur_node, parent_node=None):
            children = [child for child in cur_node.children if child.start_point != child.end_point]
            # 只选取第一层方法，不考虑闭包
            if cur_node.type == "method_declaration":
                for child_node in children:
                    # 获得形参的Node
                    if child_node.type == "formal_parameters":
                        params_node = child_node
                        params_value = self.subcode(params_node.start_point, params_node.end_point, code_lines).decode()
                        text = params_node.text.decode()
                    # 获得body block的Node, Node的起点作为method declaration的终点。
                    if child_node.type == "block":
                        body_block = child_node
                    # 函数名的类型的identifier，是declaration的子节点
                    if child_node.type == "identifier":
                        method_node = child_node
                        method_name = self.subcode(method_node.start_point, method_node.end_point, code_lines).decode()

                param_list = [param.text.decode() for param in params_node.children if (param.start_point != param.end_point and param.is_named)]

                start_point = cur_node.start_point
                end_point = body_block.start_point
                value = self.subcode(start_point, end_point, code_lines).decode()

                method_index = len(signature_list)
                signature = {
                    "method_index_in_code_snippet": method_index,
                    "string": value,
                    "method_name": method_name,
                    "parameter_list": param_list,
                    "parameter number": len(param_list),
                }
                signature_list.append(signature)

            for child_node in children:
                dfs(child_node, parent_node=cur_node)

        dfs(root_node)
        signature_data = {
            "method_num": len(signature_list),
            "list": signature_list
        }
        return signature_data

    def extract_first_level_method_declaration(self, code):
        tree_sitter_tree = self.parser.parse(code.encode())

        root_node =  tree_sitter_tree.root_node
        code_lines = [line.encode() for line in code.split('\n')]

        signature_list = []

        target_node = []
        def get_first_class_body(cur_node):
            children = [child for child in cur_node.children if child.start_point != child.end_point]
            if cur_node.type == "class_body":
                target_node.append(cur_node)
                return
            else:
                for child_node in children:
                    get_first_class_body(child_node)


        get_first_class_body(root_node)
        class_node = target_node.pop()
        assert class_node.type == "class_body"
        children = [child for child in class_node.children if child.start_point != child.end_point]
        for class_child in children:
            # 只选取第一层方法，不考虑闭包
            if class_child.type == "method_declaration":
                method_node = class_child
                method_children = [child for child in method_node.children if child.start_point != child.end_point]
                for child_node in method_children:
                    # 获得形参的Node
                    if child_node.type == "formal_parameters":
                        params_node = child_node
                    # 获得body block的Node, Node的起点作为method declaration的终点。
                    if child_node.type == "block":
                        body_block = child_node
                    # 函数名的类型的identifier，是declaration的子节点
                    if child_node.type == "identifier":
                        method_node = child_node
                        method_name = self.subcode(method_node.start_point, method_node.end_point, code_lines).decode()

                param_list = [param.text.decode() for param in params_node.children if (param.start_point != param.end_point and param.is_named)]

                start_point = class_child.start_point
                end_point = body_block.start_point
                value = self.subcode(start_point, end_point, code_lines).decode()

                method_index = len(signature_list)
                signature = {
                    "method_index_in_code_snippet": method_index,
                    "parameter number": len(param_list),
                    "method_name": method_name,
                    "parameter_list": param_list,
                    "string": value,
                }
                signature_list.append(signature)

        signature_data = {
            "method_num": len(signature_list),
            "list": signature_list
        }
        return signature_data

    def parse_recursive_ast(self, code):
        # must add this head for php code

        ast_tree = self.parser.parse(code.encode())

        code_lines = [line.encode() for line in code.split('\n')]

        # 1) build ast tree in Dict type
        try:
            code_tree = self.build_recursive_tree(ast_tree.root_node, code_lines)
            # if not (MIN_AST_SIZE < len(code_tree) < MAX_AST_SIZE):
            #     raise AssertionError(
            #         f"Code\'s AST(node num: {len(code_tree)}) ({MIN_AST_SIZE}, {MAX_AST_SIZE}) is too small/large!")

            # assert len(code_tree) > 1, AssertionError('AST parsed error.')
            # # check whether an ast contains nodes with null children
            # for node in code_tree.values():
            #     if 'children' in node:
            #         assert len(node['children']) > 0, AssertionError('AST has a node without child and value')
            #     if 'value' in node:
            #         assert len(node['value']) > 0, AssertionError('AST has a node without child and value')
            return code_tree
        except RecursionError as err:
            # RecursionError: maximum recursion depth exceeded while getting the str of an object
            print(err)
            # raw_ast is too large, skip this ast
            return None
        except AssertionError as err:
            print(err)
            return None

    def parse_raw_ast(self, code, MIN_AST_SIZE=10, MAX_AST_SIZE=999, append_index=False):
        # must add this head for php code
        if self.LANGUAGE == 'php':
            code = '<?php ' + code

        ast_tree = self.parser.parse(code.encode())

        code_lines = [line.encode() for line in code.split('\n')]

        # 1) build ast tree in Dict type
        try:
            code_tree = self.build_tree(ast_tree.root_node, code_lines, append_index)
            if not (MIN_AST_SIZE < len(code_tree) < MAX_AST_SIZE):
                raise AssertionError(
                    f"Code\'s AST(node num: {len(code_tree)}) ({MIN_AST_SIZE}, {MAX_AST_SIZE}) is too small/large!")
            # if str.lower(code_tree[0]['type']) == 'error':
            #     raise RuntimeError
            # if self.LANGUAGE in {'java'}:
            #     # rename Root's children whose type is ERROR into ‘local_variable_declaration’
            #     roots_children = code_tree[0]['children']
            #     for child in roots_children:
            #         if child == ['ERROR']:
            #             ast_tree[child]['type'] = 'local_variable_declaration'
            #             break

            if self.LANGUAGE == 'php':
                """
                first 3 nodes would be follow:
                0: {'type': 'program', 'parent': None, 'children': [1, 2, 6]}
                1: {'type': 'php_tag', 'parent': 0, 'value': '<?php'}
                2: {'type': 'ERROR', 'parent': 0, 'children': [3, 5]}
                solution: remove 2nd, connect 3rd to 1st, rename 3rd node's type to ‘local_variable_declaration’
                """
                php_tag_node = code_tree.pop(1)
                del code_tree[0]['children'][code_tree[0]['children'].index(1)]
                code_tree[2]['type'] = 'local_variable_declaration'
                # node index: from 2-..., should move forward and update children info
                code_tree[0]['children'] = [index - 1 for index in code_tree[0]['children']]
                for idx in sorted(code_tree.keys())[1:]:
                    new_idx = idx - 1
                    new_node = code_tree.pop(idx)
                    if new_node['parent'] > 1:
                        new_node['parent'] = new_node['parent'] - 1
                    if 'children' in new_node:
                        new_node['children'] = [index - 1 for index in new_node['children'] if index > 0]
                    code_tree[new_idx] = new_node

            if self.LANGUAGE == 'cpp':
                def del_node(ast, index):
                    def _del(idx):
                        node = ast.pop(idx)
                        parent_children = ast[node['parent']]['children']
                        del parent_children[parent_children.index(idx)]
                        return node['parent']

                    parent_idx = _del(index)
                    while len(ast[parent_idx]['children']) == 0:
                        parent_idx = _del(parent_idx)
                    return ast

                pop_indices = [node_idx for node_idx, node_info in code_tree.items() \
                               if node_info['type'] == "LineBreakOp"]
                for idx in pop_indices:
                    code_tree = del_node(code_tree, idx)
                code_tree = \
                    util_ast.reset_indices_for_value_format(code_tree, root_idx=util_ast.get_root_idx(code_tree))

            assert len(code_tree) > 1, AssertionError('AST parsed error.')
            # check whether an ast contains nodes with null children
            for node in code_tree.values():
                if 'children' in node:
                    assert len(node['children']) > 0, AssertionError('AST has a node without child and value')
                if 'value' in node:
                    assert len(node['value']) > 0, AssertionError('AST has a node without child and value')
            return code_tree
        except RecursionError as err:
            # RecursionError: maximum recursion depth exceeded while getting the str of an object
            print(err)
            # raw_ast is too large, skip this ast
            return None
        except AssertionError as err:
            print(err)
            return None

    def _traverse_recursive_new_tree(self, root_node, code_lines):
        '''
        build ast with tree_sitter, operator and keyword has no pre-defined type
        '''
        ast_tree = self._traverse_new_tree(root_node, code_lines)

        node_num = len(ast_tree)

        root_node = ast_tree[0]

        def recursive_node_to_tree(node):
            if "children" in node.keys():
                assert len(node["children"]) > 0
                children = [recursive_node_to_tree(ast_tree[child_idx]) for child_idx in node["children"]]
                node["children"] = children
                return node
            else:
                return node


        recursive_tree = recursive_node_to_tree(root_node)
        return recursive_tree, node_num

    def _traverse_new_tree(self, root_node, code_lines):
        """
        traverse ast with tree_sitter.walk(), operator and keyword has no pre-defined type.
        :param root: ast tree root node
        :param code_lines: [...], ...
        :return:
            [
                {'type': "node_type", 
                'children': "node_ids(List)", 
                }, # non-leaf node

                {'type': "node_type", 
                'value': "node_value(str)" 
                }, # leaf node
                ...
            ]
        # 文档：What is a field name
        # 简单来说，就是方便分析特定节点的一个标识，有了field name会方便很多
        https://tree-sitter.github.io/tree-sitter/using-parsers#node-field-names
        """

        # 测试一下：定位到class_name
        # cursor.goto_first_child() # class declaration
        # cursor.goto_first_child() # class
        # cursor.goto_next_sibling() # class name
        # name_1 = cursor.current_field_name() # name: name

        # x = cursor.goto_next_sibling() # body
        # name_2 = cursor.current_field_name() # name: body

        # y = cursor.goto_next_sibling()
        
        ast_tree = {}
        root_cursor = root_node.walk()

        # https://github.com/tree-sitter/py-tree-sitter/issues/33
        def traverse_cursor_tree(root_cursor):
            cursor = root_cursor
            parent_node_idx = None

            reached_root = False
            while reached_root == False:
                child_num = cursor.node.child_count
                children = [child for child in cursor.node.children]
                # 用(1) cursor的方式和(2) 统计数量的方式                   
                # 交叉验证子节点数量
                assert len(children) == child_num, AssertionError("children nums do not match")

                current_node_idx = len(ast_tree)

                # 排除掉标点符号
                if cursor.node.start_point != cursor.node.end_point:
                    if child_num == 0:
                        # 该节点是叶子节点
                        if cursor.node.is_named:
                            value = self.subcode(cursor.node.start_point, cursor.node.end_point, code_lines).decode()
                            if not value:  # value='', delete current node
                                continue 
                            field_name = cursor.current_field_name()
                            leaf_node = {
                                'parent': parent_node_idx,
                                'field_name': field_name,
                                'index': current_node_idx,
                                'type': cursor.node.type,
                                'value': value,
                            }
                            # 添加节点
                            ast_tree[current_node_idx] = leaf_node
                            # 在父节点中添加子节点
                            ast_tree[parent_node_idx]['children'].append(current_node_idx)
                        else:
                            # leaf node is operator or keyword
                            leaf_node = {
                                'parent': parent_node_idx,
                                'field_name': cursor.current_field_name(),
                                'index': current_node_idx,
                                'type': self.define_node_type(cursor.node.type),
                                'value': cursor.node.type,
                            }
                            # 添加节点
                            ast_tree[current_node_idx] = leaf_node
                            # 在父节点中添加子节点
                            ast_tree[parent_node_idx]['children'].append(current_node_idx)

                    elif child_num > 0:
                        # 该节点是非叶子节点，有多个子节点
                        # current node has many child nodes
                        non_leaf_node = {
                            'parent': parent_node_idx, 
                            'field_name': cursor.current_field_name(),
                            'index': current_node_idx,
                            'type': cursor.node.type, 
                            'children': []
                        }
                        # 添加节点
                        ast_tree[current_node_idx] = non_leaf_node
                        # update parent node's children
                        if parent_node_idx is not None:
                            ast_tree[parent_node_idx]['children'].append(current_node_idx)

                if cursor.goto_first_child():
                    parent_node_idx = current_node_idx
                    continue

                if cursor.goto_next_sibling():
                    continue

                
                retracing = True
                while retracing:
                    
                    goto_parent = cursor.goto_parent()
                    # 回溯到父节点的时候，记录父节点的index
                    if goto_parent:
                        parent_node_idx = ast_tree[parent_node_idx]["parent"]
                    # 如果无法回溯到父节点，说明前序遍历完了
                    elif not goto_parent:
                        retracing = False
                        reached_root = True

                    if cursor.goto_next_sibling():
                        retracing = False

        traverse_cursor_tree(root_cursor)
        return ast_tree

    def parse_new_tree(self, code_string, MIN_AST_SIZE=0, MAX_AST_SIZE=99):

        tree_sitter_tree = self.parser.parse(code_string.encode())
        code_lines = [line.encode() for line in code_string.split('\n')]

        try:
            code_tree = self._traverse_new_tree(tree_sitter_tree.root_node, code_lines)

            if not (MIN_AST_SIZE < len(code_tree) < MAX_AST_SIZE):
                raise AssertionError(
                    f"Code\'s AST(node num: {len(code_tree)}) ({MIN_AST_SIZE}, {MAX_AST_SIZE}) is too small/large!")

            assert len(code_tree) > 1, AssertionError('AST parsed error.')
            # check whether an ast contains nodes with null children
            for node in code_tree.values():
                if 'children' in node:
                    assert len(node['children']) > 0, AssertionError('AST has a node without child or value')
                if 'value' in node:
                    assert len(node['value']) > 0, AssertionError('AST has a node without child or value')
            return code_tree
        except RecursionError as err:
            # RecursionError: maximum recursion depth exceeded while getting the str of an object
            print(err)
            # raw_ast is too large, skip this ast
            return None
        except AssertionError as err:
            print(err)
            return None

    def parse_recursive_new_tree(self, code_string, MIN_AST_SIZE=0, MAX_AST_SIZE=99):
        tree_sitter_tree = self.parser.parse(code_string.encode())
        code_lines = [line.encode() for line in code_string.split('\n')]

        try:
            code_tree, node_num = self._traverse_recursive_new_tree(tree_sitter_tree.root_node, code_lines)

            if not (MIN_AST_SIZE < len(code_tree) < MAX_AST_SIZE):
                raise AssertionError(
                    f"Code\'s AST(node num: {len(code_tree)}) ({MIN_AST_SIZE}, {MAX_AST_SIZE}) is too small/large!")
            return code_tree, node_num
        except RecursionError as err:
            # RecursionError: maximum recursion depth exceeded while getting the str of an object
            print(err)
            # raw_ast is too large, skip this ast
            return None
        except AssertionError as err:
            print(err)
            return None

    def build_new_tree(self, code_string, MIN_AST_SIZE=10, MAX_AST_SIZE=99):
        
        tree_sitter_tree = self.tree_sitter_parse()
        code_lines = [line.encode() for line in code_string.split('\n')]

        try:
            if not (MIN_AST_SIZE < len(code_tree) < MAX_AST_SIZE):
                raise AssertionError(
                    f"Code\'s AST(node num: {len(code_tree)}) ({MIN_AST_SIZE}, {MAX_AST_SIZE}) is too small/large!")

            for node in code_tree.values():
                if 'children' in node:
                    assert len(node['children']) > 0, AssertionError('AST has a node without child and value')
                if 'value' in node:
                    assert len(node['value']) > 0, AssertionError('AST has a node without child and value')
        except RecursionError as err:
            # RecursionError: maximum recursion depth exceeded while getting the str of an object
            print(err)
            # raw_ast is too large, skip this ast
            return None
        except AssertionError as err:
            print(err)
            return None

    def tree_sitter_parse(self, code_string):
        tree_sitter_node = self.parser.parse(code_string.encode())
        return tree_sitter_node


def extract_method_declaration(raw_code: str):
    parser = TreeSitterASTParser(SO_FILE=os.path.join(__TREE_SITTER_LIBS_DIR__, f"java.so"), LANGUAGE="java")
    signatures = parser.extract_first_level_method_declaration(raw_code)

    return signatures

def build_recursiveAST(code_string: str, to_file="cache_recursive_tree.json"):
    parser = TreeSitterASTParser(SO_FILE=os.path.join(__TREE_SITTER_LIBS_DIR__, f"java.so"), LANGUAGE="java")
    recursive_tree = parser.parse_recursive_ast(code_string)
    if to_file:
        with open(to_file, "w") as f:
            json.dump(recursive_tree, f, indent=4)
        print("Tree json output to:")
        print(to_file)
    else:
        json_string = json.dumps(recursive_tree, indent=4)
        return json_string

def test_TreeSitterASTParser():
    # code = "public static string StripExtension(string filename){int idx = filename.IndexOf('.');if (idx != -1){filename = filename.Substring(0, idx);}return filename;}"
    code = "import java . util . * ; class Main { public static void main ( String [ ] args ) { Scanner sc = new Scanner ( System . in ) ; int x = sc . nextInt ( ) ; int y = sc . nextInt ( ) ; System . out . println ( Math . max ( x , y ) ) ; } }"
    code2 = """public static AuthenticationScheme basic(String userName, String password) {
        final BasicAuthScheme scheme = new BasicAuthScheme();
        scheme.setUserName(userName);
        scheme.setPassword(password);
        return scheme;
    }"""
    code3 = """public static AuthenticationScheme basic(String userName) {
        return userName;
    }"""
    
    parser = TreeSitterASTParser(SO_FILE=os.path.join(__TREE_SITTER_LIBS_DIR__, f"java.so"), LANGUAGE="java")
    raw_ast = parser.parse_raw_ast(code2)
    # print(raw_ast)
    with open("parser/results.json", "w") as f:
        json.dump(raw_ast, f)

    # new_ast = util_ast.convert(raw_ast)
    # with open("parser/new_results.json", "w") as f:
    #     json.dump(new_ast, f)

    MAX_SUB_TOKEN_LEN = 5
    ast = util_ast.value2children(raw_ast)
    with open("parser/value_to_children.json", "w") as f:
        json.dump(ast, f)
    padded_ast = util_ast.pad_leaf_node(ast, MAX_SUB_TOKEN_LEN)
    with open("parser/padded_ast.json", "w") as f:
        json.dump(ast, f)
    root_idx = util_ast.get_root_idx(padded_ast)

    print(padded_ast[1])
    sbt_tree = util_ast.build_sbtao_tree(padded_ast, idx=root_idx)
    with open("parser/sbt_tree_results.json", "w") as f:
        json.dump(sbt_tree, f)
    print(sbt_tree)

def test_recursiveAST():

    test_code = """class RootNode {
        public static AuthenticationScheme basic(String userName, String password) {
            final BasicAuthScheme scheme = new BasicAuthScheme();
            scheme.setUserName(userName);
            scheme.setPassword(password);
            return scheme;
        }
    }"""
    test_code_2 = "import java . util . * ; class Main { public static void main ( String [ ] args ) { Scanner sc = new Scanner ( System . in ) ; int x = sc . nextInt ( ) ; int y = sc . nextInt ( ) ; System . out . println ( Math . max ( x , y ) ) ; } }"
    parser = TreeSitterASTParser(SO_FILE=os.path.join(__TREE_SITTER_LIBS_DIR__, f"java.so"), LANGUAGE="java")
    recursive_tree = parser.parse_recursive_ast(test_code)
    with open("parser/recursive_tree.json", "w") as f:
        json.dump(recursive_tree, f)
    print(recursive_tree)

def test_extract_method_declaration():
    # 闭包的情况
    test_code1 = """private static <T> Iterator<T> consumingForArray(final T... elements) {
    return new UnmodifiableIterator<T>() {
      int index = 0;

      @Override
      public boolean hasNext() {
        return index < elements.length;
      }

      @Override
      public T next() {
        if (!hasNext()) {
          throw new NoSuchElementException();
        }
        T result = elements[index];
        elements[index] = null;
        index++;
        return result;
      }
    };
  }
    """
    # 增加一个类，让它变成一个完整的Java类结构，解析器才能正确解析
    code_string = "class main { %s }" % test_code1
    signature_list = extract_method_declaration(code_string)
    print(signature_list)


def test_tree_sitter_parse():
    # Tree 和 TreeCursor的定义：
    # https://github.com/andreypopp/py-tree-sitter/blob/andreypopp/patch/tree_sitter/__init__.pyi
    # TreeCursor的用法
    # https://github.com/tree-sitter/py-tree-sitter/blob/b5dfe29b4ead51678bf72c5da47feaa56d4e2be1/tests/test_tree_sitter.py#L370
    test_code = """class RootNode {
        public static AuthenticationScheme basic(String userName, String password) {
            final BasicAuthScheme scheme = new BasicAuthScheme();
            scheme.setUserName(userName);
            scheme.setPassword(password);
            return scheme;
        }
    }"""
    parser = TreeSitterASTParser(SO_FILE=os.path.join(__TREE_SITTER_LIBS_DIR__, f"java.so"), LANGUAGE="java")
    tree_sitter_node = parser.tree_sitter_parse(test_code)

    assert isinstance(tree_sitter_node, Tree)

    tree_sitter_node_cursor = tree_sitter_node.walk()

    assert isinstance(tree_sitter_node_cursor, TreeCursor)

def test_private_traverse_new_tree(visualize_ast_in_browser=True):
    """
    _traverse_new_tree() is a private function
    """
    test_code = []
    test_code.append("""class RootNode {
        public static AuthenticationScheme basic(String userName, String password) {
            final BasicAuthScheme scheme = new BasicAuthScheme();
            scheme.setUserName(userName);
            scheme.setPassword(password);
            return scheme;
        }
    }""")
    test_code.append("os.print(233);")

    parser = TreeSitterASTParser(SO_FILE=os.path.join(__TREE_SITTER_LIBS_DIR__, f"java.so"), LANGUAGE="java")


    code_string = test_code[0]

    code_lines = [line.encode() for line in code_string.split('\n')]
    tree_sitter_tree = parser.tree_sitter_parse(code_string)
    assert hasattr(tree_sitter_tree, "root_node")
    
    ast_tree = parser._traverse_new_tree(tree_sitter_tree.root_node, code_lines)

    if visualize_ast_in_browser:
        ast_json = json.dumps(ast_tree)
        visualize_ast.visualize_code_json(ast_json)

def test_private_traverse_recursive_new_tree(visualize_ast_in_browser=True):
    """
    _traverse_recursive_new_tree() is a private function
    """
    test_code = []
    test_code.append("""class RootNode {
        public static AuthenticationScheme basic(String userName, String password) {
            final BasicAuthScheme scheme = new BasicAuthScheme();
            scheme.setUserName(userName);
            scheme.setPassword(password);
            return scheme;
        }
    }""")
    test_code.append("os.print(233);")

    code_string = test_code[0]

    parser = TreeSitterASTParser(SO_FILE=os.path.join(__TREE_SITTER_LIBS_DIR__, f"java.so"), LANGUAGE="java")    

    tree_sitter_tree = parser.tree_sitter_parse(code_string)
    
    code_lines = [line.encode() for line in code_string.split('\n')]
    
    assert hasattr(tree_sitter_tree, "root_node")

    recursive_tree, node_num = parser._traverse_recursive_new_tree(tree_sitter_tree, code_lines)

    assert node_num == 64

    if visualize_ast_in_browser:
        recursive_tree_json = json.dumps(recursive_tree)
        visualize_ast.visualize_code_json(recursive_tree_json)

def test_parse_new_tree(visualize_ast_in_browser=True):
    test_code = []
    test_code.append("""class RootNode {
        public static AuthenticationScheme basic(String userName, String password) {
            final BasicAuthScheme scheme = new BasicAuthScheme();
            scheme.setUserName(userName);
            scheme.setPassword(password);
            return scheme;
        }
    }""")
    test_code.append("os.print(233);")
    test_code.append("a.b.outputStream.printTable(message);")

    code_string = test_code[2]

    parser = TreeSitterASTParser(SO_FILE=os.path.join(__TREE_SITTER_LIBS_DIR__, f"java.so"), LANGUAGE="java")    

    ast_tree = parser.parse_new_tree(code_string)

    if visualize_ast_in_browser:
        ast_json = json.dumps(ast_tree)
        visualize_ast.visualize_code_json(ast_json)

def test_parse_recursive_new_tree(visualize_ast_in_browser=True):
    test_code = []
    test_code.append("""class RootNode {
        public static AuthenticationScheme basic(String userName, String password) {
            final BasicAuthScheme scheme = new BasicAuthScheme();
            scheme.setUserName(userName);
            scheme.setPassword(password);
            return scheme;
        }
    }""")
    test_code.append("os.print(233);")
    code_string = test_code[1]

    parser = TreeSitterASTParser(SO_FILE=os.path.join(__TREE_SITTER_LIBS_DIR__, f"java.so"), LANGUAGE="java")    

    recursive_tree, node_num = parser.parse_recursive_new_tree(code_string)

    if visualize_ast_in_browser:
        recursive_tree_json = json.dumps(recursive_tree)
        visualize_ast.visualize_code_json(recursive_tree_json)

if __name__ == "__main__":
    """
    python -m code_parser.build
    """
    test_tree_sitter_parse()
    test_private_traverse_new_tree(visualize_ast_in_browser=False)
    test_private_traverse_recursive_new_tree(visualize_ast_in_browser=False)

    test_parse_new_tree(visualize_ast_in_browser=True)
    test_parse_recursive_new_tree(visualize_ast_in_browser=False)

