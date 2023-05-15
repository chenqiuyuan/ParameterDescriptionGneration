from graphviz import Digraph
from .extract_dfg import extract_parameter_code_lines


def draw_graph():
    code = """class main{
        public static void parameterFlow(int x, int y){
            int result = 0;
            if (y < x){
                result = y;
            }
            else{
                result = x;
            }

            String irrelevant = "log message";
            System.out.println(irrelevant);

            return result;
        }
    }"""

    data_flow_dict, param_flow_dict, node_dict = extract_parameter_code_lines(code, draw_figure=True)

    dot = Digraph(comment='这是一个有向图')
    nodes = data_flow_dict.keys()
    keys = list(data_flow_dict.keys())

    for key, value in data_flow_dict.items():
        node_key = str(key)
        # 各个variable按照顺序从小到大
        ordered_key = str(keys.index(key) + 1)
        code = value[0]
        """Template of the node
        <
        <table BORDER="0" CELLBORDER="0" CELLSPACING="0">
            <tr>
				<td> </td>
                <td bgcolor='#66FFFF'><font point-size='24' color='black'>x</font></td>
                <td><SUP><font point-size='10' color='red'>12</font></SUP></td>
            </tr>
        </table> 
		>
        """
        # <x<SUP><font point-size='10' color='red'>9</font></SUP>>
        node_str = f"""<
        <table BORDER="0" CELLBORDER="0" CELLSPACING="0">
            <tr>
				<td> </td>
                <td bgcolor='#00FF00'><font point-size='24' color='black'><b>{code}</b></font></td>
                <td><SUP><font point-size='20' color='red'><b>{ordered_key}</b></font></SUP></td>
            </tr>
        </table> 
		>"""
        dot.node(node_key, node_str)

        end = node_key
        start_list = value[4]
        for start in start_list:
            dot.edge(str(start), str(end))
    print(233)
    print(dot.source)
    with open("code_parser/DFG/data_flow.dot", "w") as f:
        f.write(dot.source)
    return dot

def draw_AST():
    dot = Digraph(comment='这是一个有向图')
    dot.node("level 0", "method declaration")
    dot.edge("level 0", "level 1-1")
    dot.edge("level 0", "level 1-2")
    dot.edge("level 0", "level 1-3")

    dot.node("level 1-1", "method name")
    dot.node("level 2-1", "parameterFlow")
    dot.edge("level 1-1", "level 2-1")

    dot.node("level 1-2", "parameters")
    dot.node("level 2-2", "int x")
    dot.node("level 2-3", "int y")
    dot.edge("level 1-2", "level 2-2")
    dot.edge("level 1-2", "level 2-3")

    dot.node("level 1-3", "method body")

    
    dot.node("2", "body")
    return dot


def example():
    dot = Digraph(comment='这是一个有向图')
    dot.node('A', '作者')
    dot.node('B', '医生')
    dot.node('C', '律师<SUP></SUP>')

    dot.edges(['AB', 'AC'])
    dot.edge('B', 'C')
    print(dot.source)

if __name__ == "__main__":
    """
    python -m code_parser.DFG.draw_DFG
    """
    example()
    draw_graph()
    print(233)