welcome to my new game, Astraeus.

**The Astraeus Incident**

Astraeus was never meant to reach its destination.

What began as a routine deep-space expedition has become something far worse. As the lone conscious presence aboard the drifting vessel, you awaken to fragmented systems, corrupted logs, and a reality that no longer behaves as it should.

Corridors shift. Signals repeat. Time fractures.

An impossible anomaly has formed near the ship—a gravitational singularity that doesn’t just distort space, but memory, perception… and something deeper. Echoes of the crew linger in broken loops. Rooms appear where none existed. And something is watching from within the core.

As you navigate the collapsing interior of Astraeus, you must piece together what happened, uncover the truth behind the anomaly, and decide whether escape is even possible.

Or if you were ever meant to leave at all.

**This is not a story about survival.**

It’s a story about understanding something that should not exist.

## Project LABYRINTH — Adaptive Puzzle Engine

Doors now run through an adaptive puzzle protocol before unlocking.

- Puzzles scale with inferred player intelligence (`skill_rating`) based on speed, streak, and accuracy.
- Difficulty rises with smarter performance and softens after repeated mistakes.
- The engine tracks mistake categories (`arithmetic`, `pattern`, `logic`) and changes future puzzle generation.
- Every run gets a unique `run_id`, and generated puzzle signatures are not repeated inside that run.
- LABYRINTH learning state is saved in `save.json` so adaptation persists across sessions.

### In-Game Controls

- `E` near a closed door: start LABYRINTH challenge.
- `ENTER`: submit answer.
- `BACKSPACE`: edit answer.
- `ESC`: abort challenge and return to gameplay.
