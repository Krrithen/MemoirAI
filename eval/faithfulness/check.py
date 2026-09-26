"""Judge-free faithfulness check: which content words in the story never appear in the transcript?

It also lists the reverse (transcript words missing from the story), since a model can
look faithful by dropping facts. It is lexical and deliberately simple, so it both over- and under-flags:
- a paraphrase ("dad" -> "father") is flagged even though it is faithful;
- an invented fact made only of transcript words is missed.
The list of novel words is printed for each story so a human can read it, and the
rate is only meant for comparing prompts on the same transcripts, not as a truth score.
"""

import re

# Function words and speech fillers; everything else counts as content.
STOPWORDS = set(
    """
    a about above after again against all am an and any are as at be because been before being below between
    both but by can could did do does doing down during each few for from further had has have having he her
    here hers herself him himself his how i if in into is it its itself just me more most my myself no nor not
    now of off on once only or other our ours ourselves out over own same she should so some such than that the
    their theirs them themselves then there these they this those through to too under until up very was we were
    what when where which while who whom why will with would you your yours yourself yourselves
    um uh like yeah okay oh well kind sort basically honestly really actually literally
    s t d ll m re ve didn don doesn isn wasn weren won wouldn couldn shouldn let let's
    """.split()
)

SUFFIXES = ("ingly", "edly", "ing", "ies", "ied", "ed", "es", "ly", "s")


def stem(word: str) -> str:
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            break
    # collapse doubled final consonant from inflection: "spilled" -> "spill" -> "spil"
    if len(word) > 3 and word[-1] == word[-2] and word[-1] not in "aeiou":
        word = word[:-1]
    return word.rstrip("e")


def content_words(text: str) -> list[str]:
    words = re.findall(r"[a-z]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def novel_words(transcript: str, story: str) -> list[str]:
    """Content words in the story whose stem is not in the transcript, in order, deduplicated."""
    source = {stem(w) for w in content_words(transcript)}
    seen, novel = set(), []
    for w in content_words(story):
        s = stem(w)
        if s not in source and s not in seen:
            seen.add(s)
            novel.append(w)
    return novel


def score(transcript: str, story: str) -> dict:
    story_content = content_words(story)
    novel = novel_words(transcript, story)
    novel_tokens = sum(1 for w in story_content if stem(w) in {stem(n) for n in novel})
    return {
        # added: in the story but never said
        "novel_words": novel,
        "novel_rate": novel_tokens / len(story_content) if story_content else 0.0,
        # dropped: said but missing from the story (may be a lost fact, or a removed hedge like "I think")
        "dropped_words": novel_words(story, transcript),
        "length_ratio": len(story.split()) / len(transcript.split()),
    }
