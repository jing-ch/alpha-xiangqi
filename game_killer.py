#!/usr/bin/env python3

"""Game Killer — a xiangqi (Chinese chess) engine using minimax search.

Plays xiangqi over the UCI protocol. Move selection combines a small opening
book with an iterative-deepening alpha-beta search, scored by a material-based
evaluation function adapted from Shannon's 1950 chess paper. Designed to
respond within a one-second-per-move time limit.

Author: Jinghan Chen
"""

import random
import sys
import time
import pyffish as sf

fen = sf.start_fen("xiangqi")
moves = []

# referenced Shannon's paper on chess, but adapted for xiangqi. 
# Uppercase = Red, lowercase = Black. The general (k) is omitted: it is never
# captured, so its count always cancels and checkmate is handled by the search.
PIECE_VALUES = {
    'r': 9.0,    # chariot (rook)
    'c': 4.5,    # cannon
    'n': 4.0,    # horse
    'a': 2.0,    # advisor
    'b': 2.0,    # elephant
    'p': 1.0,    # soldier (pawn)
}

OPENING_BOOK = {
    # FEN: best move
    "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w": "h2e2",
    "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C2C4/9/RNBAKABNR b": "h9g7",
}

INF = float('inf')
MATE = 100000.0          # bigger than any possible material score
DEFAULT_MOVETIME = 1.0   # seconds, used when a 'go' command omits movetime
TIME_SAFETY = 0.9        # use 90% of the budget; leave a buffer for I/O
SOFT_FRACTION = 0.5      # don't start a new depth past this share of the budget
MAX_DEPTH = 64           # hard cap on the iterative-deepening loop
TOP_N_MOVES = 10         # search only the best N moves per node, to go deeper

# Time management: iterative deepening with a hard deadline.
# Search depth 1, 2, 3, ... keeping the best move from the last depth that
# fully completes. minimax_ab aborts (SearchTimeout) once time.time() passes
# the deadline = start + 0.9*budget; the unfinished depth is discarded and the
# previous depth's move is used. A soft stop skips starting a new depth past
# 0.5*budget. Guarantees: never forfeits, always returns a legal move, and
# searches as deep as the position and the clock allow.


class SearchTimeout(Exception):
    '''Raised inside the search when the per-move deadline is exceeded.'''
    pass

def evaluate(fen, moves):
    '''Static material score from Red's perspective (+ good for Red).'''
    # `fen` is already a full FEN; only rebuild it if there are pending moves.
    if moves:
        fen = sf.get_fen("xiangqi", fen, moves)
    board = fen.split(" ")[0]
    score = 0.0
    for ch in board:
        value = PIECE_VALUES.get(ch.lower())
        if value is None:
            continue  # digits, '/', or the general
        score += value if ch.isupper() else -value
    return score

def choose_opening_move(fen, moves):
    '''If the given position is in the opening book, return the book move.'''
    # Only consider the root position, before any moves.
    if not moves:
        return OPENING_BOOK.get(fen, None)
    else:
        return None
    

def side_to_move(position_fen):
    '''Returns 'w' if Red is to move, 'b' if Black is to move.'''
    return position_fen.split(" ")[1]

def board_pieces(board):
    '''Map occupied squares to their piece, e.g. {'b10': 'r', 'h3': 'C'}.'''
    pieces = {}
    for row_index, row in enumerate(board.split('/')):
        rank = 10 - row_index          # FEN lists rank 10 first, rank 1 last
        col = 0
        for ch in row:
            if ch.isdigit():
                col += int(ch)         # run of empty squares
            else:
                pieces[f"{chr(ord('a') + col)}{rank}"] = ch
                col += 1
    return pieces

def split_move(move):
    '''Split a UCI move into (source, destination), e.g. 'b3b10' -> ('b3', 'b10').'''
    i = 1
    while move[i].isdigit():           # skip the source rank (1 or 2 digits)
        i += 1
    return move[:i], move[i:]

def order_moves(fen, legal):
    '''Orders legal moves so the most promising are searched first, then keeps the
    top N to bound the branching factor. All scoring comes from one board parse --
    no pyffish calls.

    Higher score = searched earlier:
      * captures rank above quiet moves, biggest victim first / cheapest attacker
        (MVV-LVA) -- this is what drives the alpha-beta cutoffs;
      * quiet moves are ranked by how far they advance toward the enemy.
    The sort is stable, so after the caller's shuffle, equal-scored moves keep a
    random order (preserving the anti-shuffle tie-break).
    '''
    pieces = board_pieces(fen.split(" ")[0])

    def score(move):
        src, dst = split_move(move)
        victim = pieces.get(dst)
        if victim is not None:         # capture: MVV-LVA, always above quiet moves
            attacker = pieces.get(src, '')
            return (1000 + 10 * PIECE_VALUES.get(victim.lower(), 0)
                         - PIECE_VALUES.get(attacker.lower(), 0))
        mover = pieces.get(src, '')    # quiet move: prefer advancing toward the enemy
        forward = int(dst[1:]) - int(src[1:])
        return forward if mover.isupper() else -forward

    return sorted(legal, key=score, reverse=True)[:TOP_N_MOVES]


