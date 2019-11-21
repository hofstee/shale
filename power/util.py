from itertools import islice

def window(seq, n=2):
    "Returns a sliding window (of width n) over data from the iterable"
    "   s -> (s0,s1,...s[n-1]), (s1,s2,...,sn), ...                   "
    it = iter(seq)
    result = tuple(islice(it, n))
    if len(result) == n:
        yield result
    for elem in it:
        result = result[1:] + (elem,)
        yield result


def filter_ancestors(df):
    df = df.copy()

    # We can take advantage of the structure of our data. Our data has
    # two fields, `id` and `last`, which form the inclusive range of
    # the subtree with `id` as its root. This means that a parent must
    # have a lower `id` than its children, so we can sort the list to
    # traverse the tree using DFS.
    df.sort_values(by=["id"], inplace=True)

    last = 0
    indices_to_drop = []
    for index, row in df.sort_values(by=["id"]).itertuples():
        if row["id"] < last:
            indices_to_drop.append(index)

    return df.drop(indices_to_drop)


def get_labels(s):
    """
    e.g.
    '''
                      Total
          Hierarchy   Power
    '''

    will become

    ["Hierarchy", "Total Power"]
    """
    lines = list(filter(lambda x: len(x) > 0, s.split("\n")))
    line_length = max([len(line) for line in lines])

    # split into chunks divided when all lines have spaces
    intervals = []
    for col in range(line_length):
        all_spaces = all(line[col:col+1] in (" ", "") for line in lines)
        if all_spaces: continue

        intervals.append(col)

    # collapse consecutive numbers into just the first one
    last = 0
    slices = []
    for pos in intervals:
        if pos != last+1:
            slices.append(pos)
        last = pos
    slices.append(line_length)

    # iterate through pairs of the intervals and slice the lines by that
    labels = []
    for beg,end in window(slices, 2):
        temp = filter(lambda x: len(x) > 0, (line[beg:end].strip() for line in lines))
        labels.append(" ".join(temp))

    return labels
