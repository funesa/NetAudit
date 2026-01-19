import argparse
from license_manager import lic_manager

def main():
    print("=== NetAudit Key Generator ===")
    customer = input("Nome do Cliente: ").strip()
    if not customer:
        print("Nome obrigatório!")
        return

    try:
        months_str = input("Meses de validade (Padrão 12): ").strip()
        months = int(months_str) if months_str else 12
    except:
        months = 12

    tier = input("Tier (premium/basic) [premium]: ").strip() or "premium"

    print(f"\nGerando chave para: {customer} ({months} meses) - {tier}...")
    
    key = lic_manager.generate_key(customer, months, tier)
    
    print("\n" + "="*60)
    print("LICENÇA GERADA:")
    print("="*60)
    print(key)
    print("="*60)
    print("\nCopie a chave acima e use na tela de ativação (/license).")

if __name__ == "__main__":
    main()
