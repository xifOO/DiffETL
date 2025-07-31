from collections import defaultdict
from typing import Any, Callable, Dict, List

from diffetl.transform.commit import CommitElement


class CommitGroup(defaultdict):

    def __init__(self):
        super().__init__(list)

    def add_all(self, elements: Dict[str, CommitElement]) -> 'CommitGroup':
        self["all"] = list(elements.values())
        return self
    
    def by_author(self, elements: Dict[str, CommitElement]) -> 'CommitGroup':
        self.clear()
        for ce in elements.values():
            key = ce.commit.author.name
            self[key].append(ce)
        return self

    def filter(self, predicate: Callable[[CommitElement], bool]) -> 'CommitGroup':
        new_group = CommitGroup()
        for key, items in self.items():
            new_group[key] = [ce for ce in items if predicate(ce)]
        return new_group
    
    def map(self, func: Callable[[List[CommitElement]], Any]) -> Dict[str, Any]:
        return {key: func(items) for key, items in self.items()}

    def count(self) -> Dict[str, int]:
        return {key: len(items) for key, items in self.items()}
    
    def flatten(self) -> List[CommitElement]:
        seen = set()
        result = []
        for items in self.values():
            for ce in items:
                if ce.hexsha not in seen:
                    seen.add(ce.hexsha)
                    result.append(ce)
        return result

