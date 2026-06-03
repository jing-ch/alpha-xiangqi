#!/usr/bin/env python3
import random
import sys
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

def evaluate(fen, moves):
    '''Static material score from Red's perspective (+ good for Red).'''
    board = sf.get_fen("xiangqi", fen, moves).split(" ")[0]
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
            move = make_random_move()
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
    main()