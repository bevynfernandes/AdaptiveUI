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
