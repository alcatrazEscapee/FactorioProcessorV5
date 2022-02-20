from typing import Optional
from tkinter import Tk, Frame, Button, Label, Canvas, Toplevel, StringVar, simpledialog, filedialog
from multiprocessing import Process, Pipe
from multiprocessing.connection import Connection
from numpy import int32

from assembler import Assembler
from processor import Processor, ProcessorError, GPU, Device, ImageBuffer

import os
import time
import tkinter
import constants
import processor


REFRESH_MS = 10
CLOCK_NS = 20_000_000


def main():
    App()


class App:

    def __init__(self):
        self.root = Tk()
        self.root.title('ProcessorV5')
        self.root.rowconfigure(0, minsize=320, weight=1)
        self.root.columnconfigure(0, minsize=60, weight=1)
        self.root.columnconfigure(1, minsize=320, weight=1)
        self.root.protocol("WM_DELETE_WINDOW", self.on_shutdown)

        self.buttons = Frame(self.root)
        self.buttons.grid(row=0, column=0, sticky='ns')

        self.load_button = Button(self.buttons, text='Load', command=self.on_load)
        self.load_button.grid(row=0, column=0, sticky='ew', padx=5, pady=5)

        self.run_button = Button(self.buttons, text='Run', command=self.on_run)
        self.run_button.grid(row=1, column=0, sticky='ew', padx=5, pady=5)

        self.halt_button = Button(self.buttons, text='Halt', command=self.on_halt)
        self.halt_button.grid(row=2, column=0, sticky='ew', padx=5, pady=5)

        self.info_text = StringVar()
        self.info_text.set('Ready')
        self.info_label = Label(self.buttons, textvariable=self.info_text)
        self.info_label.grid(row=3, column=0, sticky='ew', padx=5, pady=5)

        self.perf_clock_ns = CLOCK_NS
        self.perf_text = StringVar()
        self.perf_text.set(format_frequency(1_000_000_000 / self.perf_clock_ns))
        self.perf_label = Label(self.buttons, textvariable=self.perf_text)
        self.perf_label.grid(row=4, column=0, sticky='ew', padx=5, pady=5)
        self.perf_label.bind('<Button-1>', self.on_perf_text_click)

        self.canvas = Canvas(self.root, bg='white', height=320, width=320)
        self.canvas.grid(row=0, column=1, padx=5, pady=5)

        self.key_mapping = {38: 0, 40: 1}
        self.keys = [0, 0]
        self.root.bind('<KeyPress>', self.on_key_down)
        self.root.bind('<KeyRelease>', self.on_key_up)

        self.asm: Optional[Assembler] = None
        self.processor_thread: Optional[Process] = None
        self.processor_pipe: AutoClosingPipe = AutoClosingPipe()

        self.update_screen(ImageBuffer.empty())
        self.root.after(REFRESH_MS, self.tick)
        self.root.mainloop()

    def tick(self):
        for key, *data in self.processor_pipe.poll():
            if key == 'screen':
                buffer, *_ = data
                self.update_screen(buffer)
            elif key == 'perf':
                freq, *_ = data
                self.perf_text.set(format_frequency(freq))
            elif key == 'halt':
                self.on_halt()

        self.root.after(REFRESH_MS, self.tick)

    def on_load(self):
        path = filedialog.askopenfilename(
            filetypes=[('Assembly Files', '*.s'), ('All Files', '*.*')],
            initialdir=os.path.join(os.getcwd(), '../')
        )
        if not path:
            return

        with open(path, 'r', encoding='utf-8') as f:
            text = f.read()

        asm = Assembler(path, text, enable_assertions=True)
        if not asm.assemble():
            error = Toplevel(self.root)
            error.grab_set()

            text = Label(error, text=asm.error)
            text.pack()
            return

        self.asm = asm
        self.info_text.set('Loaded')

    def on_run(self):
        if self.asm is not None:
            self.update_screen(ImageBuffer.empty())
            proc = Processor()
            proc.load(self.asm.code, self.asm.sprites)
            parent, child = Pipe()

            self.processor_pipe.reopen(parent)
            self.processor_thread = Process(target=manage_processor, args=(proc, self.perf_clock_ns, child))
            self.processor_thread.start()
            self.info_text.set('Running')

    def on_perf_text_click(self, event):
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

    def on_key_down(self, key):
        if key.keycode in self.key_mapping:
            k = self.key_mapping[key.keycode]
            self.keys[k] = 1 - self.keys[k]
            self.processor_pipe.send('key', k, int32(self.keys[k]))

    def on_key_up(self, key):
        pass

    def on_halt(self):
        self.close_processor_thread()
        self.info_text.set('Loaded' if self.asm is not None else 'Ready')
        self.perf_text.set(format_frequency(1_000_000_000 / self.perf_clock_ns))

    def on_shutdown(self):
        self.close_processor_thread()
        self.root.destroy()

    def update_screen(self, screen: ImageBuffer):
        self.canvas.delete(tkinter.ALL)
        for x in range(constants.SCREEN_WIDTH):
            for y in range(constants.SCREEN_HEIGHT):
                self.canvas.create_rectangle(x * 10, y * 10, x * 10 + 10, y * 10 + 10, fill='white' if screen[x, y] == '#' else 'black')

    def close_processor_thread(self):
        self.processor_pipe.send('shutdown')
        self.processor_thread = None


