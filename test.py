import marimo

__generated_with = "0.19.11"
app = marimo.App()


@app.cell
def _():
    import bits
    from os   import urandom

    return bits, urandom


@app.cell
def _(bits):
    OT_cls = bits.one_of_two_bytes_OT()
    return (OT_cls,)


@app.cell
def _(bits, urandom):
    m0 = urandom(16)
    m1 = urandom(16)
    print(bits(m0),bits(m1))
    return m0, m1


@app.cell
def _(OT_cls, m0, m1):
    ot = OT_cls(m0,m1)
    ot.mess0, ot.mess1
    return (ot,)


@app.cell
def _(ot):
    ot.get(0)
    return


if __name__ == "__main__":
    app.run()
