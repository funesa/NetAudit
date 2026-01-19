"""
Script para criar um pacote ZIP do NetAudit System
Empacota a pasta dist/NetAudit_System em um arquivo ZIP
"""
import os
import shutil
import zipfile
from datetime import datetime

def create_zip_package():
    print("📦 Criando pacote ZIP do NetAudit System...")
    
    # Diretórios
    dist_folder = "dist/NetAudit_System"
    output_zip = "dist/NetAudit_System_Portable.zip"
    
    # Remover ZIP antigo se existir
    if os.path.exists(output_zip):
        os.remove(output_zip)
        print(f"🗑️  Removido ZIP antigo")
    
    # Criar ZIP
    print(f"📁 Compactando {dist_folder}...")
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk(dist_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, "dist")
                zipf.write(file_path, arcname)
                print(f"  ✓ {arcname}")
    
    # Estatísticas
    zip_size = os.path.getsize(output_zip) / (1024 * 1024)  # MB
    print(f"\n✅ Pacote criado com sucesso!")
    print(f"📦 Arquivo: {output_zip}")
    print(f"📊 Tamanho: {zip_size:.2f} MB")
    print(f"⏰ Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

if __name__ == '__main__':
    create_zip_package()
