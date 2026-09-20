"""Four-valued support: conflict blocks unconditional downstream affirmation.

First compute the signed least fixed point. Then retain its conflict set as
blocked premises while recomputing usable paths. This is conservative when a
conflict itself depends on another conflict and cannot oscillate/self-certify.
"""


def project(nodes, revoked=()):
    revoked = set(revoked)

    def closure(blocked):
        positive, negative = set(), set()
        for key, node in nodes.items():
            if key not in revoked:
                if node.get("positive_witness"):
                    positive.add(key)
                if node.get("negative_witness"):
                    negative.add(key)
        while True:
            before = (len(positive), len(negative))
            for key, node in nodes.items():
                if key in revoked:
                    continue
                for polarity, target in (("positive", positive), ("negative", negative)):
                    if any(group and all(p in positive and p not in blocked for p in group)
                           for group in node.get(polarity + "_supports", [])):
                        target.add(key)
            if before == (len(positive), len(negative)):
                return positive, negative

    raw_positive, raw_negative = closure(set())
    conflicts = raw_positive & raw_negative
    positive, negative = closure(conflicts)
    return {key: {"status": "conflict" if key in conflicts else "positive" if key in positive else
                  "negative" if key in negative else "neither", "usable_positive": key in positive and key not in conflicts,
                  "positive_supported": key in raw_positive, "negative_supported": key in raw_negative,
                  "blocked_paths": [g for g in node.get("positive_supports", []) if set(g) & conflicts],
                  "revoked": key in revoked} for key, node in nodes.items()}
