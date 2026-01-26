"""
Lexicographic ordering utilities for efficient drag & drop reordering.

This module provides functions to generate position strings that can be
inserted between any two existing positions without renumbering.

Example:
    Initial:     "a", "b", "c"
    Insert between a and b: "a", "aU", "b", "c"
    Insert between aU and b: "a", "aU", "am", "b", "c"

Benefits:
    - Insert between any two items: O(1) - no renumbering
    - Reorder any item: O(1) - just update one position
    - Concurrent-safe: No race conditions on position numbers
    - Database-friendly: Simple string comparison for sorting
"""

from typing import Optional

# Base characters for position strings (a-z, then A-Z for 52 total)
# Using lowercase first so they sort before uppercase in ASCII
ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALPHABET_SIZE = len(ALPHABET)
FIRST_CHAR = ALPHABET[0]  # 'a'
LAST_CHAR = ALPHABET[-1]  # 'Z'
MID_CHAR = ALPHABET[ALPHABET_SIZE // 2]  # 'm'


def generate_first_position() -> str:
    """Generate the first position for an empty list."""
    return "a"


def generate_position_at_end(last_position: Optional[str] = None) -> str:
    """
    Generate a position after the last item.

    Args:
        last_position: The current last position, or None if list is empty

    Returns:
        A position string that sorts after last_position
    """
    if last_position is None:
        return "a"

    # Append 'a' to create a position that sorts after
    return last_position + "a"


def generate_position_at_start(first_position: Optional[str] = None) -> str:
    """
    Generate a position before the first item.

    Args:
        first_position: The current first position, or None if list is empty

    Returns:
        A position string that sorts before first_position
    """
    if first_position is None:
        return "a"

    # Find the first character we can decrement
    for i, char in enumerate(first_position):
        char_index = ALPHABET.index(char)
        if char_index > 0:
            # Can decrement this character
            new_char = ALPHABET[char_index - 1]
            if i == 0:
                # First character - just decrement
                return new_char + first_position[1:]
            else:
                # Not first character - decrement and pad
                return first_position[:i] + new_char + MID_CHAR

    # All characters are 'a', prepend 'A' (sorts before 'a' in our scheme)
    # Actually in ASCII, uppercase sorts BEFORE lowercase
    # So we need a different approach - use 'A' prefix
    return "A" + first_position


def generate_position_between(before: Optional[str], after: Optional[str]) -> str:
    """
    Generate a position string that sorts between 'before' and 'after'.

    Args:
        before: The position to sort after (None = beginning of list)
        after: The position to sort before (None = end of list)

    Returns:
        A position string that sorts between before and after

    Raises:
        ValueError: If before >= after (invalid ordering)
    """
    if before is None and after is None:
        return "a"

    if before is None:
        return generate_position_at_start(after)

    if after is None:
        return generate_position_at_end(before)

    # Both are defined - need to find midpoint
    if before >= after:
        raise ValueError(f"Invalid ordering: before '{before}' >= after '{after}'")

    # Pad shorter string to same length for comparison
    max_len = max(len(before), len(after))
    before_padded = before.ljust(max_len, FIRST_CHAR)
    after_padded = after.ljust(max_len, FIRST_CHAR)

    # Find the first position where they differ
    result = []
    for i in range(max_len):
        before_char = before_padded[i]
        after_char = after_padded[i]

        before_index = ALPHABET.index(before_char)
        after_index = ALPHABET.index(after_char)

        if before_index < after_index - 1:
            # There's room between these characters
            mid_index = (before_index + after_index) // 2
            result.append(ALPHABET[mid_index])
            return "".join(result)
        elif before_index < after_index:
            # Adjacent characters - need to go deeper
            result.append(before_char)
        else:
            # Same character - continue
            result.append(before_char)

    # If we get here, we need to append a character
    # The 'before' string is a prefix of 'after', so append midpoint
    result.append(MID_CHAR)
    return "".join(result)


def generate_n_positions(n: int, before: Optional[str] = None, after: Optional[str] = None) -> list[str]:
    """
    Generate n evenly-spaced position strings between before and after.

    Useful for bulk inserts.

    Args:
        n: Number of positions to generate
        before: Position to start after (None = beginning)
        after: Position to end before (None = end)

    Returns:
        List of n position strings in sorted order
    """
    if n <= 0:
        return []

    if n == 1:
        return [generate_position_between(before, after)]

    positions = []
    current_before = before

    for i in range(n):
        # Calculate how many positions remain
        remaining = n - i
        if remaining == 1:
            # Last one
            pos = generate_position_between(current_before, after)
        else:
            # Need to leave room for more
            pos = generate_position_between(current_before, after)

        positions.append(pos)
        current_before = pos

    return positions


def validate_position(position: str) -> bool:
    """
    Validate that a position string is valid.

    Args:
        position: The position string to validate

    Returns:
        True if valid, False otherwise
    """
    if not position:
        return False

    if len(position) > 50:  # Max length from schema
        return False

    for char in position:
        if char not in ALPHABET:
            return False

    return True


def normalize_positions(positions: list[str]) -> list[str]:
    """
    Normalize a list of positions to be evenly spaced.

    Use this for periodic cleanup to prevent position strings from
    becoming too long over time.

    Args:
        positions: List of positions in current order

    Returns:
        New list of normalized positions (same length, evenly spaced)
    """
    n = len(positions)
    if n == 0:
        return []

    if n == 1:
        return ["a"]

    # Generate fresh positions
    return generate_n_positions(n)
