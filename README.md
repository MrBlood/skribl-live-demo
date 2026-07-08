# Skribl Live Demo

Server-backed Flask demo for Skribl Pad.

## Routes

- `/` - editor
- `/skribl-pad` - editor
- `/api/skribls` - create Skribl post
- `/api/skribls/<id>` - fetch Skribl post JSON
- `/s/<id>` - public player

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app.py init-db
flask --app app.py run
```

Open:

```text
http://127.0.0.1:5000/skribl-pad
```

## Deploy

Start command:

```bash
gunicorn app:app
```
