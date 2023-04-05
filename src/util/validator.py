from .plural import plural
from types import UnionType
from typing import Any, cast, get_args
from typing_extensions import TypedDict


class ValidationException(Exception):

    def __init__(self, path: list[str], detail: str, misc: Any = None):
        self.message = f"Validation error at /{'/'.join(path)}: {detail}"
        if misc:
            self.message += f" {misc}"
        self.path = path
        self.detail = detail
        self.misc = misc
        self.args = (self.message, path, detail, misc)


class Validator:

    def __init__(self, raise_exception: bool = False):
        self.__raise_exception = raise_exception

    def __error(self, path: list[str], detail: str, misc: Any = None):
        """
        Validation failure wrapper.
        """
        if self.__raise_exception:
            raise ValidationException(path, detail, misc)
        return False

    def validate(self, obj: object, t: type, __path: list[str] = []) -> bool:
        """
        Validate the object. This function operates similar to python's default `isinstance`
        function but with recursive validation suitable for runtime schema checking.

        If this validator was constructed with `raise_exception = True`, a failure in validation
        will raise an exception containing details about where and why validation failed. Otherwise,
        the function will simply return `False`.

        Note: An exception will always be raised if an unrecognized generic class is encountered.

        :param object: The object to validate.
        :param t: The type to check against.
        :param __path: Validation path used for internal error reporting.
        :returns: True/False, unless `raise_exception` is set.
        """
        # Unions require special handling because they can fail on one branch but still succeed
        if isinstance(t, UnionType):
            return self.__validate_Union(obj, t, __path)

        # Gather initial information about type and object
        type_is_typed_dict = hasattr(t, '__required_keys__')
        type_is_generic_type = hasattr(t, '__args__')
        type_name = t.__name__
        object_is_tuple_like = isinstance(obj, tuple) or isinstance(obj, list)
        object_name = type(cast(object, obj)).__name__  # Not sure why cast is required here

        # Basic (non subscripted) types can be compared directly
        if not (type_is_typed_dict or type_is_generic_type):
            if not isinstance(obj, t):
                return self.__error(__path,
                                    f"Incorrect type: Expected {type_name} got {object_name}")
            return True

        # Special type handlers
        if type_is_typed_dict:
            return self.__validate_TypedDict(obj, cast(type[TypedDict], t), __path)
        type_origin: type = getattr(t, '__origin__')
        if type_origin == tuple and object_is_tuple_like:
            return self.__validate_Tuple(obj, t, __path)

        # Base type validation
        if not isinstance(obj, type_origin):
            return self.__error(__path,
                                f"Incorrect base type: Expected {type_name} got {object_name}")

        # Standard type handlers
        if type_origin == list:
            return self.__validate_List(obj, t, __path)
        if type_origin == dict:
            return self.__validate_Dict(obj, t, __path)

        # Unrecognized generic class
        raise ValidationException(__path, f"Unsupported type {type_name}")

    # ======================= #
    #  Special type handlers  #
    # ======================= #

    def __validate_TypedDict(self, obj: Any, t: type[TypedDict], __path: list[str]):
        """
        Special validation handler for `TypedDict` objects.
        """
        # Make sure that required keys are present
        required_keys: list[str] = getattr(t, '__required_keys__')
        optional_keys: list[str] = getattr(t, '__optional_keys__')
        missing_required = [key for key in required_keys if key not in obj]
        if len(missing_required) > 0:
            return self.__error(__path, f"Missing required key{plural(missing_required)}: "
                                        f"{missing_required}")
        # Validate required and optional key types
        raw_types = t.__annotations__
        types: dict[str, type] = {key: raw_types[key] for key in required_keys} | \
            {key: get_args(raw_types[key])[0] for key in optional_keys if key in obj}
        return all([self.validate(obj[key], types[key], __path + [key]) for key in types])

    def __validate_Tuple(self, obj: Any, t: type, __path: list[str]):
        """
        Special validation handler for tuples. This function exists because many input formats (such
        as JSON) do not differentiate between tuples and lists, so it treats the two types as
        identical.
        """
        type_generic_args = cast(list[type], get_args(t))
        obj_cast = cast(list[Any], obj)
        arg_diff = len(type_generic_args) - len(obj_cast)
        if arg_diff != 0:
            err = 'many' if arg_diff < 0 else 'few'
            return self.__error(__path, f"Too {err} items: Expected {len(type_generic_args)} "
                                        f"got {len(obj_cast)}")
        enumerator = enumerate(type_generic_args)
        return all([self.validate(obj_cast[i], t, __path + [str(i)]) for i, t in enumerator])

    def __validate_Union(self, obj: Any, t: type, __path: list[str]):
        """
        Special validation handler for unions. This function exists because a union can have one or
        more acceptable branches fail, but overall the check must pass as long as at least one of
        them is valid.
        """
        print("union", get_args(t))
        exceptions: list[ValidationException] = []
        for u_type in get_args(t):
            try:
                name = f"[U:{u_type.__name__}]"
                if self.validate(obj, u_type, __path + [name]):
                    return True
            except ValidationException as e:
                exceptions.append(e)
        type_strings = [str(type.__name__) for type in get_args(t)]
        got_type = str(type(object).__name__)
        detail = f"Type {got_type} not valid for any of {type_strings}"
        return self.__error(__path, f"Union validation failure: {detail}", exceptions)

    # ======================== #
    #  Standard type handlers  #
    # ======================== #

    def __validate_List(self, obj: Any, t: type, __path: list[str]):
        """Validation handler for lists"""
        obj_cast = cast(list[Any], obj)
        required_type: type = cast(list[type], get_args(t))[0]
        enumerator = enumerate(obj_cast)
        return all([self.validate(x, required_type, __path + [str(i)]) for i, x in enumerator])

    def __validate_Dict(self, obj: Any, t: type, __path: list[str]):
        """Validation handler for dictionaries"""
        obj_cast = cast(dict[Any, Any], obj)
        key_type, value_type = cast(tuple[type, type], get_args(t))

        def test(key: Any, value: Any):
            return self.validate(key, key_type, __path + [key]) and \
                self.validate(value, value_type, __path + [key])
        return all([test(key, obj_cast[key]) for key in obj_cast])
