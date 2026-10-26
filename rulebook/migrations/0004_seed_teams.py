from django.db import migrations

# RB-4: today's teams. (name, rotates), in display order.
TEAMS = [
    ("Alpha", True),
    ("Omega", True),
    ("Wildcards", False),
    ("New Members", False),
]


def seed(apps, schema_editor):
    # RB-4: get_or_create, so running it twice adds nothing and a team Skye has
    # already edited keeps her edits.
    Team = apps.get_model("rulebook", "Team")
    for order, (name, rotates) in enumerate(TEAMS, start=1):
        Team.objects.get_or_create(
            name=name, defaults={"rotates": rotates, "display_order": order}
        )


class Migration(migrations.Migration):
    dependencies = [("rulebook", "0003_team")]

    # Reverse does nothing, so a rollback never deletes rows Skye has edited.
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
