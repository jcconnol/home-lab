"""Chess referee helpers; move selection can happen on the phone or tower."""
import time
import chess
import chess.pgn


def board_for(state):
    board = chess.Board()
    for move in state["moves"]:
        board.push_uci(move)
    return board


def create():
    return {"moves": [], "remaining": [300.0, 300.0], "turn_started": None, "winner": None}


def refresh_clock(state, players):
    if state["winner"] is None and len(players) == 2 and state["turn_started"] is not None:
        side = len(state["moves"]) % 2
        elapsed = max(0, time.time() - state["turn_started"])
        if elapsed >= state["remaining"][side]:
            board = board_for(state)
            state["winner"] = "draw" if board.has_insufficient_material(not board.turn) else str(1 - side)


def move(state, side, uci, players):
    refresh_clock(state, players)
    if len(players) != 2 or state["winner"] is not None:
        raise ValueError("Match is not active")
    if side != len(state["moves"]) % 2:
        raise ValueError("Not your turn")
    board = board_for(state)
    try:
        candidate = chess.Move.from_uci(uci)
    except (ValueError, TypeError):
        raise ValueError("Use a legal UCI move, for example e2e4")
    if candidate not in board.legal_moves:
        raise ValueError("Illegal move")
    elapsed = max(0, time.time() - state["turn_started"])
    state["remaining"][side] = max(0, state["remaining"][side] - elapsed)
    state["moves"].append(uci)
    state["turn_started"] = time.time()
    board.push(candidate)
    outcome = board.outcome(claim_draw=True)
    if outcome:
        state["winner"] = "draw" if outcome.winner is None else "0" if outcome.winner else "1"
    return state


def public(state, players, device):
    refresh_clock(state, players)
    board = board_for(state)
    candidates = []
    for move in board.legal_moves:
        copy = board.copy()
        copy.push(move)
        # Features are observations. The browser evaluates them locally.
        material = sum(len(copy.pieces(piece, board.turn)) * value - len(copy.pieces(piece, not board.turn)) * value
                       for piece, value in [(chess.PAWN, 1), (chess.KNIGHT, 3), (chess.BISHOP, 3), (chess.ROOK, 5), (chess.QUEEN, 9)])
        candidates.append({"uci": move.uci(), "features": [material, float(copy.is_check()), float(copy.is_checkmate()),
                                                          (3.5 - abs(chess.square_file(move.to_square) - 3.5)) / 3.5]})
    game = chess.pgn.Game.from_board(board)
    game.headers["White"] = players[0] if players else "waiting"
    game.headers["Black"] = players[1] if len(players) > 1 else "waiting"
    if state["winner"] is not None:
        game.headers["Result"] = "1/2-1/2" if state["winner"] == "draw" else "1-0" if state["winner"] == "0" else "0-1"
    remaining = list(state["remaining"])
    if len(players) == 2 and state["winner"] is None and state["turn_started"]:
        side = len(state["moves"]) % 2
        remaining[side] = max(0, remaining[side] - (time.time() - state["turn_started"]))
    return {"fen": board.fen(), "moves": state["moves"], "legal_moves": candidates, "remaining": remaining,
            "turn": len(state["moves"]) % 2, "you": players.index(device) if device in players else None,
            "winner": state["winner"], "pgn": str(game), "evaluation": "Phone-local handcrafted evaluator, or configured tower model. Not a pretrained phone LLM."}
