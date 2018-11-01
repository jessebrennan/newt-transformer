#!/usr/local/bin/python3.6
import json
import logging
import sys

import argparse
import typing

from newt.transform.gen3old import Gen3Transformer
from newt.transform.gen3standard import Gen3Transformer as Gen3TransformerStandard, Bundle


def open_json_file(json_path):
    """opens and parses json file at path"""
    with open(json_path, 'r') as fp:
        return json.load(fp)


def _recursive_traversal(d, f):
    """
    recursively apply function f to each value in a dictionary

    f takes in the dictionary, the key, and the value
    """
    for k, v in d.items():
        if type(v) == dict:
            _recursive_traversal(v, f)
        else:
            f(d, k, v)


def fix_empty_strings(bundle_iterator):
    """
    As bundles come through, the metadata is cleaned to replace
    "" with None

    :param bundle_iterator: An iterator of :class:`Bundle`
    :return: a bundle iterator
    """
    def replace_empty_strings(d, k, v):
        if v == '':
            d[k] = None
    for bundle in bundle_iterator:
        try:
            metadata = bundle.metadata
        except AttributeError:
            metadata = bundle['metadata']
        _recursive_traversal(metadata, replace_empty_strings)
        yield bundle


def write_output(bundles: typing.Iterator[Bundle], out_file, pretty_print):
    with open(out_file, 'w') as fp:
        json.dump(list(bundles), fp, indent=2 if pretty_print else None)


def add_parser_to_subparser(sub_parser, parse_name, parse_help):
    """used to give all sub-parsers the same arguments"""
    parser = sub_parser.add_parser(parse_name, help=parse_help)

    parser.add_argument('input_json', help='metadata json to be transformed')
    parser.add_argument('--output-json', dest='output_json',
                        help='where to write transformed output.', required=False,
                        default='out.json')
    parser.add_argument('--pp', action='store_true', default=False,
                        help='pretty print output json.')


def main(argv=None):
    # If called programmatically (i.e. tests), we don't want to override logging info
    if not argv:
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser()

    transform_source = parser.add_subparsers(dest='transform_source', help='Metadata source format')

    add_parser_to_subparser(transform_source, 'gen3', 'Gen3 metadata as formatted by sheepdog exporter')
    add_parser_to_subparser(transform_source, 'new', 'Gen3 metadata as formatted by sheepdog exporter')

    options = parser.parse_args(argv)

    # This shouldn't be necessary and is either a bug with argparse, or indication of its misuse
    if not options.transform_source:
        parser.print_usage()
        exit(1)
    json_dict = open_json_file(options.input_json)
    if options.transform_source == 'gen3':
        transformer = Gen3Transformer(json_dict)
    elif options.transform_source == 'new':
        transformer = Gen3TransformerStandard(json_dict)
    else:
        raise ValueError(f'Invalid metadata source format {options.transform_source}')

    bundle_iterator = transformer.transform()
    write_output(fix_empty_strings(bundle_iterator), options.output_json, options.pp)
