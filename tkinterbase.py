from tkinter import Label, Button, Toplevel, Entry, filedialog, PhotoImage, ttk, colorchooser, Scrollbar
import tkinter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.widgets import SpanSelector
from matplotlib.dates import date2num
import itertools
import datetime
import numpy as np
from annotations import Annotation, save_json
import data
from tkinter import messagebox
import logging


class TkBase:
    id_generator = itertools.count(1)

    def __init__(self, master, path, toolitems):
        logging.basicConfig(filename='event_log.log', level=logging.INFO)
        FIGSIZE = (8, 3)
        self.window_id = next(self.id_generator)
        self.master = master
        self.toolitems = toolitems

        self.master.protocol("WM_DELETE_WINDOW", self.master.quit)
        master.title("BrainWave Visualization")
        master.state('zoomed')
        master.protocol("WM_DELETE_WINDOW", self.root_close)

        self.initialize_annotation_display()

        self.initialize_graph_display(FIGSIZE)

        self.project_path = path
        self.json_path = self.project_path + "annotations.json"
        try:
            self.data, self.timestamps, self.annotations = data.open_project(
                path)
            if self.annotations != []:
                if self.annotations[0] == -1:
                    messagebox.showerror("Error: ", self.annotations[1])
                    self.annotations = []
            self.draw_graph(self.data, self.timestamps, self.annotations)
            for id in self.annotations:
                id = id.id
                self.index_to_ids.append(id)
            for a in self.annotations:
                self.listb.insert(tkinter.END, a.title)
        except Exception as e:
            logging.error('Error during opening initial project')
            logging.error(e)
            messagebox.showerror("Error:", e)

        # put the plot with navbar on the tkinter window
        self.main_canvas.mpl_connect('button_release_event', self.butrelease)

        # add span selector to the axes but set it defaultly to not visible,
        # only activate it when the button annotate is pressed
        self.span = SpanSelector(self.main_graph_ax, self.onselect, 'horizontal', useblit=True,
                                 rectprops=dict(alpha=0.5, facecolor='red'), span_stays=True)
        self.span.set_visible(False)

        # create buttons for interaction
        self.annotate_button = Button(master, command=self.annotate)

        self.export_button = Button(master, command=self.export)

        self.close_button = Button(master, command=master.quit)

        # variables for storing min and max of the current span selection
        self.span_min = None
        self.span_max = None

    def initialize_annotation_display(self):
        """
        initializes the functionalities of the annotation display like the list and the buttons to browse annotations
        """
        logging.info('Initializing annotation display')

        self.id_to_shape = dict()

        self.annotation_frame = tkinter.Frame(self.master, bg="#949494")
        self.annotation_frame.pack(side=tkinter.RIGHT, padx=(10, 10))

        self.listbox_frame = tkinter.Frame(self.annotation_frame, bg="#949494")
        self.listbox_frame.pack()

        # list to convert from indices in listbox to annotation ids
        self.index_to_ids = list()

        self.scrollbar = Scrollbar(self.listbox_frame, orient=tkinter.VERTICAL)
        self.listb = tkinter.Listbox(self.listbox_frame, width=30, height=int(
            0.1 * self.master.winfo_reqheight()), yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.listb.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.listb.bind('<<ListboxSelect>>', self.listbox_selection)
        self.listb.pack(side="bottom", fill="y")

        self.labelTitle = tkinter.Label(self.annotation_frame,
                                        text="Title:", bg="#949494", anchor='w')
        self.labelTitle.pack(side="top")

        self.labelDescription = tkinter.Label(self.annotation_frame,
                                              text="description:",
                                              wraplength=150, bg="#949494", anchor='w')
        self.labelDescription.pack(side="top")

        self.go_to_annotation = ttk.Button(
            self.annotation_frame, text='Go-To', width=30, command=self.goto_callback)
        self.go_to_annotation.pack(side="top")

        self.edit_annotation = ttk.Button(
            self.annotation_frame, text='Edit', width=30, command=self.edit_callback)
        self.edit_annotation.pack(side="top")

        self.delete_annotation = ttk.Button(
            self.annotation_frame, text='Delete', width=30, command=self.delete_callback)
        self.delete_annotation.pack(side="top")

    def initialize_graph_display(self, FIGSIZE):
        """
        initializes the functionalities of the graph display including the main and reference graph
        """

        logging.info('Initializing graph display')

        # create matplotlib figures with single axes on which the data will be
        # displayed
        self.main_graph, self.main_graph_ax = plt.subplots(figsize=FIGSIZE)
        self.main_graph.set_facecolor('xkcd:grey')
        self.main_graph_ax.set_facecolor('xkcd:dark grey')

        # second, reference graph
        self.reference_graph, self.reference_graph_ax = plt.subplots(
            figsize=FIGSIZE)
        self.reference_graph.set_facecolor('xkcd:grey')
        self.reference_graph_ax.set_facecolor('xkcd:dark grey')
        self.main_canvas = FigureCanvasTkAgg(
            self.main_graph, master=self.master)
        self.main_canvas.get_tk_widget().pack(
            side=tkinter.BOTTOM, fill=tkinter.BOTH, expand=1)
        self.toolbar = NavigationToolbar(
            self.main_canvas, self.master, tkbase_=self, toolitems=self.toolitems)

        self.reference_canvas = FigureCanvasTkAgg(
            self.reference_graph, master=self.master)
        self.reference_canvas.get_tk_widget().pack(
            side=tkinter.BOTTOM, fill=tkinter.BOTH, expand=1)

    def open(self):
        """
         callback method for the open button, opens an existing project
        """
        logging.info('Opening file...')
        path = filedialog.askdirectory()
        logging.info('Path given: {}'.format(path))
        self.project_path = path + "/"
        self.json_path = self.project_path + "annotations.json"
        try:
            logging.info('Checking validity of path')
            if data.check_valid_path(path):
                self.data, self.timestamps, self.annotations = data.open_project(
                    self.project_path)
                if self.annotations != []:
                    if self.annotations[0] == -1:
                        messagebox.showerror("Error: ", self.annotations[1])
                        self.annotations = []
                self.draw_graph(self.data, self.timestamps, self.annotations)
                self.index_to_ids = list()
                self.id_to_shape = dict()
                for id in self.annotations:
                    id = id.id
                    self.index_to_ids.append(id)
                self.listb.delete(0, tkinter.END)
                for a in self.annotations:
                    self.listb.insert(tkinter.END, a.title)
                self.span = SpanSelector(self.main_graph_ax, self.onselect, 'horizontal', useblit=True,
                                         rectprops=dict(alpha=0.5, facecolor='red'), span_stays=True)
                self.span.set_visible(False)
                self.span_min = None
                self.span_max = None
            else:
                logging.warning('Invalid path given.')
            logging.info('File open successfully')
        except Exception as e:
            logging.error(e)
            messagebox.showerror("Error:", e)

    def open_concurrent(self):
        """
        callback method for the open concurrent button, opens a new window with a new project identical in functionality to the original application
        """

        logging.info('Opening concurrent window')
        second_toolitems = (
            ('Home', 'Reset original view', 'home', 'home'),
            ('Back', 'Back to previous view', 'back', 'back'),
            ('Forward', 'Forward to next view', 'forward', 'forward'),
            (None, None, None, None),
            ('Pan', 'Pan axes with left mouse, zoom with right', 'move', 'pan'),
            ('Zoom', 'Zoom to rectangle', 'zoom_to_rect', 'zoom'),
            ('Subplots', 'Configure subplots', 'subplots', 'configure_subplots'),
            (None, None, None, None),
            ('Annotate', 'Create an annotation', 'annotate', 'call_annotate'),
            ('Confirm', 'Confirm annotation', 'confirm', 'call_confirm'),
            (None, None, None, None),
            ('Open', 'Opens a new project', 'open', 'call_open'),
            ('Export', 'Export to PDF', 'export', 'call_export'),
            ('Save', 'Save the graph as PNG', 'filesave', 'save_figure'),
            (None, None, None, None),
            ('Quit', 'Quit application', 'quit', 'call_quit'),
        )
        path = filedialog.askdirectory()
        path = path + "/"
        logging.info('Path given: {}'.format(path))
        try:
            logging.info('Checking validity of path')
            if data.check_valid_path(path):
                new_root = Toplevel(self.master)
                new_root.configure(bg='#949494')
                child_gui = TkBase(new_root, path, second_toolitems)
                child_gui.master.protocol(
                    "WM_DELETE_WINDOW", child_gui.child_close)
                child_gui.master.iconbitmap(r'res/general_images/favicon.ico')
            else:
                logging.warning('Invalid path given.')
        except Exception as e:
            logging.error(e)
            raise Exception(e)

    def butrelease(self, event):
        """
        callback method for the annotate button activates the span selector
        """

        # deactivate toolbar functionalities if any are active
        if (self.toolbar._active == 'PAN'):
            self.toolbar.pan()

        if (self.toolbar._active == 'ZOOM'):
            self.toolbar.zoom()

    def export(self):
        """
        callback method for the export button opens a prompt asking for filename in order to save the figure
        """
        def cancel():
            logging.info('Canceling export')
            self.span_min = False
            popup.destroy()
            popup.update()

        def save():
            logging.info('Asking for filename')
            if not export_popup_entry.get().strip():
                logging.info('No filename given')
                error_label = Label(
                    popup, text="Please add a filename!", fg="red")
                error_label.grid(row=1, column=0)
            else:
                filename = self.project_path + export_popup_entry.get() + '.pdf'
                logging.info('Saving figure at {}'.format(filename))
                with PdfPages(filename) as export_pdf:
                    plt.figure(self.window_id * 2 - 1)
                    export_pdf.savefig()
                    plt.figure(self.window_id * 2)
                    export_pdf.savefig()
                logging.info('Export finished')
                cancel()

        logging.info('Exporting graph to pdf')
        popup = Toplevel(self.master)
        popup.title('')
        popup.iconbitmap(r'res/general_images/favicon.ico')
        popup.grab_set()

        export_popup_label = Label(popup, text="Enter desired file name: ")
        export_popup_label.grid(row=0, column=0)

        export_popup_entry = Entry(popup)
        export_popup_entry.grid(row=0, column=1)

        close_export_popup_button = Button(popup, text="Confirm", command=save)
        close_export_popup_button.grid(row=1, column=1)

    def listbox_selection(self, event):
        """
        callback function for the listbox widget
        """
        if(self.listb.curselection()):
            id = self.index_to_ids[self.listb.curselection()[0]]

            for a in self.annotations:
                if a.id == id:

                    self.labelTitle['text'] = "Title: " + a.title
                    self.labelDescription[
                        'text'] = "Description: \n" + a.content

    def goto_callback(self):
        """
        callback for go to annotation button
        """
        if(self.listb.curselection()):
            id = self.index_to_ids[self.listb.curselection()[0]]

            for a in self.annotations:
                if a.id == id:

                    if(a.end != a.start):
                        range = self.get_vertical_range(a)
                        diff = (range[0] - range[1]) / 2
                        delta = (a.end - a.start) / 15
                        self.main_graph_ax.axis(
                            [a.start - delta, a.end + delta, range[1] - diff, range[0] + diff])

                    else:

                        delta = datetime.timedelta(seconds=5)

                        range_indices = np.where(np.logical_and(
                            self.timestamps > a.start - datetime.timedelta(milliseconds=19), self.timestamps < a.end + datetime.timedelta(milliseconds=19)))
                        range_data = self.data[range_indices]
                        ypoint = range_data[np.argmax(range_data)]

                        self.main_graph_ax.axis(
                            [a.start - delta, a.end + delta, ypoint - 30, ypoint + 30])

                    self.main_graph.canvas.toolbar.push_current()
                    self.main_graph.canvas.draw()

    def edit_callback(self):
        """
        callback for edit annotation button
        """
        if(self.listb.curselection()):
            # method called when cancel button on popup is pressed
            def cancel():
                top.destroy()
                top.update()

            # method called when save button on popup is pressed
            def save():

                if not title_entry.get().strip():
                    error_label = Label(
                        top, text="Please add a title!", fg="red")
                    error_label.grid(row=3)
                else:
                    annotation.title = title_entry.get()
                    annotation.content = description_entry.get(
                        1.0, tkinter.END)
                    save_json(self.annotations,
                              self.json_path)
                    self.listb.delete(index)
                    self.listb.insert(index, title_entry.get())
                    cancel()

            index = self.listb.curselection()[0]
            id = self.index_to_ids[self.listb.curselection()[0]]

            annotation = None

            for a in self.annotations:
                if a.id == id:
                    # popup in which you edit the annotation
                    annotation = a
                    top = Toplevel(self.master)
                    top.title('edit annotation')
                    top.grab_set()

                    # labels in top level window showing annotation start time
                    # and end time
                    annotation_start_label = Label(
                        top, text='Annotation start time: ' + str(a.start))
                    annotation_end_label = Label(
                        top, text='Annotation end time: ' + str(a.end))
                    annotation_start_label.grid(row=0)
                    annotation_end_label.grid(row=1)

                    annotation_title_label = Label(top, text='Title')
                    annotation_title_label.grid(row=2)
                    title_entry = Entry(top, font=("Courier", 12))
                    title_entry.insert(tkinter.END, a.title)
                    title_entry.grid(row=4)

                    description_label = Label(top, text='Description')
                    description_label.grid(row=5)
                    description_entry = tkinter.Text(top, height=6, width=30)
                    description_entry.insert(tkinter.END, a.content)
                    description_entry.grid(row=6)

                    cancel_button = Button(
                        master=top, text="Cancel", command=cancel, bg='white')
                    cancel_button.grid(row=8)

                    save_button = Button(
                        master=top, text="Save", command=save, bg='white')
                    save_button.grid(row=7)

                    top.resizable(False, False)
                    top.iconbitmap(r"./res/general_images/favicon.ico")
                    top.protocol("WM_DELETE_WINDOW", cancel)

    def delete_callback(self):
        """
        callback for the delete annotation button
        """
        if(self.listb.curselection()):
            index = self.listb.curselection()[0]
            id = self.index_to_ids[self.listb.curselection()[0]]

            for a in self.annotations:
                if a.id == id:
                    self.index_to_ids.remove(id)
                    self.annotations.remove(a)
                    self.id_to_shape[id].remove()
                    del self.id_to_shape[id]
                    self.main_graph.canvas.draw()
                    save_json(self.annotations,
                              self.json_path)
                    self.listb.delete(index)

    def pick_color(self):
        color = colorchooser.askcolor()
        return color[0]

    def annotate(self):
        """
        callback for the annotate button on the toolbar
        """

        # activate the span selector
        self.span.set_visible(True)

        # deactivate toolbar functionalities if any are active
        if (self.toolbar._active == 'PAN'):
            self.toolbar.pan()

        if (self.toolbar._active == 'ZOOM'):
            self.toolbar.zoom()

        self.annotate_button.config(text='Confirm', command=self.confirm)

    def confirm(self):
        """
        callback method for the annotate button after span is sellected this button
        is pressed to add descriptions to the annotation and confirm selection
        """
        annotation_color = None
        # if something is selected
        if (self.span_min):
            def pick_color():
                nonlocal annotation_color
                annotation_color = self.pick_color()

            # method called when cancel button on popup is pressed
            def cancel():
                self.span_min = False
                top.destroy()
                top.update()

            # method called when save button on popup is pressed
            def save():
                if not title_entry.get().strip():
                    error_label = Label(
                        top, text="Please add a title!", fg="red")
                    error_label.grid(row=3)
                else:
                    nonlocal annotation_color
                    if annotation_color is None:
                        annotation_color = (256, 0, 0)
                    new_annotation = Annotation(title_entry.get(), description_entry.get(1.0, tkinter.END),
                                                self.span_min, self.span_max, annotation_color)
                    self.annotations.append(new_annotation)
                    save_json(self.annotations, self.json_path)
                    self.draw_annotation(new_annotation)
                    self.index_to_ids.append(new_annotation.id)
                    self.listb.insert(tkinter.END, new_annotation.title)

                    # set spans back to none after the annotation is saved to
                    # prevent buggy behavior
                    self.span_min = None
                    self.span_max = None

                    # destroy popup after annotation is saved
                    cancel()

            # create popup where you add text to the annotation
            top = Toplevel(self.master)
            top.title('Confirm Annotation')
            top.grab_set()

            # labels in top level window showing annotation start time and end
            # time
            annotation_start_label = Label(
                top, text='Annotation start time: ' + str(self.span_min))
            annotation_end_label = Label(
                top, text='Annotation end time: ' + str(self.span_max))
            annotation_start_label.grid(row=0)
            annotation_end_label.grid(row=1)

            annotation_title_label = Label(top, text='Title')
            annotation_title_label.grid(row=2)
            title_entry = Entry(top, font=("Courier", 12))
            title_entry.grid(row=4)

            description_label = Label(top, text='Description')
            description_label.grid(row=5)
            description_entry = tkinter.Text(top, height=6, width=30)
            description_entry.grid(row=6)

            save_button = Button(master=top, text="Save",
                                 command=save, bg='white')
            save_button.grid(row=7)

            cancel_button = Button(
                master=top, text="Cancel", command=cancel, bg='white')
            cancel_button.grid(row=8)

            color_button = Button(master=top, text="Choose color",
                                  command=pick_color, bg='white')
            color_button.grid(row=9)

            # change button back to annotate button and hide span selector
            # again
            self.annotate_button.config(text='Annotate', command=self.annotate)
            self.span.set_visible(False)

            # hide the rectangle after confirm button is pressed
            self.span.stay_rect.set_visible(False)
            self.main_canvas.draw()

            top.resizable(False, False)
            top.iconbitmap(r"./res/general_images/favicon.ico")
            top.protocol("WM_DELETE_WINDOW", cancel)

    def onselect(self, min, max):
        """
        callback method of the span selector, after every selection it writes
        the selected range to class variables
        """
        self.span_min = datetime.datetime.fromordinal(
            int(min)) + datetime.timedelta(seconds=divmod(min, 1)[1] * 86400)
        self.span_max = datetime.datetime.fromordinal(
            int(max)) + datetime.timedelta(seconds=divmod(max, 1)[1] * 86400)

    def get_vertical_range(self, annotation):
        """
        get vertical range for a given annotation
        """

        range_indices = np.where(np.logical_and(
            self.timestamps > annotation.start, self.timestamps < annotation.end))

        range_data = self.data[range_indices]
        return range_data[np.argmax(
            range_data)], range_data[np.argmin(range_data)]

    def draw_annotation(self, annotation):
        """
        draws annotation to the main graph as a box if it's a span or a line if it's a point annotation
        """

        # if date range annotation draw rectangle
        annotation_color = annotation.color
        annotation_color = tuple(map(lambda x: x / 256, annotation_color))
        annotation_color = annotation_color + (0.5,)
        if(annotation.start != annotation.end):
            vmax, vmin = self.get_vertical_range(annotation)
            self.id_to_shape[annotation.id] = self.main_graph_ax.add_patch(plt.Rectangle((date2num(annotation.start), vmin - 10),
                                                                                         date2num(annotation.end) - date2num(annotation.start), vmax - vmin + 20, color=annotation_color))
        # if point annotation draw a vertical line
        if(annotation.start == annotation.end):
            plt.figure(self.window_id * 2 - 1)
            self.id_to_shape[annotation.id] = plt.axvline(
                x=date2num(annotation.start), color=annotation_color)
        self.main_graph.canvas.draw()

    def draw_graph(self, data, timestamps, annotations):
        """
        draws the main graph and the referece graph given data, timestamps and annotations
        """
        logging.info('Drawing main graph')
        self.main_graph_ax.clear()
        # plot values on the axe and set plot hue to NHS blue
        self.main_graph_ax.plot(timestamps, data, color='#5436ff')
        # draw all saved annotations
        logging.info('Drawing annotations')
        for annotation in annotations:
            self.draw_annotation(annotation)

        self.main_graph_ax.xaxis_date()
        plt.gcf().autofmt_xdate()
        # adding grid
        self.main_graph_ax.grid(
            color='grey', linestyle='-', linewidth=0.25, alpha=0.5)
        # removing top and right borders
        self.main_graph_ax.spines['top'].set_visible(False)
        self.main_graph_ax.spines['right'].set_visible(False)
        # put the plot with navbar on the tkinter window
        self.main_canvas.draw()
        self.toolbar.update()
        self.main_graph.canvas.toolbar.push_current()

        # second, reference graph displayed
        logging.info('Drawing reference graph')
        self.reference_graph_ax.clear()
        self.reference_graph_ax.plot(
            self.timestamps, self.data, color="cyan", linewidth=1)
        self.reference_graph_ax.xaxis_date()
        # put the second plot on the tkinter window
        self.reference_canvas.draw()

    def root_close(self):
        if messagebox.askokcancel(
                "Close app", "Closing this window will close all windows, are you sure?"):
            self.master.quit()

    def child_close(self):
        self.master.destroy()


class NavigationToolbar(NavigationToolbar2Tk):
    """
    encapsulates all of the graph functionalities in an extension of tk navigation toolbar
    """

    def __init__(self, canvas_, parent_, tkbase_, toolitems):
        self.tkbase_ = tkbase_
        self.parent_ = parent_
        self.toolitems = toolitems
        NavigationToolbar2Tk.__init__(self, canvas_, parent_)

    def _Button(self, text, file, command, extension='.gif'):
        img_file = ("./res/button_images/" + file + extension)
        im = PhotoImage(master=self, file=img_file)
        b = Button(
            master=self, text=text, padx=2, pady=2, image=im, command=command)
        b._ntimage = im
        b.pack(side=tkinter.LEFT)
        return b

    def call_annotate(self):
        self.tkbase_.annotate()

    def call_confirm(self):
        self.tkbase_.confirm()

    def call_open(self):
        self.tkbase_.open()

    def call_open_concurrent(self):
        try:
            self.tkbase_.open_concurrent()
        except Exception as e:
            logging.warning('Open concurrent failed')
            messagebox.showerror("Error:", e)

    def call_export(self):
        self.tkbase_.export()

    def call_quit(self):
        self.tkbase_.root_close()
