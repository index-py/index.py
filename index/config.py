import os
import json
import typing
import logging
import warnings

import yaml

from .utils import Singleton

__all__ = ["Config"]

LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}


logger: logging.Logger = logging.getLogger("index")


class ConfigError(Exception):
    pass


class ConfigFileError(ConfigError):
    pass


class UpperDict:
    def __init__(self, data: dict):
        self.__dict: typing.Dict[str, typing.Any] = dict()

        for key in data.keys():
            self[key] = data[key]

    def __str__(self) -> str:
        indent = 4
        result = ["{"]

        def append(line):
            result.append(" " * indent + line)

        for key, value in self.__dict.items():
            if isinstance(value, UpperDict):
                append(f"{key}: {{")
                for line in str(value).splitlines()[1:-1]:
                    append(f"{line}")
                append("}")
            else:
                if isinstance(value, str):
                    append(f"{key}: '{value}',")
                else:
                    append(f"{key}: {value},")

        result.append("}")

        return "\n".join(result)

    def __setitem__(self, key: str, value: typing.Any) -> None:
        key = key.upper()

        if isinstance(value, dict):
            if key in self.__dict.keys():
                for k, v in value.items():
                    self.__dict[key][k.upper()] = v
            else:
                self.__dict[key] = UpperDict(value)
        else:
            self.__dict[key] = value

    def __getitem__(self, key: str) -> typing.Any:
        return self.__dict[key.upper()]

    def __getattr__(self, name: str) -> typing.Any:
        try:
            value = self.get(name, ...)
            if value is ...:
                raise KeyError()
            return value
        except KeyError:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute '{name}'"
            )

    def get(self, key: str, default=None) -> typing.Any:
        try:
            return self[key]
        except KeyError:
            return default


def _import_environ() -> typing.Dict:
    result: typing.Dict[str, typing.Any] = {}

    if os.environ.get("INDEX_DEBUG"):
        result["debug"] = os.environ.get("INDEX_DEBUG") in ("on", "True")

    if os.environ.get("INDEX_ENV"):
        result["env"] = os.environ.get("INDEX_ENV")

    return result


class Config(UpperDict, metaclass=Singleton):
    def __init__(self) -> None:
        super().__init__({})
        self.setdefault()
        # read config from file
        self.import_from_file()
        # read config from environ
        self.update(_import_environ())

    @property
    def path(self) -> str:
        """return os.getcwd()"""
        return os.getcwd()

    def import_from_file(self) -> None:
        filename = None

        for _filename in ["config.json", "index.json", "index.yaml", "index.yml"]:
            if os.path.exists(os.path.normpath(_filename)):
                if filename is not None:
                    raise ConfigFileError(
                        f"`{filename}` and `{_filename}` cannot be used at the same project."
                    )
                filename = _filename
                # TODO clear in 0.8
                if filename == "config.json":
                    warnings.warn(
                        "Please use `index.json` or` index.yaml`, `config.json` will be deprecated in 0.8."
                    )

        if filename is None:
            return

        with open(filename, "rb") as file:
            if filename.endswith(".json"):
                data = json.load(file)
            elif filename.endswith(".yaml") or filename.endswith(".yml"):
                data = yaml.safe_load(file)

        if not isinstance(data, dict):
            raise ConfigError(f"config must be a dictionary.")

        self.update(data)

    def setdefault(self) -> None:
        """set default value"""

        self["env"] = "dev"
        self["debug"] = False
        self["host"] = "127.0.0.1"
        self["port"] = 4190
        self["log_level"] = "info"
        self["hotreload"] = True
        # url
        self["allow_underline"] = False
        # middleware
        self["force_ssl"] = False
        self["allowed_hosts"] = ["*"]
        self["cors_allow_origins"] = ()
        self["cors_allow_methods"] = ("GET",)
        self["cors_allow_headers"] = ()
        self["cors_allow_credentials"] = False
        self["cors_allow_origin_regex"] = None
        self["cors_expose_headers"] = ()
        self["cors_max_age"] = 600

    def update(self, data: dict) -> None:
        for key in data.keys():
            self[key] = data[key]

    def __setattr__(self, name: str, value: typing.Any) -> None:
        if name == f"_UpperDict__dict":
            return super().__setattr__(name, value)
        raise ConfigError("Modifying the attribute value of Config is not allowed.")

    def __delattr__(self, name: str) -> None:
        raise ConfigError("Modifying the attribute value of Config is not allowed.")

    def __delitem__(self, key: str) -> None:
        raise ConfigError("Modifying the attribute value of Config is not allowed.")

    def __setitem__(self, key: str, value: typing.Any) -> None:
        key = key.upper()

        if key == "DEBUG":
            value = bool(value)
        elif key == "PORT":
            value = int(value)
        elif key == "ALLOWED_HOSTS":
            value = list(value)
            value.append("testserver")

        super().__setitem__(key, value)

    def get(self, key, default=None) -> typing.Any:
        env = super().get(self["env"], {})
        value = env.get(key, None)
        if value is None:
            value = super().get(key, default)
        return value


config = Config()
