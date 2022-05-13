from typing import Optional, Any
from tkinter import Tk, Frame, Button, Label, Canvas, Toplevel, StringVar, simpledialog, filedialog
from multiprocessing import Process, Pipe
from multiprocessing.connection import Connection
from numpy import int32

from assembler import Assembler
from processor import Processor, ProcessorError, ProcessorEvent, GPU, Device, ImageBuffer
from utils import ConnectionManager, KeyDebouncer

import os
import time
import tkinter
import constants


REFRESH_MS = 10
CLOCK_NS = 20_000_000

DIRECTIVE_SIM_CLOCK_TIME = 'sim_clock_time'

P2C_SCREEN = 'screen'
P2C_STATS = 'stats'
P2C_PRINT = 'print'
P2C_HALT = 'halt'

C2P_KEY = 'key'
C2P_HALT = 'halt'

def main():
    App()


class App:

    def __init__(self):
        self.root = Tk()
        self.root.title('ProcessorV5')
        self.root.protocol("WM_DELETE_WINDOW", self.on_shutdown)

        self.root.rowconfigure(0, minsize=320, weight=1)
        self.root.columnconfigure(0, minsize=60, weight=1)
        self.root.columnconfigure(1, minsize=320, weight=1)

        self.buttons = Frame(self.root)
        self.buttons.grid(row=0, column=0, sticky='ns')

        self.load_button = Button(self.buttons, text='Load', command=self.on_load)
        self.load_button.grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        self.load_last_file: str | None = None

        self.reload_button = Button(self.buttons, text='Reload', command=self.on_reload)
        self.reload_button.grid(row=1, column=0, sticky='ew', padx=5, pady=5)

        self.run_button = Button(self.buttons, text='Run', command=self.on_run)
        self.run_button.grid(row=2, column=0, sticky='ew', padx=5, pady=5)

        self.halt_button = Button(self.buttons, text='Halt', command=self.on_halt)
        self.halt_button.grid(row=3, column=0, sticky='ew', padx=5, pady=5)

        self.info_text = StringVar()
        self.info_text.set('Ready')
        self.info_label = Label(self.buttons, textvariable=self.info_text)
        self.info_label.grid(row=4, column=0, sticky='ew', padx=5, pady=5)

        self.perf_clock_ns = CLOCK_NS
        self.perf_text = StringVar()
        self.perf_text.set(format_frequency(1_000_000_000 / self.perf_clock_ns))
        self.perf_label = Label(self.buttons, textvariable=self.perf_text)
        self.perf_label.grid(row=5, column=0, sticky='ew', padx=5, pady=0)
        self.perf_label.bind('<Button-1>', self.on_perf_text_click)

        self.mem_text = StringVar()
        self.mem_text.set('')
        self.mem_label = Label(self.buttons, textvariable=self.mem_text)
        self.mem_label.grid(row=6, column=0, sticky='ew', padx=5, pady=0)

        self.inst_mem_text = StringVar()
        self.inst_mem_text.set('')
        self.inst_mem_label = Label(self.buttons, textvariable=self.inst_mem_text)
        self.inst_mem_label.grid(row=7, column=0, sticky='ew', padx=5, pady=0)

        self.gpu_mem_text = StringVar()
        self.gpu_mem_text.set('')
        self.gpu_mem_label = Label(self.buttons, textvariable=self.gpu_mem_text)
        self.gpu_mem_label.grid(row=8, column=0, sticky='ew', padx=5, pady=0)

        self.cpi_text = StringVar()
        self.cpi_text.set('')
        self.cpi_label = Label(self.buttons, textvariable=self.cpi_text)
        self.cpi_label.grid(row=8, column=0, sticky='ew', padx=5, pady=0)

        self.canvas = Canvas(self.root, bg='white', height=320, width=320)
        self.canvas.grid(row=0, column=1, padx=5, pady=5)

        self.key_mapping = {
            'Up': constants.CONTROL_PORT_UP,
            'Down': constants.CONTROL_PORT_DOWN,
            'Left': constants.CONTROL_PORT_LEFT,
            'Right': constants.CONTROL_PORT_RIGHT,
            'space': constants.CONTROL_PORT_X
        }
        self.key_states = {i: False for i in self.key_mapping.values()}
        self.key_debouncer = KeyDebouncer(self.on_key_event)
        self.root.bind('<KeyPress>', self.key_debouncer.on_pressed)
        self.root.bind('<KeyRelease>', self.key_debouncer.on_released)

        self.asm: Optional[Assembler] = None
        self.processor_thread: Optional[Process] = None
        self.processor_pipe: ConnectionManager = ConnectionManager()

        self.update_screen(ImageBuffer.empty())
        self.root.after(REFRESH_MS, self.tick)
        self.root.mainloop()

    def tick(self):
        for key, *data in self.processor_pipe.poll():
            if key == P2C_SCREEN:
                buffer, *_ = data
                self.update_screen(buffer)
            elif key == P2C_STATS:
                freq, mem, inst_mem, gpu_mem, cpi, *_ = data
                self.perf_text.set(format_frequency(freq))
                self.mem_text.set(mem)
                self.inst_mem_text.set(inst_mem)
                self.gpu_mem_text.set(gpu_mem)
                self.cpi_text.set('%.2f CPI' % cpi)
            elif key == P2C_PRINT:
                arg, *_ = data
                print(arg)
            elif key == P2C_HALT:
                self.on_halt()

        self.root.after(REFRESH_MS, self.tick)

    def on_load(self):
        if path := filedialog.askopenfilename(
            filetypes=[('Assembly Files', '*.s'), ('All Files', '*.*')],
            initialdir=os.path.join(os.getcwd(), '../')
        ):
            self.load_last_file = path
            self.assemble(path)

    def on_reload(self):
        if self.load_last_file is not None:
            self.assemble(self.load_last_file)
        else:
            self.show_error_modal('No assembly file selected, cannot reload.')

    def on_run(self):
        if self.asm is not None:
            self.update_screen(ImageBuffer.empty())
            proc = Processor(self.asm.code, self.asm.sprites, self.asm.print_table)
            parent, child = Pipe()

            self.processor_pipe.reopen(parent)
            self.processor_thread = Process(target=manage_processor, args=(proc, self.perf_clock_ns, child))
            self.processor_thread.start()
            self.info_text.set('Running')

    def on_perf_text_click(self):
        if self.processor_pipe.closed():
            entry = simpledialog.askstring('ProcessorV5', 'Clock Cycle Time')
            if entry.endswith('ns'):
                self.perf_clock_ns = int(entry[:-2])
            elif entry.endswith('us'):
                self.perf_clock_ns = int(entry[:-2]) * 1_000
            elif entry.endswith('ms'):
                self.perf_clock_ns = int(entry[:-2]) * 1_000_000
            else:
                self.perf_clock_ns = int(entry) * 1_000_000
            self.perf_text.set(format_frequency(1_000_000_000 / self.perf_clock_ns))

    def on_key_event(self, event, pressed: bool):
        if event.keysym in self.key_mapping:
            self.processor_pipe.send(C2P_KEY, self.key_mapping[event.keysym], pressed)

    def on_halt(self):
        self.close_processor_thread()
        self.info_text.set('Loaded' if self.asm is not None else 'Ready')
        self.perf_text.set(format_frequency(1_000_000_000 / self.perf_clock_ns))

    def on_shutdown(self):
        self.close_processor_thread()
        self.root.destroy()

    def assemble(self, path: str):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
        except OSError:
            return self.show_error_modal('Error loading from file: %s' % path)

        asm = Assembler(path, text, enable_assertions=True, enable_print=True)
        if not asm.assemble():
            return self.show_error_modal(asm.error)

        self.asm = asm
        self.info_text.set('Loaded')

        # Accept certain directives from the assembly
        if DIRECTIVE_SIM_CLOCK_TIME in asm.directives:
            self.set_frequency(asm.directives[DIRECTIVE_SIM_CLOCK_TIME])

    def set_frequency(self, value: str):
        if value.endswith('ns'):
            self.perf_clock_ns = int(value[:-2])
        elif value.endswith('us'):
            self.perf_clock_ns = int(value[:-2]) * 1_000
        elif value.endswith('ms'):
            self.perf_clock_ns = int(value[:-2]) * 1_000_000
        else:
            self.perf_clock_ns = int(value) * 1_000_000
        self.perf_text.set(format_frequency(1_000_000_000 / self.perf_clock_ns))

    def update_screen(self, screen: ImageBuffer):
        self.canvas.delete(tkinter.ALL)
        for x in range(constants.SCREEN_WIDTH):
            for y in range(constants.SCREEN_HEIGHT):
                self.canvas.create_rectangle(x * 10, y * 10, x * 10 + 10, y * 10 + 10, fill='white' if screen[x, y] == '#' else 'black')

    def show_error_modal(self, error_text: str):
        error = Toplevel(self.root)
        error.grab_set()

        text = Label(error, text=error_text)
        text.pack()

    def close_processor_thread(self):
        self.processor_pipe.send(C2P_HALT)
        self.processor_thread = None


