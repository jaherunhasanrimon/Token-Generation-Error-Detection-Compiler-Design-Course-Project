from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"
INPUT_FILE = TEMP_DIR / "input.c"
LEXER_BINARY = BASE_DIR / "lexer"
LEXER_TIMEOUT_SECONDS = 5

app = Flask(__name__)


def ensure_temp_dir() -> None:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def parse_lexer_output(output: str) -> dict:
    tokens: list[dict] = []
    errors: list[dict] = []

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        parts = [segment.strip() for segment in line.split("|", maxsplit=2)]
        if len(parts) != 3:
            errors.append(
                {
                    "line": 0,
                    "lexeme": raw_line,
                    "message": "Unable to parse lexer output",
                }
            )
            continue

        line_number, token_type, lexeme = parts
        try:
            parsed_line = int(line_number)
        except ValueError:
            errors.append(
                {
                    "line": 0,
                    "lexeme": raw_line,
                    "message": "Invalid line number received from lexer",
                }
            )
            continue

        if token_type == "ERROR":
            message = "Invalid token"
            if lexeme == "Unterminated comment":
                message = "Unterminated multi-line comment"
            elif lexeme == "Unterminated string":
                message = "Unterminated string literal"
            elif lexeme == "Invalid character literal":
                message = "Invalid character literal. Use single quotes for one character only."
            elif lexeme == "Unterminated character literal":
                message = "Unterminated character literal"

            errors.append(
                {
                    "line": parsed_line,
                    "lexeme": lexeme,
                    "message": message,
                }
            )
        else:
            tokens.append(
                {
                    "line": parsed_line,
                    "type": token_type,
                    "lexeme": lexeme,
                }
            )

    return {
        "tokens": tokens,
        "errors": errors,
        "summary": {
            "total_tokens": len(tokens),
            "total_errors": len(errors),
        },
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    code = payload.get("code", "")

    if not isinstance(code, str):
        return jsonify({"message": "The `code` field must be a string."}), 400

    if not code.strip():
        return jsonify({"message": "Please enter some source code to analyze."}), 400

    if not LEXER_BINARY.exists():
        return (
            jsonify(
                {
                    "message": "Lexer binary not found. Compile it first with `flex lexer.l && cc lex.yy.c -o lexer -lfl`."
                }
            ),
            500,
        )

    ensure_temp_dir()
    INPUT_FILE.write_text(code, encoding="utf-8")

    try:
        completed = subprocess.run(
            [str(LEXER_BINARY), str(INPUT_FILE)],
            capture_output=True,
            text=True,
            timeout=LEXER_TIMEOUT_SECONDS,
            check=False,
            cwd=BASE_DIR,
        )
    except subprocess.TimeoutExpired:
        return jsonify({"message": "Lexer execution timed out after 5 seconds."}), 504
    except OSError as exc:
        return jsonify({"message": f"Failed to run lexer: {exc}"}), 500

    if completed.returncode != 0:
        stderr = completed.stderr.strip() or "Lexer process failed."
        return jsonify({"message": stderr}), 500

    result = parse_lexer_output(completed.stdout)
    result["raw_output"] = completed.stdout
    return jsonify(result)


if __name__ == "__main__":
    ensure_temp_dir()
    if not shutil.which("python3"):
        raise RuntimeError("Python 3 is required to run the Flask app.")
    app.run(debug=True)
