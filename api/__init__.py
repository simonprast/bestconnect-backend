# This file shall demonstrate how single functions can be dynamically replaced within
# a pip package without requiring a fork or any changes to the package itself.
# This could only be implemented using functions, not using objects.
# For documentation purposes, this piece of code is being left here.

"""
import graphql

from api.format_error import format_error as format_error_custom

graphql.error.format_error = lambda error: format_error_custom(error)
"""


# Another file: .format_error.py
"""
# Original file: graphql.error.format_error
# This file adds the 'code' of the raised exceptions to the return string of the GraphQL error.
from graphql.error.base import GraphQLError

# Necessary for static type checking
if False:  # flake8: noqa
    from typing import Any, Dict


def format_error(error):
    # type: (Exception) -> Dict[str, Any]
    # Protect against UnicodeEncodeError when run in py2 (#216)
    try:
        message = str(error)
        if error.code:
            code = str(error.code)
        else:
            code = None
    except UnicodeEncodeError:
        message = error.message.encode("utf-8")  # type: ignore
    formatted_error = {"message": message, "code": code}  # type: Dict[str, Any]
    if isinstance(error, GraphQLError):
        if error.locations is not None:
            formatted_error["locations"] = [
                {"line": loc.line, "column": loc.column} for loc in error.locations
            ]
        if error.path is not None:
            formatted_error["path"] = error.path

        if error.extensions is not None:
            formatted_error["extensions"] = error.extensions

    return formatted_error
"""
