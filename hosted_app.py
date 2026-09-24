"""Hosted demo: each browser session gets an isolated, temporary database."""
import runpy
from pathlib import Path
from tempfile import TemporaryDirectory
import streamlit as st

if 'hosted_workspace' not in st.session_state:
    st.session_state.hosted_workspace = TemporaryDirectory(prefix='gtm-demo-')
st.session_state.router_db = str(Path(st.session_state.hosted_workspace.name) / 'router.db')
st.session_state.hosted_demo = True
runpy.run_path(str(Path(__file__).with_name('app.py')), run_name='__main__')
