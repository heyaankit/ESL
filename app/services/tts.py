import os
import numpy as np
from onnxruntime import InferenceSession

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODELS_DIR, "model.onnx")
VOICES_DIR = os.path.join(MODELS_DIR, "voices")

VOCAB = {
    ";": 1, ":": 2, ",": 3, ".": 4, "!": 5, "?": 6, "—": 9, "…": 10, '"': 11,
    "(": 12, ")": 13, "“": 14, "”": 15, " ": 16, "\u0303": 17, "ʣ": 18,
    "ʥ": 19, "ʦ": 20, "ʨ": 21, "ᵝ": 22, "\uAB67": 23, "A": 24, "I": 25,
    "O": 31, "Q": 33, "S": 35, "T": 36, "W": 39, "Y": 41, "ᵊ": 42,
    "a": 43, "b": 44, "c": 45, "d": 46, "e": 47, "f": 48, "h": 50,
    "i": 51, "j": 52, "k": 53, "l": 54, "m": 55, "n": 56, "o": 57,
    "p": 58, "q": 59, "r": 60, "s": 61, "t": 62, "u": 63, "v": 64,
    "w": 65, "x": 66, "y": 67, "z": 68, "ɑ": 69, "ɐ": 70, "ɒ": 71,
    "æ": 72, "β": 75, "ɔ": 76, "ɕ": 77, "ç": 78, "ɖ": 80, "ð": 81,
    "ʤ": 82, "ə": 83, "ɚ": 85, "ɛ": 86, "ɜ": 87, "ɟ": 90, "ɡ": 92,
    "ɥ": 99, "ɨ": 101, "ɪ": 102, "ʝ": 103, "ɯ": 110, "ɰ": 111,
    "ŋ": 112, "ɳ": 113, "ɲ": 114, "ɴ": 115, "ø": 116, "ɸ": 118,
    "θ": 119, "œ": 120, "ɹ": 123, "ɾ": 125, "ɻ": 126, "ʁ": 128,
    "ɽ": 129, "ʂ": 130, "ʃ": 131, "ʈ": 132, "ʧ": 133, "ʊ": 135,
    "ʋ": 136, "ʌ": 138, "ɣ": 139, "ɤ": 140, "χ": 142, "ʎ": 143,
    "ʒ": 147, "ʔ": 148, "ˈ": 156, "ˌ": 157, "ː": 158, "ʰ": 162,
    "ʲ": 164, "↓": 169, "→": 171, "↗": 172, "↘": 173, "ᵻ": 177
}

AVAILABLE_VOICES = [
    "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica",
    "af_kore", "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky",
    "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam",
    "am_michael", "am_onyx", "am_puck", "am_santa",
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis"
]

SAMPLE_RATE = 24000
MAX_TOKENS = 510

_sess = None


def _text_to_token_ids(text: str) -> list[int]:
    from misaki.en import G2P
    g2p = G2P()
    result = g2p(text)
    phoneme_str = result[0]
    token_ids = [VOCAB[p] for p in phoneme_str if p in VOCAB]
    if len(token_ids) > MAX_TOKENS:
        token_ids = token_ids[:MAX_TOKENS]
    return token_ids


def _load_voice(voice_name: str, num_tokens: int) -> np.ndarray:
    voice_path = os.path.join(VOICES_DIR, f"{voice_name}.bin")
    if not os.path.exists(voice_path):
        raise ValueError(f"Voice file not found: {voice_path}")
    voices = np.fromfile(voice_path, dtype=np.float32).reshape(-1, 256)
    ref_idx = min(num_tokens, len(voices) - 1)
    return voices[ref_idx:ref_idx + 1]


def _get_session():
    global _sess
    if _sess is None:
        print(f"Loading Kokoro model from {MODEL_PATH}...")
        _sess = InferenceSession(MODEL_PATH)
        print("Kokoro model loaded")
    return _sess


def generate_speech(text: str, voice: str = "af_sarah", speed: float = 1.0) -> tuple[bytes, int]:
    if voice not in AVAILABLE_VOICES:
        raise ValueError(f"Invalid voice '{voice}'. Available: {AVAILABLE_VOICES[:10]}...")

    token_ids = _text_to_token_ids(text)
    if not token_ids:
        raise ValueError("No valid phonemes found in text")

    input_ids = [[0] + token_ids + [0]]
    ref_s = _load_voice(voice, len(token_ids))

    sess = _get_session()
    audio = sess.run(None, dict(
        input_ids=input_ids,
        style=ref_s,
        speed=np.array([speed], dtype=np.float32)
    ))[0]

    audio = audio[0]
    pcm_data = (audio * 32767).astype(np.int16).tobytes()
    return pcm_data, SAMPLE_RATE


def get_voices() -> list[str]:
    return AVAILABLE_VOICES