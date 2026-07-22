"""Fuzzy dedup через hash-based blocking + word fingerprints"""
import re
from typing import Dict, Set
from collections import defaultdict, deque

try:
    from rapidfuzz import fuzz
except ImportError:
    from difflib import SequenceMatcher as _SM
    class fuzz:
        @staticmethod
        def token_sort_ratio(a, b):
            return int(_SM(None, a, b).ratio() * 100)

class FuzzyDedup:
    MAX_BLOCK_SIZE = 100
    MAX_FINGERPRINTS = 100000
    
    def __init__(self, threshold: float = 0.92):
        self.threshold = threshold * 100
        self.blocks: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.MAX_BLOCK_SIZE))
        self.fingerprints_set: Set[str] = set()
        self.fingerprints_fifo: deque = deque(maxlen=self.MAX_FINGERPRINTS)
        self._overflow_count = 0
    
    def _block_key(self, name: str) -> str:
        letters = re.sub(r'[^A-ZА-ЯЁ]', '', name.upper())
        if len(letters) >= 6:
            return f"{letters[:3]}_{letters[-3:]}"
        return letters
    
    def _fingerprint(self, name: str) -> str:
        words = sorted(name.upper().split())
        return "|".join(words)
    
    def is_duplicate(self, name: str) -> bool:
        fg = self._fingerprint(name)
        if fg in self.fingerprints_set:
            return True
        
        key = self._block_key(name)
        block = self.blocks[key]
        
        if len(block) == self.MAX_BLOCK_SIZE:
            self._overflow_count += 1
        
        for existing in block:
            if fuzz.token_sort_ratio(name, existing) > self.threshold:
                return True
        
        block.append(name)
        
        if len(self.fingerprints_fifo) == self.MAX_FINGERPRINTS:
            oldest = self.fingerprints_fifo[0]
            self.fingerprints_set.discard(oldest)
        
        self.fingerprints_fifo.append(fg)
        self.fingerprints_set.add(fg)
        return False
    
    def get_stats(self) -> dict:
        sizes = [len(b) for b in self.blocks.values()]
        return {
            "total_blocks": len(self.blocks),
            "max_block_size": max(sizes) if sizes else 0,
            "overflow_count": self._overflow_count,
            "fingerprints_count": len(self.fingerprints_set),
        }
