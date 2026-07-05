#!/home/johntynan/.pyenv/versions/3.11.8/bin/python
import requests
import json
import sys
import textwrap
import os

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:1.5b"  # default model

SYSTEM_PROMPT = """
You are a local Python coding assistant running on Linux.
You help with:
- Python scripting
- MIDI parsing and routing
- ALSA and Linux audio/MIDI tools
- Arduino serial communication
- DAW workflows and automation
Respond concisely, with code when useful.
"""

# ---------------------------
# Documentation prompt helpers
# ---------------------------
def generate_general_doc(filename, content):
    return f"Generate clear, structured documentation for the file {filename}:\n\n{content}"

def generate_user_doc(filename, content):
    return f"Write user-facing documentation for {filename}. Explain what it does, how to run it, and typical use cases.\n\nCode:\n{content}"

def generate_dev_doc(filename, content):
    return f"Write developer documentation for {filename}. Include architecture, function explanations, data flow, and extension points.\n\nCode:\n{content}"

# ---------------------------
# Streaming call to Ollama
# ---------------------------
def call_ollama_stream(prompt, history):
    conversation = SYSTEM_PROMPT.strip() + "\n\n"
    for role, content in history:
        if role == "user":
            conversation += f"User: {content}\n"
        elif role == "assistant":
            conversation += f"Assistant: {content}\n"
    conversation += f"User: {prompt}\nAssistant:"

    payload = {
        "model": MODEL,
        "prompt": conversation,
        "stream": True
    }

    try:
        with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=600) as r:
            r.raise_for_status()
            full_response = ""
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line.decode("utf-8"))
                    token = data.get("response", "")
                    full_response += token
                    print(token, end="", flush=True)
                except json.JSONDecodeError:
                    continue
            print()
            return full_response.strip()

    except requests.RequestException as e:
        print(f"[error] Request to Ollama failed: {e}")
        return None

# ---------------------------
# File loading
# ---------------------------
def load_file(path):
    if not os.path.exists(path):
        return f"[error] File not found: {path}"
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception as e:
        return f"[error] Could not read file: {e}"

# ---------------------------
# Project-wide loading
# ---------------------------
def load_project(dirpath):
    if not os.path.isdir(dirpath):
        return f"[error] Directory not found: {dirpath}"

    collected = ""
    for root, dirs, files in os.walk(dirpath):
        for fname in files:
            if fname.endswith(".py"):
                fullpath = os.path.join(root, fname)
                try:
                    with open(fullpath, "r") as f:
                        collected += f"\n\n# FILE: {fullpath}\n" + f.read()
                except Exception as e:
                    collected += f"\n\n# FILE: {fullpath}\n[error reading file: {e}]"
    return collected.strip()

# ---------------------------
# Patch/diff generation
# ---------------------------
def generate_patch(filename, content):
    return (
        f"Generate a unified diff patch for {filename}. "
        f"Only output the patch. Do not explain it.\n\n"
        f"File contents:\n{content}"
    )

# ---------------------------
# Main REPL
# ---------------------------
def main():
    global MODEL

    print(f"Local LLM Terminal Assistant (model: {MODEL})")
    print("Type 'exit' or 'quit' to leave. Ctrl+C also works.\n")

    history = []

    while True:
        try:
            user_input = input(">>> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[bye]")
            break

        if user_input.lower() in ("exit", "quit"):
            print("[bye]")
            break

        if not user_input:
            continue

        # ---------------------------
        # Documentation commands
        # ---------------------------
        if user_input.startswith("/doc "):
            path = user_input.split(" ", 1)[1].strip()
            content = load_file(path)
            if content.startswith("[error]"):
                print(content)
                continue
            prompt = generate_general_doc(path, content)
            history.append(("user", prompt))
            print("\n[thinking...]\n")
            response = call_ollama_stream(prompt, history)
            history.append(("assistant", response))
            continue

        if user_input.startswith("/userdoc "):
            path = user_input.split(" ", 1)[1].strip()
            content = load_file(path)
            if content.startswith("[error]"):
                print(content)
                continue
            prompt = generate_user_doc(path, content)
            history.append(("user", prompt))
            print("\n[thinking...]\n")
            response = call_ollama_stream(prompt, history)
            history.append(("assistant", response))
            continue

        if user_input.startswith("/devdoc "):
            path = user_input.split(" ", 1)[1].strip()
            content = load_file(path)
            if content.startswith("[error]"):
                print(content)
                continue
            prompt = generate_dev_doc(path, content)
            history.append(("user", prompt))
            print("\n[thinking...]\n")
            response = call_ollama_stream(prompt, history)
            history.append(("assistant", response))
            continue

        # ---------------------------
        # Patch/diff generation
        # ---------------------------
        if user_input.startswith("/patch "):
            path = user_input.split(" ", 1)[1].strip()
            content = load_file(path)
            if content.startswith("[error]"):
                print(content)
                continue
            prompt = generate_patch(path, content)
            history.append(("user", prompt))
            print("\n[thinking...]\n")
            response = call_ollama_stream(prompt, history)
            history.append(("assistant", response))
            continue

        # ---------------------------
        # Model switching
        # ---------------------------
        if user_input.startswith("/model "):
            new_model = user_input.split(" ", 1)[1].strip()
            MODEL = new_model
            print(f"[model switched to {MODEL}]")
            continue

        # ---------------------------
        # File loading
        # ---------------------------
        if user_input.startswith("/load "):
            path = user_input.split(" ", 1)[1].strip()
            content = load_file(path)
            if content.startswith("[error]"):
                print(content)
                continue
            history.append(("user", f"Here is the file {path}:\n\n{content}"))
            print(f"[loaded {path} into conversation]")
            continue

        # ---------------------------
        # Project-wide loading
        # ---------------------------
        if user_input.startswith("/load_project "):
            dirpath = user_input.split(" ", 1)[1].strip()
            content = load_project(dirpath)
            if content.startswith("[error]"):
                print(content)
                continue
            history.append(("user", f"Here is the project {dirpath}:\n\n{content}"))
            print(f"[loaded project {dirpath} into conversation]")
            continue

        # ---------------------------
        # Normal LLM prompt (streaming)
        # ---------------------------
        history.append(("user", user_input))
        print("\n[thinking...]\n")
        response = call_ollama_stream(user_input, history)
        history.append(("assistant", response))


if __name__ == "__main__":
    main()

