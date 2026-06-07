import base64
from functools import lru_cache
from io import BytesIO
from urllib.parse import quote, urlparse

from app.config.settings import settings


QR_BOX_SIZE = 10
QR_BORDER_SIZE = 3


def _normalize_base_url(base_url: str | None):

    configured_base_url = (
        base_url
        or settings.FRONTEND_PUBLIC_BASE_URL
        or ""
    ).strip().rstrip("/")

    parsed_url = urlparse(configured_base_url)

    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        return settings.FRONTEND_PUBLIC_BASE_URL.rstrip("/")

    return configured_base_url


def build_public_menu_url(slug: str, base_url: str | None = None):

    encoded_slug = quote(slug, safe="")

    return f"{_normalize_base_url(base_url)}/menu/{encoded_slug}"


@lru_cache(maxsize=512)
def build_qr_image_data_url(menu_url: str):

    import qrcode

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=QR_BOX_SIZE,
        border=QR_BORDER_SIZE
    )
    qr.add_data(menu_url)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)

    encoded_png = base64.b64encode(buffer.getvalue()).decode("ascii")

    return f"data:image/png;base64,{encoded_png}"


def build_qr_response(restaurant, base_url: str | None = None):

    menu_url = build_public_menu_url(
        restaurant["slug"],
        base_url=base_url
    )
    qr_image_url = build_qr_image_data_url(menu_url)

    return {
        "restaurant_id": restaurant["id"],
        "slug": restaurant["slug"],
        "menu_url": menu_url,
        "qr_image_url": qr_image_url,
        "qr_image_data_url": qr_image_url
    }
