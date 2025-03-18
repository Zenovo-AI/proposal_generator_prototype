from fuzzywuzzy import fuzz
from fuzzywuzzy import process

def find_best_match(text, choices, threshold=80):
    """
    Finds the best matching phrase in `choices` from `text` using fuzzy matching.
    Returns the best match if it meets the threshold, otherwise None.
    """
    best_match = process.extractOne(text, choices, scorer=fuzz.partial_ratio)
    if best_match and best_match[1] >= threshold:
        return best_match[0]  # Return the actual best-matched phrase
    return None

def extract_relevant_content(text):
    """
    Extracts the relevant portion of the proposal dynamically using fuzzy matching.
    """
    start_phrase = "Proposal for Borehole Drilling and Rehabilitation Services"
    end_phrase = "Please let us know if there are any further details required or adjustments needed to this proposal."

    # Use fuzzy matching to find the closest match
    text_lines = text.split("\n")
    start_match = process.extractOne(start_phrase, text_lines, scorer=fuzz.partial_ratio)
    end_match = process.extractOne(end_phrase, text_lines, scorer=fuzz.partial_ratio)

    if start_match and start_match[1] > 80:  # Confidence threshold
        start_index = text_lines.index(start_match[0])
    else:
        raise ValueError(f"Start phrase not found. Closest match: {start_match}")

    if end_match and end_match[1] > 80:  # Confidence threshold
        end_index = text_lines.index(end_match[0])
    else:
        raise ValueError(f"End phrase not found. Closest match: {end_match}")

    # Extract and return the relevant portion
    relevant_content = "\n".join(text_lines[start_index:end_index + 1])
    return relevant_content