import json
import logging
import os
import zipfile
from tkinter import filedialog

import requests
import shutil

from glob import glob
from typing import List, Union

from resource_pack_packer import settings
from resource_pack_packer.configs import PackInfo
from resource_pack_packer.console import choose_from_list
from resource_pack_packer.settings import MAIN_SETTINGS, parse_dir

logger = logging.getLogger("Setup")

URL_CURSEFORGE = "https://api.curseforge.com"
URL_MINECRAFT_VERSION_INDEX = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"


def update_cache(value: Union[str, List[str]], src: str):
    cache_data = {
        "cache": []
    }
    # Cache file exists
    if os.path.exists(src):
        with open(src, "r") as file:
            cache_data = json.load(file)

    # Add to cache with duplicates
    if isinstance(value, str):
        cache_set = set(cache_data["cache"])
        cache_set.add(value)
        cache_data["cache"] = list(set(cache_data["cache"]) | cache_set)
    elif isinstance(value, list):
        cache_data["cache"] = list(set(cache_data["cache"]) | set(value))

    with open(src, "w", encoding="utf-8") as file:
        json.dump(cache_data, file, ensure_ascii=False, indent=2)


def check_cache(value: str, src: str) -> bool:
    if os.path.exists(src):
        with open(src, "r") as file:
            cache_data = json.load(file)
            if value in cache_data["cache"]:
                return True
    return False


def extract_jar(src: str, mc_version: str):
    out_dir = os.path.join(MAIN_SETTINGS.working_directory, "dev", mc_version)
    with zipfile.ZipFile(src) as jar:
        for file in jar.namelist():
            if file.startswith("assets"):
                jar.extract(file, out_dir)


def download_file(url: str, dest: str):
    if not os.path.exists(os.path.dirname(dest)):
        os.makedirs(os.path.dirname(dest))

    with requests.get(url, stream=True) as r:
        with open(dest, "wb") as f:
            shutil.copyfileobj(r.raw, f)


class Mod:
    def __init__(self, name: str, project: int, file: int):
        self.name = name
        self.project = project
        self.file = file
        self.directory = ""
        self.file_name = ""

    def download(self, mod_cache: str) -> bool:
        download_dir = os.path.join(MAIN_SETTINGS.working_directory, "dev", "src")
        self.file_name = f"{self.name}.{self.project}.{self.file}.jar"
        self.directory = os.path.join(download_dir, self.file_name)

        # Check if mod is already downloaded
        if check_cache(f"{self.name}.{self.project}.{self.file}", mod_cache):
            return False

        # Download file
        # Get download link
        r = requests.get(f"{URL_CURSEFORGE}/v1/mods/{self.project}/files/{self.file}/download-url", headers={
            "accept": "application/json",
            "x-api-key": MAIN_SETTINGS.curseforge_token
        })

        download_url = r.json()["data"]
        download_file(download_url, self.directory)

        return True

    def install(self, mc_version: str):
        # Install mod
        if not os.path.exists(os.path.join(MAIN_SETTINGS.minecraft_dir, "mods", self.file_name)):
            shutil.copy(self.directory, os.path.join(MAIN_SETTINGS.minecraft_dir, "mods", self.file_name))

        extract_jar(self.directory, mc_version)

    @staticmethod
    def parse(data: dict) -> "Mod":
        return Mod(data["name"], data["project"], data["file"])


def install_version_from_index(index_dir: str) -> str:
    with open(index_dir, "r") as index_file:
        data = json.load(index_file)
    version_url = data["downloads"]["client"]["url"]
    out_dir = os.path.join(index_dir.replace(".json", ".jar"))
    download_file(version_url, out_dir)
    return out_dir


