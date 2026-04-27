from dataclasses import dataclass


@dataclass(frozen=True)
class Pricing:
    input: float
    output: float


# Prices in USD, source: https://openai.com/api/pricing/
USD_PER_TOKEN = {
    "o1": Pricing(15e-6, 60e-6),
    "o3-pro": Pricing(20e-6, 80e-6),
    "o3-mini": Pricing(1.1e-6, 4.4e-6),
    "o4-mini": Pricing(1.1e-6, 4.4e-6),
    "gpt-5": Pricing(1.25e-6, 10e-6),
    "gpt-5.1": Pricing(1.25e-6, 10e-6),
    "gpt-5.2": Pricing(1.75e-6, 14e-6),
    "gpt-5.2-codex": Pricing(1.75e-6, 14e-6),
    "gpt-5.3-codex": Pricing(1.75e-6, 14e-6),
    "gpt-5.4-nano": Pricing(0.2e-6, 1.25e-6),
    "gpt-5.4-mini": Pricing(0.75e-6, 4.5e-6),
    "gpt-5.4": Pricing(2.5e-6, 15e-6),
    "gpt-5.4-pro": Pricing(30e-6, 180e-6),
    "gpt-5.5": Pricing(5e-6, 30e-6),
}

KNOWN_MODELS = sorted(USD_PER_TOKEN.keys())

USD_PER_WEB_SEARCH_CALL = 0.01
