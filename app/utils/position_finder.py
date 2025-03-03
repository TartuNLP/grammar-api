def find_correction_spans(orig_sent: str, corr_sent: str, init_pos: int) -> (list, int):
    """
    Compares two sentences and returns a list of correction spans along with the updated position offset.
    Each correction contains the original value, its start and end positions, and a possible replacement.
    """
    corrections = []
    orig_tokens = orig_sent.split()
    corr_tokens = corr_sent.split()
    pos = init_pos
    i = j = 0

    while i < len(orig_tokens) or j < len(corr_tokens):
        # advance if tokens are identical
        while i < len(orig_tokens) and j < len(corr_tokens) and orig_tokens[i] == corr_tokens[j]:
            pos += len(orig_tokens[i]) + (1 if i < len(orig_tokens) - 1 else 0)
            i += 1
            j += 1

        if i >= len(orig_tokens) and j >= len(corr_tokens):
            break

        start_pos = pos
        end_i = i
        end_j = j
        matched = False

        while end_i < len(orig_tokens) and not matched:
            for k in range(j, min(len(corr_tokens), j + 3)):
                if end_i + 1 < len(orig_tokens):
                    if orig_tokens[end_i] == corr_tokens[k]:
                        end_j = k
                        matched = True
                        break
            if not matched:
                end_i += 1

        if not matched:
            end_i = len(orig_tokens)
            end_j = len(corr_tokens)

        if i < len(orig_tokens):
            value = " ".join(orig_tokens[i:end_i])
            replacement = " ".join(corr_tokens[j:end_j]) if j < end_j else None
            if value.strip():
                end_pos = start_pos + len(value)
                corrections.append({
                    "span": {
                        "start": start_pos,
                        "end": end_pos,
                        "value": value
                    },
                    "replacements": [
                        {"value": replacement}
                    ]
                })
                pos = end_pos

        i = end_i
        j = end_j
        if i < len(orig_tokens):
            pos += 1

    return corrections, pos