from enum import IntEnum, auto
from typing import Dict, Callable
from numpy import int32
from simulator import Port, ReadPort, Entity, signals
from utils import AnyValue


class DeciderOperation(IntEnum):
    LESS_THAN = auto()
    GREATER_THAN = auto()
    LESS_EQUAL = auto()
    GREATER_EQUAL = auto()
    EQUAL = auto()
    NOT_EQUAL = auto()


class DeciderMode(IntEnum):
    SINGLE_SINGLE = auto()
    SINGLE_EVERYTHING = auto()
    EACH_EACH = auto()
    EACH_SINGLE = auto()
    ANYTHING_EVERYTHING = auto()
    ANYTHING_SINGLE = auto()
    EVERYTHING_EVERYTHING = auto()
    EVERYTHING_SINGLE = auto()


class DeciderCombinator(Entity):

    OPERATIONS: Dict[DeciderOperation, Callable[[int32, int32], bool]] = {
        DeciderOperation.LESS_THAN: lambda x, y: x < y,
        DeciderOperation.GREATER_THAN: lambda x, y: x > y,
        DeciderOperation.LESS_EQUAL: lambda x, y: x <= y,
        DeciderOperation.GREATER_EQUAL: lambda x, y: x >= y,
        DeciderOperation.EQUAL: lambda x, y: x == y,
        DeciderOperation.NOT_EQUAL: lambda x, y: x != y
    }

    KEYS: Dict[DeciderOperation, str] = {
        DeciderOperation.LESS_THAN: '<',
        DeciderOperation.GREATER_THAN: '>',
        DeciderOperation.LESS_EQUAL: '<=',
        DeciderOperation.GREATER_EQUAL: '>=',
        DeciderOperation.EQUAL: '=',
        DeciderOperation.NOT_EQUAL: '!='
    }

    VALUES: Dict[str, DeciderOperation] = {v: k for k, v in KEYS.items()}

    def __init__(self, left: str, right: AnyValue, out: str, operation: DeciderOperation, output_input_count: bool = False):
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
        if left == signals.EACH:
            if signals.is_virtual(out):
                if out != signals.EACH:
                    raise TypeError('output signal may be EACH or single signal if left is EACH, not %s' % out)
                self.mode = DeciderMode.EACH_EACH
            else:
                self.mode = DeciderMode.EACH_SINGLE
        elif left == signals.ANYTHING:
            if signals.is_virtual(out):
                if out != signals.EVERYTHING:
                    raise TypeError('output signal may be EVERYTHING or single signal if left is ANYTHING, not %s' % out)
                self.mode = DeciderMode.ANYTHING_EVERYTHING
            else:
                self.mode = DeciderMode.ANYTHING_SINGLE
        elif left == signals.EVERYTHING:
            if signals.is_virtual(out):
                if out != signals.EVERYTHING:
                    raise TypeError('output signal may be EVERYTHING or single signal if left is EVERYTHING, not %s' % out)
                self.mode = DeciderMode.EVERYTHING_EVERYTHING
            else:
                self.mode = DeciderMode.EVERYTHING_SINGLE
        else:
            # left is single signal, output can be single or everything
            if signals.is_virtual(out):
                if out != signals.EVERYTHING:
                    raise TypeError('output signal may be EVERYTHING or single signal if left is single signal, not %s' % out)
                self.mode = DeciderMode.SINGLE_EVERYTHING
            else:
                self.mode = DeciderMode.SINGLE_SINGLE

        if signals.is_named(right):
            if signals.is_virtual(right):
                raise TypeError('right signal may be single signal or constant, not %s' % right)
            self.right_constant = False
        else:
            right = int32(right)
            self.right_constant = True

        self.left: str = left
        self.right: str | int32 = right
        self.out: str = out
        self.operator = DeciderCombinator.OPERATIONS[operation]
        self.output_input_count = output_input_count

        self.key = '%s%s if %s %s %s' % (
            out,
            '' if self.output_input_count else '=1',
            left,
            DeciderCombinator.KEYS[operation],
            str(right) if self.right_constant else right
        )

    def tick(self):
        # Initially clear output signals
        self.red_out.clear()
        self.green_out.clear()

        # Compute right value, will be used in both cases
        # Right may be a constant or a signal
        if self.right_constant:
            right_value = self.right
        else:
            right_value = self.green_in[self.right] + self.red_in[self.right]

        # All input signals, used for everything output
        all_in_signals: Dict[str, int32] = self.read_in()

        if self.mode == DeciderMode.SINGLE_SINGLE or self.mode == DeciderMode.SINGLE_EVERYTHING:
            # Compare one signal, then either output a single signal or everything
            left_value = self.green_in[self.left] + self.red_in[self.left]
            if self.operator(left_value, right_value):
                # Test pass, so output
                if self.mode == DeciderMode.SINGLE_SINGLE:
                    out_value = self.green_in[self.out] + self.red_in[self.out]
                    self.set_out(self.out, out_value)
                else:
                    for signal_name, signal_value in all_in_signals.items():
                        self.set_out(signal_name, signal_value)

        elif self.mode == DeciderMode.EACH_SINGLE or self.mode == DeciderMode.EACH_EACH:
            # Each signal input. Sum all inputs into one signal with all values
            all_pass_signals: Dict[str, int32] = {}

            # Compare each signal to the condition and determine which pass
            for signal_name, signal_value in all_in_signals.items():
                if self.operator(signal_value, right_value):
                    all_pass_signals[signal_name] = signal_value

            # Output the passed values depending on the settings
            if self.mode == DeciderMode.EACH_SINGLE:
                if self.output_input_count:
                    out_value = sum(v for v in all_pass_signals.values())
                else:
                    out_value = len(all_pass_signals.values())

                # Output to the desired single output channel. Set directly as to skip the `output_input_count` check
                self.red_out[self.out] = out_value
                self.green_out[self.out] = out_value
            else:
                # Output each signal that passed
                for signal_name, signal_value in all_pass_signals.items():
                    self.set_out(signal_name, signal_value)
        else:
            # Compare all signals, looking for either ALL or ANY to pass, based on the condition
            if self.mode == DeciderMode.EVERYTHING_SINGLE or self.mode == DeciderMode.EVERYTHING_EVERYTHING:
                result_value = True
            else:
                result_value = False

            # Iterate through all signals, and accumulate the result in 'result_value'
            for signal_name, signal_value in all_in_signals.items():
                # Only compare non-zero input signals
                if signal_value != 0 and (self.operator(signal_value, right_value) != result_value):
                    result_value = not result_value
                    break

            if result_value:
                # Condition passes, so output according to output mode
                if self.mode == DeciderMode.EVERYTHING_SINGLE or self.mode == DeciderMode.ANYTHING_SINGLE:
                    # single output
                    out_value = self.green_in[self.out] + self.red_in[self.out]
                    self.set_out(self.out, out_value)
                else:
                    # everything output
                    for signal_name, signal_value in all_in_signals.items():
                        self.set_out(signal_name, signal_value)

    def read_in(self) -> Dict[str, int32]:
        return signals.union(self.green_in.signals, self.red_in.signals)

    def set_out(self, signal_name: str, signal_value: int32):
        if not self.output_input_count:
            signal_value = 1
        self.red_out[signal_name] = signal_value
        self.green_out[signal_name] = signal_value

    def __str__(self) -> str: return repr(self)
    def __repr__(self) -> str: return '[%s <- %s <- %s]' % (self.green_out, self.key, self.read_in())

    def __eq__(self, other): return isinstance(other, DeciderCombinator) and self.left == other.left and self.right == other.right and self.out == other.out and self.operator == other.operator and self.output_input_count == other.output_input_count
    def __ne__(self, other): return not self.__eq__(other)
