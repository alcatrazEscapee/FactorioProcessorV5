from typing import Dict, Callable
from enum import IntEnum, auto
from numpy import int32
from simulator import Signal, Entity
from utils import AnyValue


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

    def __init__(self, left: AnyValue, right: AnyValue, out: str, operation: ArithmeticOperation):
        super().__init__()
        self.green_in = Signal()
        self.green_out = Signal()
        self.red_in = Signal()
        self.red_out = Signal()

        self.connections = {'1': {'red': self.red_in, 'green': self.green_in}, '2': {'red': self.red_out, 'green': self.green_out}}

        # Signal conditions
        if Signal.is_named(left):
            if Signal.is_virtual(left):
                if left != Signal.EACH:
                    raise TypeError('left signal may be EACH or any single signal, not %s' % left)
                if Signal.is_virtual(out):
                    if out != Signal.EACH:
                        raise TypeError('output signal may be EACH or any single signal, not %s' % out)
                    # EACH -> EACH
                    self.mode = ArithmeticMode.EACH_EACH
                else:
                    self.mode = ArithmeticMode.EACH_SINGLE
            else:
                # Left is single signal
                if Signal.is_virtual(out):
                    raise TypeError('output signal must be single signal if left is single signal, not %s' % out)
                self.mode = ArithmeticMode.SINGLE_SINGLE
            self.left_constant = False
        else:
            left = int32(left)
            self.left_constant = True

        if Signal.is_named(right):
            if Signal.is_virtual(right):
                raise TypeError('right signal may be single signal or constant, not %s' % right)
            self.right_constant = False
        else:
            right = int32(right)
            self.right_constant = True

        self.left = left
        self.right = right
        self.out = out
        self.operator = ArithmeticCombinator.OPERATIONS[operation]

    def tick(self):
        # Initially clear output signals
        self.red_out.clear()
        self.green_out.clear()

        # Compute right value, will be used in both cases
        # Right may be a constant or a signal
        if self.right_constant:
            right_value = self.right
        else:
            right_value = self.green_in.get(self.right) + self.red_in.get(self.right)

        if self.mode == ArithmeticMode.SINGLE_SINGLE:
            # Single signal input. Sum input values
            if self.left_constant:
                left_value = self.left
            else:
                left_value = self.green_in.get(self.left) + self.red_in.get(self.left)

            # Apply the operation to the left and right signals
            out_value = self.operator(left_value, right_value)

            # Set the output on both channels
            self.red_out.set(self.out, out_value)
            self.green_out.set(self.out, out_value)

        else:
            # Each signal input. Sum all inputs into one signal with all values
            all_in_signals: Signal = self.green_in + self.red_in
            # Only used in the EACH_SINGLE case
            sum_out_value = int32(0)

            for signal_name, signal_value in all_in_signals.values.items():
                out_value = self.operator(signal_value, right_value)
                if self.mode == ArithmeticMode.EACH_EACH:
                    self.red_out.set(signal_name, out_value)
                    self.green_out.set(signal_name, out_value)
                else:
                    sum_out_value += out_value

            if self.mode == ArithmeticMode.EACH_SINGLE:
                # output the sum value to the out channel
                self.red_out.set(self.out, sum_out_value)
                self.green_out.set(self.out, sum_out_value)

        # Handled input signals, so clear them
        self.red_in.clear()
        self.green_in.clear()

    def __str__(self):
        return 'Arithmetic: GI = %s, RI = %s, GO = %s, RO = %s' % (str(self.green_in), str(self.red_in), str(self.green_out), str(self.red_out))
