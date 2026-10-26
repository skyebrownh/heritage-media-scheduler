"""RB-5, RB-7: plain-Python date helpers shared by every dated rule. No Django imports."""


def nth_in_month(day):
    """RB-5: which occurrence of its weekday a date is in its month (1 to 5).

    Days 1-7 are always the 1st occurrence of their weekday, 8-14 the 2nd, and so on,
    so the weekday itself doesn't matter.
    """
    return (day.day - 1) // 7 + 1


def ranges_overlap(from_a, until_a, from_b, until_b):
    """RB-7: whether two date ranges share a day. Both ends are inclusive.

    An empty (None) `until` means the range never ends.
    """
    a_ends_before_b_starts = until_a is not None and until_a < from_b
    b_ends_before_a_starts = until_b is not None and until_b < from_a
    return not (a_ends_before_b_starts or b_ends_before_a_starts)
