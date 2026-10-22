"""Работа с Яндекс Диском через REST API."""
import os
from datetime import datetime

import requests


class CloudError(Exception):
    """Базовая ошибка при работе с облачным хранилищем."""


class CloudAuthError(CloudError):
    """Токен доступа неверен или не имеет нужных прав."""


class CloudNotFoundError(CloudError):
    """Запрошенный ресурс не найден в облачном хранилище."""


class YandexDiskStorage:
    """Облачное хранилище на базе Яндекс Диска."""

    API_URL = 'https://cloud-api.yandex.net/v1/disk/resources'
    PAGE_SIZE = 1000
    TIMEOUT = 30

    def __init__(self, token, folder):
        """Принимает токен доступа и путь к существующей папке на диске."""
        self.token = token
        self.folder = folder.strip('/')

    def load(self, path):
        """Загружает локальный файл в хранилище."""
        self._upload(path, overwrite=False)

    def reload(self, path):
        """Перезаписывает файл в хранилище локальной версией."""
        self._upload(path, overwrite=True)

    def delete(self, filename):
        """Удаляет файл из хранилища."""
        response = self._request(
            'DELETE',
            self.API_URL,
            params={'path': self._remote_path(filename),
                    'permanently': 'true'},
        )
        self._check_status(response, (202, 204))

    def get_info(self):
        """Возвращает {имя файла: время изменения (timestamp)} файлов папки."""
        files = {}
        offset = 0
        while True:
            items = self._get_page(offset)
            files.update(self._extract_files(items))
            if len(items) < self.PAGE_SIZE:
                return files
            offset += self.PAGE_SIZE

    def _headers(self):
        return {'Authorization': f'OAuth {self.token}'}

    def _remote_path(self, filename=''):
        return f'/{self.folder}/{filename}'.rstrip('/') or '/'

    def _request(self, method, url, **kwargs):
        try:
            return requests.request(
                method, url, headers=self._headers(),
                timeout=self.TIMEOUT, **kwargs
            )
        except requests.RequestException as error:
            raise CloudError(f'Нет связи с Яндекс Диском: {error}') from error

    @staticmethod
    def _check_status(response, ok_codes):
        if response.status_code in ok_codes:
            return
        message = f'Яндекс Диск вернул код {response.status_code}'
        if response.status_code == 401:
            raise CloudAuthError(f'{message}: неверный токен')
        if response.status_code == 404:
            raise CloudNotFoundError(f'{message}: ресурс не найден')
        raise CloudError(f'{message}: {response.text[:200]}')

    def _get_page(self, offset):
        response = self._request(
            'GET',
            self.API_URL,
            params={
                'path': self._remote_path(),
                'limit': self.PAGE_SIZE,
                'offset': offset,
                'fields': '_embedded.items.name,_embedded.items.type,'
                          '_embedded.items.modified',
            },
        )
        self._check_status(response, (200,))
        return self._parse_items(response)

    @staticmethod
    def _parse_items(response):
        try:
            return response.json()['_embedded']['items']
        except (ValueError, KeyError, TypeError) as error:
            raise CloudError('Неожиданный ответ Яндекс Диска') from error

    @staticmethod
    def _extract_files(items):
        try:
            return {item['name']: datetime.fromisoformat(
                        item['modified']).timestamp()
                    for item in items if item.get('type') == 'file'}
        except (KeyError, ValueError, TypeError) as error:
            raise CloudError('Неожиданный ответ Яндекс Диска') from error

    def _get_upload_url(self, filename, overwrite):
        response = self._request(
            'GET',
            f'{self.API_URL}/upload',
            params={'path': self._remote_path(filename),
                    'overwrite': str(overwrite).lower()},
        )
        self._check_status(response, (200,))
        try:
            return response.json()['href']
        except (ValueError, KeyError, TypeError) as error:
            raise CloudError('Яндекс Диск не вернул ссылку для загрузки') \
                from error

    def _put_file(self, url, path):
        with open(path, 'rb') as file:
            response = self._request('PUT', url, data=file)
        self._check_status(response, (200, 201, 202))

    def _upload(self, path, overwrite):
        filename = os.path.basename(path)
        url = self._get_upload_url(filename, overwrite)
        self._put_file(url, path)
