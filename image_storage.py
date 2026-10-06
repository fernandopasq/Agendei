import io
import os

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_BYTES = 8 * 1024 * 1024
IMAGE_OUTPUTS = {
    "profile": (512, 512),
    "banner": (1200, 600),
    "gallery": (1200, 900),
}
SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}


class ImageUploadError(ValueError):
    """An image upload failed validation or could not be stored."""


def _crop_image(image, output_size, crop_x, crop_y, crop_zoom):
    output_width, output_height = output_size
    source_width, source_height = image.size
    target_ratio = output_width / output_height

    if source_width / source_height > target_ratio:
        crop_height = source_height
        crop_width = source_height * target_ratio
    else:
        crop_width = source_width
        crop_height = source_width / target_ratio

    crop_width = max(1, crop_width / crop_zoom)
    crop_height = max(1, crop_height / crop_zoom)
    center_x = crop_x * source_width
    center_y = crop_y * source_height
    left = min(max(0, center_x - crop_width / 2), source_width - crop_width)
    top = min(max(0, center_y - crop_height / 2), source_height - crop_height)
    bounds = (
        round(left),
        round(top),
        round(left + crop_width),
        round(top + crop_height),
    )

    return image.crop(bounds).resize(output_size, Image.Resampling.LANCZOS)


def save_image_upload(db, uploaded_file, owner_type, owner_id, role, form):
    """Validates, crops, stores an upload, and returns its generated numeric ID."""
    valid_owner_role = (
        owner_type == "user" and role == "profile"
    ) or (
        owner_type == "business" and role in {"banner", "gallery"}
    )
    if not valid_owner_role:
        raise ImageUploadError("Tipo de imagem inválido.")
    if not uploaded_file or not uploaded_file.filename:
        raise ImageUploadError("Selecione uma imagem para enviar.")

    content = uploaded_file.stream.read(MAX_IMAGE_BYTES + 1)
    if len(content) > MAX_IMAGE_BYTES:
        raise ImageUploadError("A imagem deve ter no máximo 8 MB.")
    if not content:
        raise ImageUploadError("O arquivo enviado está vazio.")

    try:
        with Image.open(io.BytesIO(content)) as source:
            if source.format not in SUPPORTED_FORMATS:
                raise ImageUploadError("Use uma imagem JPEG, PNG ou WebP.")
            source.verify()
        with Image.open(io.BytesIO(content)) as source:
            if source.width * source.height > 25_000_000:
                raise ImageUploadError("A imagem excede o limite de resolução permitido.")
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.load()
    except ImageUploadError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as error:
        raise ImageUploadError("Não foi possível ler a imagem enviada.") from error

    try:
        crop_x = min(1.0, max(0.0, float(form.get("crop_x", 0.5))))
        crop_y = min(1.0, max(0.0, float(form.get("crop_y", 0.5))))
        crop_zoom = min(3.0, max(1.0, float(form.get("crop_zoom", 1))))
    except (TypeError, ValueError) as error:
        raise ImageUploadError("As opções de corte da imagem são inválidas.") from error

    output = _crop_image(image, IMAGE_OUTPUTS[role], crop_x, crop_y, crop_zoom)
    encoded = io.BytesIO()
    output.save(encoded, format="WEBP", quality=86, method=6)
    storage_dir = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        "users" if owner_type == "user" else "businesses",
        str(owner_id),
        role,
    )
    try:
        os.makedirs(storage_dir, exist_ok=True)
    except OSError as error:
        raise ImageUploadError("Não foi possível preparar o armazenamento das imagens.") from error

    cursor = db.cursor()
    cursor.execute(
        "SELECT image_id, storage_path FROM image_assets "
        "WHERE owner_type = ? AND owner_id = ? AND role = ?",
        (owner_type, owner_id, role),
    )
    previous_assets = cursor.fetchall() if role != "gallery" else []
    position = 0
    if role == "gallery":
        cursor.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 AS next_position "
            "FROM image_assets WHERE owner_type = ? AND owner_id = ? AND role = ?",
            (owner_type, owner_id, role),
        )
        position = cursor.fetchone()["next_position"]
    else:
        cursor.executemany(
            "DELETE FROM image_assets WHERE image_id = ?",
            [(asset["image_id"],) for asset in previous_assets],
        )

    try:
        cursor.execute("""
            INSERT INTO image_assets (
                owner_type, owner_id, role, storage_path, position,
                crop_x, crop_y, crop_zoom
            )
            VALUES (?, ?, ?, NULL, ?, ?, ?, ?)
        """, (owner_type, owner_id, role, position, crop_x, crop_y, crop_zoom))
        image_id = cursor.lastrowid
        relative_path = os.path.join(
            "users" if owner_type == "user" else "businesses",
            str(owner_id),
            role,
            f"{image_id}.webp",
        )
        cursor.execute(
            "UPDATE image_assets SET storage_path = ? WHERE image_id = ?",
            (relative_path, image_id),
        )
        absolute_path = os.path.join(current_app.config["UPLOAD_FOLDER"], relative_path)
        with open(absolute_path, "xb") as image_file:
            image_file.write(encoded.getvalue())
        db.commit()
    except OSError as error:
        db.rollback()
        if "absolute_path" in locals() and os.path.exists(absolute_path):
            os.remove(absolute_path)
        raise ImageUploadError("Não foi possível armazenar a imagem no servidor.") from error
    except Exception:
        db.rollback()
        if "absolute_path" in locals() and os.path.exists(absolute_path):
            os.remove(absolute_path)
        raise

    for asset in previous_assets:
        previous_path = os.path.join(
            current_app.config["UPLOAD_FOLDER"], asset["storage_path"]
        )
        if os.path.exists(previous_path):
            os.remove(previous_path)
    return image_id


