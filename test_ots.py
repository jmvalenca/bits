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
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import pytest
    from os import urandom
    from random import choice
    import numpy as np
    from bits import bits
    from ots import one_of_two_ot, GOT_all_but_one, one_of_all_ot
    from config import config, config_NP
    params    = config().__dict__
    params_NP = config_NP().__dict__

    # Teste data
    # LPN
    tags = bits([bits(urandom(params['N'])) for _ in range(params_NP['N'])])

    #Naor_Pinkas
    msgs = [bits(urandom(params_NP['msize'])) for _ in range(params_NP['N'])]
    messages = set(msgs)


@app.class_definition
class Test_OTS(object):

    #@pytest.mark.skip("not needed")
    def test_one_of_two_OT(self):
        cls = one_of_two_ot()
        ot  = cls(*tags)
        b = choice([0,1])
        assert tags[b] == ot.get(b)
    
    #@pytest.mark.skip("not needed")
    def test_one_of_N_OT(self):
        cls = one_of_all_ot()
        ot  = cls(msgs)
        b   = choice(range(len(msgs)))
        assert msgs[b] == ot.get(b)

    #@pytest.mark.skip("not needed")
    def test_got_all_but_one(self):
        cls = GOT_all_but_one()
        ot = cls(msgs)
        b   = choice(range(len(msgs)))
        retrived = set(ot.get(b))
        assert msgs[b] not in retrived
        assert retrived.issubset(messages)


if __name__ == "__main__":
    app.run()
