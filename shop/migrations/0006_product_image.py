from django.db import migrations, models
import shop.models


class Migration(migrations.Migration):
    dependencies = [("shop", "0005_auditevent")]
    operations = [
        migrations.AddField(
            model_name="product",
            name="image",
            field=models.ImageField(blank=True, max_length=255, upload_to=shop.models.product_image_path),
        ),
    ]
