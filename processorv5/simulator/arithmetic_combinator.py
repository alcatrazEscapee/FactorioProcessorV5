from typing import Dict, Callable
from enum import IntEnum, auto
from numpy import int32
from simulator import Port, ReadPort, Entity, signals
from utils import AnyValue, AnyInt


class ArithmeticOperation(IntEnum):
    ADD = auto()
    SUBTRACT = auto()
    MULTIPLY = auto()
    DIVIDE = auto()
    MODULO = auto()
    EXPONENT = auto()
    LEFT_SHIFT = auto()
    RIGHT_SHIFT = auto()
    AND = auto()
    OR = auto()
    XOR = auto()


class ArithmeticMode(IntEnum):
    EACH_EACH = auto()  # Modes for operation
    EACH_SINGLE = auto()
    SINGLE_SINGLE = auto()


class ArithmeticCombinator(Entity):

    OPERATIONS: Dict[ArithmeticOperation, Callable[[int32, int32], int32]] = {
        ArithmeticOperation.ADD: lambda x, y: x + y,
        ArithmeticOperation.SUBTRACT: lambda x, y: x - y,
        ArithmeticOperation.MULTIPLY: lambda x, y: x * y,
        ArithmeticOperation.DIVIDE: lambda x, y: x // y,
        ArithmeticOperation.MODULO: lambda x, y: x % y,
        ArithmeticOperation.EXPONENT: lambda x, y: x ** y,
        ArithmeticOperation.LEFT_SHIFT: lambda x, y: x << y,
        ArithmeticOperation.RIGHT_SHIFT: lambda x, y: x >> y,
        ArithmeticOperation.AND: lambda x, y: x & y,
        ArithmeticOperation.OR: lambda x, y: x | y,
        ArithmeticOperation.XOR: lambda x, y: x ^ y
    }

    KEYS: Dict[ArithmeticOperation, str] = {
        ArithmeticOperation.ADD: '+',
        ArithmeticOperation.SUBTRACT: '-',
        ArithmeticOperation.MULTIPLY: '*',
        ArithmeticOperation.DIVIDE: '/',
        ArithmeticOperation.MODULO: '%',
        ArithmeticOperation.EXPONENT: '**',
        ArithmeticOperation.LEFT_SHIFT: '<<',
        ArithmeticOperation.RIGHT_SHIFT: '>>',
        ArithmeticOperation.AND: '&',
        ArithmeticOperation.OR: '|',
        ArithmeticOperation.XOR: '^'
    }

    VALUES: Dict[str, ArithmeticOperation] = {v: k for k, v in KEYS.items()}

    def __init__(self, left: AnyValue, right: AnyValue, out: str, operation: ArithmeticOperation):
        super().__init__()
        self.red_in = ReadPort()
        self.green_in = ReadPort()
        self.red_out = Port()
        self.green_out = Port()

        self.connections = {
            1: {'red': self.red_in, 'green': self.green_in},
            2: {'red': self.red_out, 'green': self.green_out}
        }

        # Signal conditions
        if signals.is_named(left):
            if signals.is_virtual(left):
                if left != signals.EACH:
                    raise TypeError('left signal may be EACH or any single signal, not %s' % left)
                if signals.is_virtual(out):
                    if out != signals.EACH:
                        raise TypeError('output signal may be EACH or any single signal, not %s' % out)
                    # EACH -> EACH
                    self.mode = ArithmeticMode.EACH_EACH
                else:
                    self.mode = ArithmeticMode.EACH_SINGLE
            else:
                # Left is single signal
                if signals.is_virtual(out):
                    raise TypeError('output signal must be single signal if left is single signal, not %s' % out)
                self.mode = ArithmeticMode.SINGLE_SINGLE
            self.left_constant = False
        else:
            left = int32(left)
            self.left_constant = True

        if signals.is_named(right):
            if signals.is_virtual(right):
                raise TypeError('right signal may be single signal or constant, not %s' % right)
            self.right_constant = False
        else:
            right = int32(right)
            self.right_constant = True

        self.left: int32 | str = left
        self.right: int32 | str = right
        self.out: str = out
        self.operator = ArithmeticCombinator.OPERATIONS[operation]

        self.key = '%s := %s %s %s' % (
            out,
            str(left) if self.left_constant else left,
            ArithmeticCombinator.KEYS[operation],
            str(right) if self.right_constant else right
        )

    def tick(self):
        # Compute right value, will be used in both cases
        # Right may be a constant or a signal
        if self.right_constant:
            right_value = self.right
        else:
            right_value = self.green_in[self.right] + self.red_in[self.right]

        if self.mode == ArithmeticMode.SINGLE_SINGLE:
            # Single signal input. Sum input values
            if self.left_constant:
                left_value = self.left
            else:
                left_value = self.green_in[self.left] + self.red_in[self.left]

            # Apply the operation to the left and right signals
            out_value = self.operator(left_value, right_value)

            # Set the output on both channels
            self.red_out[self.out] = out_value
            self.green_out[self.out] = out_value

        else:
            # Each signal input. Sum all inputs into one signal with all values
            all_in_signals: Dict[str, int32] = self.read_in()
            # Only used in the EACH_SINGLE case
            sum_out_value = int32(0)

            for signal_name, signal_value in all_in_signals.items():
                out_value = self.operator(signal_value, right_value)
                if self.mode == ArithmeticMode.EACH_EACH:
                    self.red_out[signal_name] = out_value
                    self.green_out[signal_name] = out_value
                else:
                    sum_out_value += out_value

            if self.mode == ArithmeticMode.EACH_SINGLE:
                # output the sum value to the out channel
                self.red_out[self.out] = sum_out_value
                self.green_out[self.out] = sum_out_value

        # Handled input signals, so clear them
        # Store the current inputs so when viewed, this combinator shows it's full operation
        self.red_in.clear()
        self.green_in.clear()

    def read_in(self) -> Dict[str, int32]:
        return signals.union(self.green_in.signals, self.red_in.signals)

    def set_left(self, value: AnyInt):
        assert self.left_constant, 'Left input is not constant: %s' % self.key
        self.left = int32(value)

    def set_right(self, value: AnyInt):
        assert self.right_constant, 'Right input is not constant: %s' % self.key
        self.right = int32(value)

    def __str__(self) -> str: return repr(self)
    def __repr__(self) -> str: return '[%s <- %s <- %s]' % (self.green_out, self.key, self.read_in())

    def __eq__(self, other): return isinstance(other, ArithmeticCombinator) and self.left == other.left and self.right == other.right and self.out == other.out and self.operator == other.operator
    def __ne__(self, other): return not self.__eq__(other)
