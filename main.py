import logging

from resource_pack_packer.packer import Packer
from resource_pack_packer.settings import MAIN_SETTINGS


def main():
    logging.basicConfig(
        format="[\x1b[32m%(asctime)s\x1b[0m] | [\x1b[33m%(levelname)s\x1b[0m] | \x1b[36m%(message)s\x1b[0m",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging.INFO
    )

    logging.info(f"Working Dir: {MAIN_SETTINGS.working_directory}")

    run_type = input("config\ndev\nmanual\npublish\nworkdir\n\n").lower()
    if run_type == "workdir":
        working_directory = input("Working Directory: ")
        MAIN_SETTINGS.working_directory = working_directory
        MAIN_SETTINGS.save()
        main()
    else:
        packer = Packer(run_type)
        packer.start()


if __name__ == "__main__":
    main()
