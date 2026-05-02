import random
import time


class AdaptivePuzzleEngine:
    def __init__(self):
        self.rng = random.Random()
        self.run_id = f"run-{int(time.time())}-{random.SystemRandom().randint(1000, 9999)}"
        self.skill_rating = 0.5
        self.total_puzzles = 0
        self.total_solved = 0
        self.total_failed = 0
        self.total_attempts = 0
        self.streak = 0
        self.mistake_profile = {
            "arithmetic": 0,
            "pattern": 0,
            "logic": 0,
        }
        self.generated_signatures = set()

    def snapshot(self):
        return {
            "run_id": self.run_id,
            "skill_rating": round(self.skill_rating, 4),
            "total_puzzles": self.total_puzzles,
            "total_solved": self.total_solved,
            "total_failed": self.total_failed,
            "total_attempts": self.total_attempts,
            "streak": self.streak,
            "mistake_profile": dict(self.mistake_profile),
        }

    def load_snapshot(self, data):
        if not isinstance(data, dict):
            return
        run_id = data.get("run_id")
        if isinstance(run_id, str) and run_id.strip():
            self.run_id = run_id

        skill = data.get("skill_rating")
        if isinstance(skill, (int, float)):
            self.skill_rating = max(0.05, min(float(skill), 2.0))

        for key in ("total_puzzles", "total_solved", "total_failed", "total_attempts", "streak"):
            value = data.get(key)
            if isinstance(value, int) and value >= 0:
                setattr(self, key, value)

        mistakes = data.get("mistake_profile")
        if isinstance(mistakes, dict):
            for category in self.mistake_profile:
                value = mistakes.get(category)
                if isinstance(value, int) and value >= 0:
                    self.mistake_profile[category] = value

    def _difficulty(self):
        pressure = self.total_solved / max(1, self.total_puzzles)
        streak_bonus = min(0.4, self.streak * 0.05)
        base = 0.7 + self.skill_rating * 1.6 + pressure + streak_bonus
        return max(1, min(8, int(round(base))))

    def _weighted_category(self):
        weights = {}
        for name, mistakes in self.mistake_profile.items():
            mastery = 1.0 / (1.0 + mistakes * 0.35)
            challenge = 1.0 + mistakes * 0.25
            # The engine alternates between confidence-building and weakness-training.
            if self.streak < 2:
                weights[name] = challenge
            else:
                weights[name] = mastery + 0.4

        total = sum(weights.values())
        pick = self.rng.uniform(0, total)
        running = 0.0
        for name, weight in weights.items():
            running += weight
            if pick <= running:
                return name
        return "arithmetic"

    def generate_puzzle(self):
        difficulty = self._difficulty()
        category = self._weighted_category()

        for _ in range(8):
            if category == "arithmetic":
                puzzle = self._make_arithmetic(difficulty)
            elif category == "pattern":
                puzzle = self._make_pattern(difficulty)
            else:
                puzzle = self._make_logic(difficulty)

            signature = f"{puzzle['category']}|{puzzle['prompt']}|{puzzle['answer']}"
            if signature not in self.generated_signatures:
                self.generated_signatures.add(signature)
                break

        puzzle["difficulty"] = difficulty
        puzzle["max_attempts"] = 2 + difficulty // 2
        puzzle["attempts"] = 0
        puzzle["started_at"] = time.time()
        puzzle["time_limit"] = max(8.0, 28.0 - (difficulty * 1.5))
        puzzle["run_id"] = self.run_id
        self.total_puzzles += 1
        return puzzle

    def submit_answer(self, puzzle, answer_text):
        puzzle["attempts"] += 1
        self.total_attempts += 1

        expected = str(puzzle["answer"]).strip().lower()
        guess = str(answer_text).strip().lower()
        elapsed = time.time() - puzzle.get("started_at", time.time())

        is_correct = guess == expected
        if is_correct:
            self.total_solved += 1
            self.streak += 1
            speed_bonus = max(0.0, (puzzle.get("time_limit", 20.0) - elapsed) / 20.0)
            self.skill_rating = min(2.0, self.skill_rating + 0.06 + speed_bonus * 0.08)
            self._decrease_mistake(puzzle["category"])
            return True, "ACCESS GRANTED"

        self.mistake_profile[puzzle["category"]] += 1
        self.streak = 0
        self.skill_rating = max(0.05, self.skill_rating - 0.04)

        if puzzle["attempts"] >= puzzle["max_attempts"]:
            self.total_failed += 1
            return False, f"ACCESS DENIED // SOLUTION: {puzzle['answer']}"

        hint = puzzle.get("hint", "Try a different angle.")
        return False, f"INCORRECT // HINT: {hint}"

    def check_timeout(self, puzzle):
        if not puzzle:
            return False
        elapsed = time.time() - puzzle.get("started_at", time.time())
        if elapsed >= puzzle.get("time_limit", 20.0):
            self.total_failed += 1
            self.streak = 0
            self.mistake_profile[puzzle["category"]] += 1
            self.skill_rating = max(0.05, self.skill_rating - 0.05)
            return True
        return False

    def _decrease_mistake(self, category):
        self.mistake_profile[category] = max(0, self.mistake_profile[category] - 1)

    def _make_arithmetic(self, difficulty):
        terms = 2 + difficulty // 2
        values = [self.rng.randint(2, 9 + difficulty) for _ in range(terms)]
        ops_pool = ["+", "-"]
        if difficulty >= 4:
            ops_pool.append("*")

        ops = [self.rng.choice(ops_pool) for _ in range(terms - 1)]
        expr_parts = [str(values[0])]
        result = values[0]
        for op, val in zip(ops, values[1:]):
            expr_parts.append(op)
            expr_parts.append(str(val))
            if op == "+":
                result += val
            elif op == "-":
                result -= val
            else:
                result *= val

        prompt = "Solve: " + " ".join(expr_parts)
        hint = "Evaluate left to right; no hidden operators."
        return {
            "category": "arithmetic",
            "prompt": prompt,
            "answer": result,
            "hint": hint,
        }

    def _make_pattern(self, difficulty):
        start = self.rng.randint(2, 6 + difficulty)
        step = self.rng.randint(1, max(2, difficulty))
        curve = self.rng.randint(0, max(1, difficulty // 3))
        seq = [start]

        for i in range(1, 5):
            seq.append(seq[-1] + step + curve * i)

        answer = seq[-1] + step + curve * 5
        prompt = "Sequence: " + ", ".join(str(n) for n in seq) + ", ?"
        hint = "Look at the change between numbers; it may itself increase."
        return {
            "category": "pattern",
            "prompt": prompt,
            "answer": answer,
            "hint": hint,
        }

    def _make_logic(self, difficulty):
        code_len = min(6, 3 + difficulty // 2)
        digits = [str(self.rng.randint(0, 9)) for _ in range(code_len)]
        transform = self.rng.choice(["reverse", "shift", "mirror"])

        if transform == "reverse":
            answer = "".join(reversed(digits))
            prompt = "Protocol Reverse: " + "".join(digits)
            hint = "Read the code from right to left."
        elif transform == "shift":
            shift_by = self.rng.randint(1, min(4, difficulty))
            shifted = [(int(d) + shift_by) % 10 for d in digits]
            answer = "".join(str(x) for x in shifted)
            prompt = f"Protocol Shift+{shift_by}: " + "".join(digits)
            hint = "Increase each digit by the shown amount and wrap after 9."
        else:
            mirror_map = {"0": "0", "1": "1", "2": "5", "5": "2", "6": "9", "8": "8", "9": "6", "3": "3", "4": "7", "7": "4"}
            answer = "".join(mirror_map[d] for d in reversed(digits))
            prompt = "Protocol Mirror: " + "".join(digits)
            hint = "Reverse the code, then mirror each digit pair (2<->5, 6<->9, 4<->7)."

        return {
            "category": "logic",
            "prompt": prompt,
            "answer": answer,
            "hint": hint,
        }
