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

__generated_with = "0.20.1"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    from os import urandom

    from bits import bits
    from ots import one_of_two_bytes_OT,  one_of_N_OT, N_1_of_N_OT

    import config_nb as config
    globals().update(config.config().__dict__)


@app.cell
def _(N):
    m0 = bits(urandom(N))
    m1 = bits(urandom(N))
    m0, m1
    return m0, m1


@app.cell
def _(m0, m1):
    OT_cls_1_of_2 = one_of_two_bytes_OT()

    ot = OT_cls_1_of_2(m0,m1)
    #ot.mess0, ot.mess1
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


@app.cell
def _(N):
    tags = [bits(urandom(N)) for _ in range(8)]
    print(bits(tags))
    return (tags,)


@app.cell
def _(tags):
    # N-1 out of N
    OT_cls_1 = one_of_N_OT()

    ot_1 = OT_cls_1(*tags)
    print(ot_1.get(1))
    return


@app.cell
def _(tags):
    # N-1 out of N
    OT_cls_2 = N_1_of_N_OT()

    ot_2 = OT_cls_2(*tags)
    all_except = ot_2.all_but(6)
    print(all_except)
    return


if __name__ == "__main__":
    app.run()
