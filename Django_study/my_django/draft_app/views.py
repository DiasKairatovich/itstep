from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image
from .forms import UploadImageForm
from .models import UploadedImage

from django.contrib import messages
from django.shortcuts import redirect
from django.core.signing import BadSignature
from django.core import signing

from django.core.cache import cache

def home(request):
    latest = cache.get("latest_images")
    if not latest:
        latest = list(UploadedImage.objects.order_by("-uploaded_at")[:3])
        cache.set("latest_images", latest, 60)  # 60 секунд
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

            cache.delete("latest_images")           # <-- Очистим кеш "latest_images"

            messages.success(request, "Файл успешно загружен!")  # <-- flash сообщение

            signed_pk = signing.dumps({"pk": obj.pk})                    # <-- подпись pk
            return redirect("upload_success", token=signed_pk)
        else:
            messages.error(request, "Ошибка: некорректная форма!")  # <-- flash сообщение
    else:
        form = UploadImageForm()

    return render(request, "upload.html", {"form": form})


from django.views.decorators.cache import cache_control

@cache_control(max_age=3600) # <-- браузер будет хранить файл в кэше и не запрашивать его снова час.
def upload_success(request, token):
    try:
        data = signing.loads(token)
        pk = data["pk"] # <-- парсим нашу подпись
    except (BadSignature, KeyError):
        messages.error(request, "Ошибка: неверная подпись данных.")
        return redirect("home")

    obj = get_object_or_404(UploadedImage, pk=pk)
    return render(request, "uploaded.html", {"obj": obj})

