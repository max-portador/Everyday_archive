from tkinter import filedialog
from MeteoLoader import MeteoArchiveLoader

save_dir = filedialog.askdirectory()

region = "Приморский край"
start_year = 2020
end_year = 2021

loader = MeteoArchiveLoader(region, 2020, 2021, save_dir)
loader.load_data()

