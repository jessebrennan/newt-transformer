import json
import os
import unittest
import uuid
from pathlib import Path

from scripts.data_bleach import main, PUBLIC_FIELDS


class TestDataBleach(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_path = Path(__file__).parents[0]
        cls.test_file = cls.test_path / 'test_data/bleach_test_data.json'
        cls.out_file = cls.test_path / f'{str(uuid.uuid4())}.tmp.json'

    def setUp(self):
        with self.assertRaises(FileNotFoundError):
            with open(self.out_file, 'r'):
                pass

    def tearDown(self):
        try:
            os.remove(self.out_file)
        except FileNotFoundError:
            pass

    def _get_output_json(self):
        with open(self.out_file, 'r') as fp:
            return json.load(fp)

    @staticmethod
    def _field_is_protected(field, sub_field):
        return not any(field == public_field and sub_field == public_sub_field
                       for public_field, public_sub_field in PUBLIC_FIELDS)

    @staticmethod
    def _is_sanitized(value):
        # These are the values that the sanitizer may set to
        return value in ['', "--------", False, 0, 0.0, [], None]

    def _properly_sanitized(self, metadata):
        for field in metadata:
            if type(metadata[field]) != dict:
                # the field should be cleared (sanitized)
                assert self._is_sanitized(metadata[field])
            else:
                for sub_field in metadata[field]:
                    if self._field_is_protected(field, sub_field) \
                            and type(metadata[field][sub_field]) != dict:
                        # TODO: currently, if a dict is a public field its subfields are still
                        # TODO: sanitized. This may not be the desired behavior
                        assert self._is_sanitized(metadata[field][sub_field])

    def _validate_output(self):
        # check the output against the agreed upon schema!
        assert os.path.isfile(str(self.out_file))
        output_json = self._get_output_json()
        for bundle in output_json:
            metadata = bundle['data_bundle']['user_metadata']
            # TODO: make some asserts here
            self._properly_sanitized(metadata)

    def test_bleach(self):
        argv = ['program_name', str(self.test_file), str(self.out_file)]
        main(argv)

        self._validate_output()
