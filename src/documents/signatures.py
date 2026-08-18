import hashlib
import tempfile
from io import BytesIO
from pathlib import Path

import img2pdf
import magic
import pikepdf
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image

from documents.data_models import ConsumableDocument
from documents.data_models import DocumentMetadataOverrides
from documents.data_models import DocumentSource
from documents.models import Document
from documents.models import SignatureProfile
from documents.tasks import consume_file

ALLOWED_SIGNATURE_MIME_TYPES = {"image/png", "image/jpeg", "application/pdf"}
MAX_SIGNATURE_SIZE = 10 * 1024 * 1024


def validate_signature_upload(upload) -> tuple[bytes, str, str]:
    data = upload.read(MAX_SIGNATURE_SIZE + 1)
    if not data or len(data) > MAX_SIGNATURE_SIZE:
        raise ValidationError("Signature files must be between 1 byte and 10 MB.")
    mime_type = magic.from_buffer(data, mime=True)
    if mime_type not in ALLOWED_SIGNATURE_MIME_TYPES:
        raise ValidationError("Only PNG, JPEG, and PDF signature files are supported.")
    try:
        if mime_type == "application/pdf":
            with pikepdf.open(BytesIO(data)) as signature_pdf:
                if not signature_pdf.pages:
                    raise ValidationError("The signature PDF has no pages.")
        else:
            with Image.open(BytesIO(data)) as signature_image:
                signature_image.verify()
                width, height = signature_image.size
                if width * height > 25_000_000 or width > 10_000 or height > 10_000:
                    raise ValidationError("The signature image dimensions are too large.")
    except ValidationError:
        raise
    except Exception as error:
        raise ValidationError("The signature file is invalid or damaged.") from error
    extension = {"image/png": ".png", "image/jpeg": ".jpg", "application/pdf": ".pdf"}[mime_type]
    return data, mime_type, extension


def signature_checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _signature_as_pdf(profile: SignatureProfile, directory: Path) -> Path:
    source = directory / Path(profile.signature_file.name).name
    with profile.signature_file.open("rb") as signature_file:
        source.write_bytes(signature_file.read())
    if profile.mime_type == "application/pdf":
        single_page = directory / "signature-page.pdf"
        with pikepdf.open(source) as signature_pdf:
            if not signature_pdf.pages:
                raise ValidationError("The signature PDF has no pages.")
            output = pikepdf.new()
            output.pages.append(signature_pdf.pages[0])
            output.save(single_page)
        return single_page
    converted = directory / "signature-image.pdf"
    converted.write_bytes(img2pdf.convert(str(source)))
    return converted


def create_signed_version(
    *,
    source_document: Document,
    profile: SignatureProfile,
    page_number: int,
    x: float,
    y: float,
    width: float,
    height: float,
    actor_id: int,
) -> Document:
    for value in (x, y, width, height):
        if not 0 <= value <= 1:
            raise ValidationError("Signature placement must be within the page.")
    if width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        raise ValidationError("Signature placement must be within the page.")

    source_path = (
        source_document.archive_path
        if source_document.has_archive_version
        else source_document.source_path
    )
    if source_path is None or magic.from_file(source_path, mime=True) != "application/pdf":
        raise ValidationError("The requested document version has no PDF rendition.")

    settings.SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=settings.SCRATCH_DIR) as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        signature_pdf_path = _signature_as_pdf(profile, temp_dir)
        signed_path = temp_dir / "signed.pdf"
        with pikepdf.open(source_path) as document_pdf, pikepdf.open(signature_pdf_path) as signature_pdf:
            if page_number < 1 or page_number > len(document_pdf.pages):
                raise ValidationError("The selected page does not exist.")
            page = document_pdf.pages[page_number - 1]
            media_box = page.mediabox
            page_width = float(media_box[2]) - float(media_box[0])
            page_height = float(media_box[3]) - float(media_box[1])
            left = float(media_box[0]) + x * page_width
            bottom = float(media_box[1]) + (1 - y - height) * page_height
            rectangle = pikepdf.Rectangle(
                left,
                bottom,
                left + width * page_width,
                bottom + height * page_height,
            )
            page.add_overlay(signature_pdf.pages[0], rectangle)
            document_pdf.save(signed_path)

        persistent_temp = Path(tempfile.mkdtemp(dir=settings.SCRATCH_DIR)) / "signed.pdf"
        persistent_temp.write_bytes(signed_path.read_bytes())

    root_document = source_document.root_document or source_document
    overrides = DocumentMetadataOverrides(
        version_label=f"Signed by {profile.user.get_full_name() or profile.user.username}",
        actor_id=actor_id,
    )
    input_document = ConsumableDocument(
        source=DocumentSource.ApiUpload,
        original_file=persistent_temp,
        root_document_id=root_document.pk,
    )
    try:
        result = consume_file.apply(
            kwargs={"input_doc": input_document, "overrides": overrides},
        ).get()
    finally:
        if persistent_temp.exists():
            persistent_temp.unlink()
        try:
            persistent_temp.parent.rmdir()
        except OSError:
            pass
    if not result or "document_id" not in result:
        raise ValidationError("The signed document version could not be created.")
    return Document.objects.get(pk=result["document_id"])
