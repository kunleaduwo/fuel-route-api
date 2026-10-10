from dataclasses import dataclass



class NoFeasiblePlan(Exception):
    pass

@dataclass
class Stop:
    index: int          # index into the candidate list passed in
    mile: float         # miles from the start of the route
    price: float        # $/gallon
    miles_bought: float  # driving range purchased at this stop


def plan_fuel_stops(stations, total_miles, range_miles=500.0, min_saving=0.03):
    nodes = [(0.0, 0.0, -1)] + [(m, p, i) for i, (m, p) in enumerate(stations)] + [(total_miles, -1.0, -2)]
    last = len(nodes) - 1
    cur, fuel, stops = 0, 0.0, []

    while cur != last:
        cur_mile, cur_price, _ = nodes[cur]
        in_range = []
        j = cur + 1
        while j <= last and nodes[j][0] - cur_mile <= range_miles + 1e-9:
            in_range.append(j)
            j += 1
        if not in_range:
            raise NoFeasiblePlan(f"No fuel station within {range_miles:.0f} miles after mile {cur_mile:.0f}.")

        nxt = next((j for j in in_range if nodes[j][1] < cur_price - min_saving), None)
        if nxt is not None:
            buy = max(0.0, (nodes[nxt][0] - cur_mile) - fuel)      # just enough to reach the cheaper stop
        else:
            buy = range_miles - fuel                               # nothing cheaper ahead: fill up
            cheapest = min(nodes[j][1] for j in in_range)
            # among stations within `min_saving` of the cheapest, go to the farthest one (fewer stops)
            nxt = max((j for j in in_range if nodes[j][1] <= cheapest + min_saving), key=lambda j: nodes[j][0])
        if buy > 1e-9 and nodes[cur][2] >= 0:
            stops.append(Stop(nodes[cur][2], cur_mile, cur_price, buy))
        fuel += buy - (nodes[nxt][0] - cur_mile)
        cur = nxt
    return stops
