"""Сравнение локальной папки с облачным хранилищем и синхронизация."""
import os

from yandex_disk import CloudError


def list_local_files(folder):
    """Возвращает множество имён файлов (без подпапок) в папке."""
    names = os.listdir(folder)
    return {name for name in names
            if os.path.isfile(os.path.join(folder, name))}


def run_action(action, argument, message, logger):
    """Выполняет действие и пишет результат в лог, не прерывая работу."""
    try:
        action(argument)
    except (CloudError, OSError) as error:
        logger.error('{}: {}', message, error)
        return
    logger.info(message)


def is_changed(path, remote_mtime, logger):
    """Проверяет, что локальный файл новее облачного."""
    try:
        return os.path.getmtime(path) > remote_mtime
    except OSError as error:
        logger.error('Не удалось прочитать файл {}: {}', path, error)
        return False


def find_changed(folder, names, remote_files, logger):
    """Возвращает имена файлов, изменённых после последней загрузки."""
    return sorted(name for name in names
                  if is_changed(os.path.join(folder, name),
                                remote_files[name], logger))


def upload_new(storage, folder, names, logger):
    """Загружает новые файлы."""
    for name in sorted(names):
        run_action(storage.load, os.path.join(folder, name),
                   f'Файл {name} загружен в хранилище', logger)


def upload_changed(storage, folder, names, logger):
    """Перезаписывает изменённые файлы."""
    for name in names:
        run_action(storage.reload, os.path.join(folder, name),
                   f'Файл {name} обновлён в хранилище', logger)


def delete_removed(storage, names, logger):
    """Удаляет из хранилища файлы, которых больше нет локально."""
    for name in sorted(names):
        run_action(storage.delete, name,
                   f'Файл {name} удалён из хранилища', logger)


def fetch_remote_files(storage, logger):
    """Получает список файлов хранилища или None при ошибке."""
    try:
        return storage.get_info()
    except CloudError as error:
        logger.error('Не удалось получить список файлов хранилища: {}',
                     error)
        return None


def fetch_local_files(folder, logger):
    """Получает список локальных файлов или None при ошибке."""
    try:
        return list_local_files(folder)
    except OSError as error:
        logger.error('Не удалось прочитать папку {}: {}', folder, error)
        return None


def sync_once(storage, folder, logger):
    """Один проход синхронизации: хранилище приводится к виду папки."""
    remote_files = fetch_remote_files(storage, logger)
    local_names = fetch_local_files(folder, logger)
    if remote_files is None or local_names is None:
        return
    remote_names = set(remote_files)
    upload_new(storage, folder, local_names - remote_names, logger)
    changed = find_changed(folder, local_names & remote_names,
                           remote_files, logger)
    upload_changed(storage, folder, changed, logger)
    delete_removed(storage, remote_names - local_names, logger)
