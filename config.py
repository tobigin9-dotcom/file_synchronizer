"""Чтение и проверка параметров программы из файла .env."""
import os
from typing import NamedTuple

from dotenv import dotenv_values


class ConfigError(Exception):
    """Ошибка в файле настроек."""


class Settings(NamedTuple):
    """Параметры работы программы."""

    local_folder: str
    cloud_folder: str
    token: str
    period: int
    log_file: str


def read_env_file(env_path):
    """Читает файл .env и возвращает словарь параметров."""
    if not os.path.isfile(env_path):
        raise ConfigError(
            f'Файл настроек не найден: {env_path}. '
            'Скопируйте .env.example в .env и заполните его.'
        )
    return dotenv_values(env_path, encoding='utf-8')


def get_required(config, key):
    """Возвращает непустое значение параметра."""
    value = (config.get(key) or '').strip()
    if not value:
        raise ConfigError(f'В .env не задан параметр {key}')
    return value


def parse_period(value):
    """Преобразует период синхронизации в положительное число секунд."""
    try:
        period = int(value)
    except ValueError:
        raise ConfigError('Параметр PERIOD должен быть целым числом секунд')
    if period <= 0:
        raise ConfigError('Параметр PERIOD должен быть больше нуля')
    return period


def load_settings(env_path):
    """Возвращает проверенные параметры программы."""
    config = read_env_file(env_path)
    return Settings(
        local_folder=os.path.expanduser(get_required(config, 'LOCAL_FOLDER')),
        cloud_folder=get_required(config, 'CLOUD_FOLDER'),
        token=get_required(config, 'TOKEN'),
        period=parse_period(get_required(config, 'PERIOD')),
        log_file=get_required(config, 'LOG_FILE'),
    )
