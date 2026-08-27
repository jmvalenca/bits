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
    from ots import LPN_1_2_OT, GOT_all_but_one, Naor_Pinkas_1_of_N_OT
    from config import config, config_NP
    params    = config().__dict__
    params_NP = config_NP().__dict__

    # Teste data
    # LPN
    tags = bits([bits(urandom(params['N'])) for _ in range(16)])

    #Naor_Pinkas
    msgs = [bits(urandom(params_NP['msize'])) for _ in range(params_NP['N'])]


@app.class_definition
class Test_OTS(object):
    
    @pytest.mark.skip("not needed")
    def test_one_of_two_OT(self):
        cls = LPN_1_2_OT()
        ot  = cls(*tags)
        b = choice([0,1])
        assert tags[b] == ot.get(b)
        
    @pytest.mark.skip("not needed")
    def test_one_of_N_OT(self):
        cls = Naor_Pinkas_1_of_N_OT()
        ot  = cls(msgs)
        b   = choice(range(len(msgs)))
        assert msgs[b] == ot.get(b)

    #@pytest.mark.skip("not needed")
    def test_got_all_but_one(self):
        cls = GOT_all_but_one()
        ot = cls(msgs)
        b   = choice(range(len(msgs)))
        retrived = ot.get(b)
        assert msgs[b] not in retrived
        assert all([x in msgs for x in retrived])


if __name__ == "__main__":
    app.run()
