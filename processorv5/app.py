from argparse import ArgumentParser, Namespace
from tkinter import Tk, Frame, Button, Label, Canvas, Toplevel, filedialog
from threading import Thread

from assembler import Assembler
from processor import Processor

import os
import processor


def parse_command_line_args():
    parser = ArgumentParser('ProcessorV5 Architecture')
    parser.add_argument('-i', action='store_true', dest='interactive', help='Open an interactive window')

    return parser.parse_args()


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

        self.run_button = Button(self.buttons, text='Run')
        self.run_button.grid(row=1, column=0, sticky='ew', padx=5, pady=5)

        self.screen = Canvas(self.root, bg='white', height=320, width=320)
        self.screen.grid(row=0, column=1, padx=5, pady=5)

        self.processor = None
        self.processor_thread = None

        self.root.mainloop()

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

        self.processor = Processor(asm.asserts, self.assert_handle)

    def on_run(self):
        if self.processor is not None:
            self.processor_thread = Thread(target=self.run_processor)
            self.processor_thread.run()

    def run_processor(self):
        pass

    def assert_handle(self):
        raise RuntimeError(processor.create_assert_debug_view(self.processor))





if __name__ == '__main__':
    main(parse_command_line_args())
