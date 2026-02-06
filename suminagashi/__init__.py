"""
Suminagashi Marbling Simulator
===============================

A physics-based Japanese ink marbling simulator using Jaffer's
Mathematical Marbling area-preserving transforms.

Each ink drop induces a radial displacement that preserves area:
    P' = C + (P - C) · sqrt(1 + r² / ||P - C||²)

This naturally creates thinning concentric rings as successive drops
push earlier ink outward — matching how real sumi ink spreads on water
via surface tension and Marangoni forces.

References:
    - Lu, Jaffer et al., "Mathematical Marbling", IEEE CG&A 2012
    - Jaffer, "Dropping Paint", people.csail.mit.edu/jaffer/Marbling/
    - Sun et al., "Hydrodynamics of marbling art", Phys Rev Fluids 2024
"""

__version__ = "1.0.0"
__author__ = "Suminagashi Simulator"
