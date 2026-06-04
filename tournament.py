#!/usr/bin/env python3
import subprocess
import time
import pyffish as sf
from itertools import combinations
from datetime import datetime

class Bot:
    """Wrapper for a UCI bot process"""
    def __init__(self, bot_path):
        self.path = bot_path
        self.process = self._start_process(bot_path)
        self._initialize()
    
    @staticmethod
    def _start_process(bot_path):
        """Start a bot subprocess"""
        return subprocess.Popen(
            ['python', bot_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
    
    def _initialize(self):
        """Initialize the bot with UCI protocol"""
        self.send("uci")
        self.wait_for("uciok")
        self.send("isready")
        self.wait_for("readyok")
    
    def send(self, command):
        self.process.stdin.write(f"{command}\n")
        self.process.stdin.flush()
    
    def wait_for(self, prefix, timeout=5):
        deadline = time.time() + timeout
        while time.time() < deadline:
            line = self.process.stdout.readline().strip()
            if line.startswith(prefix):
                return line
        return None
    
    def get_move(self, moves, time_limit):
        if moves:
            self.send(f"position startpos moves {' '.join(moves)}")
        else:
            self.send("position startpos")
        self.send(f"go movetime {time_limit * 1000}")
        
        response = self.wait_for("bestmove", timeout=time_limit + 2)
        if response:
            return response.split()[1]
        return None
    
    def quit(self):
        try:
            self.send("quit")
            self.process.terminate()
            self.process.wait(timeout=1)
        except:
            self.process.kill()
    
    @staticmethod
    def get_name(bot_path):
        try:
            process = Bot._start_process(bot_path)
            process.stdin.write("uci\n")
            process.stdin.flush()
            deadline = time.time() + 2
            while time.time() < deadline:
                line = process.stdout.readline().strip()
                if line.startswith("id name"):
                    name = line[8:].strip()
                    process.terminate()
                    return name
                elif line.startswith("uciok"):
                    break
            process.terminate()
        except:
            pass
        return bot_path.split('/')[-1].replace('.py', '')

def play_game(bot1_path, bot2_path, time_limit=1):
    """Play a single game between two bots"""
    bot1 = Bot(bot1_path)
    bot2 = Bot(bot2_path)
    
    fen = sf.start_fen("xiangqi")
    moves = []
    result = "1/2-1/2"
    for move_num in range(400):
        current_bot = bot1 if move_num % 2 == 0 else bot2
        bestmove = current_bot.get_move(moves, time_limit)
        if not bestmove or bestmove == "0000":
            result = "0-1" if move_num % 2 == 0 else "1-0"
            break
        moves.append(bestmove)
        if not sf.legal_moves("xiangqi", fen, moves):
            result = "1-0" if move_num % 2 == 0 else "0-1"
            break
    bot1.quit()
    bot2.quit()
    return result, moves

def update_scores(scores, wins, losses, draws, winner_path, loser_path=None, is_draw=False):
    if is_draw:
        scores[winner_path] += 0.5
        scores[loser_path] += 0.5
        draws[winner_path] += 1
        draws[loser_path] += 1
    else:
        scores[winner_path] += 1
        wins[winner_path] += 1
        losses[loser_path] += 1

def format_pgn(game_num, red_bot, black_bot, bot_names, result, moves):
    date = datetime.now().strftime("%Y.%m.%d")
    pgn = []
    pgn.append(f'[Event "Xiangqi Tournament"]')
    pgn.append(f'[Site "Local"]')
    pgn.append(f'[Date "{date}"]')
    pgn.append(f'[Round "{game_num}"]')
    pgn.append(f'[Red "{bot_names[red_bot]}"]')
    pgn.append(f'[Black "{bot_names[black_bot]}"]')
    pgn.append(f'[Result "{result}"]')
    pgn.append('')
    move_text = []
    for i in range(0, len(moves), 2):
        move_num = i // 2 + 1
        if i + 1 < len(moves):
            move_text.append(f"{move_num}. {moves[i]} {moves[i+1]}")
        else:
            move_text.append(f"{move_num}. {moves[i]}")
    pgn.append(' '.join(move_text) + f' {result}')
    pgn.append('')
    return '\n'.join(pgn)

def play_and_record_game(game_num, red_bot, black_bot, bot_names, scores, wins, losses, draws, time_limit):
    """Play a game and update scores"""
    result, moves = play_game(red_bot, black_bot, time_limit)
    print(format_pgn(game_num, red_bot, black_bot, bot_names, result, moves))
    if result == "1-0":
        update_scores(scores, wins, losses, draws, red_bot, black_bot)
    elif result == "0-1":
        update_scores(scores, wins, losses, draws, black_bot, red_bot)
    else:
        update_scores(scores, wins, losses, draws, red_bot, black_bot, is_draw=True)

def play_round_robin_tournament(bots, games_per_matchup=2, time_limit=1):
    bot_names = {path: Bot.get_name(path) for path in bots}
    scores = {path: 0 for path in bots}
    wins = {path: 0 for path in bots}
    losses = {path: 0 for path in bots}
    draws = {path: 0 for path in bots}
    pairings = list(combinations(bots, 2))    

    print(f"Tournament Results")
    game_num = 0
    for bot1, bot2 in pairings:
        for _ in range(games_per_matchup):
            game_num += 1
            play_and_record_game(game_num, bot1, bot2, bot_names, scores, wins, losses, draws, time_limit)
            game_num += 1
            play_and_record_game(game_num, bot2, bot1, bot_names, scores, wins, losses, draws, time_limit)    
    print(f"\n{'Bot':<30} {'Score':>6} {'Record':>10} {'Win%':>6}")
    print("----------")    
    for bot_path in sorted(bots, key=lambda e: scores[e], reverse=True):
        w, l, d = wins[bot_path], losses[bot_path], draws[bot_path]
        total = w + l + d
        win_pct = (w / total * 100) if total > 0 else 0
        print(f"{bot_names[bot_path]:<30} {scores[bot_path]:>6.1f} {w:>3}-{l:<3}-{d:<2} {win_pct:>5.1f}%")
    print()
    return scores

if __name__ == "__main__":
    bots = [
        "./game_killer.py",
        "./random_bot.py",
    ]

    play_round_robin_tournament(bots, games_per_matchup=2, time_limit=1)