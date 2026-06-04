#!/usr/bin/env python3

"""Minimax game-tree visualization for Game Killer (extra credit).

Invoked via `python game_killer.py draw`. It builds a top-3, depth-4 minimax tree
from a fixed opening, labels every node with its backpropagated minimax value
(leaves with their evaluation), marks the edges alpha-beta would prune, and
renders the tree to an image with the graphviz `dot` binary.

This module is imported only in draw mode, so it never affects engine runtime.
"""

import subprocess
import pyffish as sf

import game_killer as g

# Configuration
OPENING = ["h3e3", "h8e8"]   # known opening; root is Red to move, so plies go R-B-R-B
DRAW_DEPTH = 4               # half-moves to expand
DRAW_TOP_N = 3              # moves shown per node

INF = float("inf")


def fmt(x):
    '''Format an alpha/beta bound for labels: None -> '-', infinities spelled out.'''
    if x is None:
        return "-"
    if x == INF:
        return "inf"
    if x == -INF:
        return "-inf"
    return f"{x:g}"


class Node:
    __slots__ = ("fen", "is_max", "edges", "value", "alpha", "beta", "pruned")

    def __init__(self, fen):
        self.fen = fen
        self.is_max = g.side_to_move(fen) == "w"   # Red maximizes (eval is Red's view)
        self.edges = []        # list of Edge
        self.value = None      # backpropagated minimax value
        self.alpha = None      # alpha/beta as alpha-beta would see them (None if pruned)
        self.beta = None
        self.pruned = False    # lies inside a pruned subtree


class Edge:
    __slots__ = ("move", "child", "pruned", "cutoff", "cut_alpha", "cut_beta")

    def __init__(self, move, child):
        self.move = move
        self.child = child
        self.pruned = False    # skipped by alpha-beta
        self.cutoff = False    # this edge triggered the cut-off
        self.cut_alpha = None  # alpha/beta at the moment of the cut-off
        self.cut_beta = None


# 1. Build the tree (top-N moves per node, fixed depth, deterministic ordering).
def build(fen, depth):
    node = Node(fen)
    legal = sf.legal_moves("xiangqi", fen, [])
    if depth == 0 or not legal:
        return node
    for move in g.order_moves(fen, legal)[:DRAW_TOP_N]:
        child_fen = sf.get_fen("xiangqi", fen, [move])
        node.edges.append(Edge(move, build(child_fen, depth - 1)))
    return node


# 2. Label every node with its minimax value (leaves with the evaluation).
def label_minimax(node):
    if not node.edges:
        node.value = g.evaluate(node.fen, [])
        return node.value
    child_values = [label_minimax(e.child) for e in node.edges]
    node.value = max(child_values) if node.is_max else min(child_values)
    return node.value


# 3. Replay alpha-beta over the already-valued tree to mark the pruned edges.
def mark_alphabeta(node, alpha, beta):
    node.alpha, node.beta = alpha, beta
    if not node.edges:
        return
    cutoff = False
    best = -INF if node.is_max else INF
    for edge in node.edges:
        if cutoff:                         # everything after the cut-off is pruned
            edge.pruned = True
            mark_pruned_subtree(edge.child)
            continue
        mark_alphabeta(edge.child, alpha, beta)
        if node.is_max:
            best = max(best, edge.child.value)
            alpha = max(alpha, best)
        else:
            best = min(best, edge.child.value)
            beta = min(beta, best)
        if beta <= alpha:                  # this edge caused the cut-off
            edge.cutoff = True
            edge.cut_alpha, edge.cut_beta = alpha, beta
            cutoff = True


def mark_pruned_subtree(node):
    node.pruned = True
    for edge in node.edges:
        edge.pruned = True
        mark_pruned_subtree(edge.child)


