# apps/auth_core/management/commands/export_users.py

import json
import csv
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.auth_core.models import Usuario

User = get_user_model()


class Command(BaseCommand):
    help = 'Export all users from the database to JSON and CSV files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'csv', 'both'],
            default='both',
            help='Output format: json, csv, or both (default: both)'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='/tmp',
            help='Output directory for the files (default: /tmp)'
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        format_type = options['format']
        
        # Get all users
        users = Usuario.objects.all().select_related('cliente')
        
        self.stdout.write(f"Found {users.count()} users in the database")
        
        # Prepare data
        users_data = []
        for user in users:
            user_data = {
                'id': user.id,
                'email': user.email,
                'nombre': user.nombre,
                'apellido': user.apellido,
                'telefono': user.telefono,
                'tipo_usuario': user.tipo_usuario,
                'cliente_id': user.cliente.id if user.cliente else None,
                'cliente_nombre': user.cliente.nombre if user.cliente else None,
                'username': user.username,
                'oauth_provider': user.oauth_provider,
                'oauth_uid': user.oauth_uid,
                'is_active': user.is_active,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
            }
            users_data.append(user_data)

        # Export to JSON
        if format_type in ['json', 'both']:
            json_file = f"{output_dir}/usuarios_export.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, indent=2, ensure_ascii=False)
            self.stdout.write(
                self.style.SUCCESS(f'Users exported to JSON: {json_file}')
            )

        # Export to CSV
        if format_type in ['csv', 'both']:
            csv_file = f"{output_dir}/usuarios_export.csv"
            if users_data:
                with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=users_data[0].keys())
                    writer.writeheader()
                    writer.writerows(users_data)
                self.stdout.write(
                    self.style.SUCCESS(f'Users exported to CSV: {csv_file}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Export completed successfully!')
        )
