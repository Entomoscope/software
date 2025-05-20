import tkinter as tk
from tkinter import scrolledtext
from tkinter.font import Font
from tkinter.messagebox import askyesno

from datetime import datetime

from configuration import Configuration

from peripherals.pinout import GNSS_EXI_PIN, GNSS_RESET_PIN
from peripherals.max_m10s import MAXM10S

VERSION = '1.0.0'

TK_WINDOWS_TITLE = 'Entomoscope - GNSS position - v' + VERSION
TK_WINDOW_WIDTH_IN_PX = 700
TK_WINDOW_HEIGHT_IN_PX = 400

REFRESH_UI_INTERVAL_IN_MS = 500

DISPLAY_RAW_DATA = False

class TkInterface(tk.Tk):

    def __init__(self):

        tk.Tk.__init__(self)

        self.title(TK_WINDOWS_TITLE)
        self.geometry(f'{TK_WINDOW_WIDTH_IN_PX}x{TK_WINDOW_HEIGHT_IN_PX}')

        self.font = Font(font='Consolas')
        self.font.config(size=8)

        self.gnss = MAXM10S(i2c_bus=1, i2c_address=0x42, rst_pin=GNSS_RESET_PIN, exi_pin=GNSS_EXI_PIN)

        self.configuration = Configuration()

        self.search = False

        self.protocol("WM_DELETE_WINDOW", self.close_window)

        self.create_widgets()

        self.status_text.set('Ready')

        self.update()

        self.after(REFRESH_UI_INTERVAL_IN_MS, self.refreshUi)

    def close_window(self):

        self.quit()

    def refreshUi(self):

        if self.search:

            self.gnss.get_data()

            if DISPLAY_RAW_DATA:
                self.raw_data_str.set(self.gnss.nav_pvt['raw'])

            self.num_satellites_str.set(f"Number of satellites: {self.gnss.nav_pvt['num_sv']}")

            if self.gnss.nav_pvt['num_sv'] < 4:
                self.num_satellites_validity_str.set('Not enough (min 4)')
            else:
                self.num_satellites_validity_str.set('Enough')

            self.date_str.set(f"Date: {self.gnss.nav_pvt['day']:02d}/{self.gnss.nav_pvt['month']:02d}/{self.gnss.nav_pvt['year']:04d}")

            if self.gnss.nav_pvt['valid'] & 0x01:
                self.date_validity_str.set('Valid')
            else:
                self.date_validity_str.set('Not valid')

            self.time_str.set(f"Time (UTC): {self.gnss.nav_pvt['hour']:02d}:{self.gnss.nav_pvt['minute']:02d}:{self.gnss.nav_pvt['second']:02d}")

            if self.gnss.nav_pvt['valid'] & 0x02:
                self.time_validity_str.set('Valid')
            else:
                self.time_validity_str.set('Not valid')

            self.longitude_str.set(f"Longitude: {self.gnss.nav_pvt['lon']:.6f}")

            self.latitude_str.set(f"Latitude: {self.gnss.nav_pvt['lat']:.6f}")

            self.dop_str.set(f"DOP: {self.gnss.nav_pvt['position_dop']:.2f}")

            if self.gnss.nav_pvt['position_dop'] < 1.0:
                self.dop_validity_str.set('Ideal')
            elif self.gnss.nav_pvt['position_dop'] < 2.0:
                self.dop_validity_str.set('Excellent')
            elif self.gnss.nav_pvt['position_dop'] < 5.0:
                self.dop_validity_str.set('Good')
            elif self.gnss.nav_pvt['position_dop'] < 10.0:
                self.dop_validity_str.set('Moderate')
            elif self.gnss.nav_pvt['position_dop'] < 20.0:
                self.dop_validity_str.set('Fair')
            else:
                self.dop_validity_str.set('Poor')

        # f"{self.nav_pvt['day']:02d}/{self.nav_pvt['month']:02d}/{self.nav_pvt['year']:04d} {self.nav_pvt['hour']:02d}:{self.nav_pvt['minute']:02d}:{self.nav_pvt['second']:02d} [{ self.nav_pvt['valid'] & 0x01} {self.nav_pvt['valid'] & 0x02} {self.nav_pvt['valid'] & 0x04} {self.nav_pvt['valid'] & 0x08}] {self.nav_pvt['fix_type']} {self.nav_pvt['num_sv']} [{self.nav_pvt['lon']} {self.nav_pvt['lat']}] {self.nav_pvt['flag3'] & 0x01}"

        self.after(REFRESH_UI_INTERVAL_IN_MS, self.refreshUi)

    def create_widgets(self):

        # Bottom frame
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=False)

        self.status_text = tk.StringVar()
        self.status_text.set('Initializing...')
        self.status_label = tk.Label(bottom_frame, textvariable=self.status_text, font=self.font, bg='white')
        self.status_label.pack(fill=tk.BOTH, expand=True, pady=(5,0))

        # Left frame
        left_frame = tk.Frame(self)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        mode_label_frame = tk.LabelFrame(left_frame, text='Mode', font=self.font)
        mode_label_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,0))

        self.mode_int = tk.IntVar()
        self.mode_int.set(1)
        radio = tk.Radiobutton(mode_label_frame, text='Automatic', variable=self.mode_int, value=1, command=self.select_mode, font=self.font)
        radio.pack(side=tk.LEFT, fill=tk.X)

        radio = tk.Radiobutton(mode_label_frame, text='Manual', variable=self.mode_int, value=2, command=self.select_mode, font=self.font)
        radio.pack(side=tk.LEFT, fill=tk.X)

        # Automatic mode
        self.auto_label_frame = tk.LabelFrame(left_frame, text='Automatic', font=self.font)
        self.auto_label_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,0))

        self.search_button = tk.Button(self.auto_label_frame, text='Start', command=self.start_gnss, font=self.font)
        self.search_button.pack(side=tk.TOP, pady=(20,0))

        self.raw_data_str = tk.StringVar()
        self.raw_data_str.set('')
        raw_data_label = tk.Label(self.auto_label_frame, textvariable=self.raw_data_str, font=self.font)
        raw_data_label.pack(side=tk.TOP)

        sub_frame = tk.Frame(self.auto_label_frame)
        sub_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        sub_frame.columnconfigure(0, weight=1)
        sub_frame.columnconfigure(1, weight=1)

        self.num_satellites_str = tk.StringVar()
        self.num_satellites_str.set('Number of satellites: 0')
        label = tk.Label(sub_frame, textvariable=self.num_satellites_str, font=self.font)
        label.grid(row=0, column=0, pady=(10,0))

        self.num_satellites_validity_str = tk.StringVar()
        self.num_satellites_validity_str.set('Not enough (min 4)')
        label = tk.Label(sub_frame, textvariable=self.num_satellites_validity_str, font=self.font)
        label.grid(row=0, column=1, pady=(10,0))

        self.date_str = tk.StringVar()
        self.date_str.set('Date: 00/00/0000')
        label = tk.Label(sub_frame, textvariable=self.date_str, font=self.font)
        label.grid(row=1, column=0, pady=(10,0))

        self.date_validity_str = tk.StringVar()
        self.date_validity_str.set('Not valid')
        label = tk.Label(sub_frame, textvariable=self.date_validity_str, font=self.font)
        label.grid(row=1, column=1, pady=(10,0))

        self.time_str = tk.StringVar()
        self.time_str.set('Time (UTC): 00:00:00')
        label = tk.Label(sub_frame, textvariable=self.time_str, font=self.font)
        label.grid(row=2, column=0, pady=(10,0))

        self.time_validity_str = tk.StringVar()
        self.time_validity_str.set('Not valid')
        label = tk.Label(sub_frame, textvariable=self.time_validity_str, font=self.font)
        label.grid(row=2, column=1, pady=(10,0))

        self.longitude_str = tk.StringVar()
        self.longitude_str.set('Longitude:')
        label = tk.Label(sub_frame, textvariable=self.longitude_str, font=self.font)
        label.grid(row=3, column=0, pady=(10,0))

        self.longitude_validity_str = tk.StringVar()
        self.longitude_validity_str.set('Not valid')
        label = tk.Label(sub_frame, textvariable=self.longitude_validity_str, font=self.font)
        label.grid(row=3, column=1, pady=(10,0))

        self.latitude_str = tk.StringVar()
        self.latitude_str.set('Latitude:')
        label = tk.Label(sub_frame, textvariable=self.latitude_str, font=self.font)
        label.grid(row=4, column=0, pady=(10,0))

        self.latitude_validity_str = tk.StringVar()
        self.latitude_validity_str.set('Not valid')
        label = tk.Label(sub_frame, textvariable=self.latitude_validity_str, font=self.font)
        label.grid(row=4, column=1, pady=(10,0))

        self.dop_str = tk.StringVar()
        self.dop_str.set('DOP: 20.0')
        label = tk.Label(sub_frame, textvariable=self.dop_str, font=self.font)
        label.grid(row=5, column=0, pady=(10,0))

        self.dop_validity_str = tk.StringVar()
        self.dop_validity_str.set('Poor')
        label = tk.Label(sub_frame, textvariable=self.dop_validity_str, font=self.font)
        label.grid(row=5, column=1, pady=(10,0))

        self.save_button = tk.Button(self.auto_label_frame, text='Save', command=self.save_auto_gnss_data, state=tk.DISABLED, font=self.font)
        self.save_button.pack(side=tk.TOP, pady=(20,20))

        # Manual mode
        self.manual_label_frame = tk.LabelFrame(left_frame, text='Manual', font=self.font)

        subframe_1 = tk.Frame(self.manual_label_frame)
        subframe_1.pack(side=tk.TOP, fill=tk.X)

        subframe_2 = tk.Frame(self.manual_label_frame)
        subframe_2.pack(side=tk.TOP, fill=tk.X)

        subframe_3 = tk.Frame(self.manual_label_frame)
        subframe_3.pack(side=tk.TOP, fill=tk.X)

        label = tk.Label(subframe_1, text='Latitude:', font=self.font)
        label.pack(side=tk.LEFT, padx=(5,5), pady=(20,0))

        self.latitude_entry = tk.Entry(subframe_1, width=50, font=self.font)
        self.latitude_entry.pack(side=tk.LEFT, padx=(5,5), pady=(20,5))

        label = tk.Label(subframe_2, text='Longitude:', font=self.font)
        label.pack(side=tk.LEFT, padx=(5,5))

        self.longitude_entry = tk.Entry(subframe_2, width=50, font=self.font)
        self.longitude_entry.pack(side=tk.LEFT, padx=(5,5), pady=(0,5))

        button = tk.Button(subframe_3, text='Save', command=self.save_manual_gnss_data, font=self.font)
        button.pack(side=tk.TOP, pady=(20,20))

        # Right frame
        right_frame = tk.Frame(self)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configuration scrolltext
        self.configuration_scolltext = scrolledtext.ScrolledText(right_frame, width=25, font=self.font)
        self.configuration_scolltext.pack(fill=tk.BOTH, expand=True, pady=(5,5), padx=(5,5))
        self.update_configuration_display()


    def select_mode(self):

        if self.mode_int.get() == 1:

            self.auto_label_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,0))
            self.manual_label_frame.pack_forget()

        else:

            self.manual_label_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,0))
            self.auto_label_frame.pack_forget()


    def start_gnss(self):

        self.search = True

        self.search_button.configure(text='Stop', command=self.stop_gnss)

        self.gnss.enable()

        self.gnss.com_start()

        self.save_button.configure(state=tk.DISABLED)

    def stop_gnss(self):

        self.search = False

        self.search_button.configure(text='Start', command=self.start_gnss)

        self.gnss.disable()

        self.gnss.com_stop()

        self.save_button.configure(state=tk.NORMAL)

    def save_auto_gnss_data(self):

        if self.latitude_validity_str.get == 'Valid' and self.longitude_validity_str.get() == 'Valid' and self.time_validity_str.get() == 'Valid' and self.date_validity_str.get() == 'Valid':

            save_data = True

        else:

            save_data = askyesno(title='Confirmation', message="Some GNSS data are not valid.\n\nSave them anyway?")

        if save_data:

            self.configuration.gnss['latitude'] = f"{self.gnss.nav_pvt['lat']:.6f}"
            self.configuration.gnss['longitude'] = f"{self.gnss.nav_pvt['lon']:.6f}"
            self.configuration.gnss['last_update_dop'] = self.gnss.nav_pvt['position_dop']
            self.configuration.gnss['last_update_num_satellites'] = self.gnss.nav_pvt['num_sv']
            self.configuration.gnss['last_update'] = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
            self.configuration.gnss['mode'] = 'auto'

            self.update_configuration()

            self.status_text.set('GNSS data saved')

        else:

            self.status_text.set('GNSS data not saved')

    def save_manual_gnss_data(self):

        try:

            latitude = float(self.latitude_entry.get())
            longitude = float(self.longitude_entry.get())

            self.configuration.gnss['latitude'] = f"{latitude:.6f}"
            self.configuration.gnss['longitude'] = f"{longitude:.6f}"
            self.configuration.gnss['last_update_dop'] = 0.0
            self.configuration.gnss['last_update_num_satellites'] = 0
            self.configuration.gnss['last_update'] = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
            self.configuration.gnss['mode'] = 'manual'

            self.update_configuration()

            self.status_text.set('GNSS data saved')

        except BaseException as e:

            print(e)

            self.status_text.set('Latitude and longitude coordinates must be in decimal degrees notation (e.g. X.XXXXXX)')


    def update_configuration(self):

        self.configuration.save()

        self.configuration.read()

        self.update_configuration_display()

    def update_configuration_display(self):

        configuration = self.configuration.to_string()

        s = configuration.find('Gnss\n')
        e = configuration.find('Images capture\n')

        configuration = configuration[s:e]

        self.configuration_scolltext.configure(state=tk.NORMAL)
        self.configuration_scolltext.delete('0.0', tk.END)
        self.configuration_scolltext.insert(tk.END, configuration)
        self.configuration_scolltext.configure(state=tk.DISABLED)

def main():

    tk_interface = TkInterface()

    tk_interface.mainloop()

if __name__ == '__main__':

    main()