def setup():
    if MAIN_SETTINGS.curseforge_token is None:
        logger.error("Token not provided")
        return

    # Pack info
    config_files = glob(os.path.join(MAIN_SETTINGS.working_directory, "configs", "*"))
    config_file_names = []
    for file in config_files:
        config_file_names.append(os.path.basename(file))

    selected_pack_name = choose_from_list(config_file_names, "Select pack:")[0]
    pack_info = PackInfo.parse(selected_pack_name)
    config = choose_from_list(pack_info.configs, "Select config")[0]

    if not config.curseforge_dependencies:
        logger.error("No dependencies found")
        return

    # Minecraft version
    mc_jar = None
    # Check for installed versions
    for version in config.mc_versions:
        mc_jar_unchecked = os.path.join(MAIN_SETTINGS.minecraft_dir, "versions", version, f"{version}.jar")
        # Version installed
        if os.path.exists(mc_jar_unchecked) and os.path.isfile(mc_jar_unchecked):
            mc_jar = mc_jar_unchecked
            break

    # Install if version not installed
    if mc_jar is None:
        # Check if index for versions are preset
        for version in config.mc_versions:
            version_index = os.path.join(MAIN_SETTINGS.minecraft_dir, "versions", version, f"{version}.json")
            if os.path.exists(version_index):
                mc_jar = install_version_from_index(version_index)
                logger.info(f"Installed Minecraft: {version}")
                break

        # If no versions can be found
        if mc_jar is None:
            version_manifest = requests.get(URL_MINECRAFT_VERSION_INDEX, headers={"accept": "application/json"}).json()
            version_index = None
            for version in version_manifest["versions"]:
                if version["id"] == config.mc_version:
                    version_index = version["url"]
                    break
            if version_index is not None:
                index_dir = os.path.join(MAIN_SETTINGS.minecraft_dir, "versions", config.mc_version, f"{config.mc_version}.json")
                download_file(version_index, index_dir)
                mc_jar = install_version_from_index(index_dir)
                logger.info(f"Installed Minecraft: {config.mc_version}")
            else:
                logger.error(f"Version could not be found: {config.mc_version}")

    mc_version = os.path.basename(mc_jar).replace(".jar", "")

    mod_cache = os.path.join(MAIN_SETTINGS.working_directory, "dev", mc_version, "cache.json")

    # Download
    for i, mod in enumerate(config.curseforge_dependencies, start=1):
        downloaded = mod.download(mod_cache)
        if downloaded:
            logger.info(f"Downloaded mod [{i}/{len(config.curseforge_dependencies)}]: {mod.name}")
        else:
            logger.info(f"Already downloaded mod [{i}/{len(config.curseforge_dependencies)}]: {mod.name}")

    # Preinstall
    if os.path.exists(os.path.join(MAIN_SETTINGS.minecraft_dir, "mods")):
        if any(os.scandir(os.path.join(MAIN_SETTINGS.minecraft_dir, "mods"))):
            mod_input = input("Mods already installed. Remove, keep, cancel, or backup? ").lower()
            if mod_input == "remove":
                shutil.rmtree(os.path.join(MAIN_SETTINGS.minecraft_dir, "mods"))
                logger.info("Cleared mods")
            elif mod_input == "keep":
                pass
            elif mod_input == "cancel":
                return
            else:
                backup_dir = os.path.join(MAIN_SETTINGS.minecraft_dir, "mods-RPPBACKUP")
                shutil.move(os.path.join(MAIN_SETTINGS.minecraft_dir, "mods"), backup_dir)
                logger.info(f"Created backup mods to: {backup_dir}")

    if not os.path.exists(os.path.join(MAIN_SETTINGS.minecraft_dir, "mods")):
        os.makedirs(os.path.join(MAIN_SETTINGS.minecraft_dir, "mods"))

    # Clear dependencies
    if os.path.exists(os.path.join(MAIN_SETTINGS.working_directory, "dev", mc_version, "assets")):
        shutil.rmtree(os.path.join(MAIN_SETTINGS.working_directory, "dev", mc_version, "assets"))

    # Minecraft install
    extract_jar(mc_jar, mc_version)
    logger.info(f"Installed Minecraft: {mc_version}")

    # Install
    mods = []
    for i, mod in enumerate(config.curseforge_dependencies, start=1):
        name = f"{mod.name}.{mod.project}.{mod.file}"
        mods.append(name)
        mod.install(mc_version)
        logger.info(f"Installed mod [{i}/{len(config.curseforge_dependencies)}]: {name}")

    # Update mod cache
    if mods:
        update_cache(mods, mod_cache)
