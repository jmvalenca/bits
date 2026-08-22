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
    from ots import LPN_1_2_OT, LPN_1_of_N_OT, Naor_Pinkas_1_of_N_OT 
    from config import config, config_NP
    params    = config().__dict__
    params_NP = config_NP().__dict__

    tags = bits([bits(urandom(params['N'])) for _ in range(16)])

    #Naor_Pinkas

    msgs = [bits(urandom(params_NP['msize'])) for _ in range(params_NP['N'])]


@app.class_definition
class Test_1_of_2_OTS(object):
    def test_one_of_two_OT(self):
        cls = LPN_1_2_OT()
        ot  = cls(*tags)
        b = choice([0,1])
        assert tags[b] == ot.get(b)


@app.cell
def Test_1_N_OTS(N_1_of_N_OT):
    class Test_1_N_OTS(object):
    #    @pytest.mark.skip(reason="needs debugging")
        def test_one_of_N_OT(self):
            cls = LPN_1_of_N_OT()
            ot  = cls(*tags)
            b   = choice(range(len(tags)))
            assert tags[b] == ot.get(b)
    
        @pytest.mark.skip(reason="needs debugging")
        def test_all_but_one_OT(self):
            cls = N_1_of_N_OT()
            ot  = cls(*tags)
            b   = choice(range(len(tags)))
            xcepts = ot.all_but(b)
            assert np.all(np.isin(xcepts,tags))
            assert not np.all(np.isin(tags[b],xcepts))

    return


@app.cell
def Test_N_OTS(N_1_of_N_noreduct_OT):
    class Test_N_OTS(object):
    #    @pytest.mark.skip(reason="needs debugging")
        def test_one_of_N_noreduc_OT(self):
            cls = Naor_Pinkas_1_of_N_OT()
            ot  = cls(msgs)
            b   = choice(range(len(msgs)))
            assert msgs[b] == ot.get(b)

        @pytest.mark.skip(reason="needs debugging")
        def test_all_but_one_noreduct_OT(self):
            cls = N_1_of_N_noreduct_OT()
            ot  = cls(*tags)
            b   = choice(range(len(tags)))
            xcepts = ot.all_but(b)
            assert np.all(np.isin(xcepts,tags))
            assert not np.all(np.isin(tags[b],xcepts))

    return


if __name__ == "__main__":
    app.run()
