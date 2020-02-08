# modules
import os

# helper to create updated assets
def file_updated(file_name: str = "", updates: dict = {}):
    # read in the original file
    with open(file_name, "r") as f:
        filedata = f.read()
    # replace each key found with its value
    for key, value in updates.items():
        if value != "":
            filedata = filedata.replace(key, value)
    # save temp version of the file
    with open(f"{file_name}.asset", "w") as f:
        f.write(filedata)
    # return name of updated file
    return f"{file_name}.asset"

