import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .optimizer import NoFeasiblePlan
from .routing import RoutingError
from .service import plan_trip



@csrf_exempt
@require_http_methods(["GET", "POST"])
def route_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Body must be valid JSON."}, status=400)
    else:
        data = request.GET
    start, finish = data.get("start"), data.get("finish")
    if not start or not finish:
        return JsonResponse({"error": "Both 'start' and 'finish' are required."}, status=400)
    try:
        return JsonResponse(plan_trip(str(start), str(finish)))
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except NoFeasiblePlan as exc:
        return JsonResponse({"error": str(exc)}, status=422)
    except RoutingError as exc:
        return JsonResponse({"error": str(exc)}, status=502)


def map_page(request):
    return render(request, "planner/map.html")
