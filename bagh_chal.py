"""老虎吃羊棋 (Bagh-chal) — 尼泊尔传统不对称围堵棋.

5x5 点阵棋盘(含对角线),4 只老虎对 20 只羊.
老虎:沿线走一格,或跳过相邻羊吃掉它;吃满 5 只羊获胜.
羊:先逐只布子(20 只),布完后沿线走一格;困死所有老虎获胜.
纯标准库,无第三方依赖.
"""

import argparse
import copy
import random
import sys

SIZE = 5
N_TIGERS = 4
N_GOATS = 20
GOATS_TO_WIN = 5          # 老虎吃满 5 只即胜
TIGER = "T"
GOAT = "G"
EMPTY = "."

# 8 个方向
DIRS = [(-1, -1), (-1, 0), (-1, 1),
        (0, -1),           (0, 1),
        (1, -1),  (1, 0),  (1, 1)]


def in_bounds(r, c):
    return 0 <= r < SIZE and 0 <= c < SIZE


def linked(a, b):
    """两点 (r,c) 之间是否有线相连."""
    (r1, c1), (r2, c2) = a, b
    dr, dc = r2 - r1, c2 - c1
    if max(abs(dr), abs(dc)) != 1:
        return False
    if dr == 0 or dc == 0:
        return True
    # 对角线只存在于 (r+c) 为偶数的 2x2 方格里(棋盘交错对角线)
    return (min(r1, r2) + min(c1, c2)) % 2 == 0


def neighbors(p):
    r, c = p
    return [(r + dr, c + dc) for dr, dc in DIRS
            if in_bounds(r + dr, c + dc) and linked(p, (r + dr, c + dc))]


def other(player):
    return GOAT if player == TIGER else TIGER


class BaghChal:
    """棋局. phase: 'place'(羊布子) / 'move'(走子)."""

    def __init__(self):
        self.board = [[EMPTY] * SIZE for _ in range(SIZE)]
        for r, c in [(0, 0), (0, 4), (4, 0), (4, 4)]:
            self.board[r][c] = TIGER
        self.goats_placed = 0
        self.goats_captured = 0
        self.turn = GOAT          # 羊先布子
        self.phase = "place"
        self.n_moves = 0

    # ---- 基本走法 ----

    def tiger_moves(self, p):
        """老虎在 p 的全部走法: [(起点, 落点, 吃子点或None)]."""
        r, c = p
        moves = []
        for q in neighbors(p):
            qr, qc = q
            if self.board[qr][qc] == EMPTY:
                moves.append((p, q, None))
            elif self.board[qr][qc] == GOAT:
                jr, jc = qr + (qr - r), qc + (qc - c)
                if in_bounds(jr, jc) and linked(q, (jr, jc)) \
                        and self.board[jr][jc] == EMPTY:
                    moves.append((p, (jr, jc), q))
        return moves

    def all_tiger_moves(self):
        moves = []
        for r in range(SIZE):
            for c in range(SIZE):
                if self.board[r][c] == TIGER:
                    moves.extend(self.tiger_moves((r, c)))
        return moves

    def goat_moves(self):
        moves = []
        for r in range(SIZE):
            for c in range(SIZE):
                if self.board[r][c] == GOAT:
                    for q in neighbors((r, c)):
                        qr, qc = q
                        if self.board[qr][qc] == EMPTY:
                            moves.append(((r, c), q))
        return moves

    def tiger_trapped(self):
        return not self.all_tiger_moves()

    # ---- 执行走法 ----

    def _check_turn(self, player):
        if player != self.turn:
            raise ValueError(f"现在轮到 {self.turn}, 不是 {player}")

    def place_goat(self, p):
        """羊布子阶段放一只羊."""
        self._check_turn(GOAT)
        if self.phase != "place":
            raise ValueError("布子阶段已结束")
        r, c = p
        if not in_bounds(r, c):
            raise ValueError(f"布子越界: {p}")
        if self.board[r][c] != EMPTY:
            raise ValueError(f"布子点被占: {p}")
        self.board[r][c] = GOAT
        self.goats_placed += 1
        self.n_moves += 1
        if self.goats_placed >= N_GOATS:
            self.phase = "move"
        self.turn = TIGER
        return self.winner()

    def move_tiger(self, src, dst):
        self._check_turn(TIGER)
        r, c = src
        if not in_bounds(*src) or self.board[r][c] != TIGER:
            raise ValueError(f"起点不是老虎: {src}")
        for s, d, cap in self.tiger_moves(src):
            if d == dst:
                self.board[r][c] = EMPTY
                self.board[dst[0]][dst[1]] = TIGER
                if cap is not None:
                    self.board[cap[0]][cap[1]] = EMPTY
                    self.goats_captured += 1
                self.n_moves += 1
                self.turn = GOAT  # 老虎走完永远轮到羊(布子或走子)
                return self.winner()
        raise ValueError(f"老虎非法走法: {src} -> {dst}")

    def move_goat(self, src, dst):
        self._check_turn(GOAT)
        if self.phase != "move":
            raise ValueError("走子阶段未开始, 羊只能布子")
        r, c = src
        if not in_bounds(*src) or self.board[r][c] != GOAT:
            raise ValueError(f"起点不是羊: {src}")
        if not in_bounds(*dst) or self.board[dst[0]][dst[1]] != EMPTY:
            raise ValueError(f"落点非法: {dst}")
        if not linked(src, dst):
            raise ValueError(f"羊只能沿线走一格: {src} -> {dst}")
        self.board[r][c] = EMPTY
        self.board[dst[0]][dst[1]] = GOAT
        self.n_moves += 1
        self.turn = TIGER
        return self.winner()

    # ---- 胜负 ----

    def winner(self):
        """返回 'T'(老虎胜)/'G'(羊胜)/None(继续)."""
        if self.goats_captured >= GOATS_TO_WIN:
            return TIGER
        if self.tiger_trapped():
            return GOAT
        goats_on = sum(row.count(GOAT) for row in self.board)
        if goats_on + self.goats_captured < GOATS_TO_WIN and \
                self.goats_placed >= N_GOATS:
            # 羊不够 5 只可被吃, 老虎永远吃不满 -> 判羊胜
            return GOAT
        return None

    def render(self):
        lines = []
        for r in range(SIZE):
            row = []
            for c in range(SIZE):
                row.append(self.board[r][c])
            lines.append(" ".join(row) + f"  {r}")
        lines.append("0 1 2 3 4")
        phase = "布子" if self.phase == "place" else "走子"
        lines.append(f"阶段:{phase} 轮到:{'羊' if self.turn == GOAT else '老虎'} "
                     f"已布羊:{self.goats_placed}/20 已吃:{self.goats_captured}/5")
        return "\n".join(lines)


