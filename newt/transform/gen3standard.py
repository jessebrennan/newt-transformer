import datetime
import json
import typing
import uuid
from collections import namedtuple

from newt.transform.abstract import AbstractTransformer


"""A metadata link is all the information necessary to get metadata
for a particular field from the field that links to it."""
MetadataLink = namedtuple('MetadataLink', ['source_field_name', 'linked_field_name', 'link_name'])


class Bundle(dict):
    """represent a bundle but act like a dict"""

    def __init__(self, metadata_dict):
        """Initialize the bundle structure to match the schema"""
        super().__init__()

        now = str(datetime.datetime.now(datetime.timezone.utc).isoformat())

        self.metadata = metadata_dict
        self.data_objects = {}
        self.data_bundle = {
            'id': str(uuid.uuid4()),
            'data_object_ids': [],
            'created': now,
            'updated': now,
            'version': now,
            # FIXME LAST WE WERE MAKING SURE THE BUNDLE SCHEMA MATCHED
            # TODO: Do we create bundle checksums???
            ''
            'user_metadata': metadata_dict,
        }

        self['data_bundle'] = self.data_bundle
        self['data_objects'] = self.data_objects

    def add_metadata_field(self,
                           metadata_source: dict,
                           source_field_name: str,
                           linked_field_name: str,
                           link_name: str):
        """
        Add a metadata field to the bundle

        :param metadata_source: this is the dictionary containing all metadata entries (from sheepdog)
        :param source_field_name: the metadata field that contains the link
        :param linked_field_name: the metadata field that is linked to
        :param link_name: the actual name of the link in the source_field. Usually there is some subtle variation
        """
        if linked_field_name == 'program':
            # Since gen3 export exports a single program, we just grab the only value
            self.metadata[linked_field_name] = list(metadata_source[linked_field_name].values())[0]
        elif source_field_name in self.metadata.keys():
            # Get the id of the specific item we want to add
            linked_field_key = self.metadata[source_field_name]['link_fields'][link_name]
            # Get the dictionary that goes with that specific item
            linked_field_dict = metadata_source[linked_field_name][linked_field_key]
            # Add it to this bundle's metadata
            self.metadata[linked_field_name] = linked_field_dict
        else:
            # When the item is a child of an existing field
            # Get the ID from the item we already have
            existing_id = self.metadata[linked_field_name]['node_id']
            # Go to the list of entries we want to look in
            entries = metadata_source[source_field_name]
            # Look for the entry that links to our item
            for key in entries:
                entry = entries[key]
                if entry['link_fields'][link_name] == existing_id:
                    linked_field_dict = entry
            # Add it to this bundle's metadata
            self.metadata[source_field_name] = linked_field_dict

    def add_file(self, objects_source: dict, link_source: str):
        """
        Add a file to the bundle

        :param objects_source: this is the dictionary containing all data_objects in a dict keyed by their ids
        :param link_source: This is the metadata field that links to the file by giving its uuid
        """
        source_dict = self.metadata[link_source]
        file_key = source_dict['object_id']
        file_dict = objects_source[file_key]

        # The format of the bundle is a little broken. Here we fix it:
        # put filename in file_dict since it's only stored in the metadata for some reason...
        file_dict['name'] = source_dict['file_name']
        # TODO: If we can remove dependency on the 'name' field than to add bundles, we can just copy over verbatim

        # actually add the file!
        self.data_objects[file_key] = file_dict
        self.data_bundle['data_object_ids'].append(file_key)

    def to_json(self) -> str:
        return json.dumps(self)


class Gen3Transformer(AbstractTransformer):

    @staticmethod
    def _build_data_objects_dict(data_objects: list):
        return {entry['id']: entry for entry in data_objects}

    @staticmethod
    def _build_metadata_dict(input_metadata):
        def build_metadata_field(metadata, field_name: str, key: str):
            """
            Builds dict from metadata where key is node_id, value is the corresponding metadata
            """
            return {entry[key]: entry for entry in metadata[field_name]}
        for field in input_metadata:
            # Working around details of gen3 data model
            if field == 'project' or field == 'program':
                key = 'id'
            else:
                key = 'node_id'
            input_metadata[field] = build_metadata_field(input_metadata, field, key)
        return input_metadata

    def __init__(self, input_dict: dict) -> None:
        super().__init__()
        self._metadata = self._build_metadata_dict(input_dict['metadata'])
        self._data_objects_dict = self._build_data_objects_dict(input_dict['data_objects'])
        self._metadata_links = [MetadataLink('aligned_reads_index', 'submitted_aligned_reads',
                                             'submitted_aligned_reads_files.id'),
                                MetadataLink('submitted_aligned_reads', 'read_group', 'read_groups.id#1'),
                                MetadataLink('read_group', 'aliquot', 'aliquots.id'),
                                MetadataLink('aliquot', 'sample', 'samples.id#1'),
                                MetadataLink('sample', 'case', 'cases.id'),
                                MetadataLink('case', 'study', 'studies.id#1'),
                                MetadataLink('demographic', 'case', 'cases.id'),
                                MetadataLink('study', 'project', 'projects.id'),
                                MetadataLink('project', 'program', 'id')
                                ]

    def _build_bundle(self, metadata_dict: dict):
        bundle = Bundle(metadata_dict)

        for link_details in self._metadata_links:
            bundle.add_metadata_field(self._metadata, *link_details)

        bundle.add_file(self._data_objects_dict, 'aligned_reads_index')
        bundle.add_file(self._data_objects_dict, 'submitted_aligned_reads')

        return bundle

    def transform(self) -> typing.Iterator[Bundle]:
        def index_to_bundle(aligned_read_index):
            # prepackage the bundle with the tree root that is used to fill in the rest of the fields
            metadata_dict = {'aligned_reads_index': aligned_read_index}
            return self._build_bundle(metadata_dict)
        return (index_to_bundle(aligned_read_index)
                for aligned_read_index in self._metadata['aligned_reads_index'].values())
