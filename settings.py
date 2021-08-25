import json
from os import path


class Settings:
    def __init__(self):
        # Generates settings file if not found
        if not path.exists("settings.json"):
            with open("settings.json", "x") as file:
                data = {
                    "locations": {
                        "pack_folder": path.normpath(
                            path.join(path.abspath(path.expanduser(input("Minecraft Folder: "))), "resourcepacks")),
                        "temp": "temp",
                        "out": path.normpath(path.abspath(path.expanduser(input("Output Folder: "))))
                    }
                }
                json.dump(data, file, indent="\t")

        with open("settings.json", "r") as file:
            self.data = json.load(file)

    def parse_dir(dir):
        return path.normpath(path.abspath(path.expanduser(dir)))


def generate_config(mc_version, delete_textures, ignore_folders, regenerate_meta, patches):
    data = {
        mc_version: {
            "mc_version": mc_version,
            "textures": {
                "delete": delete_textures,
                "ignore": ignore_folders
            },
            "regenerate_meta": regenerate_meta,
            "patches": patches
        }
    }

    return data


class Configs:
    def __init__(self):
        with open("configs.json") as file:
            self.data = json.load(file)

    def get_config(data, pack):
        return data["packs"][pack]["configs"]

    def check_option(root, option):
        if option in root:
            return True
        else:
            return False
