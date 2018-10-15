import json
import sys


PUBLIC_FIELDS = [x.split('.') for x in [
    "aliquot.experimental_strategy",
    "aliquot.node_id",
    "aliquot.submitter_id",
    "case.node_id",
    "case.project_id",
    "case.submitter_id",
    "read_group.sequencing_center",
    "sample.biospecimen_type",
    "sample.composition",
    "sample.node_id",
    "sample.submitter_id",
    "demographic.bmi",
    "demographic.weight",
    "demographic.height",
    "demographic.race",
    "demographic.gender",
    "demographic.ethnicity",
    "demographic.age_range",
    "read_group.library_strategy",
    "aliquot.experimental_strategy",
    "aliquot.analyte_isolation_method",
    "sample.biospecimen_anatomic_site_detail",
    "sample.biospecimen_anatomic_site",
    "project.code",
    "project.name"]]


def error(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
    exit(1)


def is_protected_field(key, context):
    return not any([context + [key] == field for field in PUBLIC_FIELDS])


def get_sanitized_value(value):
    result = None
    if value is None:
        result = None
    elif isinstance(value, str):
        result = "--------" if len(value) > 0 else ""
    elif isinstance(value, bool):
        result = False
    elif isinstance(value, float):
        result = 0.0
    elif isinstance(value, int):
        result = 0
    elif isinstance(value, list):
        result = []
    return result


def recursive_clear(d, context=None):
    """
    clear the values of a dictionary unless the value is another dictionary
    in which case recurse
    """
    if context is None:
        context = []

    for key in d:
        val = d[key]
        if type(val) == dict:
            recursive_clear(val, context=context + [key])
        else:
            if is_protected_field(key, context):
                d[key] = get_sanitized_value(d[key])


def sanitize_bundle(bundle):
    metadata = bundle['data_bundle']['user_metadata']
    recursive_clear(metadata)


def main(argv):
    if len(argv) != 3:
        error('Usage: python3 data_bleach.py INPUT.json OUTPUT.json')
    with open(argv[1], 'r') as fp:
        data = json.load(fp)
    for bundle in data:
        sanitize_bundle(bundle)
    with open(argv[2], 'w') as fp:
        json.dump(data, fp)


if __name__ == '__main__':
    main(sys.argv)

