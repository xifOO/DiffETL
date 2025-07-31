from abc import ABC, abstractmethod


class MessageQualityAssessor(ABC):
    def __init__(self): ...

    @abstractmethod
    def is_message_valid(self): ...

    @abstractmethod
    def is_diff_valid(self): ...