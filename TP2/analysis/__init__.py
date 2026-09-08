"""Experiment runner: sweep one GA knob at a time and dump comparable CSVs.

A layer strictly above ``run.py``: it builds config variants, runs them, and
writes their results side by side. Nothing here is imported by ``ga/`` or
``problems/`` - the engine never learns that sweeps exist.
"""
