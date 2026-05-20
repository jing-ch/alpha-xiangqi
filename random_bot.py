#!/usr/bin/env python3
import random
import sys
import pyffish as sf

fen = sf.start_fen("xiangqi")
moves = []

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
        print("id name Random Bot")
        print("id author Oscar Veliz")
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