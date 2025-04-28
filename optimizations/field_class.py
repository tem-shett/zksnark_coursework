from consts import MOD

class Field:
    def __init__(self, x):
        self.x = int(x) % MOD

    def __add__(self, other):
        if isinstance(other, Field):
            return Field(self.x + other.x)
        return Field(self.x + other)

    def __sub__(self, other):
        if isinstance(other, Field):
            return Field(self.x - other.x)
        return Field(self.x - other)

    def __mul__(self, other):
        if isinstance(other, Field):
            return Field(self.x * other.x)
        return Field(self.x * other)

    def __pow__(self, exponent):
        return Field(pow(self.x, exponent, MOD))

    def __truediv__(self, other):
        if isinstance(other, Field):
            return self * other.inverse()
        return self * Field(other).inverse()

    def inverse(self):
        return self ** (MOD - 2)

    def __eq__(self, other):
        if isinstance(other, Field):
            return self.x == other.x
        return self.x == (other % MOD)

    def __neg__(self):
        return Field(-self.x)

    def __repr__(self):
        return f"Field({self.x})"

    __radd__ = __add__
    __rsub__ = __sub__
    __rmul__ = __mul__
