from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "memory" / "learning.db"
TRAINING_PATH = BASE_DIR / "memory" / "self_training.jsonl"


def _norm(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text).strip().lower())
    return text[:500]


def _fingerprint(text: str) -> str:
    return hashlib.sha256(_norm(text).encode("utf-8")).hexdigest()[:20]


class LearningEngine:
    """Persistent, non-destructive experience memory.

    JARVIS does not retrain the neural model automatically. Instead it learns
    from verified experiences: failures, corrections and successful tool paths.
    Those experiences become retrievable lessons for future tasks.
    """

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self):
        con = sqlite3.connect(self.db_path, timeout=10)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self):
        with self._connect() as con:
            con.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS experiences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created REAL NOT NULL,
                    kind TEXT NOT NULL,
                    task TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    success INTEGER NOT NULL DEFAULT 0,
                    fingerprint TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL UNIQUE,
                    node_type TEXT NOT NULL,
                    hits INTEGER NOT NULL DEFAULT 0,
                    errors INTEGER NOT NULL DEFAULT 0,
                    last_seen REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS edges (
                    source INTEGER NOT NULL,
                    target INTEGER NOT NULL,
                    weight INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY(source, target),
                    FOREIGN KEY(source) REFERENCES nodes(id),
                    FOREIGN KEY(target) REFERENCES nodes(id)
                );
                CREATE INDEX IF NOT EXISTS idx_exp_fp ON experiences(fingerprint);
                CREATE INDEX IF NOT EXISTS idx_exp_created ON experiences(created DESC);
                CREATE TABLE IF NOT EXISTS proactive_state (
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    question TEXT NOT NULL DEFAULT '',
                    created REAL NOT NULL DEFAULT 0
                );
                """
            )

    def _node(self, con, label: str, node_type: str, error: bool = False) -> int:
        label = _norm(label)[:120] or "unknown"
        now = time.time()
        con.execute(
            "INSERT INTO nodes(label,node_type,hits,errors,last_seen) VALUES(?,?,?,?,?) "
            "ON CONFLICT(label) DO UPDATE SET hits=hits+1, errors=errors+excluded.errors, last_seen=excluded.last_seen",
            (label, node_type, 1, 1 if error else 0, now),
        )
        return int(con.execute("SELECT id FROM nodes WHERE label=?", (label,)).fetchone()[0])

    def _connect_nodes(self, con, source: int, target: int):
        con.execute(
            "INSERT INTO edges(source,target,weight) VALUES(?,?,1) "
            "ON CONFLICT(source,target) DO UPDATE SET weight=weight+1",
            (source, target),
        )

    def record(self, task: str, kind: str, detail: str, success: bool = False,
               tool: str | None = None, error: bool = False):
        task = str(task).strip()[:1000]
        detail = str(detail).strip()[:2000]
        if not task:
            return
        with self._lock, self._connect() as con:
            fp = _fingerprint(task + "|" + kind + "|" + detail)
            exists = con.execute("SELECT 1 FROM experiences WHERE fingerprint=? LIMIT 1", (fp,)).fetchone()
            if not exists:
                con.execute(
                    "INSERT INTO experiences(created,kind,task,detail,success,fingerprint) VALUES(?,?,?,?,?,?)",
                    (time.time(), kind, task, detail, int(success), fp),
                )
            task_id = self._node(con, task[:100], "task", error=error)
            if tool:
                tool_id = self._node(con, tool, "tool", error=error)
                self._connect_nodes(con, task_id, tool_id)
            lesson_id = self._node(con, kind, "lesson", error=error)
            self._connect_nodes(con, task_id, lesson_id)

    def record_failure(self, task: str, tool: str, result: str):
        self.record(task, "failure", result, success=False, tool=tool, error=True)

    def record_success(self, task: str, tool: str, result: str):
        self.record(task, "success", result, success=True, tool=tool, error=False)

    def record_recovery(self, task: str, failed_tool: str, error: str,
                       recovery_tool: str, recovery_result: str):
        """Persist a verified recovery so future tasks can reuse the successful route."""
        detail = (
            f"FALLO con {failed_tool}: {str(error)[:900]} | "
            f"RECUPERACIÓN con {recovery_tool}: {str(recovery_result)[:1100]}"
        )
        self.record(task, "recovery", detail, success=True, tool=recovery_tool, error=False)
        with self._lock, self._connect() as con:
            failed_id = self._node(con, failed_tool, "tool", error=True)
            recovery_id = self._node(con, recovery_tool, "tool", error=False)
            self._connect_nodes(con, failed_id, recovery_id)

    def teach(self, task: str, correction: str):
        self.record(task, "correction", correction, success=True, error=False)

    def relevant_lessons(self, task: str, limit: int = 5) -> list[dict[str, Any]]:
        terms = [t for t in re.findall(r"[a-záéíóúñü0-9_]{4,}", _norm(task))[:12]]
        if not terms:
            return []
        clauses = " OR ".join("task LIKE ? OR detail LIKE ?" for _ in terms)
        params: list[Any] = []
        for t in terms:
            params += [f"%{t}%", f"%{t}%"]
        # Global corrections are always eligible learning context.
        global_clause = "(kind='correction' AND task='global')"
        params.append(limit)
        with self._lock, self._connect() as con:
            rows = con.execute(
                f"SELECT kind,task,detail,success,created FROM experiences WHERE ({clauses}) OR {global_clause} ORDER BY created DESC LIMIT ?",
                params,
            ).fetchall()
        return [dict(r) for r in rows]

    def context(self, task: str, limit: int = 5) -> str:
        lessons = self.relevant_lessons(task, limit)
        if not lessons:
            return "No hay experiencias previas relevantes registradas."
        lines = ["EXPERIENCIAS APRENDIDAS (usa esto como memoria, no como verdad absoluta):"]
        for x in lessons:
            status = (
                "CORRECCIÓN" if x["kind"] == "correction"
                else "RECUPERACIÓN" if x["kind"] == "recovery"
                else "ÉXITO" if x["success"] else "ERROR"
            )
            lines.append(f"- [{status}] {x['task']} -> {x['detail']}")
        return "\n".join(lines)

    def record_knowledge_graph(self, topic: str, synthesis: str, confidence: float, sources: list[str], contributions: dict[str, str] | None = None):
        """Store a learned concept as a durable graph, with source and concept links."""
        topic = str(topic).strip()[:300]
        synthesis = str(synthesis).strip()[:2500]
        if not topic or not synthesis:
            return
        confidence = max(0.0, min(1.0, float(confidence)))
        with self._lock, self._connect() as con:
            root = self._node(con, topic, "knowledge", error=False)
            summary = self._node(con, f"knowledge:{topic}", "knowledge_lesson", error=False)
            self._connect_nodes(con, root, summary)
            conf_node = self._node(con, f"confidence:{confidence:.2f}", "confidence", error=False)
            self._connect_nodes(con, root, conf_node)
            for source in sources or []:
                src = self._node(con, str(source), "ai_source", error=False)
                self._connect_nodes(con, src, root)
            for source, contribution in (contributions or {}).items():
                c = self._node(con, f"{source}:{topic}", "ai_contribution", error=False)
                self._connect_nodes(con, c, root)
                if contribution:
                    snippet = self._node(con, str(contribution)[:100], "evidence", error=False)
                    self._connect_nodes(con, c, snippet)
            fp = _fingerprint("knowledge|" + topic + "|" + synthesis)
            if not con.execute("SELECT 1 FROM experiences WHERE fingerprint=? LIMIT 1", (fp,)).fetchone():
                con.execute(
                    "INSERT INTO experiences(created,kind,task,detail,success,fingerprint) VALUES(?,?,?,?,?,?)",
                    (time.time(), "knowledge", topic, f"{synthesis} | CONFIDENCE={confidence:.2f} | SOURCES={', '.join(sources or [])}", 1, fp),
                )

    def record_reflection(self, task: str, result: str, lesson: str, confidence: float = 0.8):
        """Store a verified reflection and append it to the local self-training corpus.

        This is behavioral learning: it changes the persistent context JARVIS uses later.
        It does not pretend to modify Qwen's neural weights.
        """
        lesson = str(lesson).strip()[:1600]
        if not lesson:
            return
        detail = f"OBSERVACIÓN: {str(result)[:900]} | LECCIÓN: {lesson} | CONFIDENCE={max(0.0,min(1.0,float(confidence))):.2f}"
        self.record(task, "reflection", detail, success=True, error=False)
        TRAINING_PATH.parent.mkdir(parents=True, exist_ok=True)
        item = {
            "created": time.time(),
            "task": str(task)[:1000],
            "result": str(result)[:1500],
            "lesson": lesson,
            "confidence": max(0.0, min(1.0, float(confidence))),
        }
        with self._lock:
            with TRAINING_PATH.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    def adaptive_context(self, limit: int = 8) -> str:
        """Return persistent self-learned behavioral lessons for the system prompt."""
        with self._lock, self._connect() as con:
            rows = con.execute(
                "SELECT task,detail,created FROM experiences WHERE kind='reflection' ORDER BY created DESC LIMIT ?",
                (limit,),
            ).fetchall()
        if not rows:
            return "No hay reglas adaptativas aprendidas todavía."
        lines = ["REGLAS ADAPTATIVAS APRENDIDAS (solo usa las que estén respaldadas por experiencias reales):"]
        for r in rows:
            m = re.search(r"CONFIDENCE=([0-9.]+)", str(r['detail']))
            confidence = float(m.group(1)) if m else 1.0
            if confidence >= 0.75:
                lines.append(f"- {r['detail']}")
        return "\n".join(lines) if len(lines) > 1 else "No hay reglas adaptativas de alta confianza todavía."

    def set_proactive_question(self, question: str) -> None:
        question = str(question).strip()[:600]
        with self._lock, self._connect() as con:
            con.execute(
                "INSERT INTO proactive_state(id,question,created) VALUES(1,?,?) "
                "ON CONFLICT(id) DO UPDATE SET question=excluded.question,created=excluded.created",
                (question, time.time()),
            )

    def get_proactive_question(self) -> str:
        with self._lock, self._connect() as con:
            row = con.execute("SELECT question FROM proactive_state WHERE id=1").fetchone()
        return str(row[0]) if row else ""

    def clear_proactive_question(self) -> None:
        with self._lock, self._connect() as con:
            con.execute("DELETE FROM proactive_state WHERE id=1")

    def record_proactive_answer(self, question: str, answer: str) -> None:
        self.record(
            "Pregunta proactiva: " + str(question)[:700],
            "proactive_answer",
            str(answer)[:1500],
            success=True,
            error=False,
        )
        self.clear_proactive_question()

    def recent_proactive_questions(self, limit: int = 10) -> list[str]:
        with self._lock, self._connect() as con:
            rows = con.execute(
                "SELECT task FROM experiences WHERE kind='proactive_answer' ORDER BY created DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [str(r[0]) for r in rows]

    def stats(self) -> dict[str, int]:
        with self._lock, self._connect() as con:
            exp = con.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
            errors = con.execute("SELECT COUNT(*) FROM experiences WHERE success=0").fetchone()[0]
            corrections = con.execute("SELECT COUNT(*) FROM experiences WHERE kind='correction'").fetchone()[0]
            nodes = con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            edges = con.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            successes = con.execute("SELECT COUNT(*) FROM experiences WHERE success=1").fetchone()[0]
        return {"experiences": exp, "errors": errors, "corrections": corrections,
                "nodes": nodes, "edges": edges, "successes": successes}

    def recent(self, limit: int = 12) -> list[dict[str, Any]]:
        with self._lock, self._connect() as con:
            rows = con.execute(
                "SELECT kind,task,detail,success,created FROM experiences ORDER BY created DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def graph(self, limit: int = 34) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        with self._lock, self._connect() as con:
            nodes = [dict(r) for r in con.execute(
                "SELECT id,label,node_type,hits,errors FROM nodes ORDER BY hits DESC,last_seen DESC LIMIT ?", (limit,)
            ).fetchall()]
            ids = {n["id"] for n in nodes}
            edges = [dict(r) for r in con.execute("SELECT source,target,weight FROM edges ORDER BY weight DESC LIMIT 120").fetchall()
                     if r["source"] in ids and r["target"] in ids]
        return nodes, edges


_ENGINE: LearningEngine | None = None


def get_learning_engine() -> LearningEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = LearningEngine()
    return _ENGINE
