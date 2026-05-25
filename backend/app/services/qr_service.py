from urllib.parse import quote

from app.config.settings import settings


def build_public_menu_url(slug: str):

    return f"{settings.FRONTEND_PUBLIC_BASE_URL.rstrip('/')}/menu/{slug}"


def build_qr_response(restaurant):

    menu_url = build_public_menu_url(restaurant["slug"])
    encoded_url = quote(menu_url, safe="")

    return {
        "restaurant_id": restaurant["id"],
        "slug": restaurant["slug"],
        "menu_url": menu_url,
        "qr_image_url": (
            "https://api.qrserver.com/v1/create-qr-code/"
            f"?size=320x320&margin=12&data={encoded_url}"
        )
    }
