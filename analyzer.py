#!/usr/bin/env python
import subprocess
import pyffish as sf
import re
import os
import tempfile
import json
import time

class Engine:
    def __init__(self):
        self.process = subprocess.Popen(
            ['fairy-stockfish_x86-64.exe'], # Download your specific version and then change this
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.send("uci")
        self.wait("uciok")
        self.send("setoption name UCI_Variant value xiangqi")
        self.send("isready")
        self.wait("readyok")
    
    def send(self, cmd):
        self.process.stdin.write(f"{cmd}\n")
        self.process.stdin.flush()
    
    def wait(self, prefix):
        deadline = time.time() + 10
        while time.time() < deadline:
            line = self.process.stdout.readline().strip()
            if line.startswith(prefix):
                return
    
    def eval(self, moves):
        if moves:
            self.send(f"position startpos moves {' '.join(moves)}")
        else:
            self.send("position startpos")
        self.send("go depth 15")
        score = None
        best = None
        deadline = time.time() + 30
        
        while time.time() < deadline:
            line = self.process.stdout.readline().strip()
            if "score" in line:
                parts = line.split()
                if "cp" in parts:
                    score = int(parts[parts.index("cp") + 1]) / 100
                elif "mate" in parts:
                    mate_in = int(parts[parts.index("mate") + 1])
                    score = f"M{mate_in}"
            elif line.startswith("bestmove"):
                best = line.split()[1]
                break
        return score, best

def generate_svg(fen, output_path, piece_style='retro_simple', board_style='clean_alpha'):
    fen_file = tempfile.NamedTemporaryFile(mode='w', suffix='.fen', delete=False)
    fen_file.write(fen)
    fen_file.close()
    try:
        cmd = ['xiangqi-setup', '--pieces', piece_style, '--board', board_style, fen_file.name, output_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        os.unlink(fen_file.name)

def parse_pgn(text):
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\d+\.', '', text)
    text = re.sub(r'(1-0|0-1|1/2-1/2|\*)', '', text)
    return ' '.join(text.split())

def analyze(game):
    moves = parse_pgn(game).split()
    engine = Engine()
    fen = sf.start_fen("xiangqi")
    os.makedirs('static', exist_ok=True)
    results = []
    for i in range(len(moves) + 1):
        partial = moves[:i]
        score, best = engine.eval(partial)
        position_fen = sf.get_fen("xiangqi", fen, partial)
        svg_path = f"static/position_{i}.svg"
        generate_svg(position_fen, svg_path, "euro_xiangqi_js", "minimal") # xiangqi-setup --help for more options
        move = moves[i-1] if i > 0 else "start"
        side = "Red" if i % 2 == 0 else "Black"
        if isinstance(score, float):
            s = f"{score:+.1f}"
        else:
            s = score if score else "?"
        b = best if best else "?"
        print(f"{i:3} {side:5} {move:8} {s:>6} {b}")
        results.append({
            'move_num': i,
            'side': side,
            'move': move,
            'score': s,
            'best': b,
            'fen': position_fen,
            'svg': f"position_{i}.svg"
        })
    with open('static/analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to static/")
    engine.process.terminate()

if __name__ == "__main__":
    print("Paste game:")
    analyze(input())