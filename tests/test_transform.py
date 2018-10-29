import datetime
import json
import os
import unittest
import uuid

import jsonschema
from pathlib import Path

from newt.main import main
from tests.schemas import schema as output_schema


def message(message: str):
    print("{}: {}".format(datetime.datetime.now(), message))


class AbstractTransformerTest:

    @classmethod
    def setUpClass(cls):
        cls.test_path = Path(__file__).parents[0]
        cls.test_file = cls.test_path / 'test_data/topmed-public.json'
        cls.out_file = cls.test_path / f'{str(uuid.uuid4())}.tmp.json'

    def setUp(self):
        message('Make sure the output file doesn\'t exist yet')
        with self.assertRaises(FileNotFoundError):
            with open(self.out_file, 'r'):
                pass

    def _get_output_json(self):
        with open(self.out_file, 'r') as fp:
            return json.load(fp)

    def _validate_output(self):
        message('Make sure that the output file was actually created')
        assert os.path.isfile(str(self.out_file))

    def tearDown(self):
        message('Clean up the output file if there is one')
        try:
            os.remove(self.out_file)
        except FileNotFoundError:
            pass


class TestSheepdogGen3Transforming(AbstractTransformerTest, unittest.TestCase):

    def _validate_output(self):
        super()._validate_output()

        with open(self.test_path / 'test_data/transformer_sample_output.json', 'r',) as fp:
            valid_output = json.load(fp)
        valid_bundle_did = valid_output[0]['bundle_did']
        valid_output = valid_output[0]

        test_output = self._get_output_json()

        # since bundle did is changed each time the transformer runs, just normalize it for comparison
        for bundle in test_output:
            bundle['bundle_did'] = valid_bundle_did
        self.assertTrue(valid_output in test_output)

    def test_sheepdog_gen3_transforming(self):
        message('Run the transformer on sheepdog\'s output')
        argv = ['gen3', str(self.test_file), '--output-json', str(self.out_file)]
        message(f'Passing args: {" ".join(argv)}')
        main(argv)

        self._validate_output()


class TestSheepdogGen3TransformingStandard(AbstractTransformerTest, unittest.TestCase):
    """Test new transformer against schema"""

    def _validate_output(self):
        super()._validate_output()
        # check the output against the agreed upon schema!
        output_json = self._get_output_json()
        for bundle in output_json:
            jsonschema.validate(bundle, output_schema)

    def test_sheepdog_gen3_transforming(self):
        message('Run the transformer on sheepdog\'s output')
        argv = ['new', str(self.test_file), '--output-json', str(self.out_file), '--pp']
        message(f'Passing args: {" ".join(argv)}')
        main(argv)

        self._validate_output()
