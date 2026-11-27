"""Report installed streamlit version and segmented_control signature."""
import inspect

import streamlit as st

print("version:", st.__version__)
print("has segmented_control:", hasattr(st, "segmented_control"))
if hasattr(st, "segmented_control"):
    print("sig:", inspect.signature(st.segmented_control))
print("radio sig:", inspect.signature(st.radio))
