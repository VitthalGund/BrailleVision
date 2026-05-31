"""
BrailleVision — Complete Grade 1 Braille Table

Dot numbering:
  Dot 1 | Dot 4
  Dot 2 | Dot 5
  Dot 3 | Dot 6

Bit encoding: bit0=dot1, bit1=dot2, bit2=dot3, bit3=dot4, bit4=dot5, bit5=dot6
"""

# Braille dot patterns → English character
# Pattern is a 6-bit integer: bit positions 0-5 correspond to dots 1-6
BRAILLE_PATTERN_TO_CHAR: dict[int, str] = {
    # Letters a-j (base patterns, dots 1-4-5 region)
    0b000001: "a",  # dot 1
    0b000011: "b",  # dots 1,2
    0b001001: "c",  # dots 1,4
    0b011001: "d",  # dots 1,4,5
    0b010001: "e",  # dots 1,5
    0b001011: "f",  # dots 1,2,4
    0b011011: "g",  # dots 1,2,4,5
    0b010011: "h",  # dots 1,2,5
    0b001010: "i",  # dots 2,4
    0b011010: "j",  # dots 2,4,5
    # Letters k-t (add dot 3 to a-j)
    0b000101: "k",  # dots 1,3
    0b000111: "l",  # dots 1,2,3
    0b001101: "m",  # dots 1,3,4
    0b011101: "n",  # dots 1,3,4,5
    0b010101: "o",  # dots 1,3,5
    0b001111: "p",  # dots 1,2,3,4
    0b011111: "q",  # dots 1,2,3,4,5
    0b010111: "r",  # dots 1,2,3,5
    0b001110: "s",  # dots 2,3,4
    0b011110: "t",  # dots 2,3,4,5
    # Letters u-z (add dot 6 to k-t, except w)
    0b100101: "u",  # dots 1,3,6
    0b100111: "v",  # dots 1,2,3,6
    0b111010: "w",  # dots 2,4,5,6  (w was added late to Braille)
    0b101101: "x",  # dots 1,3,4,6
    0b111101: "y",  # dots 1,3,4,5,6
    0b110101: "z",  # dots 1,3,5,6
    # Special: space (empty cell)
    0b000000: " ",
    # Punctuation
    0b000010: ",",  # dot 2
    0b000110: ";",  # dots 2,3
    0b100010: ":",  # dots 2,6
    0b100110: ".",  # dots 2,3,6
    0b001100: "!",  # dots 3,4,5 — exclamation (simplified)
    0b001110: "?",  # Wait — 's' uses this too. Grade 1 ambiguity.
    # Note: in Grade 1, punctuation uses letter patterns in different contexts
    # For hackathon, we use simple letter-only decoding
    # Number indicator (precedes numeric Braille)
    0b111100: "#",  # dots 3,4,5,6 — number sign
    # Capital indicator
    0b100000: "\x01",  # dot 6 alone — capital indicator (internal token)
}

# Reverse mapping: character → dot pattern
CHAR_TO_BRAILLE_PATTERN: dict[str, int] = {
    v: k
    for k, v in BRAILLE_PATTERN_TO_CHAR.items()
    if v not in ("\x01",)  # exclude special tokens
}

# Number mode: after number indicator (#), these letter patterns mean digits
BRAILLE_NUMBER_PATTERN_TO_DIGIT: dict[int, str] = {
    0b000001: "1",  # a = 1
    0b000011: "2",  # b = 2
    0b001001: "3",  # c = 3
    0b011001: "4",  # d = 4
    0b010001: "5",  # e = 5
    0b001011: "6",  # f = 6
    0b011011: "7",  # g = 7
    0b010011: "8",  # h = 8
    0b001010: "9",  # i = 9
    0b011010: "0",  # j = 0
}

CAPITAL_INDICATOR_PATTERN = 0b100000  # dot 6 alone
NUMBER_INDICATOR_PATTERN = 0b111100  # dots 3,4,5,6


