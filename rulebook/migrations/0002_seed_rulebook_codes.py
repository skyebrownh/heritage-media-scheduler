from django.db import migrations

# RB-3: the codes SPEC.md names. (code, name, table column), in column order.
ROLES = [
    ("propresenter", "ProPresenter", "ProPresenter"),
    ("sound", "Sound", "Sound"),
    ("camera_director", "Camera Director", "Director"),
    ("main_camera_1", "Main Camera 1", "Main 1"),
    ("main_camera_2", "Main Camera 2", "Main 2"),
    ("mobile_camera_3", "Mobile Camera 3", "Mobile 3"),
    ("on_call", "On Call", "On Call"),
]
EVENT_TYPES = [
    ("service", "Service"),
    ("prayer", "Prayer"),
    ("special_event", "Special event"),
]


def seed(apps, schema_editor):
    # get_or_create, so running it twice adds nothing, and a row Skye has already
    # edited keeps her edits.
    MediaRole = apps.get_model("rulebook", "MediaRole")
    Position = apps.get_model("rulebook", "Position")
    EventType = apps.get_model("rulebook", "EventType")

    for order, (code, name, table_column) in enumerate(ROLES, start=1):
        role, _ = MediaRole.objects.get_or_create(
            code=code,
            defaults={"name": name, "table_column": table_column, "display_order": order},
        )
        position, _ = Position.objects.get_or_create(code=code, defaults={"name": name})
        position.roles.add(role)

    shared, _ = Position.objects.get_or_create(
        code="sound_propresenter", defaults={"name": "Sound + ProPresenter"}
    )
    shared.roles.add(*MediaRole.objects.filter(code__in=["sound", "propresenter"]))

    for code, name in EVENT_TYPES:
        EventType.objects.get_or_create(code=code, defaults={"name": name})


class Migration(migrations.Migration):
    dependencies = [("rulebook", "0001_initial")]

    # Reverse does nothing, so a rollback never deletes rows Skye has edited.
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
