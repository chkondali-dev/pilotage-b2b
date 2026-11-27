"""Which TabCtx field names are assigned (Store) inside each tabs[i] block,
and at which scope level (render-level vs nested function/comprehension)."""
import ast
import io

APP = r"C:/Users/hachk/pilotage_b2b/app.py"
CTX = r"C:/Users/hachk/pilotage_b2b/ui/tabs/context.py"

ctx_tree = ast.parse(io.open(CTX, encoding="utf-8").read())
FIELDS = []
for n in ctx_tree.body:
    if isinstance(n, ast.ClassDef) and n.name == "TabCtx":
        for item in n.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                FIELDS.append(item.target.id)
FSET = set(FIELDS)

tree = ast.parse(io.open(APP, encoding="utf-8").read())


def assigned_here(stmts, names):
    """Names bound directly at THIS scope level (skip nested scopes)."""
    found = set()

    class V(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            found.add(node.name)
            for d in node.decorator_list:
                self.visit(d)
            a = node.args
            for d in list(a.defaults) + [x for x in a.kw_defaults if x]:
                self.visit(d)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ClassDef(self, node):
            found.add(node.name)
            for d in node.decorator_list:
                self.visit(d)
            for b in node.bases:
                self.visit(b)
            for k in node.keywords:
                self.visit(k.value)

        def visit_Lambda(self, node):
            for d in list(node.args.defaults) + [x for x in node.args.kw_defaults if x]:
                self.visit(d)

        def visit_ListComp(self, node):
            self.visit(node.generators[0].iter)

        visit_SetComp = visit_ListComp
        visit_DictComp = visit_ListComp
        visit_GeneratorExp = visit_ListComp

        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Store):
                found.add(node.id)

        def visit_Import(self, node):
            for a in node.names:
                found.add(a.asname or a.name.split(".")[0])

        def visit_ImportFrom(self, node):
            for a in node.names:
                found.add(a.asname or a.name)

        def visit_ExceptHandler(self, node):
            if node.name:
                found.add(node.name)
            for s in node.body:
                self.visit(s)

        def visit_Global(self, node):
            found.update(node.names)

        def visit_Nonlocal(self, node):
            found.update(node.names)

    for s in stmts:
        V().visit(s)
    return found


def assigned_nested(stmts):
    """Names assigned in ANY nested scope (function/class/lambda/comprehension)."""
    found = set()

    class V(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            inner = assigned_here(node.body, None)
            found.update(inner)
            # recurse into nested scopes inside the function body
            for s in node.body:
                self.generic_visit(s)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_ClassDef(self, node):
            inner = assigned_here(node.body, None)
            found.update(inner)
            for s in node.body:
                self.generic_visit(s)

        def visit_Lambda(self, node):
            pass

        def visit_ListComp(self, node):
            inner = set()
            for g in node.generators:
                inner.update(t.id for t in ast.walk(g.target) if isinstance(t, ast.Name))
            found.update(inner)

        visit_SetComp = visit_ListComp
        visit_DictComp = visit_ListComp
        visit_GeneratorExp = visit_ListComp

    for s in stmts:
        V().visit(s)
    return found


for n in tree.body:
    if not isinstance(n, ast.With):
        continue
    e = n.items[0].context_expr
    if not (isinstance(e, ast.Subscript) and isinstance(e.value, ast.Name)
            and e.value.id == "tabs"):
        continue
    idx = e.slice.value
    body = n.body
    here = assigned_here(body, None)
    nested = assigned_nested(body)
    render_level = (here & FSET) - nested
    nested_only = (nested & FSET) - here
    both = (here & FSET) & nested
    print(f"TAB {idx}")
    print(f"  render-level assign of TabCtx fields : {sorted(render_level)}")
    print(f"  nested-only assign                    : {sorted(nested_only)}")
    print(f"  both                                  : {sorted(both)}")
