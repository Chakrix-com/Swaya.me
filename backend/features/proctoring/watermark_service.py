"""
Steganographic watermark — embeds participant ID as zero-width characters.
"""
ZERO_WIDTH = {0: '\u200B', 1: '\u200C'}
REVERSE_ZW = {v: k for k, v in ZERO_WIDTH.items()}


def embed(text: str, participant_id: int) -> str:
    bits = format(participant_id, '032b')
    words = text.split()
    for i, bit in enumerate(bits):
        if i < len(words):
            words[i] = words[i] + ZERO_WIDTH[int(bit)]
    return ' '.join(words)


def decode(text: str) -> int | None:
    bits = []
    for word in text.split():
        if word and word[-1] in REVERSE_ZW:
            bits.append(str(REVERSE_ZW[word[-1]]))
    if len(bits) >= 32:
        return int(''.join(bits[:32]), 2)
    return None
