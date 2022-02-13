from typing import Optional
from argparse import ArgumentParser, Namespace
from tkinter import Tk, Frame, Button, Label, Canvas, Toplevel, PhotoImage, filedialog
from multiprocessing import Process, Pipe
from multiprocessing.connection import Connection
from numpy import int32

from assembler import Assembler
from processor import Processor, GPU, Device, ImageBuffer

import os
import time
import tkinter
import constants


REFRESH_MS = 10
CLOCK_MS = 2


def parse_command_line_args():
    parser = ArgumentParser('ProcessorV5 Architecture')
    parser.add_argument('-i', action='store_true', dest='interactive', help='Open an interactive window')

    return parser.parse_args()


class KeyboardInputDevice(Device):

    def __init__(self):
        self.keys = [int32(0), int32(0)]
        self.mapping = {'up': 0, 'down': 1}  # Key code -> Index

    def owns(self, addr: int32) -> bool: return addr in (3000, 3001)
    def get(self, addr: int32) -> int32: return self.keys[addr - 3000]

    def key_down(self, key):
        if key.char in self.mapping:
            self.keys[self.mapping[key.char]] = int32(1)
        print(key.char, 'down')

    def key_up(self, key):
        if key.char in self.mapping:
            self.keys[self.mapping[key.char]] = int32(0)
        print(key.char, 'up')


def main(args: Namespace):
    App()



class App:

    def __init__(self):
        self.root = Tk()
        self.root.title('ProcessorV5 Interactive')
        self.root.rowconfigure(0, minsize=100, weight=1)
        self.root.columnconfigure(1, minsize=320, weight=1)

        self.buttons = Frame(self.root)
        self.buttons.grid(row=0, column=0, sticky='ns')

        self.load_button = Button(self.buttons, text='Load', command=self.on_load)
        self.load_button.grid(row=0, column=0, sticky='ew', padx=5, pady=5)

        self.run_button = Button(self.buttons, text='Run', command=self.on_run)
        self.run_button.grid(row=1, column=0, sticky='ew', padx=5, pady=5)

        self.canvas = Canvas(self.root, bg='white', height=320, width=320)
        self.canvas.grid(row=0, column=1, padx=5, pady=5)

        self.key_mapping = {38: 0, 40: 1}
        self.keys = [0, 0]
        self.root.bind('<KeyPress>', self.on_key_down)
        self.root.bind('<KeyRelease>', self.on_key_up)

        self.processor = None
        self.processor_thread = None
        self.processor_pipe: Optional[Connection] = None

        self.root.after(REFRESH_MS, self.tick)
        self.root.mainloop()

    def tick(self):
        if self.processor_pipe is not None:
            buffer: Optional[ImageBuffer] = None
            try:
                if self.processor_pipe.poll():
                    buffer = self.processor_pipe.recv()
            except BrokenPipeError:
                self.processor_pipe = None

            if buffer is not None:
                self.update_screen(buffer)

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
        asm = Assembler(text, 'interpreted')
        if not asm.assemble():
            error = Toplevel(self.root)
            error.grab_set()

            text = Label(error, text=asm.error)
            text.pack()
            return

        self.processor = Processor(asm.asserts, asm.sprites)
        self.processor.load(asm.code)

    def on_run(self):
        if self.processor is not None:
            self.update_screen(ImageBuffer.empty())
            parent, child = Pipe()
            self.processor_pipe = parent
            self.processor_thread = Process(target=manage_processor, args=(self.processor, CLOCK_MS, child))
            self.processor_thread.start()
            self.processor = None

    def on_key_down(self, key):
        if key.keycode in self.key_mapping:
            k = self.key_mapping[key.keycode]
            self.keys[k] = 1 - self.keys[k]
            self.communicate((k, int32(self.keys[k])))

    def on_key_up(self, key):
        #if key.keycode in self.key_mapping:
        #    self.communicate((self.key_mapping[key.keycode], int32(0)))
        pass

    def update_screen(self, screen: ImageBuffer):
        self.canvas.delete(tkinter.ALL)
        for x in range(constants.SCREEN_WIDTH):
            for y in range(constants.SCREEN_HEIGHT):
                self.canvas.create_rectangle(x * 10, y * 10, x * 10 + 10, y * 10 + 10, fill='white' if screen[x, y] == '#' else 'black')

    def communicate(self, data):
        print('sending', data)
        if self.processor_pipe is not None:
            try:
                self.processor_pipe.send(data)
            except BrokenPipeError as e:
                print(e)
                self.processor_pipe = None


def manage_processor(proc: Processor, period_ms: int, pipe: Connection):
    proc.gpu = ManagedGPU(proc, pipe)
    keyboard = ManagedKeyboard()
    proc.devices.append(keyboard)
    tick_ns = time.perf_counter_ns()
    period_ns = period_ms * 1_000_000
    proc.running = True
    while proc.running:
        proc.tick()
        tick_ns += period_ns
        while pipe.poll():
            key, data = pipe.recv()
            print('Received', data)
            keyboard.data[key] = data
        while time.perf_counter_ns() < tick_ns:
            pass
    print('Shutdown')


class ManagedGPU(GPU):

    def __init__(self, proc: Processor, pipe: Connection):
        super().__init__(proc)
        self.pipe = pipe

    def flush(self):
        self.pipe.send(self.screen)

class ManagedKeyboard(Device):

    def __init__(self):
        self.data = [int32(0)] * 2

    def owns(self, addr: int32) -> bool: return 3000 <= addr <= 3001
    def get(self, addr: int32) -> int32: return self.data[addr - 3000]



if __name__ == '__main__':
    main(parse_command_line_args())
