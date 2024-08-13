import os
import requests
import datetime
import json
from tqdm import tqdm


def get_token_id(file_name):
    with open(os.path.join(os.getcwd(), file_name), 'r') as token_file:
        token = token_file.readline().strip()
        id_one = token_file.readline().strip()
    return [token, id_one]


def find_max_dpi(dict_in_search):
    max_dpi = 0
    need_elem = 0
    for item in dict_in_search:
        file_dpi = item.get('width') * item.get('height')
        if file_dpi > max_dpi:
            max_dpi = file_dpi
            need_elem = item
    return need_elem.get('url'), need_elem.get('type')


def time_convert(time_unix):
    time_bc = datetime.datetime.fromtimestamp(time_unix)
    return time_bc.strftime('%Y-%m-%d time %H-%M-%S')


class VkRequest:
    def __init__(self, token_list, version='5.131'):
        self.token = token_list[0]
        self.id = token_list[1]
        self.version = version
        self.start_params = {'access_token': self.token, 'v': self.version}
        self.json, self.export_dict = self._sort_info()

    def _get_photo_info(self):
        url = 'https://api.vk.com/method/photos.get'
        params = {
            'owner_id': self.id,
            'album_id': 'profile',
            'photo_sizes': 1,
            'extended': 1,
            'rev': 1
        }
        response = requests.get(url, params={**self.start_params, **params}).json()['response']
        return response['count'], response['items']

    def _get_logs_only(self):
        photo_count, photo_items = self._get_photo_info()
        result = {}
        for item in photo_items:
            likes_count = item['likes']['count']
            url_download, picture_size = find_max_dpi(item['sizes'])
            time_warp = time_convert(item['date'])
            new_value = result.get(likes_count, [])
            new_value.append({
                'likes_count': likes_count,
                'add_name': time_warp,
                'url_picture': url_download,
                'size': picture_size
            })
            result[likes_count] = new_value
        return result

    def _sort_info(self):
        json_list = []
        sorted_dict = {}
        picture_dict = self._get_logs_only()
        for elem in picture_dict.keys():
            for counter, value in enumerate(picture_dict[elem]):
                file_name = f'{value["likes_count"]}.jpeg' if len(picture_dict[elem]) == 1 else f'{value["likes_count"]} {value["add_name"]}.jpeg'
                json_list.append({'file name': file_name, 'size': value["size"]})
                sorted_dict[file_name] = picture_dict[elem][0]['url_picture'] if value["likes_count"] != 0 else picture_dict[elem][counter]['url_picture']
        return json_list, sorted_dict


class Yandex:
    def __init__(self, folder_name, token_list, num=5):
        self.token = token_list[0]
        self.added_files_num = num
        self.url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
        self.headers = {'Authorization': self.token}
        self.folder = self._create_folder(folder_name)

    def _create_folder(self, folder_name):
        url = "https://cloud-api.yandex.net/v1/disk/resources"
        params = {'path': folder_name}
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            requests.put(url, headers=self.headers, params=params)
            print(f'\nПапка {folder_name} успешно создана в каталоге Яндекс диска\n')
        else:
            print(f'\nПапка {folder_name} уже существует. Файлы с одинаковыми именами не будут скопированы\n')
        return folder_name

    def _in_folder(self, folder_name):

        url = "https://cloud-api.yandex.net/v1/disk/resources"
        params = {'path': folder_name}
        response = requests.get(url, headers=self.headers, params=params).json()

        if '_embedded' in response:
            resource = response['_embedded']['items']
            return [elem['name'] for elem in resource]
        else:
            print(f"Ошибка: Папка {folder_name} пустая или не существует.")
            print(f"Ответ от API: {response}")
            return []


    def create_copy(self, dict_files):
        """Метод загрузки фотографий на Я-диск"""
        files_in_folder = self._in_folder(self.folder)
        copy_counter = 0
        for key, _ in zip(dict_files.keys(), tqdm(range(self.added_files_num))):
            if copy_counter < self.added_files_num:
                if key not in files_in_folder:
                    params = {
                        'path': f'{self.folder}/{key}',
                        'url': dict_files[key],
                        'overwrite': 'false'
                    }
                    requests.post(self.url, headers=self.headers, params=params)
                    copy_counter += 1
                else:
                    print(f'Внимание: Файл {key} уже существует')
            else:
                break

        print(f'\nЗапрос завершен, новых файлов скопировано (по умолчанию: 5): {copy_counter}'
              f'\nВсего файлов в исходном альбоме VK: {len(dict_files)}')

    def check_token(self):
            url = "https://cloud-api.yandex.net/v1/disk"
            response = requests.get(url, headers=self.headers)

            if response.status_code == 200:
                print("Токен доступа действителен.")
            else:
                print(f"Ошибка авторизации: {response.json()}")


if __name__ == '__main__':
    tokenVK = 'VK_TOKEN.txt'
    tokenYandex = 'Yandex_TOKEN.txt'

    my_VK = VkRequest(get_token_id(tokenVK))

    with open('VK_photo.json', 'w') as outfile:
        json.dump(my_VK.json, outfile)


    my_yandex = Yandex('VK photo copies', get_token_id(tokenYandex), 5)
    my_yandex.create_copy(my_VK.export_dict)
