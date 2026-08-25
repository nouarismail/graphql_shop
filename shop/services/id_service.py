from graphql_relay import from_global_id


def decode_global_id(value, expected_type, label):
    try:
        type_name, database_id = from_global_id(value)
    except (TypeError, ValueError, UnicodeDecodeError):
        raise Exception(f"Invalid {label} ID")

    if type_name != expected_type or not database_id.isdigit():
        raise Exception(f"Invalid {label} ID")

    return database_id
