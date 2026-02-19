# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "galois>=0.4.10",
#     "marimo>=0.19.10",
#     "numpy>=2.4.2",
#     "pyzmq>=27.1.0",
# ]
# ///

import marimo

__generated_with = "0.19.11"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import numpy as np
    from os import urandom
    import config_nb as config
    import bits
    globals().update(config.config().__dict__)


@app.cell
def _(N):
    m0 = bits.bits(urandom(N))
    m1 = bits.bits(urandom(N))
    m0, m1
    return m0, m1


@app.cell
def _(m0, m1):
    OT_cls = bits.one_of_two_bytes_OT()

    ot = OT_cls(m0,m1)
    ot.mess0, ot.mess1
    return (ot,)


@app.cell
def _(ot):
    try:
        print(ot.get(0)) 
    except AssertionError as err:
        print (err)
    try:
        print(ot.get(1)) 
    except AssertionError as err:
        print (err)
    return


if __name__ == "__main__":
    app.run()
