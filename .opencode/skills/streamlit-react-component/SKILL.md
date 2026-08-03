---
name: streamlit-react-component
description: >
  Build custom React components (MUI, Tremor) for Streamlit apps.
  Use when the user wants to replace Streamlit native widgets with React UIs,
  build custom dashboards with Material UI or Tremor components,
  or migrate a Streamlit app to React frontend.
  Triggers on: "streamlit components", "custom component", "react streamlit",
  "MUI streamlit", "Tremor dashboard", "migration react streamlit",
  or when discussing frontend architecture for Streamlit apps.
license: MIT
metadata:
  author: OpenCode Skills
  version: "1.0.0"
  category: frontend
  tags: "streamlit, react, MUI, tremor, custom-components, dashboard"
---

# Streamlit React Custom Component

Build production-grade Streamlit custom React components.

## Architecture

`
repo/
  app.py              # Python backend (thin) — calls component()
  data_layer.py       # Data processing — exports JSON-serializable dicts
  data/               # CSV data files
  frontend/           # React app (Vite + React + MUI/Tremor)
    src/
      App.tsx         # Main React component
      tabs/           # One file per tab
      components/     # Reusable UI components
      hooks/          # Streamlit bridge hooks
    dist/             # Compiled output (committed to repo)
    package.json
    vite.config.ts
`

## Communication Python <-> React

`python
# Python side
my_component = st.components.v2.declare_component(
    "my_dashboard",
    path="frontend/dist"
)
result = my_component(
    data=json_data,
    active_tab=active_tab,
    default={"action": None}
)
# React returns: {"action": "edit_cell", "payload": {...}}
`

## Setup

`ash
# 1. Generate component from template
uvx --from cookiecutter cookiecutter gh:streamlit/component-template --directory cookiecutter/v2

# 2. Install MUI + Tremor
cd frontend
npm install @mui/material @emotion/react @emotion/styled @mui/icons-material
npm install @tremor/react

# 3. Build
npm run build
# -> frontend/dist/ -> commit to repo
`

## Skill Graph

| This Skill | Connects To | Why |
|---|---|---|
| streamlit-react-component | plugin-development | Component wrapper can be packaged as a plugin |

## Key constraints

- **No Node.js on Streamlit Cloud** — must commit compiled dist/
- **Each tab = independent React component** — progressive migration
- **Data flows DOWN (Python -> React), actions flow UP (React -> Python)**
- **Session state** managed in Python, synced to React via args