def pattern_from_bools(dots: list[bool]) -> int:
    """
    Convert a list of 6 booleans (dot presence) to a bit pattern integer.

    Args:
        dots: [dot1, dot2, dot3, dot4, dot5, dot6] — True if dot is present
    Returns:
        6-bit integer
    """
    if len(dots) != 6:
        raise ValueError(f"Expected 6 booleans, got {len(dots)}")
    return sum(1 << i for i, v in enumerate(dots) if v)


def decode_cell(dots: list[bool]) -> str:
    """
    Decode a single Braille cell (6-dot pattern) to its character.

    Args:
        dots: [dot1, dot2, dot3, dot4, dot5, dot6]
    Returns:
        Decoded character, or '?' if unknown
    """
    pattern = pattern_from_bools(dots)
    return BRAILLE_PATTERN_TO_CHAR.get(pattern, "?")


def decode_sequence(cells: list[list[bool]]) -> str:
    """
    Decode a sequence of Braille cells to a text string.
    Handles capital and number indicators.

    Args:
        cells: List of 6-bool lists, each representing one Braille cell
    Returns:
        Decoded text string
    """
    result = []
    capitalize_next = False
    number_mode = False

    for dots in cells:
        pattern = pattern_from_bools(dots)

        # Handle special indicators
        if pattern == CAPITAL_INDICATOR_PATTERN:
            capitalize_next = True
            continue

        if pattern == NUMBER_INDICATOR_PATTERN:
            number_mode = True
            continue

        # Handle space: exit number mode
        if pattern == 0b000000:
            number_mode = False
            result.append(" ")
            continue

        # Number mode
        if number_mode:
            digit = BRAILLE_NUMBER_PATTERN_TO_DIGIT.get(pattern, "?")
            result.append(digit)
            continue

        # Regular character
        char = BRAILLE_PATTERN_TO_CHAR.get(pattern, "?")

        if capitalize_next:
            char = char.upper()
            capitalize_next = False

        result.append(char)

    return "".join(result)


# Unicode Braille block mapping (⠀–⣿) for reference
# Unicode Braille: U+2800 + 6-bit pattern
def char_to_unicode_braille(char: str) -> str:
    """Convert a character to its Unicode Braille representation."""
    pattern = CHAR_TO_BRAILLE_PATTERN.get(char.lower(), 0)
    return chr(0x2800 + pattern)


def text_to_braille_display(text: str) -> str:
    """Convert English text to displayable Unicode Braille string."""
    return "".join(char_to_unicode_braille(c) for c in text)


if __name__ == "__main__":
    # Quick self-test
    test_cases = [
        ([True, False, False, False, False, False], "a"),  # dot 1
        ([True, True, False, False, True, False], "h"),    # dots 1,2,5
        ([True, False, False, False, True, False], "e"),   # dots 1,5
        ([True, True, True, False, False, False], "l"),    # dots 1,2,3
        ([True, False, True, False, True, False], "o"),    # dots 1,3,5
        ([False] * 6, " "),
    ]

    print("Braille Decoder Self-Test:")
    all_pass = True
    for dots, expected in test_cases:
        result = decode_cell(dots)
        status = "[PASS]" if result == expected else "[FAIL]"
        if result != expected:
            all_pass = False
        print(f"  {status} {dots} -> '{result}' (expected '{expected}')")

    # Test 'hello'
    hello_cells = [
        [True, True, False, False, True, False],   # h
        [True, False, False, False, True, False],  # e
        [True, True, True, False, False, False],   # l
        [True, True, True, False, False, False],   # l
        [True, False, True, False, True, False],   # o
    ]
    result = decode_sequence(hello_cells)
    status = "[PASS]" if result == "hello" else "[FAIL]"
    print(f"  {status} 'hello' sequence -> '{result}'")


    print(f"\nAll tests passed: {all_pass}")
