# Token Generation and Error Detection

A Compiler Design course project that performs lexical analysis on C-like source code using **Flex**, processes results with **Python Flask**, and shows tokens and lexical errors in a clean web interface.

## Overview

This project was built to demonstrate the **lexical analysis phase of a compiler** in a practical and interactive way. A user writes or pastes source code into the web interface, clicks **Analyze Code**, and the system:

- sends the source code to the Flask backend
- runs a compiled Flex lexer
- generates tokens with line numbers
- detects lexical errors
- displays tokens, errors, and summary information in the browser

## Features

- Lexical analysis using Flex
- Token generation with line numbers
- Lexical error detection and reporting
- Flask backend with subprocess execution and timeout protection
- Clean web interface using HTML, CSS, and JavaScript
- Token table, error report, and summary cards
- Line numbers in the code editor
- Copy output and download report options

## Tech Stack

- **Lexer:** Flex (`lexer.l`)
- **Backend:** Python Flask
- **Frontend:** HTML, CSS, JavaScript
- **Language Target:** Simplified C-like syntax

## Token Types Supported

The lexer can recognize:

- `KEYWORD`
- `FUNCTION`
- `IDENTIFIER`
- `INTEGER`
- `FLOAT`
- `STRING`
- `CHAR_LITERAL`
- `OPERATOR`
- `RELATIONAL_OP`
- `LOGICAL_OP`
- `PUNCTUATION`
- `COMMENT`
- `ERROR`

## Project Structure

```text
project/
├── app.py
├── lexer.l
├── lexer
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js
├── temp/
│   └── input.c
└── README.md
```

## How It Works

1. The user writes code in the browser editor.
2. The frontend sends the code to the backend using `POST /analyze`.
3. Flask saves the code in a temporary file.
4. Flask runs the compiled lexer executable.
5. The lexer scans the source code and prints tokens/errors.
6. Flask parses the output and returns JSON.
7. The frontend renders:
   - token table
   - error report
   - summary statistics

## Sample Input

```c
int main(){
    int i = 0;
    float b = 8.9;
    x = i * b;
    printf("Hello World");
    return 0;
}
```

## Example Output

```text
1 | KEYWORD | int
1 | KEYWORD | main
1 | PUNCTUATION | (
1 | PUNCTUATION | )
1 | PUNCTUATION | {
2 | KEYWORD | int
2 | IDENTIFIER | i
2 | OPERATOR | =
2 | INTEGER | 0
...
5 | FUNCTION | printf
5 | STRING | "Hello World"
```

## API Endpoint

### `POST /analyze`

Request:

```json
{
  "code": "int main(){ return 0; }"
}
```

Response:

```json
{
  "tokens": [
    { "line": 1, "type": "KEYWORD", "lexeme": "int" }
  ],
  "errors": [],
  "summary": {
    "total_tokens": 1,
    "total_errors": 0
  }
}
```

## Run Locally

### 1. Compile the lexer

If you are using macOS with Homebrew Flex:

```bash
flex lexer.l
cc lex.yy.c -o lexer -I/opt/homebrew/opt/flex/include -L/opt/homebrew/opt/flex/lib -lfl
```

For a standard Linux environment:

```bash
flex lexer.l
cc lex.yy.c -o lexer -lfl
```

### 2. Start the Flask server

```bash
python3 app.py
```

### 3. Open in browser

```text
http://127.0.0.1:5000
```

## Notes

- `printf` is treated as a **function**, not a C keyword.
- Double quotes are used for strings, for example `"Hello World"`.
- Single quotes are used for one character only, for example `'a'`.
- The project performs **lexical analysis only**, not full syntax or semantic analysis.

## Academic Purpose

This project was developed as a **Compiler Design course project** to demonstrate practical implementation of lexical analysis using Flex and integration with a web-based frontend.

## Author

- **Name:** Jahirun Hassan Rimon
- **Course:** Compiler Design

