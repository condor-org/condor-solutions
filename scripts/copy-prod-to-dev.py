#!/usr/bin/env python3

"""
Script para copiar variables y secrets de PROD a DEV
Uso: python3 scripts/copy-prod-to-dev.py
"""

import os
import sys
import json
import requests
from typing import Dict, List

def get_github_token() -> str:
    """Obtener token de GitHub desde variable de entorno"""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("❌ Necesitas configurar GITHUB_TOKEN")
        print("   export GITHUB_TOKEN=tu_token_aqui")
        sys.exit(1)
    return token

def get_repo_name() -> str:
    """Obtener nombre del repositorio"""
    try:
        import subprocess
        result = subprocess.run(['git', 'config', '--get', 'remote.origin.url'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            url = result.stdout.strip()
            # Extraer nombre del repo de la URL
            if 'github.com' in url:
                return url.split('github.com/')[-1].replace('.git', '')
    except:
        pass
    
    # Fallback: pedir al usuario
    repo = input("📁 Ingresa el nombre del repositorio (owner/repo): ")
    return repo

def create_environment(token: str, repo: str, env_name: str) -> bool:
    """Crear environment si no existe"""
    url = f"https://api.github.com/repos/{repo}/environments/{env_name}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.put(url, headers=headers, json={"protection_rules": []})
    return response.status_code in [200, 201, 422]  # 422 = ya existe

def get_variables(token: str, repo: str, env_name: str) -> List[Dict]:
    """Obtener variables de un environment"""
    url = f"https://api.github.com/repos/{repo}/environments/{env_name}/variables"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('variables', [])
    return []

def get_secrets(token: str, repo: str, env_name: str) -> List[Dict]:
    """Obtener secrets de un environment"""
    url = f"https://api.github.com/repos/{repo}/environments/{env_name}/secrets"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get('secrets', [])
    return []

def create_variable(token: str, repo: str, env_name: str, name: str, value: str) -> bool:
    """Crear variable en un environment"""
    url = f"https://api.github.com/repos/{repo}/environments/{env_name}/variables"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    data = {"name": name, "value": value}
    response = requests.post(url, headers=headers, json=data)
    return response.status_code in [200, 201]

def main():
    print("🚀 Copiando configuración de PROD a DEV...")
    
    # Obtener token y repo
    token = get_github_token()
    repo = get_repo_name()
    print(f"📁 Repositorio: {repo}")
    
    # Crear environment DEV si no existe
    print("🔧 Creando environment DEV si no existe...")
    if create_environment(token, repo, "dev"):
        print("  ✅ Environment DEV creado/verificado")
    else:
        print("  ❌ Error creando environment DEV")
        sys.exit(1)
    
    # Obtener variables de PROD
    print("📋 Obteniendo variables de PROD...")
    prod_vars = get_variables(token, repo, "prod")
    print(f"  📝 Encontradas {len(prod_vars)} variables")
    
    # Copiar variables a DEV
    print("📋 Copiando variables a DEV...")
    for var in prod_vars:
        name = var['name']
        value = var['value']
        print(f"  📝 Copiando variable: {name}")
        if create_variable(token, repo, "dev", name, value):
            print(f"    ✅ {name}")
        else:
            print(f"    ❌ Error copiando {name}")
    
    # Listar secrets de PROD
    print("🔐 Secrets encontrados en PROD:")
    prod_secrets = get_secrets(token, repo, "prod")
    for secret in prod_secrets:
        print(f"  🔑 {secret['name']}")
    
    print("")
    print("⚠️  IMPORTANTE: Los secrets no se pueden copiar automáticamente.")
    print("   Necesitas copiarlos manualmente desde GitHub:")
    print("   1. Ve a Settings > Environments > prod")
    print("   2. Copia cada secret")
    print("   3. Ve a Settings > Environments > dev")
    print("   4. Pega cada secret")
    print("")
    print("✅ Variables copiadas exitosamente de PROD a DEV")
    print("🔐 Recuerda copiar los secrets manualmente")

if __name__ == "__main__":
    main()