def minimax_ab(fen, moves, depth, deadline, alpha=-INF, beta=INF):
    '''Minimax search with alpha-beta pruning.

    Returns (best_value, best_move) from Red's perspective. Raises
    SearchTimeout if the wall-clock deadline is passed, so the caller can
    fall back to the last fully-completed depth.
    '''
    if time.time() > deadline:
        raise SearchTimeout

    legal = sf.legal_moves("xiangqi", fen, moves)

    if not legal:
        return (-MATE if side_to_move(fen) == 'w' else MATE), None

    if depth == 0:
        return evaluate(fen, moves), None

    red_to_move = side_to_move(fen) == 'w'
    best_move = None

    # Shuffle first so equal-scored moves break ties randomly (prevents the
    # repetitive back-and-forth shuffling), then order captures first for pruning.
    random.shuffle(legal)
    ordered_moves = order_moves(fen, legal)

    if red_to_move:
        best_value = -INF
        for move in ordered_moves:
            child_fen = sf.get_fen("xiangqi", fen, moves + [move])
            value, _ = minimax_ab(child_fen, [], depth - 1, deadline, alpha, beta)
            if value > best_value:
                best_value, best_move = value, move
            alpha = max(alpha, best_value)
            if beta <= alpha:
                break  # beta cut-off
    else:
        best_value = INF
        for move in ordered_moves:
            child_fen = sf.get_fen("xiangqi", fen, moves + [move])
            value, _ = minimax_ab(child_fen, [], depth - 1, deadline, alpha, beta)
            if value < best_value:
                best_value, best_move = value, move
            beta = min(beta, best_value)
            if beta <= alpha:
                break  # alpha cut-off

    return best_value, best_move


def choose_move(fen, moves, time_limit):
    '''Picks a move using iterative-deepening alpha-beta within a time budget.

    Searches depth 1, 2, 3, ... keeping the best move from the last depth that
    fully completes. A hard deadline (a fraction of `time_limit` seconds) aborts
    any unfinished depth, so the bot always answers in time without forfeiting.
    '''
    start = time.time()
    deadline = start + TIME_SAFETY * time_limit
    soft_limit = start + SOFT_FRACTION * time_limit

    # Collapse the game history into a single FEN once, so the search never
    # replays all prior moves on every pyffish call (it works from an empty
    # history below). This matters more the longer the game runs.
    cur = sf.get_fen("xiangqi", fen, moves)

    best = None
    for depth in range(1, MAX_DEPTH + 1):
        try:
            _, move = minimax_ab(cur, [], depth, deadline)
        except SearchTimeout:
            break                          # discard this unfinished depth
        if move is None:                   # terminal position, no legal moves
            break
        best = move                        # keep last fully-completed depth
        if time.time() >= soft_limit:      # a deeper search likely won't finish
            break

    if best is None:                       # timed out before finishing depth 1
        legal = sf.legal_moves("xiangqi", cur, [])
        return legal[0] if legal else None
    return best


def parse_time_limit(msg):
    '''Reads the per-move budget (seconds) from a UCI 'go' command's movetime.'''
    tokens = msg.split()
    if "movetime" in tokens:
        i = tokens.index("movetime")
        if i + 1 < len(tokens):
            try:
                return int(tokens[i + 1]) / 1000.0
            except ValueError:
                pass
    return DEFAULT_MOVETIME

def make_random_move():
    '''Returns a random legal move'''
    global fen, moves
    legal_moves_list = sf.legal_moves("xiangqi", fen, moves)
    if not legal_moves_list:
        return None
    return random.choice(legal_moves_list)

def uci(msg: str):
    '''Returns result of UCCI protocol given passed message'''
    global fen, moves
    if msg == "uci" or msg == "ucci":
        print("id name Game Killer")
        print("id author Jinghan Chen")
        print("uciok")
    elif msg == "isready":
        print("readyok")
    elif msg.startswith("position startpos moves"):
        fen = sf.start_fen("xiangqi")
        moves = msg.split()[3:]
    elif msg.startswith("position startpos"):
        fen = sf.start_fen("xiangqi")
        moves = []
    elif msg.startswith("position fen"):
        parts = msg.split(" ", 2)
        if len(parts) >= 3:
            fen_and_moves = parts[2]
            if " moves " in fen_and_moves:
                fen_part, moves_part = fen_and_moves.split(" moves ", 1)
                fen = fen_part
                moves = moves_part.split()
            else:
                fen = fen_and_moves
                moves = []
    elif msg.startswith("go"):
        book_move = choose_opening_move(fen, moves)
        if book_move:
            print(f"bestmove {book_move}")
        else:
            time_limit = parse_time_limit(msg)
            move = choose_move(fen, moves, time_limit)
            print(f"bestmove {move if move else '0000'}")
    elif msg == "quit":
        sys.exit(0)
    return
    
def main():
    '''Passes UCI Messages Forever'''
    try:
        while True:
            uci(input())
    except Exception as e:
        print(f"Fatal Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "draw":
        import tree_draw          # imported only in draw mode; no effect on engine runtime
        tree_draw.draw_tree()
    else:
        main()