# ---- AI ----

def ai_tiger_move(game, rng):
    moves = game.all_tiger_moves()
    if not moves:
        return None
    captures = [m for m in moves if m[2] is not None]
    if captures:
        return rng.choice(captures)
    # 否则走一步: 优先走向离羊近的位置
    goats = [(r, c) for r in range(SIZE) for c in range(SIZE)
             if game.board[r][c] == GOAT]

    def score(m):
        (dr, dc) = m[1]
        if not goats:
            return rng.random()
        d = min(abs(dr - gr) + abs(dc - gc) for gr, gc in goats)
        return -d + rng.random() * 0.5
    return max(moves, key=score)


def _tiger_mobility_after(game, move):
    """假设老虎走 move 后, 老虎方总走法数(羊用来压制)."""
    g2 = copy.deepcopy(game)
    s, d, cap = move
    g2.board[s[0]][s[1]] = EMPTY
    g2.board[d[0]][d[1]] = TIGER
    if cap:
        g2.board[cap[0]][cap[1]] = EMPTY
    return len(g2.all_tiger_moves())


def ai_goat_move(game, rng):
    moves = game.goat_moves()
    if not moves:
        return None

    def score(m):
        src, dst = m
        # 危险: 落点会被老虎下一步跳吃
        danger = 0
        for tr in range(SIZE):
            for tc in range(SIZE):
                if game.board[tr][tc] == TIGER:
                    for s, d, cap in game.tiger_moves((tr, tc)):
                        if cap == dst:
                            danger += 1
        # 收益: 走完后压制老虎走法
        # (用当前棋盘近似: 落点堵住老虎邻格)
        block = 0
        for q in neighbors(dst):
            if game.board[q[0]][q[1]] == TIGER:
                block += 1
        return block * 2 - danger * 5 + rng.random()
    return max(moves, key=score)