def format_frequency(hz: float) -> str:
    if hz < 10_000:
        return '%.0f Hz' % hz
    elif hz < 10_000_000:
        return '%.0f kHz' % (hz / 1_000)
    else:
        return '%.0f MHz' % (hz / 1_000_000)

def debug_exception_handler(proc, e):
    print(processor.debug_view(proc))


def manage_processor(proc: Processor, period_ns: int, raw: Connection):
    pipe = AutoClosingPipe(raw)
    proc.gpu = AppGPU(proc, pipe)
    keyboard = AppControlDevice()
    proc.devices.append(keyboard)
    last_ns = tick_ns = time.perf_counter_ns()
    next_ns = last_ns + 1_000_000_000  # report actual frequency every 1s
    ticks = 0
    proc.running = True
    while proc.running:
        try:
            proc.tick()
        except ProcessorError as e:
            print(e)
            print(processor.debug_view(proc))
            pipe.send('halt')
            return

        ticks += 1
        tick_ns += period_ns

        for key, *data in pipe.poll():
            if key == 'key':
                key, data = data
                keyboard.data[key] = data
            elif key == 'shutdown':
                return

        if pipe.closed():
            return

        if time.perf_counter_ns() > next_ns:
            pipe.send('perf', ticks)
            last_ns = time.perf_counter_ns()
            next_ns = last_ns + 1_000_000_000
            ticks = 0

        while time.perf_counter_ns() < tick_ns:
            pass

    pipe.send('halt')


class AutoClosingPipe:
    def __init__(self, pipe: Optional[Connection] = None):
        self.pipe: Optional[Connection] = pipe

    def closed(self) -> bool:
        return self.pipe is None

    def reopen(self, pipe: Connection):
        self.pipe = pipe

    def send(self, key: str, *data):
        if self.pipe is not None:
            try:
                self.pipe.send((key, *data))
            except BrokenPipeError:
                self.pipe = None

    def poll(self):
        try:
            while self.pipe is not None and self.pipe.poll():
                yield self.pipe.recv()
        except BrokenPipeError:
            self.pipe = None


class AppGPU(GPU):

    def __init__(self, proc: Processor, pipe: AutoClosingPipe):
        super().__init__(proc)
        self.pipe = pipe

    def flush(self):
        self.pipe.send('screen', self.screen)


class AppControlDevice(Device):

    def __init__(self):
        self.data = [int32(0)] * 2

    def owns(self, addr: int32) -> bool: return constants.CONTROL_PORT <= addr < constants.CONTROL_PORT + 2
    def get(self, addr: int32) -> int32: return self.data[addr - constants.CONTROL_PORT]


if __name__ == '__main__':
    main()
