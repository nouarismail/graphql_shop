"""Documentation must generate without database or external services."""
from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIClient


@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class OpenApiTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_public_documentation(self):
        response = self.client.get('/api/docs/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SwaggerUIBundle')
        response = self.client.get('/api/schema/', HTTP_ACCEPT='application/vnd.oai.openapi+json')
        self.assertEqual(response.status_code, 200)
        self.schema = response.json()
        self.assertEqual(self.schema['components']['securitySchemes']['BearerAuth'], {
            'type': 'http', 'scheme': 'bearer', 'bearerFormat': 'JWT',
        })
        paths = self.schema['paths']
        self.assertNotIn('/graphql/', paths)
        self.assertIn('201', paths['/api/auth/signup/']['post']['responses'])
        self.assertIn('204', paths['/api/auth/logout/']['post']['responses'])
        self.assertEqual(paths['/api/categories/']['get']['responses']['200']['content']['application/json']['schema']['type'], 'array')
        self.assertEqual(paths['/api/orders/']['get']['responses']['200']['content']['application/json']['schema']['type'], 'array')
        self.assertIn('multipart/form-data', paths['/api/products/import/']['post']['requestBody']['content'])
        self.assertIn('text/csv', paths['/api/products/export/']['get']['responses']['200']['content'])
        item = paths['/api/orders/{id}/items/{item_id}/']
        self.assertIn('200', item['delete']['responses'])
        self.assertNotIn('requestBody', item['delete'])
        self.assertIn('requestBody', item['patch'])
        self.assertIn('requestBody', paths['/api/products/ai-search/']['post'])