def ai_goat_place(game, rng):
    empties = [(r, c) for r in range(SIZE) for c in range(SIZE)
               if game.board[r][c] == EMPTY]
    tigers = [(r, c) for r in range(SIZE) for c in range(SIZE)
              if game.board[r][c] == TIGER]

    def immediate_captures(p):
        """假设在 p 布羊, 老虎下一步能跳吃几只(含刚布的这只)."""
        g2 = copy.deepcopy(game)
        g2.board[p[0]][p[1]] = GOAT
        return sum(1 for m in g2.all_tiger_moves() if m[2] is not None)

    def score(p):
        d = min(abs(p[0] - tr) + abs(p[1] - tc) for tr, tc in tigers)
        caps = immediate_captures(p)
        return -(abs(d - 2)) - caps * 10 + rng.random() * 0.3
    return max(empties, key=score)


def play_auto(games=5, seed=42, verbose=False, max_moves=600):
    rng = random.Random(seed)
    results = {"T": 0, "G": 0, "draw": 0}
    for gi in range(games):
        game = BaghChal()
        w = None
        while game.n_moves < max_moves:
            if game.turn == GOAT:
                if game.phase == "place":
                    p = ai_goat_place(game, rng)
                    w = game.place_goat(p)
                else:
                    m = ai_goat_move(game, rng)
                    if m is None:
                        break
                    w = game.move_goat(*m)
            else:
                m = ai_tiger_move(game, rng)
                if m is None:
                    w = GOAT
                    break
                w = game.move_tiger(m[0], m[1])
            if w:
                break
        key = w if w in ("T", "G") else "draw"
        results[key] += 1
        if verbose:
            name = {"T": "老虎胜", "G": "羊胜"}.get(key, "和棋")
            print(f"第 {gi + 1}/{games} 局:{name} "
                  f"(步数 {game.n_moves}, 吃羊 {game.goats_captured})")
    return results


# ---- 交互 ----

def parse_point(s):
    parts = s.strip().split()
    if len(parts) != 2:
        raise ValueError("请输入两个数字, 如: 2 3")
    r, c = int(parts[0]), int(parts[1])
    if not in_bounds(r, c):
        raise ValueError("坐标越界")
    return (r, c)


def play_interactive():
    game = BaghChal()
    print("老虎吃羊棋 (Bagh-chal)")
    print("羊: 布子阶段输入落点(如 2 3); 走子阶段输入 起点行 起点列 落点行 落点列")
    print("老虎: 输入 起点行 起点列 落点行 落点列 (跳吃自动执行)")
    print("输入 q 退出")
    while True:
        print()
        print(game.render())
        w = game.winner()
        if w:
            print("老虎获胜!" if w == TIGER else "羊获胜!")
            break
        try:
            if game.turn == GOAT and game.phase == "place":
                s = input(f"羊布子({game.goats_placed + 1}/20)> ").strip()
                if s == "q":
                    break
                game.place_goat(parse_point(s))
            elif game.turn == GOAT:
                s = input("羊走子(起点行 列 落点行 列)> ").strip()
                if s == "q":
                    break
                a, b, c, d = (int(x) for x in s.split())
                game.move_goat((a, b), (c, d))
            else:
                s = input("老虎走子(起点行 列 落点行 列)> ").strip()
                if s == "q":
                    break
                a, b, c, d = (int(x) for x in s.split())
                game.move_tiger((a, b), (c, d))
        except (ValueError, IndexError) as e:
            print("非法:", e)


def main(argv=None):
    ap = argparse.ArgumentParser(description="老虎吃羊棋 (Bagh-chal)")
    ap.add_argument("--auto", action="store_true", help="AI 对 AI 自动演示")
    ap.add_argument("--games", type=int, default=5, help="自动演示局数")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--verbose", action="store_true", help="打印每局结果")
    args = ap.parse_args(argv)
    if args.auto:
        res = play_auto(args.games, args.seed, args.verbose or True)
        print(f"总计: 老虎胜 {res['T']}, 羊胜 {res['G']}, 和棋 {res['draw']}")
    else:
        if not sys.stdin.isatty():
            print("交互模式需要终端; 无头演示请用 --auto", file=sys.stderr)
            return 2
        play_interactive()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
