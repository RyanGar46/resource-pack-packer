from packer import *


# Loads settings.json
settings = Settings().data

RESOURCE_PACK_FOLDER_DIR = parse_dir(settings["locations"]["pack_folder"])
TEMP_DIR = parse_dir(settings["locations"]["temp"])
OUT_DIR = parse_dir(settings["locations"]["out"])

RUN_TYPE = input("Run as:\nconfig\ndev\nmanual").lower()

packer = Packer(RUN_TYPE, RESOURCE_PACK_FOLDER_DIR, TEMP_DIR, OUT_DIR)

packer.start()
