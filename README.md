# shopify-delete-blogs
Shopify app to delete blogs from a .csv file with a list of URLs

## Dependencies

- Shopify API
Create custom app and obtain API Token

## Create and activate virtual env

```bash
python -m venv venv
source venv/Scripts/activate
```

## Install dependencies
```bash
pip install -r requirements.txt
```

## Create .env file

It should contain:

```bash
SHOPIFY_STORE=your-store.myshopify.com
SHOPIFY_API_TOKEN=your_shopify_api_token
```