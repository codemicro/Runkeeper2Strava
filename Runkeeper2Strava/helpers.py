import datetime

known_activities = {
    "cycling": "ride",
    "walking": "walk",
    "running": "run"
}


def time_to_iso(old_time: str) -> str:

    """
    Convert DD/MM/YYYY  HH:MM to ISO 8601 format
    13/04/2020 15:33:38
    """

    old_time = " ".join(old_time.split())  # replace multiple spaces with one in any location
    dt = datetime.datetime.strptime(old_time, "%d/%m/%Y %H:%M:%S")
    return dt.replace(microsecond=0).isoformat()


def miles_to_meters(miles: float) -> float:  # type hints hell yea

    """ Get meters from miles """

    val = miles * 1.60934
    val *= 1000
    return val


def convert_activity_type(act: str) -> str:

    """ Convert activity name from Runkeeper style to Strava style """

    return known_activities[act.lower()]


def duration_to_seconds(dur: str) -> int:

    """ Convert HH:MM:SS to seconds """

    h, m, s = 0, 0, 0

    split_duration = dur.split(":")
    num_elems = len(split_duration)

    if num_elems == 1:
        # Only seconds
        s = split_duration
    elif num_elems == 2:
        # Minutes, seconds
        m, s = split_duration
    else:
        # Hours, minutes, seconds
        h, m, s = split_duration

    return int(h) * 3600 + int(m) * 60 + int(s)
