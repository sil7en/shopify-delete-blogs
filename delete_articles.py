import os
import sys
import requests
import logging
import time
import pandas as pd
from urllib.parse import urlparse
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv(override=True)

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

# Leer variables desde el entorno
SHOPIFY_STORE = os.getenv('SHOPIFY_STORE')
SHOPIFY_API_TOKEN = os.getenv('SHOPIFY_API_TOKEN')

if not SHOPIFY_STORE or not SHOPIFY_API_TOKEN:
    logging.error("Faltan variables de entorno: SHOPIFY_STORE y SHOPIFY_API_TOKEN deben estar definidas en .env.")
    sys.exit("Credenciales no configuradas.")

headers = {
    'Content-Type': 'application/json',
    'X-Shopify-Access-Token': SHOPIFY_API_TOKEN
}

DRY_RUN = False  # Cambiar a False cuando quieras eliminar realmente los artículos
CSV_FILE = 'urls_eliminar.csv'

def shopify_request(method, url, **kwargs):
    response = requests.request(method, url, headers=headers, **kwargs)
    while response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 5))
        logging.warning(f"Límite de tasa excedido. Reintentando después de {retry_after} segundos.")
        time.sleep(retry_after)
        response = requests.request(method, url, headers=headers, **kwargs)
    return response

def get_blog_id():
    url = f"https://{SHOPIFY_STORE}/admin/api/2023-10/blogs.json"
    response = shopify_request('GET', url)
    if response.status_code == 200:
        blogs = response.json().get('blogs', [])
        if blogs:
            return blogs[0]['id']
        else:
            logging.error("No se encontraron blogs en la tienda.")
    else:
        logging.error(f"Error al obtener blogs: {response.status_code} - {response.text}")
    return None

def extract_handle_from_url(url):
    path = urlparse(url).path
    parts = path.strip('/').split('/')
    if 'blogs' in parts:
        try:
            index = parts.index('blogs')
            handle = parts[index + 2]
            return handle
        except IndexError:
            return None
    else:
        return None

def get_article_id_by_handle(blog_id, handle):
    url = f"https://{SHOPIFY_STORE}/admin/api/2023-10/blogs/{blog_id}/articles.json"
    params = {'handle': handle}
    response = shopify_request('GET', url, params=params)
    if response.status_code == 200:
        articles = response.json().get('articles', [])
        if articles:
            return articles[0]['id'], articles[0]['title']
        else:
            logging.error(f'No se encontró artículo con handle "{handle}".')
    else:
        logging.error('Error al obtener artículo: %s', response.text)
    return None, None

def delete_article(blog_id, article_id, title):
    if DRY_RUN:
        logging.info(f'[Modo de prueba] Artículo "{title}" (ID: {article_id}) NO eliminado.')
        return
    url = f"https://{SHOPIFY_STORE}/admin/api/2023-10/blogs/{blog_id}/articles/{article_id}.json"
    response = shopify_request('DELETE', url)
    if response.status_code == 200:
        logging.info(f'Artículo "{title}" eliminado exitosamente.')
    else:
        logging.error(f'Error al eliminar el artículo "{title}": {response.status_code} - {response.text}')

def main():
    blog_id = get_blog_id()
    if not blog_id:
        sys.exit("No se pudo obtener el ID del blog. Revisa tus credenciales o si tienes blogs en la tienda.")

    if not os.path.isfile(CSV_FILE):
        sys.exit(f"El archivo '{CSV_FILE}' no existe en el directorio actual.")

    # Leer el CSV
    df = pd.read_csv(CSV_FILE)
    if 'url' not in df.columns:
        sys.exit("El archivo CSV debe tener una columna 'url' con las URLs de los artículos.")

    urls = df['url'].dropna().tolist()
    logging.info(f"Se encontraron {len(urls)} URLs para procesar.")

    for url in urls:
        logging.info(f"Procesando URL: {url}")
        handle = extract_handle_from_url(url)
        if not handle:
            logging.error(f"No se pudo extraer el handle de la URL: {url}")
            continue
        article_id, title = get_article_id_by_handle(blog_id, handle)
        if article_id:
            logging.info(f"Se encontró el artículo '{title}' con ID {article_id} para el handle '{handle}'.")
            delete_article(blog_id, article_id, title)
            time.sleep(0.5)  # Para evitar exceder límites de tasa
        else:
            logging.error(f"No se pudo encontrar el artículo con handle '{handle}' para la URL: {url}")

if __name__ == '__main__':
    main()