#!/usr/bin/env python3
"""
Script to export all users from production database
Run this script on the production server
"""

import os
import sys
import django
import json
import csv
from datetime import datetime

# Add the project root to Python path
sys.path.append('/app/backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'condor_core.settings.prod')
django.setup()

from apps.auth_core.models import Usuario


def export_users():
    """Export all users to JSON and CSV files"""
    
    # Get all users with related cliente data
    users = Usuario.objects.all().select_related('cliente')
    
    print(f"Found {users.count()} users in the database")
    
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

    # Create timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Export to JSON
    json_file = f"/tmp/usuarios_export_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, indent=2, ensure_ascii=False)
    print(f'Users exported to JSON: {json_file}')

    # Export to CSV
    csv_file = f"/tmp/usuarios_export_{timestamp}.csv"
    if users_data:
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=users_data[0].keys())
            writer.writeheader()
            writer.writerows(users_data)
        print(f'Users exported to CSV: {csv_file}')

    print(f'Export completed successfully!')
    print(f'Files created:')
    print(f'  - {json_file}')
    print(f'  - {csv_file}')
    
    return json_file, csv_file


if __name__ == '__main__':
    export_users()
