from __future__ import annotations

"""Local, inspectable neural-network laboratory for J.A.R.V.I.S.

This module deliberately keeps learning separate from the production agent. JARVIS
can generate a small MLP, train it on examples, evaluate it and persist the learned
weights locally. The model cannot rewrite the application code or silently replace
the main agent.
"""

import json
import math
import random
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import numpy as np


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
            self.weights.append((rng.normal(0.0, scale, (left, right))).astype(np.float32))
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
    """Factory/trainer for small local models used as learning experiments."""

    def __init__(self, root: Path = LAB_DIR) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.last_model: Path | None = None

    @staticmethod
    def _xor_dataset() -> tuple[np.ndarray, np.ndarray]:
        x = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=np.float32)
        labels = np.array([0, 1, 1, 0])
        y = np.eye(2, dtype=np.float32)[labels]
        return x, y

    def create_and_train(self, name: str = "jarvis_mlp", hidden: Iterable[int] = (8, 8), epochs: int = 350) -> dict[str, object]:
        """Create and train an example network without modifying JARVIS itself."""
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

    def status(self) -> str:
        models = sorted(self.root.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        if not models:
            return "NEURAL LAB: sin modelos locales."
        return f"NEURAL LAB: {len(models)} modelos locales. Último: {models[0].name}"