def format_frequency(hz: float) -> str:
    if hz < 10_000:
        return '%.0f Hz' % hz
    elif hz < 10_000_000:
        return '%.0f kHz' % (hz / 1_000)
    else:
        return '%.0f MHz' % (hz / 1_000_000)


def manage_processor(proc: Processor, period_ns: int, raw: Connection):
    pipe = ConnectionManager(raw)
    keyboard = AppControlDevice()
    proc.devices.append(keyboard)
    proc.event_handle = AppEventHandle(pipe)

    last_ns = tick_ns = time.perf_counter_ns()
    next_ns = last_ns + 1_000_000_000  # report actual frequency every 1s
    ticks = 0
    proc.running = True
    while proc.running:
        try:
            proc.tick()
        except ProcessorError as e:
            print(e)
            print(proc.debug_view())
            pipe.send(P2C_HALT)
            return

        ticks += 1
        tick_ns += period_ns

        for key, *data in pipe.poll():
            if key == C2P_KEY:
                key, data = data
                keyboard.data[key - constants.CONTROL_PORT] = int32(data)
            elif key == C2P_HALT:
                return

        if pipe.closed():
            return

        if time.perf_counter_ns() > next_ns:
            _, mem = proc.memory_utilization()
            _, inst_mem = proc.instruction_memory_utilization()
            _, gpu_mem = proc.gpu_memory_utilization()
            cpi = proc.counter.tick_count / proc.cpi_instruction_count
            pipe.send(P2C_STATS, ticks, mem, inst_mem, gpu_mem, cpi)
            last_ns = time.perf_counter_ns()
            next_ns = last_ns + 1_000_000_000
            ticks = 0

        while time.perf_counter_ns() < tick_ns:
            pass

    pipe.send('halt')


class AppControlDevice(Device):

    def __init__(self):
        self.data = [int32(0)] * constants.CONTROL_PORT_WIDTH

    def reads(self, addr: int32) -> bool: return 0 <= addr - constants.CONTROL_PORT < constants.CONTROL_PORT_WIDTH
    def get(self, addr: int32) -> int32: return self.data[addr - constants.CONTROL_PORT]


class AppEventHandle:

    def __init__(self, pipe: ConnectionManager):
        self.pipe = pipe

    def __call__(self, proc: Processor, event_type: ProcessorEvent, arg: Any):
        if event_type == ProcessorEvent.PRINT:
            self.pipe.send(P2C_PRINT, arg)
        elif event_type == ProcessorEvent.GFLUSH:
            self.pipe.send(P2C_SCREEN, arg)


if __name__ == '__main__':
    main()
