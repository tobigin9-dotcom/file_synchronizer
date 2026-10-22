"""Точка входа: фоновая синхронизация папки с Яндекс Диском."""
import os
import sys
import time

from loguru import logger

from config import ConfigError, load_settings
from synchronizer import sync_once
from yandex_disk import (CloudAuthError, CloudError, CloudNotFoundError,
                         YandexDiskStorage)


def setup_logger(log_file):
    """Настраивает запись лога в файл и возвращает логгер."""
    logger.remove()
    try:
        logger.add(log_file, level='INFO', encoding='utf-8',
                   format='{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}')
    except OSError as error:
        raise ConfigError(
            f'Не удалось открыть файл лога "{log_file}": {error}. '
            'Проверьте параметр LOG_FILE в .env.'
        )
    return logger


def check_local_folder(folder):
    """Проверяет, что синхронизируемая папка существует."""
    if not os.path.isdir(folder):
        raise ConfigError(
            f'Синхронизируемая папка "{folder}" не найдена. '
            'Создайте её или исправьте параметр LOCAL_FOLDER в .env.'
        )


def check_storage(storage, settings, logger):
    """Проверяет токен и наличие папки в хранилище."""
    try:
        storage.get_info()
    except CloudAuthError:
        raise ConfigError(
            'Яндекс Диск отклонил токен. Получите новый OAuth-токен и '
            'укажите его в параметре TOKEN в .env.'
        )
    except CloudNotFoundError:
        raise ConfigError(
            f'Папка "{settings.cloud_folder}" не найдена на Яндекс Диске. '
            'Создайте её или исправьте параметр CLOUD_FOLDER в .env.'
        )
    except CloudError as error:
        logger.error('Не удалось проверить хранилище при запуске: {}', error)


def run_forever(storage, settings, logger):
    """Периодически синхронизирует папку до остановки программы."""
    while True:
        sync_once(storage, settings.local_folder, logger)
        time.sleep(settings.period)


def start(settings):
    """Запускает синхронизацию с заданными параметрами."""
    logger = setup_logger(settings.log_file)
    check_local_folder(settings.local_folder)
    logger.info('Программа запущена. Синхронизируемая папка: {}',
                settings.local_folder)
    storage = YandexDiskStorage(settings.token, settings.cloud_folder)
    check_storage(storage, settings, logger)
    run_forever(storage, settings, logger)


def main():
    """Читает настройки и запускает программу."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '.env')
    try:
        start(load_settings(env_path))
    except ConfigError as error:
        sys.exit(f'Ошибка: {error}')
    except KeyboardInterrupt:
        logger.info('Программа остановлена пользователем')


if __name__ == '__main__':
    main()
