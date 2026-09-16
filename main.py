"""Vercel's zero-config Flask detection looks for `app` in main.py at the repo
root. No vercel.json builds/rewrites needed -- Vercel wires every path to it
on its own once the project's framework is set to Flask.
"""
from app import create_app

app = create_app()
