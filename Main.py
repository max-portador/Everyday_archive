import tkinter as tk
from tkinter import filedialog
from MeteoLoader import MeteoArchiveLoader
from MeteoLoaderOneList import MeteoArchiveLoaderOneList

root = tk.Tk()
root.withdraw()
save_dir = filedialog.askdirectory()

print(save_dir)
# region = "Приморский край"
start_year = 2019
end_year = 2021

# loader = MeteoArchiveLoader(None, start_year, end_year, save_dir, [24923, 31371])
loader = MeteoArchiveLoaderOneList(None, start_year, end_year, save_dir, [24923, 31371])
loader.load_data()