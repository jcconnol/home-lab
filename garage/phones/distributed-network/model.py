"""A small, explicitly untrained network for verifying real cross-device inference."""
import math


LAYERS = [
    {"weights": [[0.5, -0.2, 0.1, 0.4], [0.2, 0.8, -0.3, 0.1], [-0.4, 0.1, 0.7, 0.2], [0.3, 0.2, 0.1, 0.6]],
     "bias": [0.1, -0.1, 0.2, 0.0], "activation": "relu"},
    {"weights": [[0.3, 0.7, -0.2, 0.1], [-0.4, 0.2, 0.8, 0.5]],
     "bias": [0.05, -0.05], "activation": "linear"},
]


def layer(values, definition):
    if not isinstance(values, list) or not values or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
        raise ValueError("Activations must be finite numbers")
    if definition["activation"] not in ("relu", "linear"):
        raise ValueError("Unsupported activation")
    if len(definition["weights"]) != len(definition["bias"]):
        raise ValueError("Invalid layer dimensions")
    result = []
    for weights, bias in zip(definition["weights"], definition["bias"]):
        if len(weights) != len(values):
            raise ValueError("Input shape mismatch")
        value = sum(w * v for w, v in zip(weights, values)) + bias
        result.append(max(0, value) if definition["activation"] == "relu" else value)
    return result


def infer(values, layers=LAYERS):
    for definition in layers:
        values = layer(values, definition)
    return values