def delete_image_asset(db, image_id, owner_type, owner_id):
    """Deletes one owned image record and its local file."""
    cursor = db.cursor()
    cursor.execute("""
        SELECT storage_path, role, position
        FROM image_assets
        WHERE image_id = ? AND owner_type = ? AND owner_id = ?
    """, (image_id, owner_type, owner_id))
    asset = cursor.fetchone()
    if not asset:
        return False

    cursor.execute("DELETE FROM image_assets WHERE image_id = ?", (image_id,))
    if asset["role"] == "gallery":
        cursor.execute("""
            UPDATE image_assets
            SET position = position - 1
            WHERE owner_type = ? AND owner_id = ? AND role = 'gallery'
              AND position > ?
        """, (owner_type, owner_id, asset["position"]))
    db.commit()

    absolute_path = os.path.join(current_app.config["UPLOAD_FOLDER"], asset["storage_path"])
    if os.path.exists(absolute_path):
        os.remove(absolute_path)
    return True


def delete_owner_image_assets(db, owner_type, owner_id):
    """Removes all image records and local files belonging to an entity."""
    cursor = db.cursor()
    cursor.execute("""
        SELECT image_id, storage_path
        FROM image_assets
        WHERE owner_type = ? AND owner_id = ?
    """, (owner_type, owner_id))
    assets = cursor.fetchall()
    cursor.execute(
        "DELETE FROM image_assets WHERE owner_type = ? AND owner_id = ?",
        (owner_type, owner_id),
    )
    db.commit()

    for asset in assets:
        absolute_path = os.path.join(
            current_app.config["UPLOAD_FOLDER"], asset["storage_path"]
        )
        if os.path.exists(absolute_path):
            os.remove(absolute_path)


def move_gallery_image(db, image_id, business_id, direction):
    """Moves a gallery asset one position while preserving contiguous ordering."""
    if direction not in {"up", "down"}:
        return False
    cursor = db.cursor()
    cursor.execute("""
        SELECT image_id, position
        FROM image_assets
        WHERE image_id = ? AND owner_type = 'business'
          AND owner_id = ? AND role = 'gallery'
    """, (image_id, business_id))
    selected = cursor.fetchone()
    if not selected:
        return False

    cursor.execute("""
        SELECT image_id, position
        FROM image_assets
        WHERE owner_type = 'business' AND owner_id = ? AND role = 'gallery'
        ORDER BY position, image_id
    """, (business_id,))
    ordered_ids = [row["image_id"] for row in cursor.fetchall()]
    current_index = ordered_ids.index(image_id)
    target_index = current_index - 1 if direction == "up" else current_index + 1
    if target_index < 0 or target_index >= len(ordered_ids):
        return False
    ordered_ids[current_index], ordered_ids[target_index] = (
        ordered_ids[target_index],
        ordered_ids[current_index],
    )
    cursor.executemany(
        "UPDATE image_assets SET position = ? WHERE image_id = ?",
        [(position, asset_id) for position, asset_id in enumerate(ordered_ids)],
    )
    db.commit()
    return True
