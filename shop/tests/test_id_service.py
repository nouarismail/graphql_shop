from django.test import SimpleTestCase
from graphql_relay import to_global_id

from shop.services.id_service import decode_global_id


class DecodeGlobalIdTests(SimpleTestCase):
    def test_returns_database_id_for_matching_type(self):
        result = decode_global_id(to_global_id("ProductType", 42), "ProductType", "Product")
        self.assertEqual(result, "42")

    def test_rejects_id_for_another_resource(self):
        with self.assertRaisesRegex(Exception, "^Invalid Product ID$"):
            decode_global_id(to_global_id("OrderType", 42), "ProductType", "Product")

    def test_rejects_malformed_or_non_numeric_ids(self):
        for value in (None, "", "not-base64!", to_global_id("ProductType", "abc"),
                      to_global_id("ProductType", "-1")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(Exception, "^Invalid Product ID$"):
                    decode_global_id(value, "ProductType", "Product")
