from io import BytesIO
from types import SimpleNamespace

from PIL import Image
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from graphql_relay import to_global_id
from rest_framework.test import APIClient
from storages.backends.s3 import S3Storage

from shop.graphql.schema import schema
from shop.models import AuditEvent, Category, Product
from shop.services import product_service


def uploaded_image():
    output = BytesIO()
    Image.new('RGB', (2, 2), 'red').save(output, format='PNG')
    return SimpleUploadedFile('photo.png', output.getvalue(), content_type='image/png')


class ProductImageTests(TestCase):
    def setUp(self):
        cache.clear()
        self.category = Category.objects.create(name='Images')
        self.user = User.objects.create_superuser(username='image-admin', password='test-password')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def create_product(self):
        response = self.client.post('/api/products/', {
            'name': 'Camera', 'price': '12.00', 'category_id': self.category.pk,
            'image': uploaded_image(),
        }, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        return Product.objects.get(pk=response.data['id'])

    def test_upload_read_replace_preserve_and_clear(self):
        product = self.create_product()
        original = product.image.name
        self.assertTrue(original.startswith('products/'))
        self.assertNotIn('photo', original)
        self.assertTrue(product.image.storage.exists(original))
        url = f'/api/products/{product.pk}/'
        self.client.get('/api/products/')  # Populate the list cache before replacing.
        response = self.client.patch(url, {'image': uploaded_image()}, format='multipart')
        self.assertEqual(response.status_code, 200, response.data)
        product.refresh_from_db()
        replacement = product.image.name
        self.assertNotEqual(original, replacement)
        self.assertIn(replacement, self.client.get('/api/products/').data['results'][0]['image'])
        event = AuditEvent.objects.filter(object_type='shop.product', action='update').first()
        self.assertEqual(event.changes['image'], {'before': original, 'after': replacement})
        self.client.patch(url, {'name': 'Renamed'}, format='json')
        product.refresh_from_db()
        self.assertEqual(product.image.name, replacement)
        # Existing GraphQL writes must also preserve the image.
        product_service.update_product(to_global_id('ProductType', product.pk), SimpleNamespace(
            name='GraphQL update', description='', price=12, category_id=self.category.pk))
        product.refresh_from_db()
        self.assertEqual(product.image.name, replacement)
        result = schema.execute('query($id: ID!) { product(id: $id) { image } }',
                                variable_values={'id': to_global_id('ProductType', product.pk)})
        self.assertIsNone(result.errors)
        self.assertEqual(result.data['product']['image'], product.image.url)
        response = self.client.patch(url, {'image': None}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['image'])
        product.refresh_from_db()
        self.assertFalse(product.image)
        result = schema.execute('query($id: ID!) { product(id: $id) { image } }',
                                variable_values={'id': to_global_id('ProductType', product.pk)})
        self.assertIsNone(result.errors)
        self.assertIsNone(result.data['product']['image'])

    def test_invalid_and_oversized_uploads(self):
        product = Product.objects.create(name='Empty', price=1, category=self.category)
        url = f'/api/products/{product.pk}/'
        invalid = SimpleUploadedFile('fake.png', b'not an image', content_type='image/png')
        response = self.client.patch(url, {'image': invalid}, format='multipart')
        self.assertEqual(response.status_code, 400)
        with override_settings(PRODUCT_IMAGE_MAX_BYTES=1):
            response = self.client.patch(url, {'image': uploaded_image()}, format='multipart')
        self.assertEqual(response.status_code, 400)
        output = BytesIO()
        Image.new('RGB', (2, 2)).save(output, format='GIF')
        response = self.client.patch(url, {'image': SimpleUploadedFile(
            'unsupported.gif', output.getvalue(), content_type='image/gif',
        )}, format='multipart')
        self.assertEqual(response.status_code, 400)
        product.refresh_from_db()
        self.assertFalse(product.image)

    def test_anonymous_and_customer_cannot_upload(self):
        product = Product.objects.create(name='Empty', price=1, category=self.category)
        self.client.force_authenticate(None)
        response = self.client.patch(f'/api/products/{product.pk}/', {'image': uploaded_image()}, format='multipart')
        self.assertIn(response.status_code, (401, 403))
        customer = User.objects.create_user(username='image-customer')
        self.client.force_authenticate(customer)
        response = self.client.patch(f'/api/products/{product.pk}/', {'image': uploaded_image()}, format='multipart')
        self.assertEqual(response.status_code, 403)

    def test_public_s3_url_uses_browser_origin(self):
        storage = S3Storage(access_key='test', secret_key='test', bucket_name='product-images',
                            endpoint_url='http://minio:9000', custom_domain='localhost:9000/product-images',
                            url_protocol='http:', querystring_auth=False)
        self.assertEqual(storage.url('products/example.png'),
                         'http://localhost:9000/product-images/products/example.png')
