import math


LEGACY_CLASSES = {
    "forklift_loaded",
    "forklift_empty",
    "troli_loaded",
    "troli_empty",
}


def normalize_class_name(name):
    """Normalize model class names without changing the legacy output contract."""
    name = str(name or "").strip().lower()
    name = name.replace("empety", "empty")
    name = name.replace("trolley", "troli")
    return name


def _area(box):
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _intersection(a, b):
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _center(box):
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def _contains(box, point):
    return (
        box[0] <= point[0] <= box[2]
        and box[1] <= point[1] <= box[3]
    )


def _expanded_vehicle_box(vehicle_box, expand_x, expand_top, expand_bottom):
    x1, y1, x2, y2 = vehicle_box
    width = max(1.0, x2 - x1)
    height = max(1.0, y2 - y1)

    return (
        x1 - (width * expand_x),
        y1 - (height * expand_top),
        x2 + (width * expand_x),
        y2 + (height * expand_bottom),
    )


def _association_score(
    vehicle_box,
    object_box,
    expand_x,
    expand_top,
    expand_bottom,
    min_object_overlap,
):
    """Return None when an object is not spatially related to a vehicle."""
    expanded = _expanded_vehicle_box(
        vehicle_box,
        expand_x,
        expand_top,
        expand_bottom,
    )

    object_center = _center(object_box)
    object_area = max(1.0, _area(object_box))
    overlap_ratio = _intersection(vehicle_box, object_box) / object_area

    center_in_vehicle = _contains(vehicle_box, object_center)
    center_in_expanded = _contains(expanded, object_center)

    if not center_in_expanded and overlap_ratio < min_object_overlap:
        return None

    vehicle_center = _center(vehicle_box)
    dx = object_center[0] - vehicle_center[0]
    dy = object_center[1] - vehicle_center[1]
    distance = math.hypot(dx, dy)

    vehicle_w = max(1.0, vehicle_box[2] - vehicle_box[0])
    vehicle_h = max(1.0, vehicle_box[3] - vehicle_box[1])
    diagonal = max(1.0, math.hypot(vehicle_w, vehicle_h))
    normalized_distance = distance / diagonal

    score = overlap_ratio

    if center_in_vehicle:
        score += 1.0
    elif center_in_expanded:
        score += 0.55

    score += max(0.0, 0.35 - (normalized_distance * 0.20))
    return score


def adapt_best4_detections(
    detections,
    min_vehicle_conf=0.35,
    min_object_conf=0.35,
    expand_x=0.25,
    expand_top=0.35,
    expand_bottom=0.15,
    min_object_overlap=0.10,
):
    """
    Convert best4 classes:
        forklift, trolley/troli, object

    into the legacy BarrierGateAI contract:
        forklift_loaded, forklift_empty,
        troli_loaded, troli_empty

    Rule:
    - forklift/trolley is the primary vehicle detection.
    - object is treated as load only when spatially associated with a vehicle.
    - one object is assigned only to the best matching vehicle.
    - vehicle without associated object becomes *_empty.
    - vehicle with one or more associated objects becomes *_loaded.

    If the input already contains legacy classes, they are returned normalized.
    This keeps old models compatible with the same code path.
    """
    if not detections:
        return []

    normalized = []
    legacy_found = False

    for obj in detections:
        item = dict(obj)
        item["name"] = normalize_class_name(item.get("name", ""))
        normalized.append(item)

        if item["name"] in LEGACY_CLASSES:
            legacy_found = True

    if legacy_found:
        return [
            item
            for item in normalized
            if item["name"] in LEGACY_CLASSES
        ]

    vehicles = []
    cargo_objects = []

    for item in normalized:
        name = item["name"]
        confidence = float(item.get("confidence", 0.0))

        if name in {"forklift", "troli"} and confidence >= min_vehicle_conf:
            vehicles.append(item)
        elif name == "object" and confidence >= min_object_conf:
            cargo_objects.append(item)

    if not vehicles:
        return []

    assignments = {index: [] for index in range(len(vehicles))}

    for cargo in cargo_objects:
        object_box = (
            float(cargo["x1"]),
            float(cargo["y1"]),
            float(cargo["x2"]),
            float(cargo["y2"]),
        )

        best_vehicle_index = None
        best_score = None

        for index, vehicle in enumerate(vehicles):
            vehicle_box = (
                float(vehicle["x1"]),
                float(vehicle["y1"]),
                float(vehicle["x2"]),
                float(vehicle["y2"]),
            )

            score = _association_score(
                vehicle_box,
                object_box,
                expand_x,
                expand_top,
                expand_bottom,
                min_object_overlap,
            )

            if score is None:
                continue

            if best_score is None or score > best_score:
                best_score = score
                best_vehicle_index = index

        if best_vehicle_index is not None:
            assignments[best_vehicle_index].append(cargo)

    derived = []

    for index, vehicle in enumerate(vehicles):
        vehicle_type = vehicle["name"]
        vehicle_conf = float(vehicle.get("confidence", 0.0))
        associated = assignments[index]

        item = dict(vehicle)

        if associated:
            best_object_conf = max(
                float(obj.get("confidence", 0.0))
                for obj in associated
            )

            # Geometric mean keeps the result conservative while avoiding
            # over-penalizing one moderately lower component confidence.
            derived_conf = math.sqrt(
                max(0.0, vehicle_conf) * max(0.0, best_object_conf)
            )

            item["name"] = f"{vehicle_type}_loaded"
            item["confidence"] = derived_conf
            item["vehicle_confidence"] = vehicle_conf
            item["object_confidence"] = best_object_conf
            item["associated_object_count"] = len(associated)
            item["load_inference"] = "spatial_association"
        else:
            item["name"] = f"{vehicle_type}_empty"
            item["confidence"] = vehicle_conf
            item["vehicle_confidence"] = vehicle_conf
            item["object_confidence"] = None
            item["associated_object_count"] = 0
            item["load_inference"] = "no_associated_object"

        derived.append(item)

    return derived
