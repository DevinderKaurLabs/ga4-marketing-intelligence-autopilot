"""One client for every model provider. All speak the OpenAI chat API, so switching is a setting.

LLM_PROVIDER = nvidia (free: Mistral, Qwen, Nemotron) | gemini (free) | openrouter | mistral | ollama | fal
"""
import json
import os
import re
import time

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

PROVIDERS = {
    # json_mode: whether to ask for JSON mode by default (some free routes return empty skeletons with it)
    "nvidia": {"base": "https://integrate.api.nvidia.com/v1", "json_mode": False},
    "gemini": {"base": "https://generativelanguage.googleapis.com/v1beta/openai/", "json_mode": True},
    "openrouter": {"base": "https://openrouter.ai/api/v1", "json_mode": False},
    "mistral": {"base": "https://api.mistral.ai/v1", "json_mode": True},
    "ollama": {"base": "http://localhost:11434/v1", "json_mode": True},
    "fal": {"base": "https://fal.run/openrouter/router/openai/v1", "json_mode": False},
}
_client = None


def provider() -> str:
    return os.getenv("LLM_PROVIDER", "gemini").lower()


def settings() -> dict:
    p = PROVIDERS.get(provider(), PROVIDERS["gemini"])
    return {"base": os.getenv("LLM_BASE_URL") or p["base"], "json_mode": p["json_mode"]}


def get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        base = settings()["base"]
        key = os.getenv("LLM_API_KEY") or ("ollama" if "localhost" in base else None)
        if not key:
            raise SystemExit("Set LLM_API_KEY for provider " + provider())
        headers = {"Authorization": f"Key {key}"} if "fal.run" in base else None
        _client = OpenAI(base_url=base, api_key=key, default_headers=headers, max_retries=2, timeout=300)
    return _client


def _create(client, kwargs, waits=(20, 40, 60, 90)):
    """Wait out free-tier rate limits instead of crashing."""
    from openai import RateLimitError

    for wait in list(waits) + [None]:
        try:
            return client.chat.completions.create(**kwargs)
        except RateLimitError:
            if wait is None:
                raise
            print(f"    rate limited by provider, waiting {wait}s and retrying...", flush=True)
            time.sleep(wait)


def chat(model: str, messages: list, json_mode=None, temperature: float = 0.2, max_tokens: int = 8000):
    """Returns (text, usage dict, latency seconds)."""
    client = get_client()
    if json_mode is None:
        json_mode = settings()["json_mode"]
    kwargs = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    started = time.time()
    for _ in range(3):
        try:
            resp = _create(client, kwargs)
            break
        except Exception as exc:
            msg = str(exc).lower()
            if "response_format" in kwargs and ("response_format" in msg or "json" in msg):
                kwargs.pop("response_format")
            elif kwargs["messages"][0]["role"] == "system" and ("instruction" in msg or "system" in msg):
                # Some models (e.g. Gemma on Google's API) reject system prompts: fold it into the user turn
                sys_msg, rest = kwargs["messages"][0], kwargs["messages"][1:]
                first = dict(rest[0])
                first["content"] = sys_msg["content"] + "\n\n" + first["content"]
                kwargs["messages"] = [first] + rest[1:]
            else:
                raise
    else:
        resp = _create(client, kwargs)
    latency = time.time() - started
    usage = getattr(resp, "usage", None)
    choice = resp.choices[0]
    text = choice.message.content or ""
    if not text.strip():
        text = "__EMPTY_OUT_OF_TOKENS__" if getattr(choice, "finish_reason", "") == "length" else "__EMPTY__"
    return (text,
            {"prompt_tokens": getattr(usage, "prompt_tokens", None),
             "completion_tokens": getattr(usage, "completion_tokens", None)},
            latency)


def extract_json(text: str) -> dict:
    if text == "__EMPTY_OUT_OF_TOKENS__":
        raise ValueError("the model used its whole length budget before answering (empty reply)")
    if text == "__EMPTY__":
        raise ValueError("the model returned an empty reply")
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S)
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in the reply: " + text[:120].replace("\n", " "))
    data = json.loads(text[start:end + 1])
    if isinstance(data, dict) and len(data) == 1 and isinstance(next(iter(data.values())), dict):
        data = next(iter(data.values()))  # unwrap {"brief": {...}}
    return data


# ---- helpers for the notebook ----------------------------------------------------------

EXCLUDE = ("image", "tts", "audio", "live", "embedding", "vision", "thinking", "learnlm", "aqa", "veo", "imagen")


def list_model_ids() -> list:
    return sorted(m.id.replace("models/", "") for m in get_client().models.list())


def pick_models(ids: list) -> tuple:
    """Pick a strong free 'flash' model as A and a second one (Gemma, else flash-lite) as B."""
    ok = [i for i in ids if not any(x in i for x in EXCLUDE)]
    if "gemini-flash-latest" in ok:
        a = "gemini-flash-latest"
    else:
        flash = sorted([i for i in ok if "flash" in i and "lite" not in i], reverse=True)
        stable = [i for i in flash if "preview" not in i and "exp" not in i]
        a = (stable or flash or ok or [None])[0]
    gemma = sorted([i for i in ok if "gemma" in i and "it" in i], reverse=True)
    lite = sorted([i for i in ok if "flash-lite" in i], reverse=True)
    b = next((m for m in gemma + lite if m != a), None)
    return a, b


NVIDIA_SKIP = ("embed", "vision", "vl", "reward", "coder", "codestral", "math", "guard", "safety", "retriever",
               "rerank", "parse", "ocr", "audio", "speech", "clip", "nemoguard", "pii", "translate", "vila",
               "detector", "content", "cosmos", "base")


def _pick(ids, must, prefer):
    pool = [i for i in ids if all(m in i.lower() for m in must) and not any(x in i.lower() for x in NVIDIA_SKIP)]
    for word in prefer:
        hits = sorted([i for i in pool if word in i.lower()], reverse=True)
        if hits:
            return hits[0]
    return sorted(pool, reverse=True)[0] if pool else None


def pick_models_nvidia(ids: list) -> list:
    """Mistral, Qwen and NVIDIA Nemotron from the NVIDIA Build catalog."""
    mistral = _pick(ids, ["mistralai/"], ["mistral-medium", "mistral-large", "mistral-small", "mixtral"])
    qwen = _pick(ids, ["qwen/"], ["qwen3.5", "qwen3", "qwen2.5"])
    nemotron = _pick(ids, ["nvidia/", "nemotron"], ["super", "ultra", "70b", "49b", "nano"])
    return [m for m in (mistral, qwen, nemotron) if m]


def pick_models_for(prov: str, ids: list) -> list:
    if prov == "nvidia":
        return pick_models_nvidia(ids)
    return [m for m in pick_models(ids) if m]


def ping(model: str) -> str:
    text, _, latency = chat(model, [{"role": "user", "content": 'Reply with exactly this JSON: {"ok": true}'}],
                            max_tokens=200)
    return f"{text.strip()[:80]}  ({latency:.1f}s)"
