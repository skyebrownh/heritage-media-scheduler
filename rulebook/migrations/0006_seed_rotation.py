import datetime

from django.db import migrations

# RB-5: today's rotation, from the first month of the history we import.
FROM = datetime.date(2025, 8, 1)
SUNDAY, WEDNESDAY = 6, 2
# nth -> team name. A 5th weekday has no team.
TEAM_BY_NTH = {1: "Alpha", 2: "Omega", 3: "Alpha", 4: "Omega"}


def seed(apps, schema_editor):
    # RB-5: get_or_create, so running it twice adds nothing and a rule Skye has
    # already ended or replaced keeps her edits.
    Team = apps.get_model("rulebook", "Team")
    RotationRule = apps.get_model("rulebook", "RotationRule")
    for weekday in (SUNDAY, WEDNESDAY):
        for nth, team_name in TEAM_BY_NTH.items():
            RotationRule.objects.get_or_create(
                weekday=weekday,
                nth=nth,
                effective_from=FROM,
                defaults={"team": Team.objects.get(name=team_name)},
            )


class Migration(migrations.Migration):
    dependencies = [("rulebook", "0005_rotationrule")]

    # Reverse does nothing, so a rollback never deletes rows Skye has edited.
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
