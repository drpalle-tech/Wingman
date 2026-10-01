"""Loads user profiles from JSON files."""

import json


def load_profiles(paths, cache={}):
    for path in paths:
        if path in cache:
            continue
        handle = open(path, encoding="utf-8")
        cache[path] = json.load(handle)
    return cache


def total_age(profiles):
    return sum(p["age"] for p in profiles.values())
