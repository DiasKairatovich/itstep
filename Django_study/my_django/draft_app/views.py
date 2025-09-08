from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image
from .forms import UploadImageForm
from .models import UploadedImage


def home(request):
    latest = UploadedImage.objects.order_by("-uploaded_at")[:3]  # последние 3 изображения
    return render(request, "home.html", {"latest": latest})


def upload_image(request):
    if request.method == "POST":
        form = UploadImageForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded = request.FILES["image"]  # InMemoryUploadedFile / TemporaryUploadedFile

            # --- Сохраняем оригинал низкоуровневым способом ---
            original_path = f"images/originals/{uploaded.name}"
            with default_storage.open(original_path, "wb") as dest:
                for chunk in uploaded.chunks():
                    dest.write(chunk)

            # --- Создаём миниатюру через Pillow ---
            with default_storage.open(original_path, "rb") as f:
                image = Image.open(f)

                # JPEG не поддерживает прозрачность → конвертируем
                if image.mode in ("RGBA", "P"):
                    image = image.convert("RGB")

                max_size = (300, 300)
                image.thumbnail(max_size, Image.Resampling.LANCZOS)

                thumb_io = BytesIO()
                image.save(thumb_io, format="JPEG", quality=85)

                thumb_name = f"thumb_{uploaded.name.rsplit('.',1)[0]}.jpg"
                thumb_path = default_storage.save(
                    f"images/thumbnails/{thumb_name}",
                    ContentFile(thumb_io.getvalue(), name=thumb_name),
                )

            # --- Записываем в БД ---
            obj = UploadedImage.objects.create(
                original=original_path,
                thumbnail=thumb_path,
            )

            return redirect("upload_success", pk=obj.pk)
    else:
        form = UploadImageForm()

    return render(request, "upload.html", {"form": form})


def upload_success(request, pk):
    obj = get_object_or_404(UploadedImage, pk=pk)
    return render(request, "uploaded.html", {"obj": obj})

