import array
import os
import time

import pygame

from core.settings import FREEZE_AUDIO_WINDOW

_master = 1.0
_muted = False
_music_base = 0.6
_music_path = None

_rate = 1.0

_loops = {}
_resample_cache = {}

_freeze_start = 0.0
_freeze_pos = 0.0
_freeze_path = None
_freeze_len = 1.0
_freeze_rate = 1.0

_RESERVED_LOOP_KEYS = ["dilation", "echo", "rewind", "freeze", "mg"]


def _effective(base):
    if _muted or _master <= 0:
        return 0.0
    return max(0.0, min(1.0, base * _master))


def init_channels():
    if not pygame.mixer.get_init():
        return
    try:
        pygame.mixer.set_num_channels(16)
        pygame.mixer.set_reserved(len(_RESERVED_LOOP_KEYS))
    except pygame.error:
        pass


# ── one-shot sound effects ────────────────────────────────────────────────

def play_sound(path, base=1.0):
    if _muted or _master <= 0:
        return
    if not pygame.mixer.get_init():
        return
    if not path or not os.path.exists(path):
        return
    try:
        sound = pygame.mixer.Sound(path)
        if _rate != 1.0:
            sound = _resampled_sound(path, sound, _rate)
        sound.set_volume(_effective(base))
        sound.play()
    except pygame.error:
        pass


def play_sfx_slowed(path, rate=0.6, volume=1.0):
    """One-shot SFX resampled slower (rate < 1) for dread whooshes/rumbles."""
    if _muted or _master <= 0:
        return
    if not pygame.mixer.get_init():
        return
    try:
        key = ("slow", path, round(rate, 2))
        sound = _resample_cache.get(key)
        if sound is None:
            base_sound = pygame.mixer.Sound(path)
            slowed = _resample_bytes(base_sound.get_raw(), rate) if rate < 1.0 else None
            try:
                sound = pygame.mixer.Sound(buffer=slowed) if slowed else base_sound
            except (pygame.error, ValueError, TypeError):
                sound = base_sound
            _resample_cache[key] = sound
            if len(_resample_cache) > 48:
                _resample_cache.pop(next(iter(_resample_cache)))
        sound.set_volume(_effective(volume))
        sound.play()
    except pygame.error:
        pass


def _resampled_sound(path, sound, rate):
    key = (path, rate)
    if key not in _resample_cache:
        try:
            slowed = _resample_bytes(sound.get_raw(), rate)
            _resample_cache[key] = pygame.mixer.Sound(buffer=slowed)
        except (pygame.error, ValueError, TypeError):
            _resample_cache[key] = None
        if len(_resample_cache) > 32:
            _resample_cache.pop(next(iter(_resample_cache)))
    cached = _resample_cache.get(key)
    return cached if cached is not None else sound


def _resample_arr(arr, rate):
    """Slow an int16 numpy array to `rate` (0 < rate <= 1) samples."""
    import numpy as np

    if len(arr) == 0 or rate >= 1.0:
        return arr
    n_out = int(len(arr) / rate)
    indices = np.floor(np.arange(n_out) * rate).astype(np.int64)
    indices = np.clip(indices, 0, len(arr) - 1)
    return arr[indices]


def _resample_bytes(raw, rate):
    samples = array.array("h", raw)
    if len(samples) == 0 or rate >= 1.0:
        return raw
    import numpy as np

    arr = np.frombuffer(samples, dtype=np.int16)
    return _resample_arr(arr, rate).astype(np.int16).tobytes()


# ── looping ability sounds ────────────────────────────────────────────────

def start_loop(key, path, base=1.0):
    if key not in _RESERVED_LOOP_KEYS or key in _loops:
        return
    if not pygame.mixer.get_init():
        return
    try:
        sound = pygame.mixer.Sound(path)
        channel = pygame.mixer.Channel(_RESERVED_LOOP_KEYS.index(key))
        channel.set_volume(_effective(base))
        channel.play(sound, loops=-1)
        _loops[key] = {"channel": channel, "sound": sound, "base": base}
    except pygame.error:
        pass


