class ToggleVar:
    """
    ToggleVar is a class for managing boolean state values.

    It contains a name and boolean state value. The state can be get, set, toggled between True/False, and converted to string representations.

    The class allows managing named boolean flags in an application.
    """

    __slots__ = ("name", "state")

    def __init__(self, name: str, bool_state: bool):
        """Initializes a ToggleVar instance.

        Args:
            name (str): The name of the toggle variable.
            bool_state (bool): The initial state of the toggle variable.
        """

        self.name = name
        self.state = bool_state

    def set(self, new: bool) -> bool:
        """Sets the state of the ToggleVar instance.

        Args:
            new (bool): The new state to set.

        Returns:
            bool: The new state after setting.
        """

        self.state = new
        return new

    def toggle(self) -> bool:
        """Toggles the state of the ToggleVar instance.

        Toggles the current state
        """
        self.state = not self.state
        return self.state

    def pp_get(self) -> str:
        """Gets a pretty-printed string representation of the ToggleVar instance.

        Returns:
            str: The pretty-printed string representation.
        """
        return "Enabled" if self.state else "Disabled"

    def __str__(self) -> str:
        """Gets a string representation of the ToggleVar instance.

        Returns:
            str: The string representation.
        """
        return str(self.state)

    def __bool__(self) -> bool:
        """Gets the boolean value of the ToggleVar instance.

        Returns:
            bool: The boolean value.
        """
        return self.state

    __repr__ = __str__


class API:
    """
    Represents an API with the ability to switch between different endpoints.

    Attributes:
        _api_list (tuple[str]): A tuple containing the list of API endpoints.
        _current (int): The index of the current API endpoint in the _api_list.

    Methods:
        __init__(self, default: str, backups: tuple[str] = None): Initializes the API object.
        use_api(self, index: int): Sets the current API endpoint using the provided index.
        increment_api(self): Increments the current API endpoint to the next one in the list.
        current(self) -> str: Returns the current API endpoint without the HTTP Protocol.
        dget(self) -> dict: Returns a dictionary representation of the API object.
        __str__(self) -> str: Returns a string representation of the API object.
    """

    __slots__ = ("_api_list", "_current")

    def __init__(self, default: str, backups: tuple[str] = None):
        if backups is None:
            backups = ()

        self._api_list = (default,) + backups
        self._current = 0

    def use_api(self, index: int):
        """
        Sets the current API to be used.

        Args:
            index (int): The index of the API to be used.
        """
        self._current = index

    def increment_api(self):
        """
        Increments the current API to the next one in the list.

        Raises:
            ValueError: If the current API is already the last one in the list.
        """
        if self._api_list.index(self.current()) + 1 >= len(self._api_list):
            raise ValueError("Unable to increment API! (reached end of list)")

        self._current += 1

    def current(self) -> str:
        """Returns the current API without the HTTP Protocol"""
        return self._api_list[self._current]

    def dget(self) -> dict:
        return {
            "_api_list": self._api_list,
            "_current": self._current,
            "current": self.current(),
        }

    def __str__(self) -> str:
        return f"https://{self.current()}"

    __repr__ = __str__
