"""Check valid values for streamlit Width type used by segmented_control."""
import typing

import streamlit as st

hints = []
for modname in ("streamlit.proto.common_pb2", "streamlit.runtime.metrics_util",
                "streamlit.elements.widgets.segmented_control"):
    try:
        __import__(modname)
    except Exception:
        pass

src = None
try:
    import streamlit.elements.widgets.segmented_control as m
    src = getattr(m, "__file__", None)
    print("module file:", src)
except Exception as exc:
    print("err", exc)

# brute force: look for the Width alias in streamlit typing helpers
import streamlit._typing as tp  # noqa
for name in dir(tp):
    if "Width" in name:
        obj = getattr(tp, name)
        print(name, obj)
        try:
            print("  args:", typing.get_args(obj))
        except Exception:
            pass
