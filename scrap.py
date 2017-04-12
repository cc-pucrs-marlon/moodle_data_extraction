import os
import re
import requests
import getpass

from bs4 import BeautifulSoup

try:
    import lxml
    PARSER = "lxml"
except ImportError:
    try:
        import html5lib
        PARSER = "html5lib"
    except ImportError:
        PARSER = "html.parser"

BASE_URL = 'https://moodle.pucrs.br'
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'DATA')
URL_LOGIN = "/login/index.php"
URL_RESOURCE = "/mod/resource/view.php?id="
URL_PAGE = "/mod/page/view.php?id="
URL_GALLERY = "/mod/lightboxgallery/view.php?id="


class ScrapMoodle:
    def __init__(self, username, password):
        self.dir_user = os.path.join(BASE_DIR, username)
        if not os.path.exists(BASE_DIR):
            os.makedirs(BASE_DIR)
        if not os.path.exists(BASE_DIR):
            os.makedirs(self.dir_user)
        self.login_credentials = {"username": username, "password": password}

    def begin(self):
        with requests.Session() as session:
            login_url = "{}{}".format(BASE_URL, URL_LOGIN)
            pag_main = session.post(login_url, data=self.login_credentials)
            if pag_main.status_code == 200 and pag_main.url != login_url:
                soup = BeautifulSoup(pag_main.text, PARSER)
                urls = dict()
                for link in soup.find_all('a'):
                    l = link.get('href')
                    n = link.find_all(text=True)
                    if l is not None and l.find("/course/view.php?id=") != -1 and l not in urls:
                        urls[l] = "".join(n)
                self.scrap_page_discipline(urls, session)
            else:
                print("Usuário ou Senha incorreto")

    def scrap_page_discipline(self, urls, session):
        for url in urls.keys():
            folder_content = os.path.join(self.dir_user, "".join([c for c in urls[url] if c.isalpha() or c.isdigit() or
                                                             c == ' ']).rstrip())
            if not os.path.exists(folder_content):
                os.makedirs(folder_content)
            pag_content = session.get(url)
            if pag_content.status_code == 200:
                soup = BeautifulSoup(pag_content.text, PARSER)
                material_links = dict()
                for link in soup.find_all('a'):
                    self.check_link(link, material_links)

                self.get_materials(material_links, session, folder_content)

    def check_link(self, link, material_links):
        l = link.get('href')
        n = link.find_all(text=True)
        if l is not None and l not in material_links:
            name = "".join(n)
            filename = "".join([c for c in name if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
            if l.find(URL_RESOURCE) != -1:
                material_links[l] = {"name": name, "type": URL_RESOURCE, "filename": filename}
            elif l.find(URL_PAGE) != -1:
                material_links[l] = {"name": name, "type": URL_PAGE, "filename": filename}
            elif l.find(URL_GALLERY) != -1:
                material_links[l] = {"name": name, "type": URL_GALLERY, "filename": filename}

    def extrair_nome_arquivo(self, headers, filename):
        if headers.get('Content-Disposition') is not None:
            d = headers.get('Content-Disposition')
            fname = re.findall("filename=(.+)", d)[0][1:-1]
        else:
            fname = filename
        return fname

    def get_materials(self, material_links, session, folder_content):
        for link in material_links.keys():
            print("Coletando o material do link: {}".format(link))
            material = material_links[link]
            if material["type"] == URL_RESOURCE:
                mat = session.get(link, stream=True)
                filename = self.extrair_nome_arquivo(mat.headers, material["filename"])
                if mat.url != link:
                    with open('{}/{}'.format(folder_content, filename), 'wb') as fd:
                        for chunk in mat.iter_content(2000):
                            fd.write(chunk)
                else:
                    mat = session.get(link)
                    soup = BeautifulSoup(mat.text, PARSER)
                    link_material = soup.find_all('frame')
                    if len(link_material) != 0:
                        l = link_material[1].get('src')
                        mat2 = session.get(l, stream=True)
                        filename = self.extrair_nome_arquivo(mat2.headers, material["filename"])
                        with open('{}/{}'.format(folder_content, filename), 'wb') as fd:
                            for chunk in mat2.iter_content(2000):
                                fd.write(chunk)
                    else:
                        link_material = soup.find('div', class_='resourceworkaround')
                        if link_material is not None:
                            a = link_material.find('a')
                            l = a.get('href')
                            mat2 = session.get(l, stream=True)
                            filename = self.extrair_nome_arquivo(mat2.headers, material["filename"])
                            with open('{}/{}'.format(folder_content, filename), 'wb') as fd:
                                for chunk in mat2.iter_content(2000):
                                    fd.write(chunk)
            if material["type"] == URL_PAGE:
                mat = session.get(link)
                soup = BeautifulSoup(mat.text, PARSER)
                texto = soup.find('section')
                if texto is not None:
                    texto = texto.get_text()
                    with open('{}/{}'.format(folder_content, material["filename"]), 'w') as fd:
                        fd.write(texto)
                else:
                    with open('{}/{}'.format(folder_content, material["filename"]), 'wb') as fd:
                        fd.write(mat.content)


if __name__ == "__main__":
    username = input("Informe o seu username: ")
    password = getpass.getpass("Informe a sua senha: ")
    scrap = ScrapMoodle(username, password)
    scrap.begin()