# 4. Emit graphviz DOT text.
def to_dot(root):
    lines = [
        "digraph minimax {",
        "  rankdir=LR;",
        "  ordering=out;",
        '  node [fontname="Helvetica", style=filled];',
        '  edge [fontname="Helvetica"];',
        '  labelloc="t";',
        f'  label="Minimax tree (root = opening {" ".join(OPENING)}); '
        'box=MAX (Red), ellipse=MIN (Black), white=leaf; '
        'red node/dashed edge = pruned by alpha-beta";',
    ]
    ids = {}
    counter = [0]

    def node_id(node):
        if id(node) not in ids:
            ids[id(node)] = f"n{counter[0]}"
            counter[0] += 1
        return ids[id(node)]

    def emit(node):
        nid = node_id(node)
        is_leaf = not node.edges
        # Shape encodes node type (box = MAX/leaf, ellipse = MIN); colour encodes
        # pruned (red) vs explored (blue MAX / orange MIN / white leaf).
        shape = "ellipse" if (not is_leaf and not node.is_max) else "box"
        if node.pruned:
            fill, border = "#f4cccc", ', color="red", penwidth=2'
        elif is_leaf:
            fill, border = "#ffffff", ''
        elif node.is_max:
            fill, border = "#cfe8ff", ''
        else:
            fill, border = "#ffe0b3", ''
        # Explored nodes show their value and the alpha/beta window they were
        # searched with; pruned nodes show nothing (alpha-beta never valued them).
        label = "" if node.pruned else f"v={node.value:g}\\nα={fmt(node.alpha)} β={fmt(node.beta)}"
        lines.append(f'  {nid} [label="{label}", shape={shape}, fillcolor="{fill}"{border}];')
        for edge in node.edges:
            emit(edge.child)
            if edge.pruned:
                color, style, width = "red", "dashed", "1"
                elabel = edge.move
            elif edge.cutoff:
                color, style, width = "red", "bold", "2"
                # Explain the cut: the search stopped because beta <= alpha here.
                elabel = f"{edge.move}\\ncut: β={fmt(edge.cut_beta)} ≤ α={fmt(edge.cut_alpha)}"
            else:
                color, style, width = "black", "solid", "1"
                elabel = edge.move
            lines.append(
                f'  {nid} -> {node_id(edge.child)} '
                f'[label="{elabel}", color="{color}", style="{style}", '
                f'penwidth={width}, fontcolor="{color}"];'
            )

    emit(root)
    lines.append("}")
    return "\n".join(lines)


# 5. Console log of alpha/beta per node, to hand-annotate the printout.
def alphabeta_log(root):
    lines = []

    def fmt(x):
        if x is None:
            return "  -  "
        if x == INF:
            return "inf"
        if x == -INF:
            return "-inf"
        return f"{x:g}"

    def walk(node, path):
        kind = "MAX" if node.is_max else "MIN"
        tag = "  (pruned)" if node.pruned else ""
        lines.append(
            f"{path or 'root':<26} {kind}  value={node.value:>4g}  "
            f"alpha={fmt(node.alpha):>5}  beta={fmt(node.beta):>5}{tag}"
        )
        for edge in node.edges:
            walk(edge.child, f"{path} {edge.move}".strip())

    walk(root, "")
    return "\n".join(lines)


def draw_tree(filename="minimax_tree"):
    root_fen = sf.get_fen("xiangqi", sf.start_fen("xiangqi"), OPENING)
    root = build(root_fen, DRAW_DEPTH)
    label_minimax(root)
    mark_alphabeta(root, -INF, INF)

    dot_path, png_path = f"{filename}.dot", f"{filename}.png"
    with open(dot_path, "w") as f:
        f.write(to_dot(root))
    try:
        subprocess.run(["dot", "-Tpng", dot_path, "-o", png_path], check=True)
        print(f"Wrote {png_path} and {dot_path}")
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(f"Wrote {dot_path}; could not run graphviz 'dot' ({exc}). Render it manually.")

    print(f"\nOpening (root): {' '.join(OPENING)}")
    print("Alpha/beta per node (for hand annotation):\n")
    print(alphabeta_log(root))
