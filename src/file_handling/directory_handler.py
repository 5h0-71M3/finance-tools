from dirlin import Folder

from src.file_handling._config import directory_config


class Directory:
    DOWNLOADS = Folder(directory_config["downloads"])
    DATA_ANALYSIS = Folder(directory_config["data_analysis"])
    DESKTOP = Folder(directory_config["desktop"])
    ACCOUNT_CURRENT = Folder(directory_config["account_current"])

    @classmethod
    def as_custom_folder_path(cls, folder_path: str):
        return Folder(folder_path)
