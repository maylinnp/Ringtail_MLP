# this file will hold what is needed to flexibly build sqlite queries
# # (at least one will hope that is the final outcome)


class Filters(list):
    def add(
        self,
        column: str,
        operator: str,
        value: str | None | float | int | iter,
    ):
        return self.append({"column": column, "operator": operator, "value": value})

    def evaluate_range(cls, min=None | float, max=None | float):

        if min is not None and max is not None:
            range_filter = {"operator": "BETWEEN", "value": [min, max]}
        elif min is not None and max is None:
            range_filter = {"operator": ">=", "value": min}
        elif min is None and max is not None:
            range_filter = {"operator": "=<", "value": max}
        else:
            range_filter = None

        return range_filter


class QueryData(object):
    # class that holds any values
    def __init__(self):
        self.numerical = FilterQueryData()
        self.interactions = FilterQueryData()
        self.ligand = FilterQueryData()


class FilterQueryData(object):
    def __init__(self):
        self.combine = "AND"


class QueryBuilder:
    """
    I would like this to:
        take filters, organize them to useful sql dictionaries
        if one or more filters are used, pop them off, return a new item to be included in the filter (i.e., the prefiltered results)

    """

    def __init__(self):
        print(
            "I am the query builder class, use my methods and pass me arguments, and I will make nice sql!"
        )

    def filter_query(self, **kvargs):
        # method that can take any number of key value pairs to use as filter value.
        organizing_dict = {
            "numerical": ["eworst", "ebest", "ligand_efficiency"],
            "interactions": ["interaction_id"],
            "ligand": ["smarts", "smarts_loc"],
        }
        # # structure may be nested
        # filter_data = QueryData()

        # filter_data.numerical = FilterQueryData()
        # filter_data.interactions = FilterQueryData()
        # filter_data.ligand = FilterQueryData()

        filter_data = {"numerical": {}, "interactions": {}, "ligand": {}}

        for k, v in kvargs.items():
            if k in organizing_dict["numerical"]:
                filter = {
                    "name": k,
                    "value": v,
                }
                filter_data["numerical"][k] = v
                # setattr(filter_data.numerical, k, v)
            if k in organizing_dict["interactions"]:
                setattr(filter_data.interactions, k, v)
            if k in organizing_dict["ligand"]:
                setattr(filter_data.ligand, k, v)
            print(f"Filter {k} of value {v} has been recorded")
        return filter_data

    def write_query(self, filters: FilterQueryData):
        # it is more important HOW I build the queries rather than making something uber multi level complex
        # run num filter
        numfilters = filters.__dict__.pop("numerical")
        print("Numerical filters:", numfilters.__dict__)


query = QueryBuilder()
filter_data = query.filter_query(
    eworst={"value": 1},
    interaction_id={"value": ["C", "Y", "AH"]},
    smarts={
        "value": [
            "hi",
            "you",
            "today",
            "is",
        ],
        "combine": "OR",
    },
)
query.write_query(filter_data)
