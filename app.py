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


def append_error(errors: list[dict], line: int, lexeme: str, message: str) -> None:
    candidate = {"line": line, "lexeme": lexeme, "message": message}
    if candidate not in errors:
        errors.append(candidate)


def add_declaration_validation_errors(tokens: list[dict], errors: list[dict]) -> None:
    declaration_keywords = {"int", "float", "char"}
    reserved_keywords = {"int", "float", "char", "if", "else", "while", "for", "return", "void", "main"}
    tokens_by_line: dict[int, list[dict]] = {}

    for token in tokens:
        tokens_by_line.setdefault(token["line"], []).append(token)

    for line_number, line_tokens in tokens_by_line.items():
        if not line_tokens:
            continue

        first_token = line_tokens[0]
        if first_token["type"] != "KEYWORD" or first_token["lexeme"] not in declaration_keywords:
            continue

        if len(line_tokens) < 2:
            continue

        next_token = line_tokens[1]
        is_main_function_signature = (
            next_token["lexeme"] == "main"
            and len(line_tokens) > 2
            and line_tokens[2]["type"] == "PUNCTUATION"
            and line_tokens[2]["lexeme"] == "("
        )

        if next_token["type"] == "KEYWORD" and not is_main_function_signature:
            append_error(
                errors,
                line_number,
                next_token["lexeme"],
                "Invalid variable name. Keywords cannot be used as identifiers.",
            )

        if next_token["type"] == "PUNCTUATION" and next_token["lexeme"] == "(":
            invalid_name = "("
            if len(line_tokens) > 2 and line_tokens[2]["type"] == "IDENTIFIER":
                invalid_name = f"({line_tokens[2]['lexeme']}"

            append_error(
                errors,
                line_number,
                invalid_name,
                "Invalid variable name. Identifiers cannot start with '('.",
            )

        if (
            len(line_tokens) > 3
            and line_tokens[1]["type"] == "IDENTIFIER"
            and line_tokens[2]["type"] == "OPERATOR"
            and line_tokens[2]["lexeme"] == "-"
            and line_tokens[3]["type"] == "IDENTIFIER"
        ):
            append_error(
                errors,
                line_number,
                f"{line_tokens[1]['lexeme']}-{line_tokens[3]['lexeme']}",
                "Invalid variable name. Identifiers cannot contain '-'.",
            )

        if len(line_tokens) > 2 and line_tokens[1]["type"] == "IDENTIFIER" and line_tokens[2]["type"] == "IDENTIFIER":
            append_error(
                errors,
                line_number,
                f"{line_tokens[1]['lexeme']} {line_tokens[2]['lexeme']}",
                "Malformed declaration. Missing operator or punctuation after the variable name.",
            )

        if next_token["type"] == "IDENTIFIER" and next_token["lexeme"] in reserved_keywords:
            append_error(
                errors,
                line_number,
                next_token["lexeme"],
                "Invalid variable name. Keywords cannot be used as identifiers.",
            )


def add_missing_semicolon_errors(tokens: list[dict], errors: list[dict]) -> None:
    tokens_by_line: dict[int, list[dict]] = {}
    existing_error_lines = {error["line"] for error in errors}

    for token in tokens:
        tokens_by_line.setdefault(token["line"], []).append(token)

    declaration_keywords = {"int", "float", "char"}
    control_keywords = {"if", "else", "while", "for"}

    for line_number, line_tokens in tokens_by_line.items():
        if not line_tokens or line_number in existing_error_lines:
            continue

        lexemes = [token["lexeme"] for token in line_tokens]
        first_token = line_tokens[0]
        ends_with_semicolon = ";" in lexemes
        opens_block = "{" in lexemes
        closes_block_only = len(line_tokens) == 1 and lexemes[0] == "}"

        if ends_with_semicolon or opens_block or closes_block_only:
            continue

        should_end_with_semicolon = False

        if first_token["type"] == "KEYWORD" and first_token["lexeme"] in declaration_keywords:
            should_end_with_semicolon = True
        elif first_token["type"] == "KEYWORD" and first_token["lexeme"] == "return":
            should_end_with_semicolon = True
        elif first_token["type"] == "FUNCTION":
            should_end_with_semicolon = True
        elif first_token["type"] == "IDENTIFIER" and "=" in lexemes:
            should_end_with_semicolon = True
        elif first_token["type"] == "KEYWORD" and first_token["lexeme"] in control_keywords:
            should_end_with_semicolon = False

        if should_end_with_semicolon:
            append_error(
                errors,
                line_number,
                "".join(lexemes),
                "Missing semicolon ';' at the end of the statement.",
            )


def add_parenthesis_validation_errors(tokens: list[dict], errors: list[dict]) -> None:
    tokens_by_line: dict[int, list[dict]] = {}

    for token in tokens:
        tokens_by_line.setdefault(token["line"], []).append(token)

    for line_number, line_tokens in tokens_by_line.items():
        if not line_tokens:
            continue

        lexemes = [token["lexeme"] for token in line_tokens]
        open_paren = lexemes.count("(")
        close_paren = lexemes.count(")")

        if open_paren > close_paren:
            append_error(
                errors,
                line_number,
                "".join(lexemes),
                "Missing closing parenthesis ')'.",
            )
        elif close_paren > open_paren:
            append_error(
                errors,
                line_number,
                "".join(lexemes),
                "Unexpected closing parenthesis ')'.",
            )


def add_operator_sequence_errors(tokens: list[dict], errors: list[dict]) -> None:
    tokens_by_line: dict[int, list[dict]] = {}
    operator_types = {"OPERATOR", "RELATIONAL_OP", "LOGICAL_OP"}

    for token in tokens:
        tokens_by_line.setdefault(token["line"], []).append(token)

    for line_number, line_tokens in tokens_by_line.items():
        for current_token, next_token in zip(line_tokens, line_tokens[1:]):
            if current_token["type"] not in operator_types or next_token["type"] not in operator_types:
                continue

            allowed_pairs = {
                ("+", "+"),
                ("-", "-"),
                ("=", "="),
                ("&", "&"),
                ("|", "|"),
            }
            pair = (current_token["lexeme"], next_token["lexeme"])
            if pair in allowed_pairs:
                continue

            append_error(
                errors,
                line_number,
                f"{current_token['lexeme']} {next_token['lexeme']}",
                "Invalid operator sequence.",
            )


def add_brace_validation_errors(tokens: list[dict], errors: list[dict]) -> None:
    balance = 0
    last_line = 1

    for token in tokens:
        last_line = max(last_line, token["line"])
        if token["type"] != "PUNCTUATION":
            continue
        if token["lexeme"] == "{":
            balance += 1
        elif token["lexeme"] == "}":
            if balance == 0:
                append_error(errors, token["line"], "}", "Unexpected closing brace '}'.")
            else:
                balance -= 1

    if balance > 0:
        append_error(errors, last_line, "{", "Missing closing brace '}'.")


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

    add_declaration_validation_errors(tokens, errors)
    add_missing_semicolon_errors(tokens, errors)
    add_parenthesis_validation_errors(tokens, errors)
    add_operator_sequence_errors(tokens, errors)
    add_brace_validation_errors(tokens, errors)

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
