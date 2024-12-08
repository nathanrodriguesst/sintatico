class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {self.value})"


class Node:
    def __init__(self, type_, value=""):
        self.type = type_
        self.value = value
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def print_tree(self, level=0):
        indent = "  " * level
        tree_representation = f"{indent}{self.type}({self.value})\n"
        for child in self.children:
            tree_representation += child.print_tree(level + 1)
        return tree_representation


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.current = 0
        self.block_counter = 0
        self.defined_functions = set()
        self.variable_scopes = [{}]

    def current_token(self):
        return self.tokens[self.current] if self.current < len(self.tokens) else None

    def eat(self, type_):
        token = self.current_token()
        if token and token.type == type_:
            self.current += 1
            if type_ == "BLOCK_START":
                self.block_counter += 1
            elif type_ == "BLOCK_END":
                self.block_counter -= 1
            return token
        raise RuntimeError(f"Unexpected token: {token}, expected: {type_}.")

    def parse(self):
        program_node = Node("Program")
        self.eat("PROGRAM_START")
        while self.current_token() and self.current_token().type != "PROGRAM_END":
            program_node.add_child(self.parse_statement_or_block())
        self.eat("PROGRAM_END")
        if self.block_counter != 0:
            raise RuntimeError("Syntax error: Mismatched block delimiters.")
        return program_node

    def parse_statement_or_block(self):
        token = self.current_token()
        if token.type == "BLOCK_START":
            return self.parse_block()
        elif token.type == "FUNCTION_DEFINITION":
            return self.parse_function_definition()
        elif token.type == "VARIABLE_DEFINITION":
            return self.parse_variable_definition()
        elif token.type == "IF_CONDITIONAL":
            return self.parse_if_conditional()
        elif token.type == "FOR_LOOP":
            return self.parse_for_loop()
        else:
            return self.parse_generic_statement()

    def parse_block(self):
        self.eat("BLOCK_START")
        self.variable_scopes.append({})
        block_node = Node("Block")
        while self.current_token() and self.current_token().type != "BLOCK_END":
            block_node.add_child(self.parse_statement_or_block())
        self.variable_scopes.pop()
        self.eat("BLOCK_END")
        return block_node

    def parse_function_definition(self):
        self.eat("FUNCTION_DEFINITION")
        func_type = self.eat("TYPE").value
        func_name = self.eat("IDENTIFIER").value
        if func_name in self.defined_functions:
            raise RuntimeError(f"Semantic error: Function '{func_name}' is already defined.")
        self.defined_functions.add(func_name)
        self.eat("LEFT_PAREN")
        params_node = Node("Parameters")
        self.variable_scopes.append({})
        while self.current_token() and self.current_token().type != "RIGHT_PAREN":
            param_type = self.eat("TYPE").value
            param_name = self.eat("IDENTIFIER").value
            if param_name in self.variable_scopes[-1]:
                raise RuntimeError(f"Semantic error: Parameter '{param_name}' is already defined.")
            self.variable_scopes[-1][param_name] = param_type
            params_node.add_child(Node("Parameter", f"{param_type} {param_name}"))
        self.eat("RIGHT_PAREN")
        self.eat("START_STATEMENT")
        func_node = Node("FunctionDefinition", f"{func_name}: {func_type}")
        func_node.add_child(params_node)
        func_node.add_child(self.parse_block())
        self.variable_scopes.pop()
        return func_node

    def parse_variable_definition(self):
        self.eat("VARIABLE_DEFINITION")
        var_type = self.eat("TYPE").value
        var_name = self.eat("IDENTIFIER").value
        if var_name in self.variable_scopes[-1]:
            raise RuntimeError(f"Semantic error: Variable '{var_name}' is already defined in the current scope.")
        self.variable_scopes[-1][var_name] = var_type
        var_node = Node("VariableDefinition", f"{var_type} {var_name}")
        if self.current_token() and self.current_token().type == "ASSIGN":
            self.eat("ASSIGN")
            expr = self.parse_expression()
            var_node.value += f" = {expr.value}"
        self.eat("COMMAND_END")
        return var_node

    def parse_if_conditional(self):
        self.eat("IF_CONDITIONAL")
        self.eat("LEFT_PAREN")
        condition = self.parse_expression()
        self.eat("RIGHT_PAREN")
        self.eat("START_STATEMENT")
        if_node = Node("IfConditional", condition.value)
        if_node.add_child(self.parse_block())
        if self.current_token() and self.current_token().type == "ELSE_CONDITIONAL":
            self.eat("ELSE_CONDITIONAL")
            else_node = Node("ElseConditional")
            else_node.add_child(self.parse_block())
            if_node.add_child(else_node)
        return if_node

    def parse_for_loop(self):
        self.eat("FOR_LOOP")
        self.eat("LEFT_PAREN")
        if self.current_token().type == "VARIABLE_DEFINITION":
            init_node = self.parse_variable_definition()
        else:
            raise RuntimeError(f"Syntax error: Expected variable definition, found {self.current_token()}.")
        condition_expr = Node("Condition")
        while self.current_token() and self.current_token().type != "COMMAND_END":
            token = self.current_token()
            if token.type == "IDENTIFIER" and not self.is_variable_defined(token.value):
                raise RuntimeError(f"Semantic error: Variable '{token.value}' is not defined.")
            condition_expr.value += token.value + " "
            self.current += 1
        condition_expr.value = condition_expr.value.strip()
        self.eat("COMMAND_END")
        increment_expr = Node("Increment")
        while self.current_token() and self.current_token().type != "RIGHT_PAREN":
            token = self.current_token()
            if token.type == "IDENTIFIER" and not self.is_variable_defined(token.value):
                raise RuntimeError(f"Semantic error: Variable '{token.value}' is not defined.")
            increment_expr.value += token.value + " "
            self.current += 1
        increment_expr.value = increment_expr.value.strip()
        self.eat("RIGHT_PAREN")
        self.eat("START_STATEMENT")
        loop_body_node = self.parse_block()
        for_node = Node("ForLoop")
        for_node.add_child(init_node)
        for_node.add_child(condition_expr)
        for_node.add_child(increment_expr)
        for_node.add_child(loop_body_node)
        return for_node

    def parse_expression(self):
        expr_node = Node("Expression")
        expr_value = ""
        while self.current_token() and self.current_token().type not in {"COMMAND_END", "RIGHT_PAREN", "BLOCK_END"}:
            token = self.current_token()
            expr_value += token.value + " "
            self.current += 1
        expr_node.value = expr_value.strip()
        return expr_node

    def parse_generic_statement(self):
        token = self.current_token()
        if not token:
            raise RuntimeError("Syntax error: Unexpected end of input.")
        if token.type == "RETURN":
            self.eat("RETURN")
            return_value = self.eat("IDENTIFIER").value
            if not self.is_variable_defined(return_value):
                raise RuntimeError(f"Semantic error: Variable '{return_value}' is not defined.")
            self.eat("COMMAND_END")
            return Node("Return", return_value)
        else:
            self.current += 1
            return Node("Statement", token.value)

    def is_variable_defined(self, var_name):
        for scope in reversed(self.variable_scopes):
            if var_name in scope:
                return True
        return False


def load_tokens(filename):
    tokens = []
    with open(filename, "r") as file:
        for line in file:
            parts = line.strip().split(", ", 1)
            if len(parts) == 2:
                tokens.append(Token(parts[0], parts[1]))
    return tokens


if __name__ == "__main__":
    try:
        tokens = load_tokens("tokens.krn")
        parser = Parser(tokens)
        syntax_tree = parser.parse()

        # Salvar a árvore sintática em "tree.krn"
        with open("tree.krn", "w") as file:
            file.write(syntax_tree.print_tree())
    except RuntimeError as e:
        print(f"Error: {e}")
