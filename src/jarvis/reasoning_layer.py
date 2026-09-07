from __future__ import annotations


class ReasoningLayer:
    """Controla esfuerzo y verificación sin mostrar el razonamiento privado del modelo."""

    def __init__(self, brain) -> None:
        self.brain = brain
        self.effort = "medium"

    def set_effort(self, effort: str) -> str:
        effort = effort.lower().strip()
        if effort not in {"low", "medium", "high"}:
            raise ValueError("El esfuerzo debe ser low, medium o high.")
        self.effort = effort
        return effort

    def answer(self, request: str) -> str:
        if self.effort == "low":
            return self.brain.ask(request)

        draft = self.brain.ask(
            "Resuelve esta solicitud de forma interna. No muestres razonamiento paso a paso; "
            "entrega solo un borrador conciso y verificable. Solicitud: " + request
        )
        if self.effort == "medium":
            return draft

        checked = self.brain.ask(
            "Verifica el siguiente borrador contra la solicitud. Corrige errores o afirmaciones "
            "no verificadas y devuelve únicamente la respuesta final, sin explicar tu cadena de "
            "pensamiento.\nSolicitud: " + request + "\nBorrador: " + draft
        )
        return checked or draft
