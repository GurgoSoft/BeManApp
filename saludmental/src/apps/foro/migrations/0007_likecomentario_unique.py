from django.db import migrations, models
from django.db.models import Count


def dedupe_likecomentario(apps, schema_editor):
    LikeComentario = apps.get_model('foro', 'LikeComentario')
    # Buscar duplicados por (usuario, comentario)
    duplicates = (
        LikeComentario.objects
        .values('usuario_id', 'comentario_id')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
    )
    for dup in duplicates:
        qs = (LikeComentario.objects
              .filter(usuario_id=dup['usuario_id'], comentario_id=dup['comentario_id'])
              .order_by('id'))
        # conservar el primero y borrar el resto
        qs.exclude(id=qs.first().id).delete()


def reverse_dedupe(apps, schema_editor):
    # No se recrean duplicados
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('foro', '0006_historia_oculto'),
    ]

    operations = [
        migrations.RunPython(dedupe_likecomentario, reverse_dedupe),
        migrations.AlterUniqueTogether(
            name='likecomentario',
            unique_together={('usuario', 'comentario')},
        ),
    ]
