# Chess on two phones

The [phone hub](../hub/README.md) supplies the installable browser client and authoritative Python-chess referee. Create a chess match on one paired device and join it from another.

Each phone can choose a legal move manually or enable the phone-local JavaScript evaluator. This is a simple handcrafted board evaluator, not a pretrained LLM or strong chess engine. Choose the configured tower model mode to compare an Ollama-compatible model. Inference location is explicit.

The referee validates moves and turns, applies five-minute clocks, handles checkmate/draw/timeout, persists the move list, and exports PGN. Invalid moves leave the board unchanged; clocks continue while a player thinks or disconnects. No physical chess-board actuation is included.
