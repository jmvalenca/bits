# /// script
# dependencies = [
#     "galois==0.4.11",
#     "marimo",
#     "numpy==2.5.2",
#     "pytest==9.1.1",
# ]
# requires-python = ">=3.14"
# ///

import marimo

__generated_with = "0.24.0"
app = marimo.App(width="medium", auto_download=["ipynb"])

with app.setup:
    import marimo as mo
    from os import urandom
    from bits import bits
    from vole import POL, VOLE_dv
    from config import config_VOLE
    zero = bits([0])
    one  = bits([255])
    params_VOLE = config_VOLE().__dict__
    n_tags = params_VOLE['n_tags']
    tsize  = params_VOLE['t_size']
    # tests
    import pytest


@app.class_definition
class Test_VOLE(object):
    def test_pol(self):
        p = POL()
        x = bits(urandom(n_tags//8))
        p.c = p.e_value(x)
        r   = p.e_value(x)
        assert r == zero
    
    def test_funcional(self):
        vole_class = VOLE_dv()
        x = bits(urandom(n_tags//8))
        protocol   = vole_class(x)
        assert x == protocol.prover.x
    #
        xx     = x.unpack()
        xtags  = protocol.prover.tags
        d  = protocol.verifier.delta
        qs = protocol.verifier.qs
        assert qs == bits([t + d if b else t  for (b,t) in zip(xx,xtags)])
    #
        p = POL()
        p.c = p.e_value(x)
        A1, A0 = p.a_values(x,xtags)
        B      = p.e_value(qs,d)
        assert B == A1*d + A0


if __name__ == "__main__":
    app.run()