def stop_loop(key):
    entry = _loops.pop(key, None)
    if entry is None:
        return
    try:
        entry["channel"].stop()
    except pygame.error:
        pass


def stop_all_loops():
    for key in list(_loops):
        stop_loop(key)


def _apply_loop_volumes():
    for entry in _loops.values():
        try:
            entry["channel"].set_volume(_effective(entry["base"]))
        except pygame.error:
            pass


# ── music ──────────────────────────────────────────────────────────────────

def music_volume(base):
    global _music_base
    _music_base = base
    return _effective(base)


def set_music_path(path):
    global _music_path
    _music_path = path


def set_master(volume):
    global _master
    _master = max(0.0, min(1.0, volume))
    _apply_loop_volumes()
    if pygame.mixer.get_init():
        try:
            pygame.mixer.music.set_volume(_effective(_music_base))
        except pygame.error:
            pass


def set_muted(muted):
    global _muted
    _muted = bool(muted)
    _apply_loop_volumes()
    if pygame.mixer.get_init():
        try:
            pygame.mixer.music.set_volume(_effective(_music_base))
        except pygame.error:
            pass


# ── time-freeze audio slowdown ────────────────────────────────────────────

def begin_freeze(rate, path):
    """Slow all audio while time is frozen.

    Captures a window of the currently playing music starting at the freeze
    moment, resamples it to `rate`, and loops it. SFX played while frozen are
    slowed via the global rate.
    """
    global _rate, _freeze_start, _freeze_pos, _freeze_path, _freeze_len, _freeze_rate

    _stop_freezing()
    _rate = max(0.01, min(1.0, rate))
    if _rate >= 1.0 or not pygame.mixer.get_init() or not path:
        return

    pos = 0
    track_len = 0.001
    try:
        pos = pygame.mixer.music.get_pos() // 1000
        if pos < 0:
            pos = 0
        track = pygame.mixer.Sound(path)
        track_len = max(0.001, track.get_length())
        start = pos % track_len
        end = min(track_len, start + FREEZE_AUDIO_WINDOW)

        freq, _fmt, channels = pygame.mixer.get_init()
        frame = max(1, channels)
        raw = track.get_raw()

        import numpy as np

        arr = np.frombuffer(raw, dtype=np.int16)
        start_idx = int(start * freq * frame)
        end_idx = int(end * freq * frame)
        window = arr[start_idx:end_idx]
        slowed = _resample_arr(window, _rate).astype(np.int16).tobytes()

        sound = pygame.mixer.Sound(buffer=slowed)
        channel = pygame.mixer.Channel(_RESERVED_LOOP_KEYS.index("freeze"))
        channel.set_volume(_effective(1.0))
        channel.play(sound, loops=-1)
        _loops["freeze"] = {"channel": channel, "sound": sound, "base": 1.0}
        pygame.mixer.music.stop()
    except (pygame.error, OSError, ValueError, TypeError):
        pass

    _freeze_start = time.time()
    _freeze_pos = pos
    _freeze_path = path
    _freeze_len = track_len
    _freeze_rate = _rate


def end_freeze():
    global _rate
    elapsed = time.time() - _freeze_start
    resume = (_freeze_pos + elapsed * _freeze_rate) % _freeze_len
    _stop_freezing()
    _rate = 1.0

    if pygame.mixer.get_init() and _freeze_path:
        if pygame.mixer.music.get_busy():
            return
        try:
            pygame.mixer.music.load(_freeze_path)
            pygame.mixer.music.set_volume(_effective(_music_base))
            pygame.mixer.music.play(-1, start=resume)
        except pygame.error:
            pass


def _stop_freezing():
    stop_loop("freeze")
    _resample_cache.clear()


def get_master():
    return _master


def is_muted():
    return _muted
