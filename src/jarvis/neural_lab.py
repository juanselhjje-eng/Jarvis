from __future__ import annotations

"""Local neural laboratory for J.A.R.V.I.S.

The lab can train small inspectable MLPs and can also build a persistent visual neural
graph from an explicitly observed screen. The visual graph is a representation of the
current observation, not a claim that an unlabelled screenshot magically trained a model.
"""

import base64
import io
import json
import math
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import numpy as np

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

ROOT = Path(__file__).resolve().parents[2]
LAB_DIR = ROOT / "data" / "neural_lab"


@dataclass
class NeuralSpec:
    name: str
    input_size: int
    hidden_sizes: list[int]
    output_size: int
    learning_rate: float = 0.03
    epochs: int = 250


class MLP:
    """Small dense network with tanh hidden layers and softmax output."""

    def __init__(self, spec: NeuralSpec, seed: int = 7) -> None:
        self.spec = spec
        rng = np.random.default_rng(seed)
        sizes = [spec.input_size, *spec.hidden_sizes, spec.output_size]
        self.weights: list[np.ndarray] = []
        self.biases: list[np.ndarray] = []
        for left, right in zip(sizes, sizes[1:]):
            scale = math.sqrt(2.0 / max(1, left))
            self.weights.append(rng.normal(0.0, scale, (left, right)).astype(np.float32))
            self.biases.append(np.zeros((1, right), dtype=np.float32))

    @staticmethod
    def _softmax(values: np.ndarray) -> np.ndarray:
        shifted = values - values.max(axis=1, keepdims=True)
        exp = np.exp(np.clip(shifted, -60, 60))
        return exp / exp.sum(axis=1, keepdims=True)

    def forward(self, x: np.ndarray) -> tuple[list[np.ndarray], list[np.ndarray]]:
        activations = [x]
        preacts: list[np.ndarray] = []
        current = x
        for index, (weight, bias) in enumerate(zip(self.weights, self.biases)):
            z = current @ weight + bias
            preacts.append(z)
            current = self._softmax(z) if index == len(self.weights) - 1 else np.tanh(z)
            activations.append(current)
        return activations, preacts

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.forward(x)[0][-1]

    def train(self, x: np.ndarray, y: np.ndarray, epochs: int | None = None) -> float:
        epochs = epochs or self.spec.epochs
        final_loss = 0.0
        for _ in range(max(1, epochs)):
            activations, preacts = self.forward(x)
            probs = activations[-1]
            final_loss = float(-np.mean(np.sum(y * np.log(probs + 1e-8), axis=1)))
            grad = (probs - y) / max(1, len(x))
            for layer in range(len(self.weights) - 1, -1, -1):
                weight_before = self.weights[layer].copy()
                self.weights[layer] -= self.spec.learning_rate * (activations[layer].T @ grad)
                self.biases[layer] -= self.spec.learning_rate * grad.sum(axis=0, keepdims=True)
                if layer > 0:
                    grad = (grad @ weight_before.T) * (1.0 - np.tanh(preacts[layer - 1]) ** 2)
        return final_loss

    def accuracy(self, x: np.ndarray, y: np.ndarray) -> float:
        predictions = np.argmax(self.predict(x), axis=1)
        expected = np.argmax(y, axis=1)
        return float(np.mean(predictions == expected))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {"spec": asdict(self.spec), "weights": [w.tolist() for w in self.weights], "biases": [b.tolist() for b in self.biases]}
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class NeuralLab:
    """Factory/trainer for local models and screen-derived neural topology."""

    def __init__(self, root: Path = LAB_DIR) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.last_model: Path | None = None
        self.last_vision_graph: Path | None = None

    @staticmethod
    def _xor_dataset() -> tuple[np.ndarray, np.ndarray]:
        x = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=np.float32)
        labels = np.array([0, 1, 1, 0])
        return x, np.eye(2, dtype=np.float32)[labels]

    def create_and_train(self, name: str = "jarvis_mlp", hidden: Iterable[int] = (8, 8), epochs: int = 350) -> dict[str, object]:
        safe_name = "".join(ch for ch in name if ch.isalnum() or ch in "_- ").strip().replace(" ", "_") or "jarvis_mlp"
        spec = NeuralSpec(safe_name, 2, [int(v) for v in hidden], 2, epochs=max(20, min(int(epochs), 5000)))
        x, y = self._xor_dataset()
        model = MLP(spec)
        loss = model.train(x, y)
        accuracy = model.accuracy(x, y)
        path = self.root / f"{safe_name}_{int(time.time())}.json"
        model.save(path)
        self.last_model = path
        return {"name": safe_name, "architecture": [2, *spec.hidden_sizes, 2], "loss": round(loss, 6), "accuracy": round(accuracy, 4), "path": str(path)}

    def learn_examples(self, examples: list[dict[str, object]], name: str = "custom_mlp") -> dict[str, object]:
        """Train from numeric examples: {input:[...], label:int}."""
        if not examples:
            raise ValueError("No hay ejemplos para aprender.")
        inputs = np.array([item["input"] for item in examples], dtype=np.float32)
        labels = np.array([int(item["label"]) for item in examples], dtype=np.int64)
        if inputs.ndim != 2:
            raise ValueError("Cada ejemplo debe tener una lista numérica de entrada.")
        classes = int(labels.max()) + 1
        if classes < 2:
            raise ValueError("Se necesitan al menos dos clases.")
        y = np.eye(classes, dtype=np.float32)[labels]
        spec = NeuralSpec(name, inputs.shape[1], [max(8, inputs.shape[1] * 2)], classes, 0.03, 300)
        model = MLP(spec)
        loss = model.train(inputs, y)
        path = self.root / f"{name}_{int(time.time())}.json"
        model.save(path)
        self.last_model = path
        return {"name": name, "architecture": [spec.input_size, *spec.hidden_sizes, spec.output_size], "loss": round(loss, 6), "accuracy": round(model.accuracy(inputs, y), 4), "path": str(path)}

    def observe_screen(self, image_base64: str, width: int, height: int, task: str = "") -> dict[str, object]:
        """Build a neural-style graph representing the current visible screen.

        The graph has input, visual-feature, semantic and action nodes. Its feature weights
        are derived from the observed pixels so the topology changes with the screen.
        """
        if not image_base64:
            return {"nodes": 0, "edges": 0, "path": "", "note": "Sin imagen."}
        raw = base64.b64decode(image_base64)
        graph: dict[str, object]
        if Image is not None:
            image = Image.open(io.BytesIO(raw)).convert("RGB")
            small = image.resize((8, 8))
            pixels = np.asarray(small, dtype=np.float32) / 255.0
        else:
            pixels = np.zeros((8, 8, 3), dtype=np.float32)
        luminance = pixels.mean(axis=2)
        nodes: list[dict[str, object]] = []
        edges: list[dict[str, object]] = []

        for i, value in enumerate(luminance.flatten()):
            nodes.append({"id": f"px_{i}", "layer": "INPUT", "activation": round(float(value), 4)})
        for i in range(16):
            row, col = divmod(i, 4)
            patch = luminance[row * 2:row * 2 + 2, col * 2:col * 2 + 2]
            activation = float(patch.mean()) if patch.size else 0.0
            nodes.append({"id": f"vision_{i}", "layer": "VISION", "activation": round(activation, 4)})
            for p in range(row * 2 * 8 + col * 2, row * 2 * 8 + col * 2 + 2):
                edges.append({"from": f"px_{p}", "to": f"vision_{i}", "weight": round(0.5 + float(activation), 4)})
        semantic = ("TEXT", "BUTTON", "INPUT", "WINDOW", "NAVIGATION", "MEDIA", "MENU", "DESKTOP")
        for i, name in enumerate(semantic):
            activation = float(luminance[i % 8:(i % 8) + 1].mean())
            nodes.append({"id": f"semantic_{i}", "layer": "SEMANTIC", "label": name, "activation": round(activation, 4)})
            for v in range(i * 2, i * 2 + 2):
                edges.append({"from": f"vision_{v}", "to": f"semantic_{i}", "weight": round(0.4 + activation, 4)})
        actions = ("MOVE", "CLICK", "TYPE", "SCROLL", "WAIT", "DONE")
        for i, name in enumerate(actions):
            nodes.append({"id": f"action_{i}", "layer": "ACTION", "label": name, "activation": 0.0})
            for s in range(2):
                edges.append({"from": f"semantic_{(i + s) % len(semantic)}", "to": f"action_{i}", "weight": 0.5})

        graph = {
            "version": 1,
            "created_at": int(time.time()),
            "screen": {"width": width, "height": height},
            "task": task[:300],
            "layers": ["INPUT", "VISION", "SEMANTIC", "ACTION"],
            "nodes": nodes,
            "edges": edges,
            "note": "Topología visual generada a partir de una captura explícita; no es entrenamiento supervisado.",
        }
        path = self.root / "vision_network.json"
        path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
        self.last_vision_graph = path
        return {"nodes": len(nodes), "edges": len(edges), "path": str(path), "screen": f"{width}x{height}"}

    def status(self) -> str:
        models = sorted(self.root.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        if not models:
            return "NEURAL LAB: sin modelos locales."
        vision = " + VISIÓN" if (self.root / "vision_network.json").exists() else ""
        return f"NEURAL LAB: {len(models)} artefactos locales{vision}. Último: {models[0].name}"
